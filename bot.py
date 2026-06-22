import os
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.types import User
from telethon import functions

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION")
OWNER_ID = int(os.getenv("OWNER_ID"))

BLACKLIST_FILE = "blacklist.txt"

MONGO_URI = os.getenv("MONGO_URI")

mongo = AsyncIOMotorClient(MONGO_URI)

db = mongo["telegram_bot"]

blacklist_col = db["blacklist"]
autobc_task = None
autofw_task = None

client = TelegramClient(
    StringSession(SESSION),
    API_ID,
    API_HASH
)

async def run_autobc(mode, reply, delay):
    while True:

        async for dialog in client.iter_dialogs():
            try:
                target = dialog.entity

                if await blacklist_col.find_one(
                    {"chat_id": dialog.id}
                ):
                    continue

                if mode == "group":
                    if not dialog.is_group:
                        continue

                elif mode == "user":
                    if not isinstance(target, User):
                        continue

                    if getattr(target, "bot", False):
                        continue

                if reply.media:
                    await client.send_file(
                        dialog.id,
                        reply.media,
                        caption=reply.text or ""
                    )
                else:
                    await client.send_message(
                        dialog.id,
                        reply.text or ""
                    )

                await asyncio.sleep(1)

            except:
                pass

        await asyncio.sleep(delay * 60)

async def run_autofw(mode, reply, delay):
    while True:

        async for dialog in client.iter_dialogs():
            try:

                target = dialog.entity

                if await blacklist_col.find_one(
                    {"chat_id": dialog.id}
                ):
                    continue

                if mode == "group":
                    if not dialog.is_group:
                        continue

                elif mode == "user":
                    if not isinstance(target, User):
                        continue

                    if getattr(target, "bot", False):
                        continue

                await client.forward_messages(
                    dialog.id,
                    reply
                )

                await asyncio.sleep(1)

            except:
                pass

        await asyncio.sleep(delay * 60)


@client.on(events.NewMessage(pattern=r"\.ping$"))
async def ping(event):
    if event.sender_id != OWNER_ID:
        return

    await event.reply("Pong!")

@client.on(events.NewMessage(pattern=r"(?i)^\.addbl$"))
async def add_blacklist(event):
    if event.sender_id != OWNER_ID:
        return

    await blacklist_col.update_one(
        {"chat_id": event.chat_id},
        {"$set": {"chat_id": event.chat_id}},
        upsert=True
    )

    await event.reply(
        f"✅ Chat berhasil di-blacklist\n\nID: `{event.chat_id}`"
    )


@client.on(events.NewMessage(pattern=r"(?i)^\.delbl$"))
async def del_blacklist(event):
    if event.sender_id != OWNER_ID:
        return

    result = await blacklist_col.delete_one(
        {"chat_id": event.chat_id}
    )

    if result.deleted_count:
        await event.reply(
            f"✅ Chat dihapus dari blacklist\n\nID: `{event.chat_id}`"
        )
    else:
        await event.reply("Chat ini tidak ada dalam blacklist.")

@client.on(events.NewMessage(pattern=r"\.cekid(?: (.+))?$"))
async def cekid(event):
    if event.sender_id != OWNER_ID:
        return

    try:
        arg = event.pattern_match.group(1)

        # Reply pesan
        if event.is_reply:
            msg = await event.get_reply_message()
            sender = await msg.get_sender()

            await event.reply(
                f"👤 Nama: {getattr(sender, 'first_name', '-')}\n"
                f"🆔 ID: `{sender.id}`"
            )
            return

        # Username
        if arg:
            entity = await client.get_entity(arg)

            await event.reply(
                f"👤 Nama: {getattr(entity, 'first_name', getattr(entity, 'title', '-'))}\n"
                f"🆔 ID: `{entity.id}`"
            )
            return

        # Chat sekarang
        chat = await event.get_chat()

        await event.reply(
            f"💬 Chat: {getattr(chat, 'title', 'Private Chat')}\n"
            f"🆔 ID: `{event.chat_id}`"
        )

    except Exception as e:
        await event.reply(f"Error: {e}")

