"""Stable content-addressable hashing utilities.

Used to generate deterministic IDs for functions, prompts, and responses
so that artefacts can be de-duplicated and reliably cross-referenced.
"""

import hashlib


def hash_content(content: str) -> str:
    """Return a hex SHA-256 digest of *content* (UTF-8 encoded)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def short_hash(content: str, length: int = 8) -> str:
    """Return the first *length* hex characters of the SHA-256 of *content*."""
    return hash_content(content)[:length]
