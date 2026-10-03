# Mina Python SDK

[![CI](https://github.com/MinaProtocol/mina-sdk-python/actions/workflows/ci.yml/badge.svg)](https://github.com/MinaProtocol/mina-sdk-python/actions/workflows/ci.yml)
[![Integration Tests](https://github.com/MinaProtocol/mina-sdk-python/actions/workflows/integration.yml/badge.svg)](https://github.com/MinaProtocol/mina-sdk-python/actions/workflows/integration.yml)
[![PyPI version](https://img.shields.io/pypi/v/mina-sdk.svg)](https://pypi.org/project/mina-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/mina-sdk.svg)](https://pypi.org/project/mina-sdk/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Python SDK for interacting with [Mina Protocol](https://minaprotocol.com) nodes.

## Features

- **Daemon GraphQL client** -- query node status, accounts, blocks; send payments and delegations
- Typed response objects with `Currency` arithmetic
- Automatic retry with configurable backoff
- Context manager support for clean resource management

## Installation

```bash
pip install mina-sdk
```

For archive database support (coming soon):

```bash
pip install mina-sdk[archive]
```

## Quick Start

```python
from mina_sdk import MinaDaemonClient, Currency

with MinaDaemonClient() as client:
    # Check sync status
    print(client.get_sync_status())  # "SYNCED"

    # Query an account
    account = client.get_account("B62q...")
    print(f"Balance: {account.balance.total} MINA")

    # Send a payment
    result = client.send_payment(
        sender="B62qsender...",
        receiver="B62qreceiver...",
        amount=Currency("1.5"),
        fee=Currency("0.01"),
    )
    print(f"Tx hash: {result.hash}")
```

## Configuration

```python
client = MinaDaemonClient(
    graphql_uri="http://127.0.0.1:3085/graphql",  # default
    retries=3,        # retry failed requests (must be >= 1)
    retry_delay=5.0,  # seconds between retries (must be >= 0)
    timeout=30.0,     # HTTP timeout in seconds (must be > 0)
)
```

## API Reference

The Mina SDKs have the same API, defined in
[mina-sdk-spec](https://github.com/o1-labs/mina-sdk-spec). `spec/` is a copy
of it at the tag in `spec/VERSION`. `tests/test_spec.py` checks that this
SDK's queries are the specification's documents, and CI checks that `spec/`
is the tag's copy.

### Queries

| Method | Returns | Description |
|--------|---------|-------------|
| `get_sync_status()` | `str` | Node sync status (SYNCED, BOOTSTRAP, etc.) |
| `get_daemon_status()` | `DaemonStatus` | Daemon status: chain length, peers, addresses, block production keys |
| `get_daemon_metrics()` | `DaemonMetrics` | Transaction and snark pool metrics, block production delay |
| `get_network_id()` | `str` | Network identifier |
| `get_account(public_key, token_id=None)` | `AccountData` | Balance, nonce, delegate, timing, permissions, zkApp state |
| `get_best_chain(max_length=None)` | `list[BlockInfo]` | Recent blocks from the best chain |
| `get_genesis_block()` | `BlockInfo` | The genesis block |
| `get_block(state_hash=None, height=None)` | `BlockInfo` | One block; give exactly one of the two |
| `get_peers()` | `list[PeerInfo]` | Connected peers |
| `get_pooled_user_commands(public_key=None)` | `list[PooledUserCommand]` | Pending payments and delegations |
| `get_pooled_zkapp_commands(public_key=None)` | `list[ZkappCommandResult]` | Pending zkApp commands |
| `get_transaction_status(payment=None, zkapp_transaction=None)` | `TransactionStatus` | `PENDING`, `INCLUDED` or `UNKNOWN`; give exactly one ID |
| `get_genesis_constants()` | `GenesisConstants` | Genesis timestamp, coinbase, account creation fee |
| `get_tracked_accounts()` | `list[TrackedAccount]` | Accounts in the daemon's keystore |
| `get_snark_pool()` | `list[CompletedWork]` | Completed snark work |
| `get_fork_config()` | `Any` | The daemon's fork configuration (JSON) |
| `execute_query(query, variables=None, query_name="custom")` | `dict` | Run a custom GraphQL query |

### Mutations

| Method | Returns | Description |
|--------|---------|-------------|
| `send_payment(sender, receiver, amount, fee, signature=None)` | `SendPaymentResult` | Send a payment; `signature` for one made outside the daemon |
| `send_delegation(sender, delegate_to, fee, signature=None)` | `SendDelegationResult` | Delegate stake; `signature` likewise |
| `send_zkapp(zkapp_command)` | `ZkappCommandResult` | Send a signed zkApp command (JSON) |
| `unlock_account(public_key, password)` | `str` | Unlock a keystore account so the daemon can sign with it |
| `set_snark_worker(public_key)` | `str \| None` | Set/unset SNARK worker |
| `set_snark_work_fee(fee)` | `str` | Set SNARK work fee |

### ITN server (`mina_sdk.itn`)

A daemon started with `ITN_FEATURES=1`, `--itn-graphql-port` and `--itn-keys`
serves a second GraphQL API, which load testing tools use. `ItnClient` signs
each request with an ed25519 `ItnKey` whose public half must be in
`--itn-keys`, and it handles the daemon's sequence numbers (a new `auth`
after a daemon restart, HTTP 412). It needs the `itn` extra:

```bash
pip install 'mina-sdk[itn]'
```

```python
from mina_sdk.itn import ItnClient, ItnKey

key = ItnKey.from_base64(open("itn_sk").read())
print("start the daemon with --itn-keys", key.public_key_base64())

with ItnClient("http://127.0.0.1:3086/graphql", key) as itn:
    logs = itn.internal_logs(0)
    if logs:
        itn.flush_internal_logs(logs[-1].id)
```

| Method | GraphQL |
|--------|---------|
| `auth()` | `auth` (server UUID, sequence number, peer ID, block producer) |
| `slots_won()` | `slotsWon` |
| `internal_logs(start)` / `flush_internal_logs(end)` | `internalLogs` / `flushInternalLogs` |
| `schedule_payments(PaymentsDetails)` | `schedulePayments` |
| `schedule_zkapp_commands(ZkappCommandsDetails)` | `scheduleZkappCommands` |
| `stop_scheduled_transactions(handle)` | `stopScheduledTransactions` |
| `update_gating(GatingUpdate)` | `updateGating` |
| `stop_daemon(delay_seconds=None, clean_config=None)` | `stopDaemon` |
| `set_zkapp_command_limit(limit)` | `zkAppCommandLimit` |
| `execute_query(query, variables, query_name)` | any document, sequenced and signed |

These need a daemon with MinaProtocol/mina#19616; older daemons answer them
with a GraphQL error:

| Method | GraphQL |
|--------|---------|
| `commit_id()` | `auth { commitId }`: the daemon's git commit |
| `scheduled_transactions()` | `scheduledTransactions`: handles of the running schedulers |
| `schedule_payments_with_handle(PaymentsDetails, handle)` | `schedulePayments` with a caller-chosen handle |
| `schedule_zkapp_commands_with_handle(ZkappCommandsDetails, handle)` | `scheduleZkappCommands` with a caller-chosen handle |
| `create_accounts(CreateAccountsDetails, handle=None)` | `createAccounts`: keys at once, funding in the background under the handle |

A handle is a UUID that the caller chooses and records before the call. A
call with the handle of a running scheduler starts nothing and returns that
handle, so these calls may be repeated after a transport error.

Requests of one client are sent one at a time, because the daemon accepts
only its exact next sequence number; the client is safe to share between
threads. A sequenced request is never repeated after a transport error,
because the daemon may already have run it. Errors: `ItnUnauthorizedError`
(401), `ItnSequencingError` (412 after a new auth), `InvalidItnKeyError`, and
`DaemonConnectionError` whose `__cause__` is an `ItnHttpError` with the
status. The documents are those of `spec/itn-operations.graphql`. Integration
tests: set `MINA_ITN_URI` and `MINA_ITN_KEY` and run
`pytest tests/test_itn_integration.py`.

### Currency

```python
from mina_sdk import Currency

a = Currency(10)              # 10 MINA
b = Currency("1.5")           # 1.5 MINA
c = Currency.from_nanomina(1_000_000_000)  # 1 MINA

print(a + b)        # 11.500000000
print(a.nanomina)   # 10000000000
print(a > b)        # True
print(3 * b)        # 4.500000000
```

### Error Handling

```python
from mina_sdk import MinaDaemonClient, GraphQLError, DaemonConnectionError, CurrencyUnderflow

with MinaDaemonClient(retries=3, retry_delay=2.0) as client:
    try:
        account = client.get_account("B62q...")
    except ValueError as e:
        # Account not found on ledger
        print(f"Account does not exist: {e}")
    except GraphQLError as e:
        # Daemon returned a GraphQL-level error
        print(f"GraphQL error: {e}")
        print(f"Raw errors: {e.errors}")
    except DaemonConnectionError as e:
        # All retry attempts exhausted
        print(f"Cannot reach daemon after retries: {e}")

# Currency underflow
from mina_sdk import Currency, CurrencyUnderflow

try:
    result = Currency(1) - Currency(2)
except CurrencyUnderflow:
    print("Subtraction would result in negative balance")
```

### Data Types

All response types are importable from the top-level package:

```python
from mina_sdk import (
    AccountBalance,    # total, liquid, locked balances, block height
    AccountData,       # public_key, nonce, balance, delegate, timing, permissions, zkApp state
    BlockInfo,         # state_hash, height, slots, creator, epochs, ledger hashes, transactions
    DaemonStatus,      # sync_status, chain height, peers, uptime, addresses
    DaemonMetrics,     # pool sizes and diffs, block production delay
    PeerInfo,          # peer_id, host, port
    PooledUserCommand, # a pending payment or delegation
    SubmittedCommand,  # result of send_payment / send_delegation
    ZkappCommandResult,  # a pending or sent zkApp command
    CompletedWork,     # snark pool entry
    GenesisConstants,
    TrackedAccount,
    TransactionStatus,
    SignatureInput,    # field, scalar
)
```

## Development

```bash
git clone https://github.com/MinaProtocol/mina-sdk-python.git
cd mina-sdk-python
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
```

### Running integration tests

Integration tests require a running Mina daemon:

```bash
MINA_GRAPHQL_URI=http://127.0.0.1:3085/graphql \
MINA_TEST_SENDER_KEY=B62q... \
MINA_TEST_RECEIVER_KEY=B62q... \
pytest tests/test_integration.py -v
```

## Troubleshooting

**Connection refused / DaemonConnectionError**

The daemon is not running or not reachable at the configured URI. Check:
- Is the daemon running? (`mina client status`)
- Is the GraphQL port open? (default: 3085)
- Is `--insecure-rest-server` set if connecting from a different host?

**GraphQLError: field not found**

The SDK's queries may be out of sync with the daemon's GraphQL schema. This can happen after a daemon upgrade. Check the documents against your node with mina-sdk-spec: `python3 scripts/check.py --endpoint http://your-node:3085/graphql` (in a clone of [mina-sdk-spec](https://github.com/o1-labs/mina-sdk-spec)).

**Account not found**

`get_account()` raises `AccountNotFoundError` (a `ValueError`) when the account doesn't exist on the ledger. This is normal for new accounts that haven't received any transactions yet.

## License

Apache License 2.0
