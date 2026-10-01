"""Shared types for the Mina SDK."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CurrencyFormat(Enum):
    """Representation format for Mina currency values.

    WHOLE: 1 MINA = 10^9 nanomina
    NANO: atomic unit (nanomina)
    """

    WHOLE = 1
    NANO = 2


class CurrencyUnderflow(Exception):
    """Raised when a subtraction would result in a negative currency value."""

    pass


class Currency:
    """Convenience wrapper for Mina currency values with arithmetic support.

    Internally stores values as nanomina (the atomic unit, 10^-9 MINA).
    All values must be non-negative.  Supports addition, subtraction,
    multiplication, and comparison.

    Examples::

        a = Currency(10)                     # 10 MINA
        b = Currency("1.5")                  # 1.5 MINA
        c = Currency.from_nanomina(500_000_000)  # 0.5 MINA
        print(a + b)   # 11.500000000
        print(a > b)   # True
    """

    NANOMINA_PER_MINA = 1_000_000_000

    def __init__(self, value: int | float | str, fmt: CurrencyFormat = CurrencyFormat.WHOLE):
        if fmt == CurrencyFormat.WHOLE:
            if isinstance(value, int):
                self._nanomina = value * self.NANOMINA_PER_MINA
            elif isinstance(value, float):
                self._nanomina = self._parse_decimal(str(value))
            elif isinstance(value, str):
                self._nanomina = self._parse_decimal(value)
            else:
                raise TypeError(f"cannot construct Currency from {type(value)}")
        elif fmt == CurrencyFormat.NANO:
            if not isinstance(value, int):
                raise TypeError(f"nanomina value must be int, got {type(value)}")
            self._nanomina = value
        else:
            raise ValueError(f"invalid CurrencyFormat: {fmt}")

        if self._nanomina < 0:
            raise ValueError(f"Currency value must be non-negative, got {self._nanomina} nanomina")

    @staticmethod
    def _parse_decimal(s: str) -> int:
        """Parse a decimal MINA string like ``"1.5"`` into nanomina.

        Raises:
            ValueError: If the string has more than 9 decimal places or is
                not a valid decimal number.
        """
        segments = s.split(".")
        if len(segments) == 1:
            return int(segments[0]) * Currency.NANOMINA_PER_MINA
        elif len(segments) == 2:
            left, right = segments
            if len(right) <= 9:
                return int(left + right + "0" * (9 - len(right)))
            else:
                raise ValueError(f"invalid mina currency format: {s}")
        else:
            raise ValueError(f"invalid mina currency format: {s}")

    @classmethod
    def from_nanomina(cls, nanomina: int) -> Currency:
        """Create a Currency from a raw nanomina value."""
        return cls(nanomina, fmt=CurrencyFormat.NANO)

    @classmethod
    def from_graphql(cls, value: str) -> Currency:
        """Parse a currency value as returned by the GraphQL API (nanomina string).

        Args:
            value: A string of digits representing nanomina.
        """
        return cls(int(value), fmt=CurrencyFormat.NANO)

    @classmethod
    def random(cls, lower: Currency, upper: Currency) -> Currency:
        """Return a random Currency between *lower* and *upper* (inclusive).

        Raises:
            TypeError: If bounds are not Currency instances.
            ValueError: If upper < lower.
        """
        if not (isinstance(lower, Currency) and isinstance(upper, Currency)):
            raise TypeError("bounds must be Currency instances")
        if upper.nanomina < lower.nanomina:
            raise ValueError("upper bound must be >= lower bound")
        if lower.nanomina == upper.nanomina:
            return lower
        delta = random.randint(0, upper.nanomina - lower.nanomina)
        return cls.from_nanomina(lower.nanomina + delta)

    @property
    def nanomina(self) -> int:
        """The value in nanomina (atomic unit)."""
        return self._nanomina

    @property
    def mina(self) -> str:
        """Decimal string representation in whole MINA (e.g. ``"1.500000000"``)."""
        s = str(self._nanomina)
        if len(s) > 9:
            return s[:-9] + "." + s[-9:]
        else:
            return "0." + "0" * (9 - len(s)) + s

    def to_nanomina_str(self) -> str:
        """String representation for GraphQL API (nanomina)."""
        return str(self._nanomina)

    def __str__(self) -> str:
        return self.mina

    def __repr__(self) -> str:
        return f"Currency({self.mina})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Currency):
            return self._nanomina == other._nanomina
        return NotImplemented

    def __lt__(self, other: Currency) -> bool:
        if isinstance(other, Currency):
            return self._nanomina < other._nanomina
        return NotImplemented

    def __le__(self, other: Currency) -> bool:
        if isinstance(other, Currency):
            return self._nanomina <= other._nanomina
        return NotImplemented

    def __gt__(self, other: Currency) -> bool:
        if isinstance(other, Currency):
            return self._nanomina > other._nanomina
        return NotImplemented

    def __ge__(self, other: Currency) -> bool:
        if isinstance(other, Currency):
            return self._nanomina >= other._nanomina
        return NotImplemented

    def __add__(self, other: Currency) -> Currency:
        if isinstance(other, Currency):
            return Currency.from_nanomina(self._nanomina + other._nanomina)
        return NotImplemented

    def __sub__(self, other: Currency) -> Currency:
        if isinstance(other, Currency):
            result = self._nanomina - other._nanomina
            if result < 0:
                raise CurrencyUnderflow(f"subtraction would result in negative: {self} - {other}")
            return Currency.from_nanomina(result)
        return NotImplemented

    def __mul__(self, other: int) -> Currency:
        """Multiply currency by an integer scalar.

        Multiplying two Currency values is not supported because
        nanomina * nanomina produces nonsensical units.
        """
        if isinstance(other, int):
            return Currency.from_nanomina(self._nanomina * other)
        return NotImplemented

    def __rmul__(self, other: int) -> Currency:
        """Support ``3 * Currency(10)`` in addition to ``Currency(10) * 3``."""
        return self.__mul__(other)

    def __hash__(self) -> int:
        return hash(self._nanomina)


@dataclass(frozen=True)
class AccountBalance:
    """Balance breakdown for a Mina account.

    Attributes:
        total: Total balance (liquid + locked).
        liquid: Available balance for transactions.
        locked: Balance locked by a vesting schedule.
        block_height: Height of the block the balance was read at.
    """

    total: Currency
    liquid: Currency | None = None
    locked: Currency | None = None
    block_height: int | None = None


@dataclass(frozen=True)
class AccountTiming:
    """Vesting schedule of a timed account."""

    initial_minimum_balance: Currency | None = None
    cliff_time: int | None = None
    cliff_amount: Currency | None = None
    vesting_period: int | None = None
    vesting_increment: Currency | None = None


@dataclass(frozen=True)
class VerificationKeyPermission:
    """The ``setVerificationKey`` permission: an auth level and a transaction version."""

    auth: str
    txn_version: str


@dataclass(frozen=True)
class AccountPermissions:
    """An account's permissions, as the daemon names the authorization levels
    (for example ``Signature``, ``Proof``, ``None``)."""

    edit_state: str | None = None
    send: str | None = None
    receive: str | None = None
    access: str | None = None
    set_delegate: str | None = None
    set_permissions: str | None = None
    set_verification_key: VerificationKeyPermission | None = None
    set_zkapp_uri: str | None = None
    edit_action_state: str | None = None
    set_token_symbol: str | None = None
    increment_nonce: str | None = None
    set_voting_for: str | None = None
    set_timing: str | None = None


@dataclass(frozen=True)
class AccountData:
    """On-ledger account state.

    Attributes:
        public_key: Base58-encoded public key.
        nonce: Transaction counter for replay protection.
        balance: Balance breakdown.
        delegate: Public key this account delegates stake to.
        token_id: Token identifier (default token for MINA).
        timing: Vesting schedule; ``None`` for an untimed account.
        zkapp_state: zkApp state; ``None`` for an account that is not a zkApp.
    """

    public_key: str
    nonce: int
    balance: AccountBalance
    delegate: str | None = None
    token_id: str | None = None
    token_symbol: str | None = None
    voting_for: str | None = None
    receipt_chain_hash: str | None = None
    timing: AccountTiming | None = None
    permissions: AccountPermissions | None = None
    zkapp_state: list[str] | None = None
    proved_state: bool | None = None
    zkapp_uri: str | None = None


@dataclass(frozen=True)
class PeerInfo:
    """A connected libp2p peer.

    Attributes:
        peer_id: Libp2p peer identifier.
        host: IP address or hostname.
        port: Libp2p listening port.
    """

    peer_id: str
    host: str
    port: int


@dataclass(frozen=True)
class AddrsAndPorts:
    """The daemon's network addresses and ports."""

    external_ip: str
    bind_ip: str
    client_port: int
    libp2p_port: int


