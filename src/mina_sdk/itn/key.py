"""The ed25519 key that signs requests to a daemon's ITN server."""

from __future__ import annotations

import base64
import binascii

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from mina_sdk.itn.errors import InvalidItnKeyError

SEED_SIZE = 32


class ItnKey:
    """An ed25519 key that signs requests to a daemon's ITN GraphQL server.

    The daemon accepts a request only when the key's public half is in its
    ``--itn-keys`` list. Keys are exchanged as standard base64 with padding:
    the private key as its 32-byte seed (the format of mina-perf-testing's
    orchestrator key and ``fetcher_sk``), and the public key as the 32-byte
    value for ``--itn-keys``.
    """

    def __init__(self, seed: bytes):
        if len(seed) != SEED_SIZE:
            raise InvalidItnKeyError(f"expected {SEED_SIZE} bytes, got {len(seed)}")
        self._seed = bytes(seed)
        self._sk = Ed25519PrivateKey.from_private_bytes(self._seed)

    @classmethod
    def from_base64(cls, seed_b64: str) -> ItnKey:
        """Load a key from the base64 encoding of its 32-byte seed. Surrounding
        white space is ignored."""
        try:
            seed = base64.b64decode(seed_b64.strip(), validate=True)
        except (binascii.Error, ValueError) as e:
            raise InvalidItnKeyError(f"not base64: {e}") from e
        return cls(seed)

    @classmethod
    def generate(cls) -> ItnKey:
        """Create a new random key."""
        sk = Ed25519PrivateKey.generate()
        return cls(sk.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))

    def to_base64(self) -> str:
        """The base64 encoding of the key's 32-byte seed; the inverse of
        ``from_base64``."""
        return base64.b64encode(self._seed).decode()

    def public_key_base64(self) -> str:
        """The base64 public key, as the daemon expects it in ``--itn-keys``."""
        raw = self._sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        return base64.b64encode(raw).decode()

    def sign_base64(self, message: bytes) -> str:
        """The base64 ed25519 signature of ``message``."""
        return base64.b64encode(self._sk.sign(message)).decode()

    def __repr__(self) -> str:
        # The public key only, so that a key never ends up in a log.
        return f"ItnKey(public={self.public_key_base64()})"