@client.on(events.NewMessage(pattern=r"\.fw (group|user|all)$"))
async def forward_broadcast(event):
    if event.sender_id != OWNER_ID:
        return

    if not event.is_reply:
        return await event.reply(
            "Reply pesan lalu gunakan:\n\n"
            ".fw group\n"
            ".fw user\n"
            ".fw all"
        )

    mode = event.pattern_match.group(1)
    reply = await event.get_reply_message()

    sukses = 0
    gagal = 0

    status = await event.reply("⏳ Forward Broadcast dimulai...")

    async for dialog in client.iter_dialogs():
        try:
            target = dialog.entity

            if await blacklist_col.find_one(
                {"chat_id": dialog.id}
            ):
                continue

            if mode == "group":
                if not dialog.is_group:
                    continue

            elif mode == "user":
                if not isinstance(target, User):
                    continue

                if getattr(target, "bot", False):
                    continue

            await client.forward_messages(
                dialog.id,
                reply
            )

            sukses += 1
            await asyncio.sleep(1)

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)

        except:
            gagal += 1

    await status.edit(
        f"✅ Forward selesai\n\n"
        f"Berhasil : {sukses}\n"
        f"Gagal    : {gagal}"
    )

@client.on(events.NewMessage(pattern=r"\.autobc (group|user|all) (\d+)$"))
async def autobc(event):
    global autobc_task

    if event.sender_id != OWNER_ID:
        return

    if not event.is_reply:
        return await event.reply(
            "Reply pesan:\n.autobc all 60"
        )

    mode = event.pattern_match.group(1)
    delay = int(event.pattern_match.group(2))

    reply = await event.get_reply_message()

    if autobc_task and not autobc_task.done():
        autobc_task.cancel()

    autobc_task = asyncio.create_task(
        run_autobc(mode, reply, delay)
    )

    await event.reply(
        f"✅ Auto BC aktif\n\nMode: {mode}\nDelay: {delay} menit"
    )

@client.on(events.NewMessage(pattern=r"\.stopautobc$"))
async def stop_autobc(event):
    global autobc_task

    if event.sender_id != OWNER_ID:
        return

    if autobc_task and not autobc_task.done():
        autobc_task.cancel()
        autobc_task = None

        await event.reply("✅ Auto BC dihentikan.")
    else:
        await event.reply("Tidak ada Auto BC yang aktif.")

@client.on(events.NewMessage(pattern=r"\.autofw (group|user|all) (\d+)$"))
async def autofw(event):
    global autofw_task

    if event.sender_id != OWNER_ID:
        return

    if not event.is_reply:
        return await event.reply(
            "Reply pesan:\n.autofw all 60"
        )

    mode = event.pattern_match.group(1)
    delay = int(event.pattern_match.group(2))

    reply = await event.get_reply_message()

    if autofw_task and not autofw_task.done():
        autofw_task.cancel()

    autofw_task = asyncio.create_task(
        run_autofw(mode, reply, delay)
    )

    await event.reply(
        f"✅ Auto FW aktif\n\nMode: {mode}\nDelay: {delay} menit"
    )

@client.on(events.NewMessage(pattern=r"\.stopautofw$"))
async def stop_autofw(event):
    global autofw_task

    if event.sender_id != OWNER_ID:
        return

    if autofw_task and not autofw_task.done():
        autofw_task.cancel()
        autofw_task = None

        await event.reply("✅ Auto FW dihentikan.")
    else:
        await event.reply("Tidak ada Auto FW yang aktif.")

@client.on(events.NewMessage(pattern=r"\.bc (group|user|all)$"))
async def broadcast(event):
    print("BC TERPANGGIL")

    if event.sender_id != OWNER_ID:
        print("OWNER ID TIDAK COCOK")
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
            if await blacklist_col.find_one(
                {"chat_id": dialog.id}
            ):
                continue

            if mode == "group":
                if not dialog.is_group:
                    continue

            elif mode == "user":
                if not isinstance(target, User):
                    continue

                if getattr(target, "bot", False):
                    continue

            await client.send_message(
                dialog.id,
                reply.message
            )

            sukses += 1

            if sukses % 20 == 0:
                print(f"Berhasil: {sukses}")

            await asyncio.sleep(1)

        except FloodWaitError as e:
            print(f"FloodWait {e.seconds} detik")
            await asyncio.sleep(e.seconds)

        except Exception as e:
            gagal += 1
            print(f"GAGAL {dialog.name}: {e}")

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
    print(f"OWNER_ID : {OWNER_ID}")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
