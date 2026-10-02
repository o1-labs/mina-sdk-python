# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- The common API of the Mina SDKs, from
  [mina-sdk-spec](https://github.com/o1-labs/mina-sdk-spec) v0.1.2: `spec/`
  is a copy at the tag in `spec/VERSION`. `tests/test_spec.py` checks that
  the query strings are the specification's documents, and a CI job checks
  that `spec/` is the tag's copy.
- Methods of the common API that this SDK did not have: `get_daemon_metrics`,
  `get_genesis_block`, `get_block`, `get_pooled_zkapp_commands`,
  `get_transaction_status`, `get_genesis_constants`, `get_tracked_accounts`,
  `get_snark_pool`, `get_fork_config`, `send_zkapp` and `unlock_account`.
- Signatures made outside the daemon: `signature=SignatureInput(...)` on
  `send_payment` and `send_delegation`.
- Result fields of the common API: more `DaemonStatus` fields
  (`AddrsAndPorts`); `AccountData` token symbol, voting-for, receipt chain
  hash, timing, permissions and zkApp state; `AccountBalance.block_height`;
  `BlockInfo` previous state hash, epoch, block creator, coinbase receiver,
  epoch data, dates, ledger hashes, coinbase, fee transfers and user
  commands; kind, source, receiver, amount, fee and memo of a sent command.
- `AccountNotFoundError`, a `ValueError`, from `get_account`.
- `execute_query`, for custom GraphQL documents, as in the other SDKs.
- ITN client, `mina_sdk.itn` (extra `itn`, which adds `cryptography`):
  `ItnClient` for the daemon's ITN GraphQL server (`--itn-graphql-port`),
  with ed25519 request signing (`ItnKey`), the `auth` handshake, sequence
  numbers (one request at a time, a new auth after HTTP 412) and no repeat
  after a transport error. It covers every operation of
  `spec/itn-operations.graphql`, as the Rust, Go and JS SDKs do.
- Integration tests of the new methods.
- `DaemonConnectionError` exception (replaces shadowed `ConnectionError`)
- `Currency.__rmul__` for `3 * Currency(10)` support
- Export all public types from `mina_sdk`: `AccountBalance`, `AccountData`,
  `BlockInfo`, `DaemonStatus`, `PeerInfo`, `SendPaymentResult`,
  `SendDelegationResult`, `GraphQLError`, `DaemonConnectionError`,
  `CurrencyUnderflow`
- Input validation for `MinaDaemonClient` configuration parameters
- Docstrings on all public classes, methods, and dataclass fields
- 11 new unit tests (49 total)

### Fixed
- HTTP status code now checked before parsing JSON response body
- JSON decode errors are caught and wrapped as `DaemonConnectionError`
- Negative `Currency` values are rejected with `ValueError`

### Changed
- Every query is a named operation of the specification. Nullable variables
  are always sent, as null when omitted: `get_account` and
  `get_pooled_user_commands` use one document each
  (`queries.GET_ACCOUNT_WITH_TOKEN` and `queries.POOLED_USER_COMMANDS_ALL`
  are deprecated aliases), and `get_best_chain` sends `maxLength: null`.
- `get_pooled_user_commands` returns `PooledUserCommand` objects, not
  dictionaries. `command["hash"]` and `command.get("hash")` still work for the
  keys of the dictionaries; the daemon's `from` is the attribute `from_`.
- `SendPaymentResult` and `SendDelegationResult` are aliases of the new
  `SubmittedCommand`.
- `Currency.__mul__` only accepts `int` scalars (was also accepting `Currency`,
  which produced nonsensical nanomina-squared units)
- `ConnectionError` is now an alias for `DaemonConnectionError` (backwards compatible)

### Removed
- The schema drift check (`scripts/check_schema_drift.py`, the Schema Drift
  Check workflow and `src/mina_sdk/schema/`). The documents of this SDK are
  the documents of mina-sdk-spec, whose weekly drift job validates them
  against the lightnet daemons of `master`, `compatible` and `develop`.

## [0.1.0] - 2025-11-20

### Added
- Initial release
- `MinaDaemonClient` with GraphQL queries and mutations
- `Currency` type with nanomina-precision arithmetic
- Typed response dataclasses
- Automatic retry with configurable backoff
- Context manager support
- Unit tests with HTTP mocking
- Integration tests against live daemon
- CI workflows: lint, test, release, integration, schema drift
- PyPI publishing via trusted publishers
