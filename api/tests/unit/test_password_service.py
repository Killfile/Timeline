from __future__ import annotations

from argon2 import PasswordHasher

from api.auth.password_service import hash_password, needs_rehash, verify_password


def test_hash_and_verify_password_round_trip() -> None:
    password = "correct-horse-battery-staple"
    password_hash = hash_password(password)

    assert password_hash
    assert verify_password(password_hash, password) is True


def test_verify_password_rejects_invalid_password() -> None:
    password = "correct-horse-battery-staple"
    password_hash = hash_password(password)

    assert verify_password(password_hash, "wrong-password") is False


def test_needs_rehash_detects_outdated_hash() -> None:
    legacy_hasher = PasswordHasher(
        time_cost=1,
        memory_cost=1024,
        parallelism=2,
        hash_len=16,
        salt_len=8,
    )
    legacy_hash = hash_password("legacy-password", hasher=legacy_hasher)

    assert needs_rehash(legacy_hash) is True
