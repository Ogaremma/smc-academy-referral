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

import asyncio
from typing import Any, Mapping

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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


TELEGRAM_GET_CHAT_URL = "https://api.telegram.org/bot{token}/getChat"


class TelegramProfileLookupError(RuntimeError):
    """Telegram could not return a profile for the requested chat id."""


def _json_or_empty(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


async def fetch_telegram_chat_profile(
    telegram_id: int,
    *,
    bot_token: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, str]:
    """Return the profile Telegram reports for a chat id via Bot API ``getChat``.

    Telegram is the only source of truth: the result holds just the fields it
    actually reports (``username``/``first_name``/``last_name``) and is empty
    when the chat exposes none. A chat the bot cannot see (for example a user
    who never started the bot) raises :class:`TelegramProfileLookupError` so
    the caller keeps the numeric fallback instead of inventing an identity.
    """

    async def _request(http: httpx.AsyncClient) -> dict[str, str]:
        url = TELEGRAM_GET_CHAT_URL.format(token=bot_token)
        response = await http.post(url, json={"chat_id": telegram_id})
        payload = _json_or_empty(response)
        if response.status_code == 429:
            retry_after = int((payload.get("parameters") or {}).get("retry_after", 1))
            await asyncio.sleep(min(retry_after, 30))
            response = await http.post(url, json={"chat_id": telegram_id})
            payload = _json_or_empty(response)
        if response.status_code != 200 or not payload.get("ok"):
            raise TelegramProfileLookupError(
                payload.get("description") or f"HTTP {response.status_code}"
            )
        return telegram_profile(payload.get("result") or {})

    if client is not None:
        return await _request(client)
    async with httpx.AsyncClient(timeout=15) as http:
        return await _request(http)


def _field_is_missing(column: Any) -> Any:
    return or_(column.is_(None), column == "")


async def count_users_missing_telegram_profile(db: AsyncSession) -> int:
    """Number of active accounts whose Telegram profile is entirely missing."""
    total = await db.scalar(
        select(func.count(User.id)).where(
            User.is_active.is_(True),
            _field_is_missing(User.username),
            _field_is_missing(User.first_name),
            _field_is_missing(User.last_name),
        )
    )
    return int(total or 0)


async def refresh_missing_telegram_profiles(
    db: AsyncSession,
    *,
    bot_token: str,
    client: httpx.AsyncClient | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Backfill Telegram profiles for accounts stored with only a numeric id.

    Only accounts whose stored ``username``, ``first_name`` and ``last_name``
    are all empty are checked, and only the fields Telegram actually reports are
    written. A chat Telegram cannot resolve stays on the numeric fallback.
    """
    targets = (
        (
            await db.execute(
                select(User)
                .where(
                    User.is_active.is_(True),
                    _field_is_missing(User.username),
                    _field_is_missing(User.first_name),
                    _field_is_missing(User.last_name),
                )
                .order_by(User.id)
            )
        )
        .scalars()
        .all()
    )

    refreshed: list[dict[str, Any]] = []
    unchanged: list[int] = []
    unresolved: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for user in targets:
        try:
            profile = await fetch_telegram_chat_profile(
                user.telegram_id, bot_token=bot_token, client=client
            )
        except TelegramProfileLookupError as error:
            unresolved.append(
                {"id": user.id, "telegram_id": user.telegram_id, "reason": str(error)}
            )
            continue
        except httpx.HTTPError as error:
            failures.append(
                {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "reason": type(error).__name__,
                }
            )
            continue
        if not profile:
            unresolved.append(
                {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "reason": "Telegram reported no profile fields.",
                }
            )
            continue
        if any(getattr(user, field, None) != value for field, value in profile.items()):
            if not dry_run:
                apply_telegram_profile(user, profile)
            refreshed.append(
                {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "fields": sorted(profile),
                }
            )
        else:
            unchanged.append(user.id)

    if not dry_run and refreshed:
        await db.commit()

    return {
        "checked": len(targets),
        "refreshed": len(refreshed),
        "unchanged": len(unchanged),
        "unresolved": len(unresolved),
        "failures": len(failures),
        "dry_run": dry_run,
        "refreshed_users": refreshed,
        "unresolved_users": unresolved,
        "failure_users": failures,
    }
