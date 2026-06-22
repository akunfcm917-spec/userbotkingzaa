import os
import asyncio

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.types import User

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION")
OWNER_ID = int(os.getenv("OWNER_ID"))

client = TelegramClient(
    StringSession(SESSION),
    API_ID,
    API_HASH
)


@client.on(events.NewMessage(pattern=r"\.ping$"))
async def ping(event):
    if event.sender_id != OWNER_ID:
        return

    await event.reply("Pong!")


@client.on(events.NewMessage(pattern=r"\.bc (group|user|all)$"))
async def broadcast(event):
    if event.sender_id != OWNER_ID:
        return

    if not event.is_reply:
        return await event.reply(
            "Reply pesan lalu gunakan:\n\n"
            ".bc group\n"
            ".bc user\n"
            ".bc all"
        )

    mode = event.pattern_match.group(1)
    reply = await event.get_reply_message()

    sukses = 0
    gagal = 0

    status = await event.reply("⏳ Broadcast dimulai...")

    async for dialog in client.iter_dialogs():
        try:
            target = dialog.entity

            if mode == "group":
                if not dialog.is_group:
                    continue

            elif mode == "user":
                if not isinstance(target, User):
                    continue

                if getattr(target, "bot", False):
                    continue

            elif mode == "all":
                pass

            await reply.copy_to(dialog.id)

            sukses += 1

            await asyncio.sleep(1)

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)

            try:
                await reply.copy_to(dialog.id)
                sukses += 1
            except:
                gagal += 1

        except Exception:
            gagal += 1

    await status.edit(
        f"✅ Broadcast selesai\n\n"
        f"Berhasil : {sukses}\n"
        f"Gagal    : {gagal}"
    )


async def main():
    await client.start()

    me = await client.get_me()

    print("LOGIN BERHASIL")
    print(f"Nama : {me.first_name}")
    print(f"ID   : {me.id}")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
