import argparse
import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import RPCError


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Read Telegram group messages (history and/or live stream)"
	)
	parser.add_argument(
		"--chat",
		dest="chat",
		help="Target chat: group name, @username, invite link, or numeric ID",
	)
	parser.add_argument(
		"--limit",
		type=int,
		default=None,
		help="Number of historical messages to fetch (overrides TELEGRAM_HISTORY_LIMIT)",
	)
	parser.add_argument(
		"--history",
		action="store_true",
		help="Fetch historical messages",
	)
	parser.add_argument(
		"--stream",
		action="store_true",
		help="Stream new incoming messages",
	)
	parser.add_argument(
		"--verbose",
		action="store_true",
		help="Enable verbose logging",
	)
	return parser.parse_args()


def load_config() -> dict:
	load_dotenv()
	config = {
		"api_id": os.getenv("TELEGRAM_API_ID"),
		"api_hash": os.getenv("TELEGRAM_API_HASH"),
		"phone_or_token": os.getenv("TELEGRAM_PHONE_OR_BOT_TOKEN"),
		"twofa_password": os.getenv("TELEGRAM_2FA_PASSWORD"),
		"default_chat": os.getenv("TELEGRAM_TARGET_CHAT"),
		"history_limit": os.getenv("TELEGRAM_HISTORY_LIMIT", "100"),
		"session_name": os.getenv("TELEGRAM_SESSION_NAME", "visa_telegram"),
	}
	return config


def is_bot_token(value: Optional[str]) -> bool:
	return bool(value and ":" in value and re.match(r"^\d+:\w+", value))


def ensure_session_path(session_name: str) -> str:
	session_dir = os.path.join(os.getcwd(), ".session")
	os.makedirs(session_dir, exist_ok=True)
	return os.path.join(session_dir, session_name)


def format_sender(sender) -> str:
	if not sender:
		return "Unknown"
	name_parts = [sender.first_name or "", sender.last_name or ""]
	name = " ".join(p for p in name_parts if p).strip()
	username = f"@{sender.username}" if getattr(sender, "username", None) else None
	identifier = username or name or str(getattr(sender, "id", "Unknown"))
	return identifier


def format_message(msg) -> str:
	timestamp = msg.date.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z") if msg.date else ""
	sender = format_sender(msg.sender)
	text = (msg.message or "").replace("\n", " ")
	if msg.media and not text:
		text = "<media>"
	return f"[{timestamp}] #{msg.id} {sender}: {text}"


async def resolve_chat(client: TelegramClient, chat_hint: Optional[str]):
	if not chat_hint:
		raise ValueError(
			"No chat specified. Use --chat or set TELEGRAM_TARGET_CHAT in .env"
		)
	try:
		return await client.get_entity(chat_hint)
	except RPCError as err:
		raise RuntimeError(f"Failed to resolve chat '{chat_hint}': {err}") from err


async def fetch_history(
	client: TelegramClient,
	target,
	limit: int,
) -> None:
	count = 0
	async for message in client.iter_messages(target, limit=limit):
		# Prefetch sender to include name/username
		if message.sender is None:
			try:
				await message.get_sender()
			except Exception:  # Best-effort, do not fail on sender fetch
				pass
		print(format_message(message))
		count += 1
	logging.info("Fetched %s messages", count)


async def stream_messages(client: TelegramClient, target) -> None:
	@client.on(events.NewMessage(chats=target))
	async def handler(event):  # noqa: ANN001 - Telethon event
		msg = event.message
		if msg.sender is None:
			try:
				await msg.get_sender()
			except Exception:
				pass
		print(format_message(msg))

	logging.info("Streaming new messages. Press Ctrl+C to stop.")
	await client.run_until_disconnected()


async def main_async() -> None:
	args = parse_args()
	config = load_config()

	log_level = logging.DEBUG if args.verbose else logging.INFO
	logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s: %(message)s")

	api_id = config["api_id"]
	api_hash = config["api_hash"]
	phone_or_token = config["phone_or_token"]
	twofa_password = config["twofa_password"]
	session_path = ensure_session_path(config["session_name"])

	if not api_id or not api_hash:
		raise SystemExit(
			"TELEGRAM_API_ID and TELEGRAM_API_HASH are required. See env.template."
		)

	try:
		api_id_int = int(api_id)
	except ValueError as err:
		raise SystemExit("TELEGRAM_API_ID must be an integer") from err

	client = TelegramClient(session_path, api_id_int, api_hash)

	# Start client (bot token or user phone)
	if is_bot_token(phone_or_token):
		await client.start(bot_token=phone_or_token)
		logging.info("Started as bot")
	else:
		await client.start(phone=phone_or_token or None, password=twofa_password or None)
		logging.info("Started as user")

	target_hint = args.chat or config["default_chat"]
	if not target_hint:
		raise SystemExit("Please specify --chat or TELEGRAM_TARGET_CHAT")

	target = await resolve_chat(client, target_hint)
	limit_env = int(config["history_limit"]) if str(config["history_limit"]).isdigit() else 100
	limit = args.limit if args.limit is not None else limit_env

	if not args.history and not args.stream:
		# Default to history only if neither specified
		args.history = True

	if args.history:
		await fetch_history(client, target, limit)

	if args.stream:
		await stream_messages(client, target)
	else:
		await client.disconnect()


def main() -> None:
	try:
		asyncio.run(main_async())
	except KeyboardInterrupt:
		print("Stopped.")


if __name__ == "__main__":
	main()
