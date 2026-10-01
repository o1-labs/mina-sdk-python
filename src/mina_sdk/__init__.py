"""Mina Protocol Python SDK.

Provides a typed client for the Mina daemon's GraphQL API with
currency arithmetic, automatic retries, and context manager support.

Quick start::

    from mina_sdk import MinaDaemonClient, Currency

    with MinaDaemonClient() as client:
        status = client.get_sync_status()
        account = client.get_account("B62q...")
        print(f"Balance: {account.balance.total} MINA")
"""

from mina_sdk.daemon.client import (
    AccountNotFoundError,
    DaemonConnectionError,
    GraphQLError,
    MinaDaemonClient,
)
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
    CurrencyFormat,
    CurrencyUnderflow,
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
)

__all__ = [
    "AccountBalance",
    "AccountData",
    "AccountNotFoundError",
    "AccountPermissions",
    "AccountTiming",
    "AddrsAndPorts",
    "BlockInfo",
    "BlockTransaction",
    "CompletedWork",
    "Currency",
    "CurrencyFormat",
    "CurrencyUnderflow",
    "DaemonConnectionError",
    "DaemonMetrics",
    "DaemonStatus",
    "EpochData",
    "FeeTransfer",
    "GenesisConstants",
    "GraphQLError",
    "MinaDaemonClient",
    "PeerInfo",
    "PooledUserCommand",
    "SendDelegationResult",
    "SendPaymentResult",
    "SignatureInput",
    "SubmittedCommand",
    "TrackedAccount",
    "TransactionStatus",
    "VerificationKeyPermission",
    "ZkappCommandResult",
    "ZkappFailure",
    "ZkappFeePayer",
]

__version__ = "0.1.0"
