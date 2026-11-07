"""Interactive Telegram Channel Auto-Connector Helper.

Automatically discovers your Telegram Channel ID (e.g. private channel 'Placements')
and writes it directly into your .env configuration.
"""

from __future__ import annotations

import os
import sys
import time
import httpx
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def read_env_var(key: str) -> str:
    if not ENV_PATH.exists():
        return ""
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                val = line.split("=", 1)[1].strip().strip("'\"")
                return val
    return ""


def update_env_var(key: str, value: str) -> None:
    lines = []
    found = False
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}=") or line.strip().startswith(f"{key} ="):
            new_lines.append(f'{key}="{value}"\n')
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f'{key}="{value}"\n')

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def main():
    print("=" * 65)
    print("🎓 TELEGRAM CHANNEL AUTO-CONNECTOR HELPER")
    print("=" * 65)

    token = read_env_var("TELEGRAM_BOT_TOKEN")
    if not token or token == "your_telegram_bot_token_here":
        print("\n🔑 Please enter your Telegram Bot Token from @BotFather:")
        token = input("Bot Token: ").strip()
        if not token:
            print("❌ Error: Bot Token cannot be empty.")
            sys.exit(1)
        update_env_var("TELEGRAM_BOT_TOKEN", token)

    # 1. Verify Bot Token
    print("\n[1/3] Verifying Bot Token with Telegram API...")
    try:
        resp = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10.0)
        data = resp.json()
        if not data.get("ok"):
            print(f"❌ Telegram API Error: {data.get('description')}")
            sys.exit(1)
        bot_info = data["result"]
        print(f"✅ Bot Verified: @{bot_info.get('username')} ({bot_info.get('first_name')})")
    except Exception as e:
        print(f"❌ Network Error: {e}")
        sys.exit(1)

    # 2. Instructions for finding channel ID
    print("\n[2/3] Channel Detection Instructions:")
    print("  1. In Telegram, open your 'Placements' channel.")
    print(f"  2. Make sure @{bot_info.get('username')} is added as an ADMINISTRATOR.")
    print("     (Required Permission: 'Post Messages')")
    print("  3. Post any test message in the channel (e.g. type 'radar test').")
    print("\n⏳ Listening for channel message (press Ctrl+C to cancel)...")

    # Clear pending updates first
    offset = 0
    try:
        init_upd = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates?offset=-1", timeout=5.0).json()
        if init_upd.get("result"):
            offset = init_upd["result"][-1]["update_id"] + 1
    except Exception:
        pass

    channel_id = None
    channel_title = ""

    for attempt in range(60):
        try:
            upd_resp = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=5", timeout=10.0)
            res = upd_resp.json()
            if res.get("ok") and res.get("result"):
                for u in res["result"]:
                    offset = u["update_id"] + 1
                    # Check channel post
                    if "channel_post" in u:
                        chat = u["channel_post"]["chat"]
                        channel_id = str(chat["id"])
                        channel_title = chat.get("title", "Placements")
                        break
                    # Or group message
                    elif "message" in u and u["message"]["chat"]["type"] in ("group", "supergroup"):
                        chat = u["message"]["chat"]
                        channel_id = str(chat["id"])
                        channel_title = chat.get("title", "Placement Group")
                        break
            if channel_id:
                break
        except Exception:
            pass
        time.sleep(1.0)
        print(".", end="", flush=True)

    if not channel_id:
        print("\n⚠️ No new message detected in the last 60 seconds.")
        print("You can manually set TELEGRAM_CHANNEL_ID in .env with your channel's public @username or chat ID.")
        return

    print(f"\n\n✅ [3/3] Detected Channel: '{channel_title}' (ID: {channel_id})")
    update_env_var("TELEGRAM_CHANNEL_ID", channel_id)
    print(f"💾 Updated TELEGRAM_CHANNEL_ID=\"{channel_id}\" in .env")

    # Send verification broadcast
    print("🚀 Sending confirmation post to channel...")
    test_msg = (
        "🎓 *Placement Intelligence Hub — Connected!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Autonomous recruitment radar is active.\n"
        "• Target 1: *Ethara.AI LLM GenOPS (₹6 LPA)*\n"
        "• Target 2: *Amazon SDE Intern 2027 / 2026*\n"
        "• Verified ATS & Off-Campus Feeds Active\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Only 100% verified opportunities will be posted here."
    )
    post_resp = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": channel_id, "text": test_msg, "parse_mode": "Markdown"}
    ).json()

    if post_resp.get("ok"):
        print("🎉 SUCCESS! Verification post published to your channel!")
    else:
        print(f"⚠️ Could not post message: {post_resp.get('description')}")
        print("Make sure the bot has the 'Post Messages' administrator permission.")


if __name__ == "__main__":
    main()

