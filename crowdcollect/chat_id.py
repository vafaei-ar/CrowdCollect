"""Command-line helper for discovering Telegram chat IDs."""

from __future__ import annotations

import getpass
import os
import sys

import requests


def get_chats(token: str) -> list[dict[str, object]]:
    response = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params={"timeout": 0, "allowed_updates": '["message","channel_post"]'},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise requests.RequestException(payload.get("description", "Telegram rejected request"))

    chats: dict[str, dict[str, object]] = {}
    for update in payload.get("result", []):
        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat") or {}
        if "id" in chat:
            chats[str(chat["id"])] = chat
    return list(chats.values())


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN") or getpass.getpass("Telegram bot token: ").strip()
    if not token:
        print("No bot token provided.", file=sys.stderr)
        return 2
    try:
        chats = get_chats(token)
    except requests.RequestException as exc:
        print(f"Could not contact Telegram: {exc}", file=sys.stderr)
        return 1
    if not chats:
        print("No chats found. Send /start to the bot, then run this command again.")
        return 0
    print("Chat IDs seen in recent bot updates:")
    for chat in chats:
        label = chat.get("title") or " ".join(
            str(chat.get(key, "")) for key in ("first_name", "last_name")
        ).strip()
        username = f" (@{chat['username']})" if chat.get("username") else ""
        print(f"  {chat['id']}: {label or chat.get('type', 'chat')}{username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
