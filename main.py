import asyncio
import os
import time
from uuid import uuid4

import redis
import telethon
import telethon.tl.types
from telethon import TelegramClient, events
from telethon.tl.functions.messages import ForwardMessagesRequest
from telethon.types import Message, UpdateNewMessage

from cansend import CanSend
from config import *
from terabox import get_data
from tools import (
    convert_seconds,
    download_file,
    download_image_to_bytesio,
    extract_code_from_url,
    get_formatted_size,
    get_urls_from_string,
    is_user_on_chat,
)

bot = TelegramClient("tele", API_ID, API_HASH)

db = redis.Redis(
    host=HOST,
    port=PORT,
    password=PASSWORD,
    decode_responses=True,
)


@bot.on(
    events.NewMessage(
        pattern="/start$",
        incoming=True,
        outgoing=False,
        func=lambda x: x.is_private,
    )
)
async def start(m: UpdateNewMessage):
    reply_text = f"""
🤖 **Hello! I am your Terabox Downloader Bot** 🤖

📥 **Send me the Terabox link and I will start downloading it for you.** 📥

🔗 **Join [Ultroid Official](https://t.me/Ultroid_Official) for Updates** 🔗

🤖 **Make Your Own Private Terabox Bot at [UltroidxTeam](https://t.me/ultroidxTeam)** 🤖
"""
    check_if_ultroid_official = await is_user_on_chat(bot, "@Ultroid_Official", m.peer_id)
    if not check_if_ultroid_official:
        await m.reply("Please join @Ultroid_Official then send me the link again.")
        return

    check_if_ultroid_official_chat = await is_user_on_chat(bot, "@UltroidOfficial_chat", m.peer_id)
    if not check_if_ultroid_official_chat:
        await m.reply("Please join @UltroidOfficial_chat then send me the link again.")
        return

    await m.reply(reply_text, link_preview=False, parse_mode="markdown")



@bot.on(
    events.NewMessage(
        pattern="/start (.*)",
        incoming=True,
        outgoing=False,
        func=lambda x: x.is_private,
    )
)
async def start(m: UpdateNewMessage):
    text = m.pattern_match.group(1)
    fileid = db.get(str(text))
    check_if = await is_user_on_chat(bot, "@Ultroid_Official", m.peer_id)
    if not check_if:
        return await m.reply("Please join @Ultroid_Official then send me the link again.")
    check_if = await is_user_on_chat(bot, "@UltroidOfficial_chat", m.peer_id)
    if not check_if:
        return await m.reply(
            "Please join @UltroidOfficial_chat then send me the link again."
        )
    await bot(
        ForwardMessagesRequest(
            from_peer=PRIVATE_CHAT_ID,
            id=[int(fileid)],
            to_peer=m.chat.id,
            drop_author=True,
            # noforwards=True,  # Uncomment it if you dont want to forward the media. or do urdo
            background=True,
            drop_media_captions=False,
            with_my_score=True,
        )
    )


@bot.on(
    events.NewMessage(
        pattern="/remove (.*)",
        incoming=True,
        outgoing=False,
        from_users=ADMINS,
    )
)
async def remove(m: UpdateNewMessage):
    user_id = m.pattern_match.group(1)
    if db.get(f"check_{user_id}"):
        db.delete(f"check_{user_id}")
        await m.reply(f"Removed {user_id} from the list.")
    else:
        await m.reply(f"{user_id} is not in the list.")


from tools import parse_rename_command

@bot.on(
    events.NewMessage(
        incoming=True,
        outgoing=False,
        func=lambda message: message.text
        and get_urls_from_string(message.text)
        and message.is_private,
    )
)
async def get_message(m: Message):
    text = m.text.strip()
    # Check if the message includes a command to rename the file
    rename_command, new_file_name = parse_rename_command(text)
    if rename_command and new_file_name:
        # If the rename command is provided with a new file name, handle the message with the new file name
        asyncio.create_task(handle_message(m, new_file_name))
    else:
        # Otherwise, handle the message without renaming the file
        asyncio.create_task(handle_message(m))


