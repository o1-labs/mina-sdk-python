"""Tests of the ITN client against a mock ITN server that checks signatures
and sequence numbers as the daemon does."""

from __future__ import annotations

import base64
import json
import struct

import httpx
import pytest
import respx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from mina_sdk import Currency, DaemonConnectionError, GraphQLError
from mina_sdk.itn import (
    GatingUpdate,
    InvalidItnKeyError,
    ItnClient,
    ItnHttpError,
    ItnKey,
    ItnSequencingError,
    ItnUnauthorizedError,
    NetworkPeer,
    PaymentsDetails,
    queries,
)

URL = "http://localhost:3086/graphql"
SEED = base64.b64encode(bytes(range(32))).decode()


def _verify(public_b64: str, sig_b64: str, message: bytes) -> bool:
    key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_b64))
    try:
        key.verify(base64.b64decode(sig_b64), message)
    except InvalidSignature:
        return False
    return True


class MockItnServer:
    """Answers like the daemon: auth with an unsequenced signature, everything
    else with the exact next sequence number of the key."""

    def __init__(self, key: ItnKey, seq: int = 0, data: dict | None = None):
        self.public = key.public_key_base64()
        self.uuid = "uuid-1"
        self.seq = seq
        self.data = data or {}
        self.requests: list[dict] = []
        self.status_override: list[int] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = request.content
        payload = json.loads(body)
        self.requests.append(payload)
        header = request.headers["Authorization"]
        sig_part, _, seq_part = header.partition(" ; ")
        # status_override answers sequenced requests only.
        if seq_part and self.status_override:
            return httpx.Response(self.status_override.pop(0), text="override")
        _, pk, sig = sig_part.split(" ")
        if pk != self.public:
            return httpx.Response(401, text="unknown key")
        if payload["query"] == queries.AUTH and not seq_part:
            if not _verify(pk, sig, body):
                return httpx.Response(401, text="bad signature")
            return httpx.Response(
                200,
                json={
                    "data": {
                        "auth": {
                            "serverUuid": self.uuid,
                            "signerSequenceNumber": str(self.seq),
                            "libp2pPort": "8302",
                            "peerId": "12D3peer",
                            "isBlockProducer": True,
                        }
                    }
                },
            )
        if not seq_part:
            return httpx.Response(200, json={"errors": [{"message": "Missing sequence"}]})
        _, uuid, n = seq_part.split(" ")
        if not _verify(pk, sig, struct.pack(">H", int(n)) + uuid.encode() + body):
            return httpx.Response(401, text="bad signature")
        if uuid != self.uuid or int(n) != self.seq:
            return httpx.Response(412, text="stale")
        self.seq = (self.seq + 1) % 65536
        return httpx.Response(200, json={"data": self.data})


@pytest.fixture
def key():
    return ItnKey.from_base64(SEED)


def _client(key):
    return ItnClient(URL, key, retries=1, retry_delay=0.0, timeout=5.0)


def test_key_round_trip_and_repr(key):
    assert key.to_base64() == SEED
    assert key.public_key_base64() in repr(key)
    assert SEED not in repr(key)
    assert ItnKey.generate().to_base64() != SEED
    with pytest.raises(InvalidItnKeyError):
        ItnKey.from_base64("not base64!")
    with pytest.raises(InvalidItnKeyError):
        ItnKey.from_base64(base64.b64encode(b"short").decode())


@respx.mock
def test_auth_then_sequenced_requests(key):
    server = MockItnServer(key, seq=7, data={"slotsWon": [1, 2]})
    respx.post(URL).mock(side_effect=server)
    with _client(key) as itn:
        auth = itn.auth()
        assert (auth.server_uuid, auth.signer_sequence_number) == ("uuid-1", 7)
        assert (auth.libp2p_port, auth.peer_id, auth.is_block_producer) == (8302, "12D3peer", True)
        assert itn.slots_won() == [1, 2]
        assert itn.slots_won() == [1, 2]
    assert server.seq == 9
    assert [r["query"] for r in server.requests][1].startswith("query SlotsWon")


@respx.mock
def test_first_request_runs_auth_itself(key):
    server = MockItnServer(key, data={"flushInternalLogs": "ok"})
    respx.post(URL).mock(side_effect=server)
    with _client(key) as itn:
        assert itn.last_auth is None
        assert itn.flush_internal_logs(5) == "ok"
        assert itn.last_auth is not None
    assert server.requests[1]["variables"] == {"endLogId": 5}


