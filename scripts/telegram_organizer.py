"""Telegram Personal Account Declutter & Organization Assistant (Telethon Engine).

Allows Chief Architect Shivam to audit dialogs, batch mark unreads, archive noisy feeds,
and structure Telegram into an elite, focused command center.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from packages.core.config import settings

try:
    from telethon import TelegramClient
    from telethon.tl.functions.messages import MarkDialogUnreadRequest
    from telethon.tl.types import Channel, Chat, Dialog, User
except ImportError:
    print("Telethon is required for this tool. Install with: pip install telethon")
    sys.exit(1)


def check_credentials() -> Tuple[int, str]:
    """Retrieves API_ID and API_HASH from environment or .env."""
    api_id_str = os.getenv("TELEGRAM_API_ID", "")
    api_hash = os.getenv("TELEGRAM_API_HASH", "")

    if not api_id_str or not api_hash:
        print("\n" + "=" * 65)
        print("🔑 TELEGRAM USER API CREDENTIALS NOT FOUND")
        print("=" * 65)
        print("To allow programmatic access to your personal Telegram account:")
        print("1. Visit https://my.telegram.org in your browser.")
        print("2. Log in with your phone number (+91...).")
        print("3. Click on 'API development tools'.")
        print("4. Create an application (e.g. Title: 'PlacementRadar', Short: 'pradar').")
        print("5. Copy your 'api_id' (integer) and 'api_hash' (hex string).")
        print("6. Add them to your .env file:")
        print('   TELEGRAM_API_ID="12345678"')
        print('   TELEGRAM_API_HASH="abcdef1234567890abcdef1234567890"')
        print("=" * 65)
        print("💡 NOTE: You can also declutter Telegram directly inside the")
        print("   Telegram Desktop app in 60 seconds without any API keys!")
        print("=" * 65 + "\n")
        sys.exit(0)

    try:
        api_id = int(api_id_str)
    except ValueError:
        print(f"Error: TELEGRAM_API_ID must be an integer, got: {api_id_str}")
        sys.exit(1)

    return api_id, api_hash


async def audit_dialogs(client: TelegramClient) -> None:
    """Scans all dialogs and groups them by category with unread counts."""
    print("\n🔍 Auditing all chats and folders across your Telegram account...\n")
    dialogs: List[Dialog] = await client.get_dialogs()

    total_chats = len(dialogs)
    total_unreads = 0
    categories = {
        "Direct Messages (Private)": [],
        "Groups (Colleges & Teams)": [],
        "Broadcast Channels": [],
        "Bots": [],
    }

    for d in dialogs:
        unreads = d.unread_count
        total_unreads += unreads

        if d.is_user:
            if getattr(d.entity, "bot", False):
                categories["Bots"].append((d.name, unreads, d.id))
            else:
                categories["Direct Messages (Private)"].append((d.name, unreads, d.id))
        elif d.is_group:
            categories["Groups (Colleges & Teams)"].append((d.name, unreads, d.id))
        elif d.is_channel:
            categories["Broadcast Channels"].append((d.name, unreads, d.id))

    print(f"📊 SUMMARY: {total_chats} Total Dialogs | {total_unreads} Total Unread Messages\n")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for cat_name, items in categories.items():
        unread_in_cat = sum(u for _, u, _ in items)
        print(f"📁 {cat_name}: {len(items)} chats ({unread_in_cat} unread)")
        # Show top unread chats in each category
        top_unreads = sorted([i for i in items if i[1] > 0], key=lambda x: x[1], reverse=True)[:5]
        for name, count, cid in top_unreads:
            print(f"   • {name[:35]:<35} -> {count} unread")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


async def mark_all_read(client: TelegramClient) -> None:
    """Marks all unread conversations as read."""
    print("\n⚡ Clearing all unread message counters...")
    dialogs = await client.get_dialogs()
    cleared = 0
    for d in dialogs:
        if d.unread_count > 0:
            try:
                await client.send_read_acknowledge(d)
                cleared += 1
            except Exception as e:
                pass
    print(f"✅ Successfully marked {cleared} unread dialogs as read!")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Telegram Personal Account Organizer")
    parser.add_argument("--audit", action="store_true", help="Audit all dialogs and unread breakdown")
    parser.add_argument("--mark-read", action="store_true", help="Mark all unread messages as read")
    args = parser.parse_args()

    api_id, api_hash = check_credentials()

    session_path = str(Path(REPO_ROOT) / "shivam_telegram_session")
    client = TelegramClient(session_path, api_id, api_hash)
    await client.start()

    me = await client.get_me()
    print(f"👋 Connected as {me.first_name} (@{me.username or 'No username'}) [ID: {me.id}]")

    if args.mark_read:
        await mark_all_read(client)

    if args.audit or not args.mark_read:
        await audit_dialogs(client)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
