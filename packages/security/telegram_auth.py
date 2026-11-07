"""Telegram WebApp HMAC-SHA256 Authentication & Signature Verification.

Verifies initData signatures from Telegram Mini Apps to authenticate users
cryptographically without passwords or insecure tokens.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, unquote

logger = logging.getLogger(__name__)


def verify_telegram_init_data(init_data_raw: str, bot_token: str, max_age_seconds: int = 86400) -> Optional[Dict[str, Any]]:
    """Validates Telegram WebApp initData string using HMAC-SHA256 signature verification.

    Args:
        init_data_raw: The raw query string sent by window.Telegram.WebApp.initData
        bot_token: The official Telegram bot token from @BotFather
        max_age_seconds: Maximum allowed age of the authentication signature (default: 24h)

    Returns:
        Dict containing verified user payload and metadata if valid; None if forged or expired.
    """
    if not init_data_raw or not bot_token:
        return None

    try:
        # Parse query string parameters
        parsed_params = dict(parse_qsl(init_data_raw, keep_blank_values=True))
        received_hash = parsed_params.pop("hash", None)

        if not received_hash:
            logger.warning("Telegram initData missing 'hash' parameter.")
            return None

        # Sort remaining keys alphabetically in k=v format separated by newline
        data_check_list = [f"{k}={v}" for k, v in sorted(parsed_params.items())]
        data_check_string = "\n".join(data_check_list)

        # Secret key: HMAC-SHA256 of bot token with constant salt "WebAppData"
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()

        # Calculated hash: HMAC-SHA256 of data_check_string with secret_key
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(calculated_hash, received_hash):
            logger.warning("Telegram initData signature verification failed! Possible forgery.")
            return None

        # Verify auth_date freshness
        auth_date_str = parsed_params.get("auth_date")
        if not auth_date_str or not auth_date_str.isdigit():
            logger.warning("Telegram initData has missing or invalid auth_date.")
            return None

        auth_date = int(auth_date_str)
        current_time = int(time.time())

        if (current_time - auth_date) > max_age_seconds:
            logger.warning(f"Telegram initData signature expired! Age: {current_time - auth_date}s > {max_age_seconds}s.")
            return None

        # Parse user field if present
        user_data = {}
        if "user" in parsed_params:
            try:
                user_data = json.loads(parsed_params["user"])
            except Exception:
                user_data = {"raw_user": parsed_params["user"]}

        return {
            "is_valid": True,
            "auth_date": auth_date,
            "user": user_data,
            "query_id": parsed_params.get("query_id"),
            "chat_type": parsed_params.get("chat_type"),
            "chat_instance": parsed_params.get("chat_instance"),
        }

    except Exception as e:
        logger.error(f"Unexpected error during Telegram initData validation: {e}")
        return None
