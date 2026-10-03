"""Client for the daemon's ITN GraphQL server (``ITN_FEATURES=1``,
``--itn-graphql-port``, ``--itn-keys``), whose requests are signed with an
ed25519 key. It needs the ``itn`` extra: ``pip install mina-sdk[itn]``.
"""

try:
    import cryptography  # noqa: F401
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "mina_sdk.itn needs the 'cryptography' package: pip install 'mina-sdk[itn]'"
    ) from e

from mina_sdk.itn import queries
from mina_sdk.itn.client import ItnClient
from mina_sdk.itn.errors import (
    InvalidItnKeyError,
    ItnHttpError,
    ItnSequencingError,
    ItnUnauthorizedError,
)
from mina_sdk.itn.key import ItnKey
from mina_sdk.itn.types import (
    CreateAccountsDetails,
    CreatedAccount,
    CreatedAccounts,
    GatingUpdate,
    ItnAuth,
    ItnLog,
    LogMetadatum,
    NetworkPeer,
    PaymentsDetails,
    ZkappCommandsDetails,
)

__all__ = [
    "CreateAccountsDetails",
    "CreatedAccount",
    "CreatedAccounts",
    "GatingUpdate",
    "InvalidItnKeyError",
    "ItnAuth",
    "ItnClient",
    "ItnHttpError",
    "ItnKey",
    "ItnLog",
    "ItnSequencingError",
    "ItnUnauthorizedError",
    "LogMetadatum",
    "NetworkPeer",
    "PaymentsDetails",
    "ZkappCommandsDetails",
    "queries",
]
