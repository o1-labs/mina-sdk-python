"""Inputs and results of the ITN client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mina_sdk.types import Currency


@dataclass(frozen=True)
class ItnAuth:
    """The result of the auth query.

    Attributes:
        server_uuid: UUID of the ITN GraphQL server; new after each daemon restart.
        signer_sequence_number: The number the next sequenced request of this
            key must carry.
        libp2p_port: The node's libp2p port.
        peer_id: The node's libp2p peer ID; ``None`` if the daemon sent none.
        is_block_producer: Whether the node produces blocks.
    """

    server_uuid: str
    signer_sequence_number: int
    libp2p_port: int
    peer_id: str | None
    is_block_producer: bool


@dataclass(frozen=True)
class LogMetadatum:
    """One (item, value) pair of an internal log; the value is any JSON value."""

    item: str
    value: Any


@dataclass(frozen=True)
class ItnLog:
    """One entry of the daemon's internal log.

    Attributes:
        id: ID of the log; IDs increase.
        process: Process that sent the log if it is not the daemon (prover or
            verifier); ``None`` for the daemon.
    """

    id: int
    timestamp: str
    message: str
    metadata: list[LogMetadatum]
    process: str | None = None


@dataclass(frozen=True)
class PaymentsDetails:
    """The input of ``schedule_payments``.

    Attributes:
        duration_min: Length of the scheduler run, in minutes.
        tps: Frequency of transactions, per second.
        memo_prefix: The memo, up to 32 characters.
        amount: Amount of each payment.
        receiver: Public key of the receiver of the payments.
        senders: Base58 private keys of the accounts to send from.
    """

    duration_min: int
    tps: float
    memo_prefix: str
    max_fee: Currency
    min_fee: Currency
    amount: Currency
    receiver: str
    senders: list[str] = field(default_factory=list)

    def to_variables(self) -> dict[str, Any]:
        return {
            "durationMin": self.duration_min,
            "tps": self.tps,
            "memoPrefix": self.memo_prefix,
            "maxFee": self.max_fee.to_nanomina_str(),
            "minFee": self.min_fee.to_nanomina_str(),
            "amount": self.amount.to_nanomina_str(),
            "receiver": self.receiver,
            "senders": list(self.senders),
        }


@dataclass(frozen=True)
class ZkappCommandsDetails:
    """The input of ``schedule_zkapp_commands``.

    Attributes:
        max_account_updates: Each generated zkApp transaction has
            2*max_account_updates+2 account updates (including balancing and
            fee payer). ``None`` sends null, and the daemon uses its default.
        max_cost: Generate max-cost zkApp commands.
        account_queue_size: Size of the queue of recently used accounts.
        deployment_fee: Fee of the initial deployment of zkApp accounts.
        init_balance: Initial balance of the zkApp accounts deployed for the test.
        no_precondition: Disable the precondition in account updates.
        duration_min: Length of the scheduler run, in minutes.
        tps: Frequency of transactions, per second.
        num_new_accounts: Number of zkApp accounts the scheduler creates during
            the test.
        num_zkapps_to_deploy: Number of zkApp accounts deployed at the start of
            the test.
        fee_payers: Base58 private keys of the fee payers, which also create
            the accounts.
        non_default_token: Load a custom (non-default) owned token. Only an
            unreleased daemon branch has this field; released daemons ignore
            it. It is sent only when set.
    """

    account_queue_size: int
    deployment_fee: Currency
    max_fee: Currency
    min_fee: Currency
    init_balance: Currency
    max_new_zkapp_balance: Currency
    min_new_zkapp_balance: Currency
    max_balance_change: Currency
    min_balance_change: Currency
    memo_prefix: str
    duration_min: int
    tps: float
    num_new_accounts: int
    num_zkapps_to_deploy: int
    fee_payers: list[str] = field(default_factory=list)
    max_account_updates: int | None = None
    max_cost: bool = False
    no_precondition: bool = False
    non_default_token: bool | None = None

    def to_variables(self) -> dict[str, Any]:
        v: dict[str, Any] = {
            "maxAccountUpdates": self.max_account_updates,
            "maxCost": self.max_cost,
            "accountQueueSize": self.account_queue_size,
            "deploymentFee": self.deployment_fee.to_nanomina_str(),
            "maxFee": self.max_fee.to_nanomina_str(),
            "minFee": self.min_fee.to_nanomina_str(),
            "initBalance": self.init_balance.to_nanomina_str(),
            "maxNewZkappBalance": self.max_new_zkapp_balance.to_nanomina_str(),
            "minNewZkappBalance": self.min_new_zkapp_balance.to_nanomina_str(),
            "maxBalanceChange": self.max_balance_change.to_nanomina_str(),
            "minBalanceChange": self.min_balance_change.to_nanomina_str(),
            "noPrecondition": self.no_precondition,
            "memoPrefix": self.memo_prefix,
            "durationMin": self.duration_min,
            "tps": self.tps,
            "numNewAccounts": self.num_new_accounts,
            "numZkappsToDeploy": self.num_zkapps_to_deploy,
            "feePayers": list(self.fee_payers),
        }
        if self.non_default_token is not None:
            v["nonDefaultToken"] = self.non_default_token
        return v


@dataclass(frozen=True)
class NetworkPeer:
    """A peer in a ``GatingUpdate``: IP address, libp2p port and base58 peer ID."""

    host: str
    libp2p_port: int
    peer_id: str

    def to_variables(self) -> dict[str, Any]:
        return {"host": self.host, "libp2pPort": self.libp2p_port, "peerId": self.peer_id}


@dataclass(frozen=True)
class GatingUpdate:
    """The input of ``update_gating``.

    Attributes:
        added_peers: Peers to connect to.
        clean_added_peers: Reset the added peers, including the seeds, to an
            empty list.
        isolate: Allow connections only from trusted peers.
        banned_peers: Peers that may never connect, unless they are also trusted.
        trusted_peers: Peers that may always connect.
    """

    added_peers: list[NetworkPeer] = field(default_factory=list)
    clean_added_peers: bool = False
    isolate: bool = False
    banned_peers: list[NetworkPeer] = field(default_factory=list)
    trusted_peers: list[NetworkPeer] = field(default_factory=list)

    def to_variables(self) -> dict[str, Any]:
        return {
            "addedPeers": [p.to_variables() for p in self.added_peers],
            "cleanAddedPeers": self.clean_added_peers,
            "isolate": self.isolate,
            "bannedPeers": [p.to_variables() for p in self.banned_peers],
            "trustedPeers": [p.to_variables() for p in self.trusted_peers],
        }


@dataclass(frozen=True)
class CreateAccountsDetails:
    """The input of ``create_accounts``.

    Attributes:
        fee_payer: Base58 private key of the account that funds the new accounts.
        num_accounts: Number of new accounts.
        fee: Fee of each zkApp command that creates accounts.
        amount: Divided among the new accounts; each pays the account creation
            fee out of its share.
    """

    fee_payer: str
    num_accounts: int
    fee: Currency
    amount: Currency

    def to_variables(self) -> dict[str, Any]:
        return {
            "feePayer": self.fee_payer,
            "numAccounts": self.num_accounts,
            "fee": self.fee.to_nanomina_str(),
            "amount": self.amount.to_nanomina_str(),
        }


@dataclass(frozen=True)
class CreatedAccount:
    """A new account of ``create_accounts``: public and base58 private key."""

    public_key: str
    private_key: str


@dataclass(frozen=True)
class CreatedAccounts:
    """The result of ``create_accounts``. ``scheduled_transactions`` lists the
    handle until the background job that funds the accounts ends."""

    handle: str
    accounts: list[CreatedAccount]
