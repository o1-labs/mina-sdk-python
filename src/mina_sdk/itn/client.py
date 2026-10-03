"""Client for the daemon's ITN GraphQL server.

A daemon started with ``ITN_FEATURES=1``, ``--itn-graphql-port <port>`` and
``--itn-keys <base64 ed25519 public keys>`` serves a second GraphQL API
(``Mina_graphql.schema_itn``). Load testing tools use it to schedule payments
and zkApp commands, read internal logs, change connection gating and stop the
daemon. Every request must be signed with an ed25519 key whose public half is
in ``--itn-keys``.

Authentication protocol (see ``spec/ITN.md``): the daemon reads the
``Authorization`` header.

- ``Signature <pk> <sig>``: the signature covers the request body. The daemon
  accepts this form for the ``Auth`` operation only.
- ``Signature <pk> <sig> ; Sequencing <uuid> <n>``: the signature covers the
  big-endian u16 ``n``, then the server UUID, then the body. ``n`` must be
  exactly the daemon's sequence number for this public key, which starts at
  0, goes up by one (wrapping) after each accepted sequenced request, and is
  shared by all clients that sign with the same key.

A bad signature or an unknown key gives HTTP 401; a wrong UUID (the daemon
restarted) or sequence number gives HTTP 412. ``ItnClient`` runs auth to learn
the UUID and the sequence number, sends sequenced requests one at a time, and
on a 412 runs auth again and repeats the request once. It never repeats a
sequenced request after a transport error, because the daemon may have run it.
"""

from __future__ import annotations

import json
import logging
import struct
import threading
import time
from typing import Any

import httpx

from mina_sdk.daemon.client import DaemonConnectionError, GraphQLError
from mina_sdk.itn import queries
from mina_sdk.itn.errors import ItnHttpError, ItnSequencingError, ItnUnauthorizedError
from mina_sdk.itn.key import ItnKey
from mina_sdk.itn.types import (
    CreateAccountsDetails,
    CreatedAccount,
    CreatedAccounts,
    GatingUpdate,
    ItnAuth,
    ItnLog,
    LogMetadatum,
    PaymentsDetails,
    ZkappCommandsDetails,
)

logger = logging.getLogger(__name__)