@dataclass(frozen=True)
class DaemonStatus:
    """Comprehensive daemon status.

    Attributes:
        sync_status: Current sync state (SYNCED, BOOTSTRAP, etc.).
        blockchain_length: Height of the node's best tip.
        highest_block_length_received: Highest block height seen from peers.
        uptime_secs: Seconds since daemon started.
        peers: Connected peers (``None`` if not available).
        commit_id: Git commit hash of the running binary.
        state_hash: Base58-encoded state hash of the best tip.
    """

    sync_status: str
    blockchain_length: int | None = None
    highest_block_length_received: int | None = None
    uptime_secs: int | None = None
    peers: list[PeerInfo] | None = None
    commit_id: str | None = None
    state_hash: str | None = None
    highest_unvalidated_block_length_received: int | None = None
    num_accounts: int | None = None
    ledger_merkle_root: str | None = None
    chain_id: str | None = None
    catchup_status: list[str] | None = None
    block_production_keys: list[str] | None = None
    coinbase_receiver: str | None = None
    addrs_and_ports: AddrsAndPorts | None = None


@dataclass(frozen=True)
class DaemonMetrics:
    """Transaction pool, snark pool and block production metrics of the daemon."""

    block_production_delay: list[int]
    transaction_pool_diff_received: int
    transaction_pool_diff_broadcasted: int
    transactions_added_to_pool: int
    transaction_pool_size: int
    snark_pool_diff_received: int
    snark_pool_diff_broadcasted: int
    pending_snark_work: int
    snark_pool_size: int


