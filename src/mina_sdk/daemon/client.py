"""Mina daemon GraphQL client."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from mina_sdk.daemon import queries
from mina_sdk.types import (
    AccountBalance,
    AccountData,
    AccountPermissions,
    AccountTiming,
    AddrsAndPorts,
    BlockInfo,
    BlockTransaction,
    CompletedWork,
    Currency,
    DaemonMetrics,
    DaemonStatus,
    EpochData,
    FeeTransfer,
    GenesisConstants,
    PeerInfo,
    PooledUserCommand,
    SendDelegationResult,
    SendPaymentResult,
    SignatureInput,
    SubmittedCommand,
    TrackedAccount,
    TransactionStatus,
    VerificationKeyPermission,
    ZkappCommandResult,
    ZkappFailure,
    ZkappFeePayer,
    _parse_response,
)

logger = logging.getLogger(__name__)


class GraphQLError(Exception):
    """Raised when the GraphQL endpoint returns an error response.

    Attributes:
        errors: List of error objects from the GraphQL response.
        query_name: Name of the query/mutation that failed.
    """

    def __init__(self, errors: list[dict[str, Any]], query_name: str = ""):
        self.errors = errors
        self.query_name = query_name
        messages = [e.get("message", str(e)) for e in errors]
        super().__init__(f"GraphQL error in {query_name}: {'; '.join(messages)}")


class DaemonConnectionError(Exception):
    """Raised when the client cannot connect to the daemon after exhausting retries.

    This replaces the previous ``ConnectionError`` name which shadowed the
    built-in ``builtins.ConnectionError``.
    """

    pass


# Keep the old name as an alias for backwards compatibility
ConnectionError = DaemonConnectionError


class AccountNotFoundError(ValueError):
    """Raised by ``get_account`` when the account does not exist on the ledger.

    It is a ``ValueError``, which ``get_account`` raised before.
    """


class MinaDaemonClient:
    """Client for interacting with a Mina daemon via its GraphQL API.

    Args:
        graphql_uri: The daemon's GraphQL endpoint URL.
        retries: Number of retry attempts for failed requests (must be >= 1).
        retry_delay: Seconds to wait between retries (must be > 0).
        timeout: HTTP request timeout in seconds (must be > 0).

    Raises:
        ValueError: If any configuration parameter is out of valid range.

    Example::

        with MinaDaemonClient() as client:
            status = client.get_sync_status()
            print(status)
    """

    def __init__(
        self,
        graphql_uri: str = "http://127.0.0.1:3085/graphql",
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
        self._retries = retries
        self._retry_delay = retry_delay
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Release resources held by the HTTP client."""
        self._client.close()

    def __enter__(self) -> MinaDaemonClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _request(
        self, query: str, variables: dict[str, Any] | None = None, query_name: str = ""
    ) -> dict[str, Any]:
        """Execute a GraphQL request with retry logic.

        Returns the ``data`` field of the response.

        Raises:
            GraphQLError: If the response contains GraphQL-level errors (not retried).
            DaemonConnectionError: If all retry attempts fail due to network errors.
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        last_error: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                logger.debug("GraphQL %s attempt %d/%d", query_name, attempt, self._retries)
                resp = self._client.post(self._uri, json=payload)
                resp.raise_for_status()

                try:
                    resp_json = resp.json()
                except ValueError as e:
                    raise DaemonConnectionError(
                        f"Invalid JSON response from {query_name}: {e}"
                    ) from e

                if "errors" in resp_json:
                    raise GraphQLError(resp_json["errors"], query_name)

                return resp_json.get("data", {})

            except GraphQLError:
                raise
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    "GraphQL %s HTTP %d (attempt %d/%d)",
                    query_name,
                    e.response.status_code,
                    attempt,
                    self._retries,
                )
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(
                    "GraphQL %s connection error (attempt %d/%d): %s",
                    query_name,
                    attempt,
                    self._retries,
                    e,
                )

            if attempt < self._retries:
                time.sleep(self._retry_delay)

        raise DaemonConnectionError(
            f"Failed to execute {query_name} after {self._retries} attempts: {last_error}"
        )

    def execute_query(
        self, query: str, variables: dict[str, Any] | None = None, query_name: str = "custom"
    ) -> dict[str, Any]:
        """Run a custom GraphQL document, with the client's transport, retries
        and errors. Returns the ``data`` field of the response.

        Raises:
            GraphQLError: If the response contains GraphQL-level errors (not retried).
            DaemonConnectionError: If all retry attempts fail due to network errors.
        """
        return self._request(query, variables=variables, query_name=query_name)

    # -- Queries --

    def get_sync_status(self) -> str:
        """Get the node's sync status.

        Returns:
            One of: ``CONNECTING``, ``LISTENING``, ``OFFLINE``, ``BOOTSTRAP``,
            ``SYNCED``, ``CATCHUP``.
        """
        data = self._request(queries.SYNC_STATUS, query_name="get_sync_status")
        return data["syncStatus"]

    def get_daemon_status(self) -> DaemonStatus:
        """Get comprehensive daemon status: sync state, chain height, uptime,
        commit hash, connected peers, addresses and block production keys."""
        data = self._request(queries.DAEMON_STATUS, query_name="get_daemon_status")
        status = data["daemonStatus"]

        peers = None
        if status.get("peers"):
            peers = [_parse_peer(p) for p in status["peers"]]
        addrs = status.get("addrsAndPorts")

        return DaemonStatus(
            sync_status=status["syncStatus"],
            blockchain_length=status.get("blockchainLength"),
            highest_block_length_received=status.get("highestBlockLengthReceived"),
            uptime_secs=status.get("uptimeSecs"),
            state_hash=status.get("stateHash"),
            commit_id=status.get("commitId"),
            peers=peers,
            highest_unvalidated_block_length_received=status.get(
                "highestUnvalidatedBlockLengthReceived"
            ),
            num_accounts=status.get("numAccounts"),
            ledger_merkle_root=status.get("ledgerMerkleRoot"),
            chain_id=status.get("chainId"),
            catchup_status=status.get("catchupStatus"),
            block_production_keys=status.get("blockProductionKeys"),
            coinbase_receiver=status.get("coinbaseReceiver"),
            addrs_and_ports=AddrsAndPorts(
                external_ip=addrs["externalIp"],
                bind_ip=addrs["bindIp"],
                client_port=addrs["clientPort"],
                libp2p_port=addrs["libp2pPort"],
            )
            if addrs
            else None,
        )

    def get_daemon_metrics(self) -> DaemonMetrics:
        """Get the daemon's transaction pool, snark pool and block production metrics."""
        data = self._request(queries.DAEMON_METRICS, query_name="get_daemon_metrics")
        m = _parse_response(data, ["daemonStatus", "metrics"])
        return DaemonMetrics(
            block_production_delay=list(m["blockProductionDelay"]),
            transaction_pool_diff_received=m["transactionPoolDiffReceived"],
            transaction_pool_diff_broadcasted=m["transactionPoolDiffBroadcasted"],
            transactions_added_to_pool=m["transactionsAddedToPool"],
            transaction_pool_size=m["transactionPoolSize"],
            snark_pool_diff_received=m["snarkPoolDiffReceived"],
            snark_pool_diff_broadcasted=m["snarkPoolDiffBroadcasted"],
            pending_snark_work=m["pendingSnarkWork"],
            snark_pool_size=m["snarkPoolSize"],
        )

    def get_network_id(self) -> str:
        """Get the network identifier (e.g. ``mina:mainnet``, ``mina:testnet``)."""
        data = self._request(queries.NETWORK_ID, query_name="get_network_id")
        return data["networkID"]

    def get_account(self, public_key: str, token_id: str | None = None) -> AccountData:
        """Get account data for a public key.

        Args:
            public_key: Base58-encoded public key (starts with ``B62q``).
            token_id: Optional token ID (defaults to MINA token).

        Raises:
            AccountNotFoundError: If the account does not exist on the ledger.
                It is a ``ValueError``.
        """
        # $token is nullable: null selects the default MINA token. Every
        # declared variable is sent, because the daemon rejects a missing one.
        data = self._request(
            queries.GET_ACCOUNT,
            variables={"publicKey": public_key, "token": token_id},
            query_name="get_account",
        )
        acc = data.get("account")
        if acc is None:
            raise AccountNotFoundError(f"account not found: {public_key}")
        return _parse_account(acc)

    def get_best_chain(self, max_length: int | None = None) -> list[BlockInfo]:
        """Get blocks from the best chain, ordered from highest to lowest.

        Args:
            max_length: Maximum number of blocks to return.  ``None`` uses the
                daemon's default.
        """
        data = self._request(
            queries.BEST_CHAIN, variables={"maxLength": max_length}, query_name="get_best_chain"
        )
        return [_parse_block(b) for b in data.get("bestChain") or []]

    def get_genesis_block(self) -> BlockInfo:
        """Get the network's genesis block."""
        data = self._request(queries.GENESIS_BLOCK, query_name="get_genesis_block")
        return _parse_block(_parse_response(data, ["genesisBlock"]))

    def get_block(self, state_hash: str | None = None, height: int | None = None) -> BlockInfo:
        """Get one block, by state hash or by height.

        Raises:
            ValueError: If not exactly one of ``state_hash`` and ``height`` is given.
        """
        if (state_hash is None) == (height is None):
            raise ValueError("get_block: pass exactly one of state_hash and height")
        data = self._request(
            queries.BLOCK,
            variables={"stateHash": state_hash, "height": height},
            query_name="get_block",
        )
        block = data.get("block")
        if block is None:
            raise ValueError("missing field 'block' in response")
        return _parse_block(block)

    def get_peers(self) -> list[PeerInfo]:
        """Get the list of connected peers."""
        data = self._request(queries.GET_PEERS, query_name="get_peers")
        return [_parse_peer(p) for p in data.get("getPeers", [])]

    def get_pooled_user_commands(self, public_key: str | None = None) -> list[PooledUserCommand]:
        """Get pending payments and delegations from the transaction pool.

        Args:
            public_key: Filter by sender public key.  If ``None``, returns all
                pending commands.
        """
        data = self._request(
            queries.POOLED_USER_COMMANDS,
            variables={"publicKey": public_key},
            query_name="get_pooled_user_commands",
        )
        return [
            PooledUserCommand(
                id=c["id"],
                hash=c["hash"],
                kind=c["kind"],
                nonce=str(c["nonce"]),
                amount=str(c["amount"]),
                fee=str(c["fee"]),
                from_=c["from"],
                to=c["to"],
                source=(c.get("source") or {}).get("publicKey", ""),
                receiver=(c.get("receiver") or {}).get("publicKey", ""),
                memo=c.get("memo") or "",
                failure_reason=c.get("failureReason"),
            )
            for c in data.get("pooledUserCommands") or []
        ]

    def get_pooled_zkapp_commands(self, public_key: str | None = None) -> list[ZkappCommandResult]:
        """Get pending zkApp commands; ``None`` for the commands of every fee payer."""
        data = self._request(
            queries.POOLED_ZKAPP_COMMANDS,
            variables={"publicKey": public_key},
            query_name="get_pooled_zkapp_commands",
        )
        return [_parse_zkapp(z) for z in data.get("pooledZkappCommands") or []]

    def get_transaction_status(
        self, payment: str | None = None, zkapp_transaction: str | None = None
    ) -> TransactionStatus:
        """Get the status of a payment or delegation (``payment``) or of a zkApp
        command (``zkapp_transaction``), by its ID.

        Raises:
            ValueError: If not exactly one of the two IDs is given.
        """
        if (payment is None) == (zkapp_transaction is None):
            raise ValueError(
                "get_transaction_status: pass exactly one of payment and zkapp_transaction"
            )
        data = self._request(
            queries.TRANSACTION_STATUS,
            variables={"payment": payment, "zkappTransaction": zkapp_transaction},
            query_name="get_transaction_status",
        )
        return TransactionStatus(_parse_response(data, ["transactionStatus"]))

    def get_genesis_constants(self) -> GenesisConstants:
        """Get the network's genesis constants."""
        data = self._request(queries.GENESIS_CONSTANTS, query_name="get_genesis_constants")
        c = _parse_response(data, ["genesisConstants"])
        return GenesisConstants(
            genesis_timestamp=c["genesisTimestamp"],
            coinbase=_currency(c["coinbase"]),
            account_creation_fee=_currency(c["accountCreationFee"]),
        )

    def get_tracked_accounts(self) -> list[TrackedAccount]:
        """Get the accounts the daemon tracks (its wallet keys)."""
        data = self._request(queries.TRACKED_ACCOUNTS, query_name="get_tracked_accounts")
        return [
            TrackedAccount(public_key=a["publicKey"], balance=_currency(a["balance"]["total"]))
            for a in data.get("trackedAccounts") or []
        ]

    def get_snark_pool(self) -> list[CompletedWork]:
        """Get the completed snark work in the snark pool."""
        data = self._request(queries.SNARK_POOL, query_name="get_snark_pool")
        return [
            CompletedWork(
                prover=w["prover"],
                fee=_currency(w["fee"]),
                work_ids=[int(i) for i in w["workIds"]],
            )
            for w in data.get("snarkPool") or []
        ]

    def get_fork_config(self) -> Any:
        """Get the daemon's fork configuration: the configuration used to seed a
        hardfork's genesis ledger, as JSON."""
        data = self._request(queries.FORK_CONFIG, query_name="get_fork_config")
        return _parse_response(data, ["fork_config"])

    # -- Mutations --

    def send_payment(
        self,
        sender: str,
        receiver: str,
        amount: Currency | str,
        fee: Currency | str,
        memo: str | None = None,
        nonce: int | None = None,
        signature: SignatureInput | None = None,
    ) -> SendPaymentResult:
        """Send a payment transaction.

        Without ``signature``, the daemon signs with the sender's key, which must
        be unlocked on the node (see ``unlock_account``).

        Args:
            sender: Sender public key (base58).
            receiver: Receiver public key (base58).
            amount: Amount to send (``Currency`` or MINA string like ``"1.5"``).
            fee: Transaction fee (``Currency`` or MINA string).
            memo: Optional transaction memo (max 32 bytes).
            nonce: Optional explicit nonce.  If omitted the daemon auto-increments.
            signature: Optional signature made outside the daemon.

        Raises:
            GraphQLError: If the daemon rejects the transaction.
        """
        if isinstance(amount, str):
            amount = Currency(amount)
        if isinstance(fee, str):
            fee = Currency(fee)

        input_obj: dict[str, Any] = {
            "from": sender,
            "to": receiver,
            "amount": amount.to_nanomina_str(),
            "fee": fee.to_nanomina_str(),
        }
        if memo is not None:
            input_obj["memo"] = memo
        if nonce is not None:
            input_obj["nonce"] = str(nonce)

        data = self._request(
            queries.SEND_PAYMENT,
            variables={"input": input_obj, "signature": _signature(signature)},
            query_name="send_payment",
        )
        return _parse_submitted(_parse_response(data, ["sendPayment", "payment"]))

    def send_delegation(
        self,
        sender: str,
        delegate_to: str,
        fee: Currency | str,
        memo: str | None = None,
        nonce: int | None = None,
        signature: SignatureInput | None = None,
    ) -> SendDelegationResult:
        """Send a stake delegation transaction.

        Without ``signature``, the daemon signs with the sender's key, which must
        be unlocked on the node.

        Args:
            sender: Delegator public key (base58).
            delegate_to: Delegate-to public key (base58).
            fee: Transaction fee (``Currency`` or MINA string).
            memo: Optional transaction memo.
            nonce: Optional explicit nonce.
            signature: Optional signature made outside the daemon.
        """
        if isinstance(fee, str):
            fee = Currency(fee)

        input_obj: dict[str, Any] = {
            "from": sender,
            "to": delegate_to,
            "fee": fee.to_nanomina_str(),
        }
        if memo is not None:
            input_obj["memo"] = memo
        if nonce is not None:
            input_obj["nonce"] = str(nonce)

        data = self._request(
            queries.SEND_DELEGATION,
            variables={"input": input_obj, "signature": _signature(signature)},
            query_name="send_delegation",
        )
        return _parse_submitted(_parse_response(data, ["sendDelegation", "delegation"]))

    def send_zkapp(self, zkapp_command: Any) -> ZkappCommandResult:
        """Send a signed zkApp command, as JSON in the daemon's
        ``ZkappCommandInput`` form (for example from o1js ``toJSON()``)."""
        data = self._request(
            queries.SEND_ZKAPP,
            variables={"input": {"zkappCommand": zkapp_command}},
            query_name="send_zkapp",
        )
        return _parse_zkapp(_parse_response(data, ["sendZkapp", "zkapp"]))

    def unlock_account(self, public_key: str, password: str) -> str:
        """Unlock an account in the daemon's keystore, so that the daemon can sign
        payments and delegations from it. Returns its public key."""
        data = self._request(
            queries.UNLOCK_ACCOUNT,
            variables={"input": {"publicKey": public_key, "password": password}},
            query_name="unlock_account",
        )
        return _parse_response(data, ["unlockAccount", "publicKey"])

    def set_snark_worker(self, public_key: str | None) -> str | None:
        """Set or unset the SNARK worker key.

        Args:
            public_key: Public key for snark worker, or ``None`` to disable.

        Returns:
            The previous snark worker public key, or ``None`` if there was none.
        """
        data = self._request(
            queries.SET_SNARK_WORKER,
            variables={"input": public_key},
            query_name="set_snark_worker",
        )
        return _parse_response(data, ["setSnarkWorker", "lastSnarkWorker"])

    def set_snark_work_fee(self, fee: Currency | str) -> str:
        """Set the fee for SNARK work.

        Args:
            fee: The fee amount (``Currency`` or MINA string).

        Returns:
            The previous fee as a nanomina string.
        """
        if isinstance(fee, str):
            fee = Currency(fee)
        data = self._request(
            queries.SET_SNARK_WORK_FEE,
            variables={"fee": fee.to_nanomina_str()},
            query_name="set_snark_work_fee",
        )
        return _parse_response(data, ["setSnarkWorkFee", "lastFee"])