@respx.mock
def test_sequence_number_wraps(key):
    server = MockItnServer(key, seq=65535, data={"updateGating": "ok"})
    respx.post(URL).mock(side_effect=server)
    with _client(key) as itn:
        itn.update_gating(GatingUpdate())
        itn.update_gating(GatingUpdate())
    assert server.seq == 1


@respx.mock
def test_412_runs_auth_again_and_repeats_once(key):
    server = MockItnServer(key, data={"stopScheduledTransactions": "stopped"})
    respx.post(URL).mock(side_effect=server)
    with _client(key) as itn:
        itn.auth()
        server.uuid = "uuid-2"  # the daemon restarted
        assert itn.stop_scheduled_transactions("h") == "stopped"
        assert itn.last_auth is not None
        assert itn.last_auth.server_uuid == "uuid-2"

        # 412, a new auth, 412 again.
        server.status_override = [412, 412]
        with pytest.raises(ItnSequencingError):
            itn.stop_scheduled_transactions("h")


@respx.mock
def test_401_is_not_repeated(key):
    server = MockItnServer(ItnKey.generate())
    route = respx.post(URL).mock(side_effect=server)
    with _client(key) as itn, pytest.raises(ItnUnauthorizedError):
        itn.slots_won()
    assert route.call_count == 1


@respx.mock
def test_transport_error_is_not_repeated(key):
    server = MockItnServer(key, data={"slotsWon": []})
    calls = []

    def flaky(request):
        calls.append(request)
        if len(calls) == 2:
            raise httpx.ConnectError("reset")
        return server(request)

    respx.post(URL).mock(side_effect=flaky)
    with _client(key) as itn:
        with pytest.raises(DaemonConnectionError):
            itn.slots_won()
        assert len(calls) == 2
        # The next request starts with a new auth.
        assert itn.slots_won() == []
    assert server.requests[-2]["query"] == queries.AUTH


@respx.mock
def test_http_error_status_is_the_cause(key):
    server = MockItnServer(key)
    respx.post(URL).mock(side_effect=server)
    with _client(key) as itn:
        itn.auth()
        server.status_override = [503]
        with pytest.raises(DaemonConnectionError) as e:
            itn.slots_won()
    assert isinstance(e.value.__cause__, ItnHttpError)
    assert e.value.__cause__.status_code == 503


@respx.mock
def test_graphql_errors(key):
    server = MockItnServer(key)
    respx.post(URL).mock(side_effect=server)
    with _client(key) as itn:
        itn.auth()
        server.data = None  # type: ignore[assignment]
        respx.post(URL).mock(
            side_effect=lambda r: (
                server(r),
                httpx.Response(200, json={"errors": [{"message": "boom"}]}),
            )[1]
        )
        with pytest.raises(GraphQLError):
            itn.slots_won()


@respx.mock
def test_variables_of_the_operations(key):
    server = MockItnServer(
        key,
        data={
            "internalLogs": [
                {
                    "id": 3,
                    "timestamp": "t",
                    "message": "m",
                    "metadata": [{"item": "k", "value": "{}"}],
                    "process": None,
                }
            ],
            "schedulePayments": "h1",
            "stopDaemon": "stopping",
            "zkAppCommandLimit": None,
            "updateGating": "ok",
        },
    )
    respx.post(URL).mock(side_effect=server)
    with _client(key) as itn:
        (log,) = itn.internal_logs(2)
        assert (log.id, log.metadata[0].item, log.process) == (3, "k", None)
        details = PaymentsDetails(
            duration_min=1,
            tps=0.5,
            memo_prefix="m",
            max_fee=Currency.from_nanomina(20),
            min_fee=Currency.from_nanomina(10),
            amount=Currency.from_nanomina(1),
            receiver="B62qr",
        )
        assert itn.schedule_payments(details) == "h1"
        assert itn.stop_daemon() == "stopping"
        assert itn.set_zkapp_command_limit(None) is None
        itn.update_gating(
            GatingUpdate(trusted_peers=[NetworkPeer(host="1.2.3.4", libp2p_port=1, peer_id="p")])
        )
    variables = [r.get("variables") for r in server.requests[1:]]
    assert variables[0] == {"startLogId": 2}
    assert variables[1]["input"]["senders"] == []
    assert variables[1]["input"]["maxFee"] == "20"
    assert variables[2] == {"delaySeconds": None, "cleanConfig": None}
    assert variables[3] == {"limit": None}
    assert variables[4]["input"]["trustedPeers"] == [
        {"host": "1.2.3.4", "libp2pPort": 1, "peerId": "p"}
    ]