async def handle_message(m: Message, file_name_override=None):

    url = get_urls_from_string(m.text)
    if not url:
        return await m.reply("Please enter a valid URL.")

    # Check if the user is a member of the required channels
    check_if_ultroid_official = await is_user_on_chat(bot, "@Ultroid_Official", m.peer_id)
    if not check_if_ultroid_official:
        return await m.reply("Please join @Ultroid_Official then send me the link again.")

    check_if_ultroid_official_chat = await is_user_on_chat(bot, "@UltroidOfficial_chat", m.peer_id)
    if not check_if_ultroid_official_chat:
        return await m.reply("Please join @UltroidOfficial_chat then send me the link again.")

    # Check for spamming
    is_spam = db.get(m.sender_id)
    if is_spam and m.sender_id not in [6695586027]:
        return await m.reply("You are spamming. Please wait a minute and try again.")

    # Check the limit
    hm = await m.reply("Sending you the media, please wait...")
    count = db.get(f"check_{m.sender_id}")
    if count and int(count) > 5:
        return await hm.edit("You are currently limited. Please come back after 2 hours or use another account.")

    # Extract the short URL from the Terabox link
    shorturl = extract_code_from_url(url)
    if not shorturl:
        return await hm.edit("It seems like your link is invalid.")

    # Retrieve the file ID from the database if it exists
    fileid = db.get(shorturl)
    if fileid:
        try:
            await hm.delete()
        except:
            pass

        await bot(
            ForwardMessagesRequest(
                from_peer=PRIVATE_CHAT_ID,
                id=[int(fileid)],
                to_peer=m.chat.id,
                drop_author=True,
                # noforwards=True, # Uncomment it if you dont want to forward the media.
                background=True,
                drop_media_captions=False,
                with_my_score=True,
            )
        )
        db.set(m.sender_id, time.monotonic(), ex=60)
        db.set(
            f"check_{m.sender_id}",
            int(count) + 1 if count else 1,
            ex=7200,
        )
        return

    # Get data from the Terabox link
    data = get_data(url)
    if not data:
        return await hm.edit("Sorry! The API is not accessible or your link is broken.")

    # Check file extension and size
    if not data["file_name"].endswith((".mp4", ".mkv", ".Mkv", ".webm")):
        return await hm.edit(
            f"Sorry! This file format is not supported. I can only download .mp4, .mkv, and .webm files."
        )
    if int(data["sizebytes"]) > 524288000 and m.sender_id not in [6695586027]:
        return await hm.edit(
            f"Sorry! This file is too large. I can only download files up to 500MB, but this file is {data['size']}."
        )

    # Customize the file name if provided
    file_name = file_name_override if file_name_override else data["file_name"]

    # Start downloading
    start_time = time.time()
    cansend = CanSend()

    async def progress_bar(current_downloaded, total_downloaded, state="Sending"):

        if not cansend.can_send():
            return
        bar_length = 20
        percent = current_downloaded / total_downloaded
        arrow = "█" * int(percent * bar_length)
        spaces = "░" * (bar_length - len(arrow))

        elapsed_time = time.time() - start_time

        head_text = f"{state} `{file_name}`"
        progress_bar = f"[{arrow + spaces}] {percent:.2%}"
        upload_speed = current_downloaded / elapsed_time if elapsed_time > 0 else 0
        speed_line = f"Speed: **{get_formatted_size(upload_speed)}/s**"

        time_remaining = (
            (total_downloaded - current_downloaded) / upload_speed
            if upload_speed > 0
            else 0
        )
        time_line = f"Time Remaining: `{convert_seconds(time_remaining)}`"

        size_line = f"Size: **{get_formatted_size(current_downloaded)}** / **{get_formatted_size(total_downloaded)}**"

        await hm.edit(
            f"{head_text}\n{progress_bar}\n{speed_line}\n{time_line}\n{size_line}",
            parse_mode="markdown",
        )

    uuid = str(uuid4())
    thumbnail = download_image_to_bytesio(data["thumb"], "thumbnail.png")

    try:
        file = await bot.send_file(
            PRIVATE_CHAT_ID,
            file=data["direct_link"],
            thumb=thumbnail if thumbnail else None,
            progress_callback=progress_bar,
            caption=f"""
File Name: `{file_name}`
Size: **{data["size"]}** 
Direct Link: [Click Here](https://t.me/TeraboxDownloadeRobot?start={uuid})

@Ultroid_Official
""",
            supports_streaming=True,
            spoiler=True,
        )
    except telethon.errors.rpcerrorlist.WebpageCurlFailedError:
        download = await download_file(
            data["direct_link"], file_name, progress_bar
        )
        if not download:
            return await hm.edit(
                f"Sorry! Download Failed but you can download it from [here]({data['direct_link']}).",
                parse_mode="markdown",
            )
        file = await bot.send_file(
            PRIVATE_CHAT_ID,
            download,
            caption=f"""
File Name: `{file_name}`
Size: **{data["size"]}** 
Direct Link: [Click Here](https://t.me/TeraboxDownloadeRobot?start={uuid})

Share : @ultroid_official
""",
            progress_callback=progress_bar,
            thumb=thumbnail if thumbnail else None,
            supports_streaming=True,
            spoiler=True,
        )
        try:
            os.unlink(download)
        except Exception as e:
            print(e)
    except Exception:
        return await hm.edit(
            f"Sorry! Download Failed but you can download it from [here]({data['direct_link']}).",
            parse_mode="markdown",
        )

    try:
        await hm.delete()
    except Exception as e:
        print(e)

    if shorturl:
        db.set(shorturl, file.id)
    if file:
        db.set(uuid, file.id)

        await bot(
            ForwardMessagesRequest(
                from_peer=PRIVATE_CHAT_ID,
                id=[file.id],
                to_peer=m.chat.id,
                top_msg_id=m.id,
                drop_author=True,
                # noforwards=True,  # Uncomment it if you dont want to forward the media.
                background=True,
                drop_media_captions=False,
                with_my_score=True,
            )
        )
        db.set(m.sender_id, time.monotonic(), ex=60)
        db.set(
            f"check_{m.sender_id}",
            int(count) + 1 if count else 1,
            ex=7200,
        )
bot.start(bot_token=BOT_TOKEN)
bot.run_until_disconnected()
