# Mina SDK common API

The Mina SDKs (`mina-sdk-rust`, `mina-sdk-go`, `mina-sdk-js`,
`mina-sdk-python`) have the same
client API for the daemon's public GraphQL server (default port 3085). This
document and [`operations.graphql`](operations.graphql) define it.
[`ITN.md`](ITN.md) defines the client of the daemon's ITN server.

Each SDK keeps a copy of these files at a release tag of this repository
(`spec/VERSION`), and a test that its query strings are the documents of
`operations.graphql`, up to white space. To change the API, change this
repository first, make a release, then update every SDK with
`scripts/sync.sh`.

## Methods

Names follow each language's style. Arguments in brackets are optional.

| Operation | Rust | Go | JS | Python | Arguments | Returns |
|:--|:--|:--|:--|:--|:--|:--|
| `SyncStatus` | `get_sync_status` | `GetSyncStatus` | `getSyncStatus` | `get_sync_status` | – | `SyncStatus` |
| `DaemonStatus` | `get_daemon_status` | `GetDaemonStatus` | `getDaemonStatus` | `get_daemon_status` | – | `DaemonStatus` |
| `DaemonMetrics` | `get_daemon_metrics` | `GetDaemonMetrics` | `getDaemonMetrics` | `get_daemon_metrics` | – | `DaemonMetrics` |
| `NetworkId` | `get_network_id` | `GetNetworkID` | `getNetworkId` | `get_network_id` | – | string |
| `Account` | `get_account` | `GetAccount` | `getAccount` | `get_account` | public key, [token ID] | `AccountData` |
| `BestChain` | `get_best_chain` | `GetBestChain` | `getBestChain` | `get_best_chain` | [max length] | list of `BlockInfo` |
| `GenesisBlock` | `get_genesis_block` | `GetGenesisBlock` | `getGenesisBlock` | `get_genesis_block` | – | `BlockInfo` |
| `Block` | `get_block` | `GetBlock` | `getBlock` | `get_block` | state hash **or** height | `BlockInfo` |
| `Peers` | `get_peers` | `GetPeers` | `getPeers` | `get_peers` | – | list of `PeerInfo` |
| `PooledUserCommands` | `get_pooled_user_commands` | `GetPooledUserCommands` | `getPooledUserCommands` | `get_pooled_user_commands` | [public key] | list of `PooledUserCommand` |
| `PooledZkappCommands` | `get_pooled_zkapp_commands` | `GetPooledZkappCommands` | `getPooledZkappCommands` | `get_pooled_zkapp_commands` | [public key] | list of `ZkappCommandResult` |
| `TransactionStatus` | `get_transaction_status` | `GetTransactionStatus` | `getTransactionStatus` | `get_transaction_status` | payment ID **or** zkApp transaction ID | `TransactionStatus` |
| `GenesisConstants` | `get_genesis_constants` | `GetGenesisConstants` | `getGenesisConstants` | `get_genesis_constants` | – | `GenesisConstants` |
| `TrackedAccounts` | `get_tracked_accounts` | `GetTrackedAccounts` | `getTrackedAccounts` | `get_tracked_accounts` | – | list of `TrackedAccount` |
| `SnarkPool` | `get_snark_pool` | `GetSnarkPool` | `getSnarkPool` | `get_snark_pool` | – | list of `CompletedWork` |
| `ForkConfig` | `get_fork_config` | `GetForkConfig` | `getForkConfig` | `get_fork_config` | – | JSON value |
| `SendPayment` | `send_payment` | `SendPayment` | `sendPayment` | `send_payment` | payment, [signature] | `SubmittedCommand` |
| `SendDelegation` | `send_delegation` | `SendDelegation` | `sendDelegation` | `send_delegation` | delegation, [signature] | `SubmittedCommand` |
| `SendZkapp` | `send_zkapp` | `SendZkapp` | `sendZkapp` | `send_zkapp` | zkApp command (JSON) | `ZkappCommandResult` |
| `UnlockAccount` | `unlock_account` | `UnlockAccount` | `unlockAccount` | `unlock_account` | public key, password | public key |
| `SetSnarkWorker` | `set_snark_worker` | `SetSnarkWorker` | `setSnarkWorker` | `set_snark_worker` | [public key] | previous worker or null |
| `SetSnarkWorkFee` | `set_snark_work_fee` | `SetSnarkWorkFee` | `setSnarkWorkFee` | `set_snark_work_fee` | fee | previous fee |

Every SDK also has a custom-query method (Rust and Python `execute_query`,
Go `Request`, JS `executeQuery`) that uses the same transport, retries and
errors.

## Rules

- **Nullable variables.** An SDK always sends every declared variable, as
  null when the caller omits it. The daemon rejects a declared variable that
  is absent from the request.
- **Signatures.** `SendPayment` and `SendDelegation` take an optional
  signature (`{ field, scalar }`, for example from `mina-signer`). Without
  one, the daemon signs with a key from its own keystore, which must be
  unlocked (`UnlockAccount`).