# -- Parsing --
#
# The daemon sends most integers (UInt32, UInt64, Length, Slot) as strings and
# amounts as nanomina strings; these helpers accept a string or a number.


def _int(v: Any) -> int:
    return int(v) if v is not None and v != "" else 0


def _opt_int(v: Any) -> int | None:
    return int(v) if v is not None and v != "" else None


def _currency(v: Any) -> Currency:
    return Currency.from_graphql(str(v))


def _opt_currency(v: Any) -> Currency | None:
    return Currency.from_graphql(str(v)) if v is not None and v != "" else None


def _signature(s: SignatureInput | None) -> dict[str, str] | None:
    return {"field": s.field, "scalar": s.scalar} if s is not None else None


def _parse_peer(p: dict[str, Any]) -> PeerInfo:
    return PeerInfo(peer_id=p["peerId"], host=p["host"], port=p["libp2pPort"])


def _parse_account(acc: dict[str, Any]) -> AccountData:
    balance = acc["balance"]
    timing = acc.get("timing") or {}
    perms = acc.get("permissions")
    vk = (perms or {}).get("setVerificationKey")
    parsed_timing = AccountTiming(
        initial_minimum_balance=_opt_currency(timing.get("initialMinimumBalance")),
        cliff_time=_opt_int(timing.get("cliffTime")),
        cliff_amount=_opt_currency(timing.get("cliffAmount")),
        vesting_period=_opt_int(timing.get("vestingPeriod")),
        vesting_increment=_opt_currency(timing.get("vestingIncrement")),
    )
    return AccountData(
        public_key=acc["publicKey"],
        nonce=int(acc["nonce"]),
        delegate=acc.get("delegate"),
        token_id=acc.get("tokenId"),
        balance=AccountBalance(
            total=_currency(balance["total"]),
            liquid=_opt_currency(balance.get("liquid")),
            locked=_opt_currency(balance.get("locked")),
            block_height=_opt_int(balance.get("blockHeight")),
        ),
        token_symbol=acc.get("tokenSymbol"),
        voting_for=acc.get("votingFor"),
        receipt_chain_hash=acc.get("receiptChainHash"),
        # The daemon sends a timing object with every field null for an
        # untimed account; that is no timing.
        timing=parsed_timing if parsed_timing != AccountTiming() else None,
        permissions=AccountPermissions(
            edit_state=perms.get("editState"),
            send=perms.get("send"),
            receive=perms.get("receive"),
            access=perms.get("access"),
            set_delegate=perms.get("setDelegate"),
            set_permissions=perms.get("setPermissions"),
            set_verification_key=VerificationKeyPermission(
                auth=vk["auth"], txn_version=str(vk["txnVersion"])
            )
            if vk
            else None,
            set_zkapp_uri=perms.get("setZkappUri"),
            edit_action_state=perms.get("editActionState"),
            set_token_symbol=perms.get("setTokenSymbol"),
            increment_nonce=perms.get("incrementNonce"),
            set_voting_for=perms.get("setVotingFor"),
            set_timing=perms.get("setTiming"),
        )
        if perms
        else None,
        zkapp_state=acc.get("zkappState"),
        proved_state=acc.get("provedState"),
        zkapp_uri=acc.get("zkappUri"),
    )