@dataclass(frozen=True)
class EpochData:
    """Seed and ledger hash of an epoch; ``length`` only for the staking epoch."""

    seed: str
    ledger_hash: str
    length: int | None = None


@dataclass(frozen=True)
class FeeTransfer:
    """A fee transfer in a block. ``transfer_type`` is the daemon's ``type``."""

    recipient: str
    fee: Currency
    transfer_type: str


@dataclass(frozen=True)
class BlockTransaction:
    """A user command in a block."""

    id: str
    hash: str
    kind: str
    nonce: int
    source: str
    receiver: str
    amount: Currency
    fee: Currency
    memo: str
    failure_reason: str | None = None


@dataclass(frozen=True)
class BlockInfo:
    """A block (from ``get_best_chain``, ``get_genesis_block`` or ``get_block``).

    Attributes:
        state_hash: Base58-encoded state hash.
        height: Block height (blockchain length at this block).
        global_slot_since_hard_fork: Slot number relative to last hard fork.
        global_slot_since_genesis: Absolute slot number since genesis.
        creator_pk: Block producer's public key.
        command_transaction_count: Number of user commands in this block.
        coinbase_receiver: The consensus state's ``coinbaseReceiever``.
    """

    state_hash: str
    height: int
    global_slot_since_hard_fork: int
    global_slot_since_genesis: int
    creator_pk: str
    command_transaction_count: int
    previous_state_hash: str = ""
    epoch: int = 0
    block_creator: str = ""
    coinbase_receiver: str | None = None
    staking_epoch: EpochData | None = None
    next_epoch: EpochData | None = None
    date: str = ""
    utc_date: str = ""
    snarked_ledger_hash: str = ""
    staged_ledger_hash: str = ""
    coinbase: Currency | None = None
    coinbase_receiver_account: str | None = None
    fee_transfers: list[FeeTransfer] = field(default_factory=list)
    user_commands: list[BlockTransaction] = field(default_factory=list)


