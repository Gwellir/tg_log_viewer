import asyncio
import pickle
import os
from pathlib import Path

import dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_file = BASE_DIR / ".env"
if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)

api_id = int(os.getenv("TG_TEST_API_ID"))
api_hash = os.getenv("TG_TEST_API_HASH")
session_str = os.getenv("TG_TEST_SESSION_STRING")
dev_tg_id = int(os.getenv("DEV_TG_ID"))


# with TelegramClient(StringSession(), api_id, api_hash) as client:
#     print(client.session.save())

client = TelegramClient(
    StringSession(session_str), api_id, api_hash, sequential_updates=True
)


async def main():
    await client.connect()
    await client.get_me()
    await client.get_dialogs()
    # await client.send_message(dev_tg_id, "UP!")
    msgs = []
    i = 0
    async for event in client.iter_admin_log("anime_lepra", delete=True):
        msg = event.action.message
        if event.action.message.from_id.user_id == 27848064 and msg.id > 2121837:
            if msg.media and msg.file and hasattr(msg.media, "webpage"):
                await msg.download_media(f"media\\{msg.id}{msg.file.ext}")
            # msgs.append(event.action.message.to_dict())
            i += 1
            # await asyncio.sleep(0.1)
            if i % 100 == 0:
                print(i)

    # async with client:
        # await client.run_until_disconnected()


if __name__ == "__main__":
    client.loop.run_until_complete(main())
