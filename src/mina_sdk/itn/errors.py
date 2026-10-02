"""Errors of the ITN client."""

from __future__ import annotations


class ItnUnauthorizedError(Exception):
    """The ITN server rejected the request signature (HTTP 401): the signature
    is wrong, or the key's public half is not in the daemon's ``--itn-keys``."""

    def __init__(self, query_name: str):
        self.query_name = query_name
        super().__init__(
            f"ITN server rejected the signature of {query_name} (HTTP 401); "
            "is the public key in --itn-keys?"
        )


class ItnSequencingError(Exception):
    """The ITN server still rejected the sequence information (HTTP 412) after
    a new auth handshake."""

    def __init__(self, query_name: str):
        self.query_name = query_name
        super().__init__(
            f"ITN server rejected the sequence number of {query_name} again "
            "after a new auth (HTTP 412)"
        )


class InvalidItnKeyError(ValueError):
    """An ITN key cannot be decoded."""

    def __init__(self, reason: str):
        super().__init__(f"invalid ITN key: {reason}")


class ItnHttpError(Exception):
    """The ``__cause__`` of a ``DaemonConnectionError`` when the daemon answered
    with an HTTP error status other than 401 and 412. Read ``status_code`` to
    tell a node that is unwell (5xx) from a request that no node would accept."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP {status_code}: {body[:200]}")
