#!/usr/bin/env python3

import argparse
import json
import os
from html import escape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def send_notification(token, chat_id, title, commandline):
    text = f"📝 {escape(title)}\n\n<pre>{escape(commandline)}</pre> ✨"
    payload = urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload.encode(),
    )
    with urlopen(request, timeout=10) as response:
        result = json.load(response)
    if not result["ok"]:
        raise RuntimeError(result["description"])


def main():
    parser = argparse.ArgumentParser(description="Send a done_tg notification")
    parser.add_argument("title")
    parser.add_argument("commandline")
    args = parser.parse_args()

    token = os.environ.get("DONE_TG_BOT_TOKEN")
    chat_id = os.environ.get("DONE_TG_CHAT_ID")
    if not token or not chat_id:
        parser.error("set DONE_TG_BOT_TOKEN and DONE_TG_CHAT_ID")

    try:
        send_notification(token, chat_id, args.title, args.commandline)
    except HTTPError as error:
        parser.exit(1, f"done_tg: Telegram HTTP {error.code}\n")
    except (URLError, TimeoutError) as error:
        # Request exception messages can include the bot token in the URL.
        parser.exit(1, f"done_tg: Telegram request failed ({type(error).__name__})\n")
    except (ValueError, KeyError):
        parser.exit(1, "done_tg: invalid Telegram response\n")
    except RuntimeError as error:
        parser.exit(1, f"done_tg: {error}\n")


if __name__ == "__main__":
    main()
