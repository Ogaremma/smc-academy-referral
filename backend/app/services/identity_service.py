"""Telegram identity persistence shared by every authentication path.

The Mini App sends the Telegram profile (username, first name, last name,
photo) with the signed ``initData`` on every launch. That profile is the only
source for the identity shown in the affiliate and admin dashboards, so it is
persisted from the validated payload whenever it is available.

Fields Telegram does not send are left untouched: a missing value must never
erase an identity that is already stored (for example when the Mini App is
opened without photo access).
"""
from __future__ import annotations

from typing import Any, Mapping

from app.db.models import User

TELEGRAM_PROFILE_FIELDS = ("username", "first_name", "last_name", "photo_url")


def telegram_profile(source: Mapping[str, Any]) -> dict[str, str]:
    """Return the Telegram profile fields present in a validated payload."""
    profile: dict[str, str] = {}
    for field in TELEGRAM_PROFILE_FIELDS:
        value = source.get(field) if hasattr(source, "get") else None
        if value is None:
            continue
        text = str(value).strip()
        if text:
            profile[field] = text
    return profile


def apply_telegram_profile(user: User, profile: Mapping[str, str]) -> bool:
    """Store the Telegram profile on the user, returning True when it changed."""
    changed = False
    for field, value in profile.items():
        if getattr(user, field, None) != value:
            setattr(user, field, value)
            changed = True
    return changed
