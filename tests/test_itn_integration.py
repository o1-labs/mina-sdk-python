"""Integration tests against a running daemon's ITN GraphQL server.

They need MINA_ITN_URI (e.g. http://127.0.0.1:3086/graphql) and MINA_ITN_KEY
(a base64 ed25519 seed whose public key is in --itn-keys), and are skipped
otherwise. None of them stops the daemon or sends transactions.
"""

from __future__ import annotations

import contextlib
import os

import pytest

from mina_sdk import GraphQLError
from mina_sdk.itn import GatingUpdate, ItnClient, ItnKey, ItnUnauthorizedError

URI = os.environ.get("MINA_ITN_URI", "")
SEED = os.environ.get("MINA_ITN_KEY", "")

pytestmark = pytest.mark.skipif(not (URI and SEED), reason="MINA_ITN_URI and MINA_ITN_KEY not set")


def _client(key: ItnKey | None = None) -> ItnClient:
    return ItnClient(URI, key or ItnKey.from_base64(SEED), retries=2, retry_delay=1.0)


def test_auth():
    with _client() as itn:
        auth = itn.auth()
    assert auth.server_uuid
    assert auth.libp2p_port > 0


def test_unknown_key_is_rejected():
    with _client(ItnKey.generate()) as itn, pytest.raises(ItnUnauthorizedError):
        itn.auth()


def test_sequenced_requests():
    with _client() as itn:
        for _ in range(3):
            itn.internal_logs(0)
        assert itn.set_zkapp_command_limit(7) == 7
        assert itn.set_zkapp_command_limit(None) is None


def test_stale_sequence_number_is_recovered():
    # Two clients with the same key share the daemon's sequence number: each
    # one's next request gets a 412, runs auth again and succeeds.
    with _client() as a, _client() as b:
        a.internal_logs(0)
        b.internal_logs(0)
        a.internal_logs(0)
        b.internal_logs(0)


def test_internal_logs_and_flush():
    with _client() as itn:
        logs = itn.internal_logs(0)
        if logs:
            assert logs[0].id <= logs[-1].id
            itn.flush_internal_logs(logs[0].id)


def test_slots_won():
    # A block producer answers with its slots, or with a GraphQL error while
    # its VRF evaluation runs; anything else is a transport or schema problem.
    with _client() as itn, contextlib.suppress(GraphQLError):
        assert all(isinstance(s, int) for s in itn.slots_won())


def test_update_gating_empty():
    # An empty update with isolate=False leaves the node's gating open.
    with _client() as itn:
        assert isinstance(itn.update_gating(GatingUpdate()), str)