class ItnClient:
    """Client for one daemon's ITN GraphQL server.

    It is safe to use from several threads; share one client per daemon,
    because it holds the daemon's session.

    Args:
        graphql_uri: The ITN endpoint, for example ``http://127.0.0.1:3086/graphql``.
        key: The key whose public half is in the daemon's ``--itn-keys``.
        retries: Number of attempts of the auth handshake (must be >= 1).
            Sequenced requests are never repeated after a transport error.
        retry_delay: Seconds between auth attempts.
        timeout: HTTP request timeout in seconds.

    Example::

        key = ItnKey.from_base64(open("itn_sk").read())
        with ItnClient("http://127.0.0.1:3086/graphql", key) as itn:
            logs = itn.internal_logs(0)
    """

    def __init__(
        self,
        graphql_uri: str,
        key: ItnKey,
        retries: int = 3,
        retry_delay: float = 5.0,
        timeout: float = 30.0,
    ):
        if not graphql_uri:
            raise ValueError("graphql_uri must not be empty")
        if retries < 1:
            raise ValueError(f"retries must be >= 1, got {retries}")
        if retry_delay < 0:
            raise ValueError(f"retry_delay must be >= 0, got {retry_delay}")
        if timeout <= 0:
            raise ValueError(f"timeout must be > 0, got {timeout}")
        self._uri = graphql_uri
        self._key = key
        self._retries = retries
        self._retry_delay = retry_delay
        self._client = httpx.Client(timeout=timeout)
        # Serializes requests: the daemon accepts only its exact next number.
        self._lock = threading.Lock()
        # Server UUID and the next sequence number of the key; None until the
        # first handshake and after an error that leaves it unknown.
        self._session: tuple[str, int] | None = None
        self._last_auth: ItnAuth | None = None

    @property
    def graphql_uri(self) -> str:
        return self._uri

    def public_key_base64(self) -> str:
        """The client key's public half, as it must appear in ``--itn-keys``."""
        return self._key.public_key_base64()

    def close(self) -> None:
        """Release resources held by the HTTP client."""
        self._client.close()

    def __enter__(self) -> ItnClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @property
    def last_auth(self) -> ItnAuth | None:
        """The answer of the latest auth handshake, or ``None`` before the first
        one. The client runs auth again by itself after a daemon restart (HTTP
        412), so a caller that keeps the node's peer ID or libp2p port can
        refresh them from here after a request."""
        return self._last_auth

    # -- Transport --

    def _post(self, body: bytes, authorization: str) -> httpx.Response:
        return self._client.post(
            self._uri,
            content=body,
            headers={"Content-Type": "application/json", "Authorization": authorization},
        )

    @staticmethod
    def _decode(resp: httpx.Response, query_name: str) -> dict[str, Any]:
        try:
            parsed = resp.json()
        except ValueError as e:
            raise DaemonConnectionError(f"Invalid JSON response from {query_name}: {e}") from e
        if parsed.get("errors"):
            raise GraphQLError(parsed["errors"], query_name)
        return parsed.get("data") or {}

    def _handshake(self) -> ItnAuth:
        """Run auth with an unsequenced signature and store the session. The
        caller holds the lock."""
        name = "itn_auth"
        body = json.dumps({"query": queries.AUTH}).encode()
        authorization = f"Signature {self._key.public_key_base64()} {self._key.sign_base64(body)}"
        last_error: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                resp = self._post(body, authorization)
            except httpx.HTTPError as e:
                last_error = e
                logger.warning("ITN auth error (attempt %d/%d): %s", attempt, self._retries, e)
            else:
                if resp.status_code == 401:
                    raise ItnUnauthorizedError(name)
                if resp.status_code >= 300:
                    last_error = ItnHttpError(resp.status_code, resp.text)
                else:
                    auth = _parse_auth(self._decode(resp, name))
                    self._session = (auth.server_uuid, auth.signer_sequence_number)
                    self._last_auth = auth
                    return auth
            if attempt < self._retries:
                time.sleep(self._retry_delay)
        raise DaemonConnectionError(
            f"Failed to execute {name} after {self._retries} attempts: {last_error}"
        ) from last_error

    def execute_query(
        self, query: str, variables: dict[str, Any] | None = None, query_name: str = "itn_custom"
    ) -> dict[str, Any]:
        """Send one sequenced, signed request and return its ``data`` field.

        Raises:
            GraphQLError: The response has GraphQL errors.
            ItnUnauthorizedError: HTTP 401.
            ItnSequencingError: HTTP 412 again after a new auth.
            DaemonConnectionError: A transport error or another HTTP error status
                (its ``__cause__`` is an ``ItnHttpError``). It is not repeated.
        """
        payload: dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables
        body = json.dumps(payload).encode()

        with self._lock:
            # A second pass only follows a 412: the daemon restarted, or another
            # client with the same key used our sequence number.
            for _ in range(2):
                if self._session is None:
                    auth = self._handshake()
                    uuid, seq = auth.server_uuid, auth.signer_sequence_number
                else:
                    uuid, seq = self._session
                message = struct.pack(">H", seq) + uuid.encode() + body
                authorization = (
                    f"Signature {self._key.public_key_base64()} "
                    f"{self._key.sign_base64(message)} ; Sequencing {uuid} {seq}"
                )
                try:
                    resp = self._post(body, authorization)
                except httpx.HTTPError as e:
                    # Unknown whether the daemon counted it: start over next time.
                    self._session = None
                    raise DaemonConnectionError(f"Failed to execute {query_name}: {e}") from e
                if resp.status_code == 412:
                    self._session = None
                    continue
                if resp.status_code == 401:
                    raise ItnUnauthorizedError(query_name)
                if resp.status_code >= 300:
                    self._session = None
                    error = ItnHttpError(resp.status_code, resp.text)
                    raise DaemonConnectionError(
                        f"Failed to execute {query_name}: {error}"
                    ) from error
                # The signature was accepted, so the daemon has moved to the next
                # number, whatever the GraphQL result is.
                self._session = (uuid, (seq + 1) % 65536)
                return self._decode(resp, query_name)
            raise ItnSequencingError(query_name)

    # -- Operations --

    def auth(self) -> ItnAuth:
        """Run the auth handshake and return the node's answer. Other methods
        run it when needed, so calling it first is optional."""
        with self._lock:
            return self._handshake()

    def slots_won(self) -> list[int]:
        """The global slots the node's block producer keys won in the current epoch."""
        data = self.execute_query(queries.SLOTS_WON, None, "itn_slots_won")
        return [int(s) for s in data["slotsWon"]]

    def internal_logs(self, start_log_id: int) -> list[ItnLog]:
        """The internal logs with an ID of at least ``start_log_id``."""
        data = self.execute_query(
            queries.INTERNAL_LOGS, {"startLogId": start_log_id}, "itn_internal_logs"
        )
        return [
            ItnLog(
                id=int(log["id"]),
                timestamp=log["timestamp"],
                message=log["message"],
                metadata=[LogMetadatum(item=m["item"], value=m["value"]) for m in log["metadata"]],
                process=log.get("process"),
            )
            for log in data["internalLogs"]
        ]

    def flush_internal_logs(self, end_log_id: int) -> str:
        """Drop the internal logs up to and including ``end_log_id``."""
        data = self.execute_query(
            queries.FLUSH_INTERNAL_LOGS, {"endLogId": end_log_id}, "itn_flush_internal_logs"
        )
        return data["flushInternalLogs"]

    def schedule_payments(self, details: PaymentsDetails) -> str:
        """Start sending payments; returns the handle for ``stop_scheduled_transactions``."""
        data = self.execute_query(
            queries.SCHEDULE_PAYMENTS, {"input": details.to_variables()}, "itn_schedule_payments"
        )
        return data["schedulePayments"]

    def schedule_zkapp_commands(self, details: ZkappCommandsDetails) -> str:
        """Start sending zkApp commands; returns the handle for
        ``stop_scheduled_transactions``."""
        data = self.execute_query(
            queries.SCHEDULE_ZKAPP_COMMANDS,
            {"input": details.to_variables()},
            "itn_schedule_zkapp_commands",
        )
        return data["scheduleZkappCommands"]

    def stop_scheduled_transactions(self, handle: str) -> str:
        """Stop the transactions of a schedule handle."""
        data = self.execute_query(
            queries.STOP_SCHEDULED_TRANSACTIONS,
            {"handle": handle},
            "itn_stop_scheduled_transactions",
        )
        return data["stopScheduledTransactions"]

    def update_gating(self, update: GatingUpdate) -> str:
        """Change the node's connection gating."""
        data = self.execute_query(
            queries.UPDATE_GATING, {"input": update.to_variables()}, "itn_update_gating"
        )
        return data["updateGating"]

    def stop_daemon(
        self, delay_seconds: int | None = None, clean_config: bool | None = None
    ) -> str:
        """Stop the daemon after ``delay_seconds`` (the daemon's minimum is 5;
        ``None`` for its default), deleting its configuration directory if
        ``clean_config`` is true."""
        data = self.execute_query(
            queries.STOP_DAEMON,
            {"delaySeconds": delay_seconds, "cleanConfig": clean_config},
            "itn_stop_daemon",
        )
        return data["stopDaemon"]

    def set_zkapp_command_limit(self, limit: int | None) -> int | None:
        """Set the block producer's limit of zkApp commands per block; ``None``
        removes the limit. Returns the limit now in force."""
        data = self.execute_query(
            queries.ZKAPP_COMMAND_LIMIT, {"limit": limit}, "itn_set_zkapp_command_limit"
        )
        return data["zkAppCommandLimit"]

    # The following methods need a daemon with MinaProtocol/mina#19616; older
    # daemons answer them with a GraphQL error. A handle is a UUID that the
    # caller chooses and records before the call. A call with the handle of a
    # running scheduler starts nothing and returns that handle, so these calls
    # may be repeated after a transport error.

    def commit_id(self) -> str:
        """The git commit of the daemon's build."""
        data = self.execute_query(queries.COMMIT_ID, None, "itn_commit_id")
        return data["auth"]["commitId"]

    def scheduled_transactions(self) -> list[str]:
        """Handles of the running payment and zkApp schedulers and account-creation jobs."""
        data = self.execute_query(
            queries.SCHEDULED_TRANSACTIONS, None, "itn_scheduled_transactions"
        )
        return list(data["scheduledTransactions"])

    def schedule_payments_with_handle(self, details: PaymentsDetails, handle: str) -> str:
        """Start sending payments under ``handle``; returns it."""
        data = self.execute_query(
            queries.SCHEDULE_PAYMENTS_WITH_HANDLE,
            {"input": details.to_variables(), "handle": handle},
            "itn_schedule_payments_with_handle",
        )
        return data["schedulePayments"]

    def schedule_zkapp_commands_with_handle(
        self, details: ZkappCommandsDetails, handle: str
    ) -> str:
        """Start sending zkApp commands under ``handle``; returns it."""
        data = self.execute_query(
            queries.SCHEDULE_ZKAPP_COMMANDS_WITH_HANDLE,
            {"input": details.to_variables(), "handle": handle},
            "itn_schedule_zkapp_commands_with_handle",
        )
        return data["scheduleZkappCommands"]

    def create_accounts(
        self, details: CreateAccountsDetails, handle: str | None = None
    ) -> CreatedAccounts:
        """Create ``details.num_accounts`` accounts and fund them in the
        background; the keys are returned at once. Wait until
        ``scheduled_transactions`` no longer lists the returned handle. ``None``
        lets the daemon choose the handle."""
        data = self.execute_query(
            queries.CREATE_ACCOUNTS,
            {"input": details.to_variables(), "handle": handle},
            "itn_create_accounts",
        )
        created = data["createAccounts"]
        return CreatedAccounts(
            handle=created["handle"],
            accounts=[
                CreatedAccount(public_key=a["publicKey"], private_key=a["privateKey"])
                for a in created["accounts"]
            ],
        )


def _parse_auth(data: dict[str, Any]) -> ItnAuth:
    auth = data.get("auth")
    if not auth or not auth.get("serverUuid"):
        raise ValueError("itn_auth: missing field auth.serverUuid")
    # UInt16 values come as strings ("8302") or numbers.
    return ItnAuth(
        server_uuid=auth["serverUuid"],
        signer_sequence_number=int(auth["signerSequenceNumber"]),
        libp2p_port=int(auth["libp2pPort"]),
        peer_id=auth.get("peerId"),
        is_block_producer=bool(auth.get("isBlockProducer")),
    )