def _parse_epoch(e: dict[str, Any] | None) -> EpochData | None:
    if not e:
        return None
    return EpochData(
        seed=e.get("seed") or "",
        ledger_hash=(e.get("ledger") or {}).get("hash") or "",
        length=_opt_int(e.get("epochLength")),
    )


def _parse_block(block: dict[str, Any]) -> BlockInfo:
    """Parse a block of the common block selection (BestChain, GenesisBlock, Block)."""
    protocol = block["protocolState"]
    consensus = protocol["consensusState"]
    chain = protocol.get("blockchainState") or {}
    txs = block.get("transactions") or {}
    creator_pk = (block.get("creatorAccount") or {}).get("publicKey") or "unknown"
    return BlockInfo(
        state_hash=block["stateHash"],
        height=_int(consensus["blockHeight"]),
        global_slot_since_hard_fork=_int(consensus["slot"]),
        global_slot_since_genesis=_int(consensus["slotSinceGenesis"]),
        creator_pk=creator_pk,
        command_transaction_count=block["commandTransactionCount"],
        previous_state_hash=protocol.get("previousStateHash") or "",
        epoch=_int(consensus.get("epoch")),
        block_creator=consensus.get("blockCreator") or "",
        coinbase_receiver=consensus.get("coinbaseReceiever"),
        staking_epoch=_parse_epoch(consensus.get("stakingEpochData")),
        next_epoch=_parse_epoch(consensus.get("nextEpochData")),
        date=str(chain.get("date") or ""),
        utc_date=str(chain.get("utcDate") or ""),
        snarked_ledger_hash=chain.get("snarkedLedgerHash") or "",
        staged_ledger_hash=chain.get("stagedLedgerHash") or "",
        coinbase=_opt_currency(txs.get("coinbase")),
        coinbase_receiver_account=(txs.get("coinbaseReceiverAccount") or {}).get("publicKey"),
        fee_transfers=[
            FeeTransfer(recipient=f["recipient"], fee=_currency(f["fee"]), transfer_type=f["type"])
            for f in txs.get("feeTransfer") or []
        ],
        user_commands=[
            BlockTransaction(
                id=c["id"],
                hash=c["hash"],
                kind=c["kind"],
                nonce=_int(c["nonce"]),
                source=c["source"]["publicKey"],
                receiver=c["receiver"]["publicKey"],
                amount=_currency(c["amount"]),
                fee=_currency(c["fee"]),
                memo=c["memo"],
                failure_reason=c.get("failureReason"),
            )
            for c in txs.get("userCommands") or []
        ],
    )


def _parse_submitted(c: dict[str, Any]) -> SubmittedCommand:
    return SubmittedCommand(
        id=c["id"],
        hash=c["hash"],
        nonce=_int(c["nonce"]),
        kind=c.get("kind") or "",
        source=(c.get("source") or {}).get("publicKey", ""),
        receiver=(c.get("receiver") or {}).get("publicKey", ""),
        amount=_opt_currency(c.get("amount")),
        fee=_opt_currency(c.get("fee")),
        memo=c.get("memo") or "",
    )


def _parse_zkapp(z: dict[str, Any]) -> ZkappCommandResult:
    command = z["zkappCommand"]
    body = command["feePayer"]["body"]
    failures = z.get("failureReason")
    return ZkappCommandResult(
        id=z["id"],
        hash=z["hash"],
        memo=command.get("memo") or "",
        fee_payer=ZkappFeePayer(
            public_key=body["publicKey"],
            fee=_currency(body["fee"]),
            nonce=_int(body["nonce"]),
            valid_until=_opt_int(body.get("validUntil")),
        ),
        failure_reason=[
            ZkappFailure(index=_opt_int(f.get("index")), failures=list(f.get("failures") or []))
            for f in failures
        ]
        if failures is not None
        else None,
    )
