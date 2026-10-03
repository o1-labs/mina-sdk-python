# Mina SDK ITN API

A daemon started with `ITN_FEATURES=1`, `--itn-graphql-port <port>` and
`--itn-keys <base64 ed25519 public keys>` serves a second GraphQL API, the
ITN server (schema `Mina_graphql.schema_itn`, see
[`schema/itn.graphql`](https://github.com/o1-labs/mina-sdk-spec/blob/main/schema/itn.graphql)). Load testing tools use it to
schedule payments and zkApp commands, read internal logs, change connection
gating and stop the daemon.

The Mina SDKs have the same ITN client (Python: `mina_sdk.itn`, with the
extra `mina-sdk[itn]`). This document and
[`itn-operations.graphql`](itn-operations.graphql) define it. The rules of
[`SPEC.md`](SPEC.md) apply: each method sends one named operation, and
nullable variables are always sent, as null when the caller omits them.

## Authentication protocol

Every request must be signed with an ed25519 key whose public half is in
`--itn-keys`. The daemon reads the `Authorization` header:

- `Signature <pk> <sig>`: the signature covers the request body. The daemon
  accepts this form for the `Auth` operation only. Every other operation
  answers "Missing sequence information".
- `Signature <pk> <sig> ; Sequencing <uuid> <n>`: the signature covers the
  big-endian `u16` `n`, then the server UUID, then the body. `n` must be
  exactly the daemon's sequence number for this public key. It starts at 0,
  goes up by one (wrapping at 2^16) after each accepted sequenced request,
  and is shared by all clients that sign with the same key.

`pk` and `sig` are standard base64. The key is a 32-byte ed25519 seed,
stored as base64.

A client must:

1. Run `Auth` to learn the server UUID and the sequence number.
2. Send sequenced requests one at a time, because the daemon accepts only the
   exact next number.
3. On HTTP 412 (the daemon restarted, or another client used the number), run
   `Auth` again and repeat the request once.
4. On HTTP 401 (a bad signature or an unknown key), fail. Do not repeat.
5. After a transport error on a sequenced request, fail. Do not repeat,
   because the daemon may already have run it. The next request runs `Auth`
   again.

## Methods

| Operation | Rust | Go | JS | Python | Arguments | Returns |
|:--|:--|:--|:--|:--|:--|:--|
| `Auth` | `auth` | `Auth` | `auth` | `auth` | – | server UUID, sequence number, libp2p port, peer ID, block producer flag |
| `SlotsWon` | `slots_won` | `SlotsWon` | `slotsWon` | `slots_won` | – | list of global slots |
| `InternalLogs` | `internal_logs` | `InternalLogs` | `internalLogs` | `internal_logs` | start log ID | list of logs (`id`, `timestamp`, `message`, `metadata` (`item`, `value`), `process?`) |
| `FlushInternalLogs` | `flush_internal_logs` | `FlushInternalLogs` | `flushInternalLogs` | `flush_internal_logs` | end log ID | string |
| `SchedulePayments` | `schedule_payments` | `SchedulePayments` | `schedulePayments` | `schedule_payments` | `PaymentsDetails` | handle |
| `ScheduleZkappCommands` | `schedule_zkapp_commands` | `ScheduleZkappCommands` | `scheduleZkappCommands` | `schedule_zkapp_commands` | `ZkappCommandsDetails` | handle |
| `StopScheduledTransactions` | `stop_scheduled_transactions` | `StopScheduledTransactions` | `stopScheduledTransactions` | `stop_scheduled_transactions` | handle | string |
| `UpdateGating` | `update_gating` | `UpdateGating` | `updateGating` | `update_gating` | `GatingUpdate` | string |
| `StopDaemon` | `stop_daemon` | `StopDaemon` | `stopDaemon` | `stop_daemon` | [delay seconds], [clean config] | string |
| `ZkappCommandLimit` | `set_zkapp_command_limit` | `SetZkappCommandLimit` | `setZkappCommandLimit` | `set_zkapp_command_limit` | limit or null | limit now in force |

### Operations for harness support

These operations need a daemon with MinaProtocol/mina#19616. Older daemons
reject them, so a client uses them only against such daemons; the operations
above do not change. A client can call `CommitId` first: an older daemon
answers it with a GraphQL error.

| Operation | Rust | Go | JS | Python | Arguments | Returns |
|:--|:--|:--|:--|:--|:--|:--|
| `CommitId` | `commit_id` | `CommitID` | `commitId` | `commit_id` | – | the daemon's git commit |
| `ScheduledTransactions` | `scheduled_transactions` | `ScheduledTransactions` | `scheduledTransactions` | `scheduled_transactions` | – | handles of the running schedulers |
| `SchedulePaymentsWithHandle` | `schedule_payments_with_handle` | `SchedulePaymentsWithHandle` | `schedulePaymentsWithHandle` | `schedule_payments_with_handle` | `PaymentsDetails`, handle | handle |
| `ScheduleZkappCommandsWithHandle` | `schedule_zkapp_commands_with_handle` | `ScheduleZkappCommandsWithHandle` | `scheduleZkappCommandsWithHandle` | `schedule_zkapp_commands_with_handle` | `ZkappCommandsDetails`, handle | handle |
| `CreateAccounts` | `create_accounts` | `CreateAccounts` | `createAccounts` | `create_accounts` | `CreateAccountsDetails`, [handle] | handle and the new accounts (public and private key) |

- **Handles.** A handle is a UUID that the client chooses. The client records
  it before it sends the request, so that it can find the scheduler again
  after a lost response or a restart. A request with the handle of a running
  scheduler starts nothing and returns that handle; so a repeat after a
  transport error is safe for these mutations, unlike the others.
- **`ScheduledTransactions`** lists the handles of the running payment and
  zkApp schedulers and account-creation jobs. A client that lost its own
  record can stop each of them with `StopScheduledTransactions`.
- **`CreateAccounts`** replaces `mina advanced itn-create-accounts`, which
  talks to the daemon over its bin_prot RPC. It returns the keys at once and
  funds the accounts in the background under the handle: a client waits until
  `ScheduledTransactions` no longer lists the handle. The amount is divided
  among the accounts, and each account pays the account creation fee out of
  its share.

The input types `PaymentsDetails`, `ZkappCommandsDetails` and `GatingUpdate`
have the fields of [`schema/itn.graphql`](https://github.com/o1-labs/mina-sdk-spec/blob/main/schema/itn.graphql). Every SDK also
has a custom-query method that signs and sequences any document.

## Notes

- The daemon ignores input fields that it does not know. A field that exists
  only on a daemon branch (for example `nonDefaultToken` on
  `georgeee/itn-arbitrary-cap-custom-token`) has no effect on other daemons.
- `StopDaemon` has a minimum delay of 5 seconds in the daemon.
