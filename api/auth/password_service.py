"""Password hashing and verification utilities."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

DEFAULT_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str, hasher: PasswordHasher = DEFAULT_HASHER) -> str:
    """Hash a plaintext password using Argon2id.

    Args:
        password: Plaintext password.
        hasher: Optional PasswordHasher override.

    Returns:
        Argon2id hash in PHC format.
    """
    return hasher.hash(password)


def verify_password(password_hash: str, password: str, hasher: PasswordHasher = DEFAULT_HASHER) -> bool:
    """Verify a plaintext password against a stored hash.

    Args:
        password_hash: Stored Argon2id hash.
        password: Plaintext password to verify.
        hasher: Optional PasswordHasher override.

    Returns:
        True if the password matches; False otherwise.
    """
    try:
        return hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str, hasher: PasswordHasher = DEFAULT_HASHER) -> bool:
    """Check whether a stored hash needs rehashing with current parameters.

    Args:
        password_hash: Stored Argon2id hash.
        hasher: Optional PasswordHasher override.

    Returns:
        True if rehashing is required; False otherwise.
    """
    return hasher.check_needs_rehash(password_hash)