- **Exactly one.** `Block` needs exactly one of state hash and height, and
  `TransactionStatus` exactly one of payment ID and zkApp transaction ID. The
  SDK rejects any other combination before it sends the request.
- **Amounts** are `Currency` (nanomina) where the daemon sends `Amount`,
  `Fee` or `Balance`. Other numbers that the daemon sends as strings (nonces,
  slots, lengths) are integers.
- **Errors.** A GraphQL `errors` array is a GraphQL error and is not retried.
  A transport failure or an HTTP error status is retried as configured, then
  reported as a connection error. `GetAccount` reports a null account as
  "account not found".

## Result types

Field names are shown in camelCase; Rust and Python use snake_case and Go
PascalCase. Python names the daemon's `from` field `from_`, because `from`
is a keyword.
`?` marks a field that can be null or absent.

The types are the union of what the SDKs returned before this API, so no
caller loses a field. Where an SDK already had a field or a type under
another name, it keeps that name (for example Go `CreatorPK` and Rust
`creator_pk` for `creatorPublicKey`, and the JS type `Block` for the result
of `getBlock`), and adds the fields of this document to it. Python's
`PooledUserCommand` also answers the dictionary keys of its earlier
dictionary result.

**`DaemonStatus`**: `syncStatus`, `blockchainLength?`,
`highestBlockLengthReceived?`, `highestUnvalidatedBlockLengthReceived?`,
`uptimeSecs?`, `stateHash?`, `commitId?`, `numAccounts?`,
`ledgerMerkleRoot?`, `chainId?`, `catchupStatus?` (list of strings),
`blockProductionKeys` (list), `coinbaseReceiver?`, `peers` (list of
`PeerInfo`), `addrsAndPorts?` (`externalIp`, `bindIp`, `clientPort`,
`libp2pPort`).

**`DaemonMetrics`**: `blockProductionDelay` (list of integers),
`transactionPoolDiffReceived`, `transactionPoolDiffBroadcasted`,
`transactionsAddedToPool`, `transactionPoolSize`, `snarkPoolDiffReceived`,
`snarkPoolDiffBroadcasted`, `pendingSnarkWork`, `snarkPoolSize`.

**`PeerInfo`**: `peerId`, `host`, `port` (the libp2p port).

**`AccountData`**: `publicKey`, `nonce`, `delegate?`, `tokenId`,
`tokenSymbol?`, `votingFor?`, `receiptChainHash?`, `balance` (`total`,
`liquid?`, `locked?`, `blockHeight?`), `timing?` (`initialMinimumBalance`,
`cliffTime`, `cliffAmount`, `vestingPeriod`, `vestingIncrement`),
`permissions?` (`editState`, `send`, `receive`, `access`, `setDelegate`,
`setPermissions`, `setVerificationKey` (`auth`, `txnVersion`),
`setZkappUri`, `editActionState`, `setTokenSymbol`, `incrementNonce`,
`setVotingFor`, `setTiming`), `zkappState?` (list of strings),
`provedState?`, `zkappUri?`.

**`BlockInfo`** (for `BestChain`, `GenesisBlock` and `Block`): `stateHash`,
`previousStateHash`, `height`, `globalSlotSinceHardFork` (`slot`),
`globalSlotSinceGenesis`, `epoch`, `creatorPublicKey`, `blockCreator`,
`coinbaseReceiver?` (the consensus state's `coinbaseReceiever`),
`commandTransactionCount`, `stakingEpoch` (`length`, `seed`, `ledgerHash`),
`nextEpoch` (`seed`, `ledgerHash`), `date`, `utcDate`, `snarkedLedgerHash`,
`stagedLedgerHash`, `coinbase`, `coinbaseReceiverAccount?`, `feeTransfers`
(list of `recipient`, `fee`, `type`), `userCommands` (list of
`BlockTransaction`).

**`BlockTransaction`**: `id`, `hash`, `kind`, `nonce`, `source`, `receiver`,
`amount`, `fee`, `memo`, `failureReason?`.

**`PooledUserCommand`**: `id`, `hash`, `kind`, `nonce`, `amount`, `fee`,
`from`, `to`, `source`, `receiver`, `memo`, `failureReason?`.

**`SubmittedCommand`**: `id`, `hash`, `kind`, `nonce`, `source`, `receiver`,
`amount`, `fee`, `memo`.

**`ZkappCommandResult`**: `id`, `hash`, `memo`, `feePayer` (`publicKey`,
`fee`, `nonce`, `validUntil?`), `failureReason?` (list of `index?` and
`failures`).

**`CompletedWork`**: `prover`, `fee`, `workIds` (list of integers).

**`TransactionStatus`**: one of `PENDING`, `INCLUDED`, `UNKNOWN`.

**`GenesisConstants`**: `genesisTimestamp`, `coinbase`, `accountCreationFee`.

**`TrackedAccount`**: `publicKey`, `balance` (total).

## Outside this API

- Trustless block verification (`verifyPrecomputedBlock`, `checkBlockClaims`)
  is a feature of `mina-sdk-js` only. It needs a WASM proof verifier and is
  not a GraphQL call.
