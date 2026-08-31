import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl

import jwt

from app.config import settings
from app.core.exceptions import InvalidTokenError, TelegramAuthError, WebhookAuthError

# Characters allowed for referral code: Uppercase alphanumeric excluding ambiguous (0, O, 1, I)
REFERRAL_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_referral_code(prefix: str = "SMC-", length: int = 6) -> str:
    """
    Generate a cryptographically secure, random referral code.
    Format: SMC-XXXXXX
    Excludes ambiguous characters: 0, O, 1, I.
    """
    random_part = "".join(secrets.choice(REFERRAL_CODE_ALPHABET) for _ in range(length))
    return f"{prefix}{random_part}"


def validate_telegram_init_data(
    init_data_str: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> Dict[str, Any]:
    """
    Validate Telegram Mini App initData according to Telegram's HMAC-SHA256 signature algorithm.
    """
    if not init_data_str:
        raise TelegramAuthError("initData string is empty")

    if not bot_token:
        raise TelegramAuthError("Bot token is not configured on server")

    parsed_params = parse_qsl(init_data_str, keep_blank_values=True)
    param_dict = dict(parsed_params)

    received_hash = param_dict.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("initData missing hash parameter")

    # Sort remaining fields alphabetically by key and create key=value string
    sorted_items = sorted(param_dict.items(), key=lambda x: x[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)

    # Derive secret key using HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    # Calculate expected hash
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash.lower(), received_hash.lower()):
        raise TelegramAuthError("Invalid Telegram authentication signature")

    # Check auth_date
    auth_date_str = param_dict.get("auth_date")
    if not auth_date_str:
        raise TelegramAuthError("initData missing auth_date parameter")

    try:
        auth_date = int(auth_date_str)
    except ValueError:
        raise TelegramAuthError("Invalid auth_date format")

    current_time = int(time.time())
    if current_time - auth_date > max_age_seconds:
        raise TelegramAuthError("Telegram authentication data has expired")

    # Extract user payload
    user_str = param_dict.get("user")
    if not user_str:
        raise TelegramAuthError("initData missing user parameter")

    try:
        user_data = json.loads(user_str)
    except Exception:
        raise TelegramAuthError("Invalid user JSON structure in initData")

    return user_data


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Authentication token has expired")
    except jwt.PyJWTError:
        raise InvalidTokenError("Invalid authentication token")


def verify_webhook_secret(provided_secret: str, expected_secret: str) -> bool:
    """
    Validate incoming webhook secret using constant-time string comparison.
    """
    if not provided_secret or not expected_secret:
        return False
    return hmac.compare_digest(provided_secret, expected_secret)
