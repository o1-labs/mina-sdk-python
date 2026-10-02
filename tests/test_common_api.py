"""Tests of the common API (spec/SPEC.md) against a mock daemon: the methods
this SDK did not have, the new result fields, and the variables sent."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from mina_sdk import (
    AccountNotFoundError,
    Currency,
    EpochData,
    FeeTransfer,
    MinaDaemonClient,
    SignatureInput,
    TransactionStatus,
    ZkappFailure,
)

GRAPHQL_URL = "http://localhost:3085/graphql"


@pytest.fixture
def client():
    c = MinaDaemonClient(graphql_uri=GRAPHQL_URL, retries=1, retry_delay=0.0, timeout=5.0)
    yield c
    c.close()


def _mock(data):
    """Answer every request with ``data``; return the route, whose calls record the requests."""
    return respx.post(GRAPHQL_URL).mock(return_value=httpx.Response(200, json={"data": data}))


def _sent(route, n=-1):
    return json.loads(route.calls[n].request.content)


def _block_json():
    def epoch(seed, ledger_hash):
        return {"seed": seed, "ledger": {"hash": ledger_hash}}

    return {
        "stateHash": "3NKblock",
        "commandTransactionCount": 1,
        "creatorAccount": {"publicKey": "B62qcreator"},
        "protocolState": {
            "previousStateHash": "3NKprev",
            "consensusState": {
                "blockHeight": "12",
                "epoch": "1",
                "slot": "30",
                "slotSinceGenesis": "40",
                "blockCreator": "B62qcreator",
                "coinbaseReceiever": "B62qcoinbase",
                "stakingEpochData": {"epochLength": "7", **epoch("seedS", "jxS")},
                "nextEpochData": epoch("seedN", "jxN"),
            },
            "blockchainState": {
                "date": "1700000000000",
                "utcDate": "1700000000001",
                "snarkedLedgerHash": "jxSnarked",
                "stagedLedgerHash": "jxStaged",
            },
        },
        "transactions": {
            "coinbase": "720000000000",
            "coinbaseReceiverAccount": {"publicKey": "B62qcoinbase"},
            "feeTransfer": [{"recipient": "B62qfee", "fee": "5", "type": "Fee_transfer"}],
            "userCommands": [
                {
                    "id": "Cmd1",
                    "hash": "5Jhash",
                    "kind": "PAYMENT",
                    "nonce": 3,
                    "source": {"publicKey": "B62qsrc"},
                    "receiver": {"publicKey": "B62qdst"},
                    "amount": "1000",
                    "fee": "10",
                    "memo": "E4Y",
                    "failureReason": None,
                }
            ],
        },
    }


def _zkapp_json(valid_until, failure_reason):
    return {
        "id": "Zk",
        "hash": "5Jz",
        "zkappCommand": {
            "memo": "E4Y",
            "feePayer": {
                "body": {
                    "publicKey": "B62qpayer",
                    "fee": "100",
                    "nonce": "7",
                    "validUntil": valid_until,
                }
            },
        },
        "failureReason": failure_reason,
    }


@respx.mock
def test_best_chain_sends_a_null_max_length_and_reads_the_common_block_selection(client):
    route = _mock({"bestChain": [_block_json()]})
    (b,) = client.get_best_chain()
    sent = _sent(route)
    assert sent["query"].startswith("query BestChain(")
    assert sent["variables"] == {"maxLength": None}
    assert (b.height, b.global_slot_since_hard_fork, b.global_slot_since_genesis, b.epoch) == (
        12,
        30,
        40,
        1,
    )
    assert b.previous_state_hash == "3NKprev"
    assert b.block_creator == "B62qcreator"
    assert b.coinbase_receiver == "B62qcoinbase"
    assert b.staking_epoch == EpochData(seed="seedS", ledger_hash="jxS", length=7)
    assert b.next_epoch == EpochData(seed="seedN", ledger_hash="jxN")
    assert (b.date, b.utc_date) == ("1700000000000", "1700000000001")
    assert b.coinbase == Currency.from_nanomina(720000000000)
    assert b.coinbase_receiver_account == "B62qcoinbase"
    assert b.fee_transfers == [
        FeeTransfer(
            recipient="B62qfee", fee=Currency.from_nanomina(5), transfer_type="Fee_transfer"
        )
    ]
    u = b.user_commands[0]
    assert (u.id, u.nonce, u.source, u.receiver) == ("Cmd1", 3, "B62qsrc", "B62qdst")
    assert (u.amount, u.fee, u.failure_reason) == (
        Currency.from_nanomina(1000),
        Currency.from_nanomina(10),
        None,
    )


@respx.mock
def test_genesis_block_and_block_by_hash_or_height(client):
    _mock({"genesisBlock": _block_json()})
    assert client.get_genesis_block().state_hash == "3NKblock"

    route = _mock({"block": _block_json()})
    client.get_block(height=12)
    assert _sent(route)["variables"] == {"stateHash": None, "height": 12}
    client.get_block(state_hash="3NKblock")
    assert _sent(route)["variables"] == {"stateHash": "3NKblock", "height": None}
    with pytest.raises(ValueError):
        client.get_block()
    with pytest.raises(ValueError):
        client.get_block(state_hash="3NK", height=1)


@respx.mock
def test_daemon_status_new_fields_and_metrics(client):
    _mock(
        {
            "daemonStatus": {
                "syncStatus": "SYNCED",
                "highestUnvalidatedBlockLengthReceived": 9,
                "numAccounts": 5,
                "ledgerMerkleRoot": "jxRoot",
                "chainId": "chain",
                "catchupStatus": None,
                "blockProductionKeys": ["B62qbp"],
                "coinbaseReceiver": "B62qcb",
                "peers": [],
                "addrsAndPorts": {
                    "externalIp": "1.2.3.4",
                    "bindIp": "0.0.0.0",  # noqa: S104 - test data
                    "clientPort": 8301,
                    "libp2pPort": 8302,
                },
            }
        }
    )
    s = client.get_daemon_status()
    assert s.highest_unvalidated_block_length_received == 9
    assert (s.num_accounts, s.ledger_merkle_root, s.chain_id) == (5, "jxRoot", "chain")
    assert s.catchup_status is None
    assert s.block_production_keys == ["B62qbp"]
    assert s.coinbase_receiver == "B62qcb"
    assert s.addrs_and_ports is not None
    assert (s.addrs_and_ports.client_port, s.addrs_and_ports.libp2p_port) == (8301, 8302)

    _mock(
        {
            "daemonStatus": {
                "metrics": {
                    "blockProductionDelay": [1, 2],
                    "transactionPoolDiffReceived": 3,
                    "transactionPoolDiffBroadcasted": 4,
                    "transactionsAddedToPool": 5,
                    "transactionPoolSize": 6,
                    "snarkPoolDiffReceived": 7,
                    "snarkPoolDiffBroadcasted": 8,
                    "pendingSnarkWork": 9,
                    "snarkPoolSize": 10,
                }
            }
        }
    )
    m = client.get_daemon_metrics()
    assert m.block_production_delay == [1, 2]
    assert (m.transaction_pool_size, m.pending_snark_work, m.snark_pool_size) == (6, 9, 10)


@respx.mock
def test_account_sends_a_null_token_and_reads_new_fields(client):
    route = _mock(
        {
            "account": {
                "publicKey": "B62qacc",
                "nonce": "4",
                "delegate": None,
                "tokenId": "wSHV",
                "tokenSymbol": "MINA",
                "votingFor": "3NKvote",
                "receiptChainHash": "2mzReceipt",
                "balance": {"total": "100", "liquid": "60", "locked": "40", "blockHeight": "12"},
                "timing": {
                    "initialMinimumBalance": "50",
                    "cliffTime": "10",
                    "cliffAmount": "5",
                    "vestingPeriod": "2",
                    "vestingIncrement": "1",
                },
                "permissions": {
                    "editState": "Signature",
                    "send": "Signature",
                    "receive": "None",
                    "setVerificationKey": {"auth": "Signature", "txnVersion": "3"},
                },
                "zkappState": ["0", "1"],
                "provedState": False,
                "zkappUri": "",
            }
        }
    )
    a = client.get_account("B62qacc")
    assert _sent(route)["variables"] == {"publicKey": "B62qacc", "token": None}
    assert (a.nonce, a.token_symbol, a.voting_for) == (4, "MINA", "3NKvote")
    assert a.balance.block_height == 12
    assert a.balance.locked == Currency.from_nanomina(40)
    assert a.timing is not None
    assert a.timing.initial_minimum_balance == Currency.from_nanomina(50)
    assert (a.timing.cliff_time, a.timing.vesting_period) == (10, 2)
    assert a.permissions is not None
    assert a.permissions.receive == "None"
    assert a.permissions.set_verification_key is not None
    assert a.permissions.set_verification_key.txn_version == "3"
    assert a.zkapp_state == ["0", "1"]
    assert a.proved_state is False

    # An untimed account: the daemon sends a timing object of nulls.
    _mock(
        {
            "account": {
                "publicKey": "B62qacc",
                "nonce": "0",
                "tokenId": "wSHV",
                "balance": {"total": "1"},
                "timing": dict.fromkeys(
                    [
                        "initialMinimumBalance",
                        "cliffTime",
                        "cliffAmount",
                        "vestingPeriod",
                        "vestingIncrement",
                    ]
                ),
            }
        }
    )
    a = client.get_account("B62qacc")
    assert a.timing is None
    assert a.permissions is None

    _mock({"account": None})
    with pytest.raises(AccountNotFoundError):
        client.get_account("B62qnone")


@respx.mock
def test_pooled_commands(client):
    route = _mock(
        {
            "pooledUserCommands": [
                {
                    "id": "Cmd",
                    "hash": "5J",
                    "kind": "PAYMENT",
                    "nonce": 2,
                    "amount": "1",
                    "fee": "2",
                    "from": "B62qa",
                    "to": "B62qb",
                    "source": {"publicKey": "B62qa"},
                    "receiver": {"publicKey": "B62qb"},
                    "memo": "E4Y",
                    "failureReason": None,
                }
            ]
        }
    )
    (c,) = client.get_pooled_user_commands()
    assert _sent(route)["variables"] == {"publicKey": None}
    assert (c.nonce, c.from_, c.source, c.receiver, c.memo) == (
        "2",
        "B62qa",
        "B62qa",
        "B62qb",
        "E4Y",
    )
    # The dictionary keys of earlier versions still work.
    assert (c["from"], c["to"], c["nonce"]) == ("B62qa", "B62qb", "2")
    assert c.get("hash") == "5J"
    assert c.get("memo", "none") == "none"
    with pytest.raises(KeyError):
        c["memo"]

    route = _mock(
        {
            "pooledZkappCommands": [
                _zkapp_json(None, [{"index": "1", "failures": ["Invalid_fee_excess"]}])
            ]
        }
    )
    (z,) = client.get_pooled_zkapp_commands("B62qpayer")
    assert _sent(route)["variables"] == {"publicKey": "B62qpayer"}
    assert z.fee_payer.fee == Currency.from_nanomina(100)
    assert (z.fee_payer.nonce, z.fee_payer.valid_until) == (7, None)
    assert z.failure_reason == [ZkappFailure(index=1, failures=["Invalid_fee_excess"])]


@respx.mock
def test_send_payment_with_and_without_signature(client):
    route = _mock(
        {
            "sendPayment": {
                "payment": {
                    "id": "Cmd",
                    "hash": "5J",
                    "kind": "PAYMENT",
                    "nonce": "3",
                    "source": {"publicKey": "B62qa"},
                    "receiver": {"publicKey": "B62qb"},
                    "amount": "1000",
                    "fee": "10",
                    "memo": "E4Y",
                }
            }
        }
    )
    amount, fee = Currency.from_nanomina(1000), Currency.from_nanomina(10)
    r = client.send_payment("B62qa", "B62qb", amount, fee)
    assert _sent(route)["variables"]["signature"] is None
    assert (r.nonce, r.kind, r.source, r.receiver, r.amount, r.fee) == (
        3,
        "PAYMENT",
        "B62qa",
        "B62qb",
        amount,
        fee,
    )
    client.send_payment("B62qa", "B62qb", amount, fee, signature=SignatureInput("1", "2"))
    assert _sent(route)["variables"]["signature"] == {"field": "1", "scalar": "2"}

    route = _mock(
        {
            "sendDelegation": {
                "delegation": {"id": "Del", "hash": "5Jd", "nonce": "4", "amount": None}
            }
        }
    )
    d = client.send_delegation("B62qa", "B62qbp", fee)
    assert "signature" in _sent(route)["variables"]
    assert (d.nonce, d.amount) == (4, None)


@respx.mock
def test_send_zkapp_and_unlock_account(client):
    route = _mock({"sendZkapp": {"zkapp": _zkapp_json("99", None)}})
    command = {"feePayer": {}, "accountUpdates": [], "memo": ""}
    z = client.send_zkapp(command)
    assert _sent(route)["variables"] == {"input": {"zkappCommand": command}}
    assert z.fee_payer.valid_until == 99
    assert z.failure_reason is None

    route = _mock({"unlockAccount": {"publicKey": "B62qacc"}})
    assert client.unlock_account("B62qacc", "pw") == "B62qacc"
    assert _sent(route)["variables"] == {"input": {"publicKey": "B62qacc", "password": "pw"}}


@respx.mock
def test_execute_query(client):
    route = _mock({"syncStatus": "SYNCED"})
    data = client.execute_query("query S { syncStatus }", {"x": None}, "sync")
    assert data == {"syncStatus": "SYNCED"}
    assert _sent(route) == {"query": "query S { syncStatus }", "variables": {"x": None}}


@respx.mock
def test_transaction_status_and_small_queries(client):
    route = _mock({"transactionStatus": "INCLUDED"})
    assert client.get_transaction_status(zkapp_transaction="5Jz") == TransactionStatus.INCLUDED
    assert _sent(route)["variables"] == {"payment": None, "zkappTransaction": "5Jz"}
    assert client.get_transaction_status(payment="Cmd") == "INCLUDED"
    with pytest.raises(ValueError):
        client.get_transaction_status()

    _mock(
        {
            "genesisConstants": {
                "genesisTimestamp": "2024-01-01T00:00:00Z",
                "coinbase": "720000000000",
                "accountCreationFee": "1000000000",
            }
        }
    )
    g = client.get_genesis_constants()
    assert g.coinbase == Currency.from_nanomina(720000000000)
    assert g.account_creation_fee == Currency.from_nanomina(1000000000)

    _mock({"trackedAccounts": [{"publicKey": "B62qt", "balance": {"total": "42"}}]})
    (t,) = client.get_tracked_accounts()
    assert (t.public_key, t.balance) == ("B62qt", Currency.from_nanomina(42))

    _mock({"snarkPool": [{"fee": "10", "prover": "B62qp", "workIds": [3, "4"]}]})
    (w,) = client.get_snark_pool()
    assert (w.prover, w.fee, w.work_ids) == ("B62qp", Currency.from_nanomina(10), [3, 4])

    _mock({"fork_config": {"proof": {"fork": None}}})
    assert client.get_fork_config() == {"proof": {"fork": None}}