# The keys of the dictionaries that get_pooled_user_commands returned before
# it returned PooledUserCommand, and the attribute of each.
_POOLED_COMMAND_KEYS = {
    "id": "id",
    "hash": "hash",
    "kind": "kind",
    "nonce": "nonce",
    "amount": "amount",
    "fee": "fee",
    "from": "from_",
    "to": "to",
}


@dataclass(frozen=True)
class PooledUserCommand:
    """A pending payment or delegation in the transaction pool.

    ``from_`` is the daemon's ``from``. For compatibility with the dictionaries
    that earlier versions returned, ``command["from"]``, ``command.get("from")``
    and the other keys ``id``, ``hash``, ``kind``, ``nonce``, ``amount``,
    ``fee`` and ``to`` also work.
    """

    id: str
    hash: str
    kind: str
    nonce: str
    amount: str
    fee: str
    from_: str
    to: str
    source: str = ""
    receiver: str = ""
    memo: str = ""
    failure_reason: str | None = None

    def __getitem__(self, key: str) -> Any:
        if key not in _POOLED_COMMAND_KEYS:
            raise KeyError(key)
        return getattr(self, _POOLED_COMMAND_KEYS[key])

    def get(self, key: str, default: Any = None) -> Any:
        """Like ``dict.get``, for the keys of earlier versions."""
        try:
            return self[key]
        except KeyError:
            return default


@dataclass(frozen=True)
class SubmittedCommand:
    """A payment or delegation that the daemon accepted into its pool.

    Attributes:
        id: Opaque transaction identifier.
        hash: Base58-encoded transaction hash.
        nonce: The nonce used for this transaction.
    """

    id: str
    hash: str
    nonce: int
    kind: str = ""
    source: str = ""
    receiver: str = ""
    amount: Currency | None = None
    fee: Currency | None = None
    memo: str = ""


# The results of send_payment and send_delegation.
SendPaymentResult = SubmittedCommand
SendDelegationResult = SubmittedCommand


@dataclass(frozen=True)
class SignatureInput:
    """A signature made outside the daemon, for example with mina-signer."""

    field: str
    scalar: str


@dataclass(frozen=True)
class ZkappFeePayer:
    """The fee payer of a zkApp command."""

    public_key: str
    fee: Currency
    nonce: int
    valid_until: int | None = None


@dataclass(frozen=True)
class ZkappFailure:
    """Why an account update of a zkApp command failed."""

    index: int | None
    failures: list[str]


@dataclass(frozen=True)
class ZkappCommandResult:
    """A zkApp command in the pool, or one just sent.

    ``failure_reason`` has one entry for each failing account update, and is
    ``None`` if the command did not fail.
    """

    id: str
    hash: str
    memo: str
    fee_payer: ZkappFeePayer
    failure_reason: list[ZkappFailure] | None = None


@dataclass(frozen=True)
class CompletedWork:
    """Completed snark work in the snark pool."""

    prover: str
    fee: Currency
    work_ids: list[int]


class TransactionStatus(str, Enum):
    """The status of a transaction. Members compare equal to the daemon's strings."""

    PENDING = "PENDING"
    INCLUDED = "INCLUDED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class GenesisConstants:
    """The network's genesis constants."""

    genesis_timestamp: str
    coinbase: Currency
    account_creation_fee: Currency


@dataclass(frozen=True)
class TrackedAccount:
    """An account the daemon tracks (one of its wallet keys)."""

    public_key: str
    balance: Currency


def _parse_response(data: dict[str, Any], path: list[str]) -> Any:
    """Navigate a nested dict by a list of keys, raising clear errors on missing fields."""
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise ValueError(f"missing field '{key}' in response at path {path}")
        current = current[key]
    return current
