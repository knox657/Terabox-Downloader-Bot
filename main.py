import asyncio
import os
import time
import random
import string
from uuid import uuid4
import json
import redis
import telethon
from telethon import TelegramClient, events
from telethon.tl.functions.messages import ForwardMessagesRequest
from telethon.types import UpdateNewMessage
from telethon.tl.custom import Button

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

import motor.motor_asyncio
from config import DB_URI, DB_NAME

dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]
user_data = database['users']

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

def new_user(id):
    return {
        '_id': id,
        'verify_status': {
            'is_verified': False,
            'verified_time': "",
            'verify_token': "",
            'link': ""
        }
    }

async def present_user(user_id: int):
    found = await user_data.find_one({'_id': user_id})
    return bool(found)

async def add_user(user_id: int):
    user = new_user(user_id)
    await user_data.insert_one(user)

async def db_verify_status(user_id):
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('verify_status', default_verify)
    return default_verify

async def db_update_verify_status(user_id, verify):
    await user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

async def full_userbase():
    user_docs = user_data.find()
    user_ids = [doc['_id'] async for doc in user_docs]
    return user_ids

async def del_user(user_id: int):
    await user_data.delete_one({'_id': user_id})

bot = TelegramClient("tele", API_ID, API_HASH)

db = redis.Redis(
    host=HOST,
    port=PORT,
    password=PASSWORD,
    decode_responses=True,
)

@bot.on(events.NewMessage(pattern="/start$", incoming=True, outgoing=False, func=lambda x: x.is_private))
async def start(m: UpdateNewMessage):
    user_id = m.sender_id
    if not db.exists(f"user:{user_id}"):
        user_details = json.dumps({"username": m.sender.username, "first_name": m.sender.first_name, "last_name": m.sender.last_name})
        db.set(f"user:{user_id}", user_details)

    verify_status = await get_verify_status(user_id)
    if verify_status and verify_status['is_verified']:
        await m.reply("You are already verified. You can start using the bot.")
        return

    if not verify_status:
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        await update_verify_status(user_id, verify_token=token, link="")
    else:
        token = verify_status['verify_token']

    link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://telegram.dog/{client.username}?start=verify_{token}')
    btn = [
        [Button.url("Click here", url=link)],
        [Button.url('How to use the bot', url=TUT_VID)]
    ]
    await m.reply(f"Your Ads token is expired, refresh your token and try again.\n\nToken Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\nWhat is the token?\n\nThis is an ads token. If you pass 1 ad, you can use the bot for 24 hours after passing the ad.", buttons=btn, protect_content=False, quote=True)

    reply_text = """
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

@bot.on(events.NewMessage(pattern="/start (.*)", incoming=True, outgoing=False, func=lambda x: x.is_private))
async def start_with_token(m: UpdateNewMessage):
    text = m.pattern_match.group(1)
    fileid = db.get(str(text))
    
    verify_status = await get_verify_status(m.sender_id)
    if IS_VERIFY and not verify_status['is_verified']:
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        await update_verify_status(m.sender_id, verify_token=token, link="")
        link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://telegram.dog/{client.username}?start=verify_{token}')
        btn = [
            [Button.url("Click here", url=link)],
            [Button.url('How to use the bot', url=TUT_VID)]
        ]
        await m.reply(f"Your Ads token is expired, refresh your token and try again.\n\nToken Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\nWhat is the token?\n\nThis is an ads token. If you pass 1 ad,
        return await m.reply(f"Your Ads token is expired, refresh your token and try again.\n\nToken Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\nWhat is the token?\n\nThis is an ads token. If you pass 1 ad, you can use the bot for 24 hours after passing the ad.", buttons=btn, protect_content=False, quote=True)
        return

    check_if = await is_user_on_chat(bot, "@Ultroid_Official", m.peer_id)
    if not check_if:
        return await m.reply("Please join @Ultroid_Official then send me the link again.")
    check_if = await is_user_on_chat(bot, "@UltroidOfficial_chat", m.peer_id)
    if not check_if:
        return await m.reply("Please join @UltroidOfficial_chat then send me the link again.")

    await bot(ForwardMessagesRequest(from_peer=PRIVATE_CHAT_ID, id=[int(fileid)], to_peer=m.chat.id, drop_author=True, background=True, drop_media_captions=False, with_my_score=True))

@bot.on(events.NewMessage(pattern="/remove (.*)", incoming=True, outgoing=False, func=lambda x: x.is_private))
async def remove_user(m: UpdateNewMessage):
    user_id = m.sender_id
    text = m.pattern_match.group(1)

    if user_id not in ADMIN_IDS:
        await m.reply("You don't have permission to use this command.")
        return

    try:
        user_to_remove = int(text)
        await del_user(user_to_remove)
        db.delete(f"user:{user_to_remove}")
        await m.reply(f"User {user_to_remove} has been removed.")
    except Exception as e:
        await m.reply(f"An error occurred: {str(e)}")

@bot.on(events.NewMessage(pattern="/broadcast (.*)", incoming=True, outgoing=False, func=lambda x: x.is_private))
async def broadcast(m: UpdateNewMessage):
    user_id = m.sender_id
    text = m.pattern_match.group(1)

    if user_id not in ADMIN_IDS:
        await m.reply("You don't have permission to use this command.")
        return

    user_ids = await full_userbase()
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
        except Exception as e:
            print(f"Failed to send message to {uid}: {str(e)}")

@bot.on(events.NewMessage(pattern="/total_users", incoming=True, outgoing=False, func=lambda x: x.is_private))
async def total_users(m: UpdateNewMessage):
    user_id = m.sender_id

    if user_id not in ADMIN_IDS:
        await m.reply("You don't have permission to use this command.")
        return

    user_count = await user_data.count_documents({})
    await m.reply(f"Total users: {user_count}")

@bot.on(events.NewMessage(incoming=True, outgoing=False, func=lambda x: x.is_private))
async def handle_message(m: UpdateNewMessage):
    user_id = m.sender_id
    message_text = m.message.message

    if not message_text:
        return

    urls = get_urls_from_string(message_text)
    if not urls:
        await m.reply("Please send a valid Terabox link.")
        return

    if IS_VERIFY:
        verify_status = await get_verify_status(user_id)
        if not verify_status['is_verified']:
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            await update_verify_status(user_id, verify_token=token, link="")
            link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://telegram.dog/{client.username}?start=verify_{token}')
            btn = [
                [Button.url("Click here", url=link)],
                [Button.url('How to use the bot', url=TUT_VID)]
            ]
            await m.reply(f"Your Ads token is expired, refresh your token and try again.\n\nToken Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\nWhat is the token?\n\nThis is an ads token. If you pass 1 ad, you can use the bot for 24 hours after passing the ad.", buttons=btn, protect_content=False, quote=True)
            return

    can_send = await CanSend(m.sender_id)
    if not can_send:
        await m.reply("You are sending messages too frequently. Please try again later.")
        return

    terabox_link = urls[0]
    await m.reply("Processing your Terabox link, please wait...")

    try:
        data = await get_data(terabox_link)
        if data['status'] == 'success':
            files = data['files']
            for file in files:
                file_id = uuid4()
                db.set(str(file_id), file['fileid'])
                await m.reply(f"File: {file['name']}\nSize: {get_formatted_size(file['size'])}\n\nTo download: /start {file_id}")
        else:
            await m.reply("Failed to process the link. Please ensure the Terabox link is correct.")
    except Exception as e:
        await m.reply(f"An error occurred while processing the link: {str(e)}")

def convert_seconds(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

async def get_message(m: UpdateNewMessage):
    asyncio.create_task(handle_message(m))

async def handle_message(m: UpdateNewMessage):
    url = get_urls_from_string(m.message.message)
    if not url:
        return await m.reply("Please enter a valid url.")
    
    check_if = await is_user_on_chat(bot, "@ultroid_official", m.sender_id)
    if not check_if:
        return await m.reply("Please join @ultroid_official then send me the link again.")
    
    check_if = await is_user_on_chat(bot, "@ultroidofficial_chat", m.sender_id)
    if not check_if:
        return await m.reply("Please join @ultroidofficial_chat then send me the link again.")
    
    is_spam = db.get(m.sender_id)
    if is_spam and m.sender_id not in [6695586027]:
        return await m.reply("You are spamming. Please wait a 1 minute and try again.")
    
    hm = await m.reply("Sending you the media wait...")
    count = db.get(f"check_{m.sender_id}")
    if count and int(count) > 5:
        return await hm.edit("You are limited now. Please come back after 2 hours or use another account.")
    
    shorturl = extract_code_from_url(url)
    if not shorturl:
        return await hm.edit("Seems like your link is invalid.")
    
    fileid = db.get(shorturl)
    if fileid:
        try:
            await hm.delete()
        except:
            pass
        
        await bot(ForwardMessagesRequest(
            from_peer=PRIVATE_CHAT_ID,
            id=[int(fileid)],
            to_peer=m.chat_id,
            drop_author=True,
            background=True,
            drop_media_captions=False,
            with_my_score=True,
        ))
        db.set(m.sender_id, time.monotonic(), ex=60)
        db.set(f"check_{m.sender_id}",
        return await hm.edit("You are limited now. Please come back after 2 hours or use another account.")
    
    data = await get_data(url)
    if not data:
        return await hm.edit("Sorry! API is dead or maybe your link is broken.")
    
    db.set(m.sender_id, time.monotonic(), ex=60)
    if (
        not data["file_name"].endswith(".mp4") and
        not data["file_name"].endswith(".mkv") and
        not data["file_name"].endswith(".Mkv") and
        not data["file_name"].endswith(".webm")
    ):
        return await hm.edit("Sorry! File is not supported for now. I can download only .mp4, .mkv and .webm files.")
    
    if int(data["sizebytes"]) > 524288000 and m.sender_id not in [6695586027]:
        return await hm.edit(f"Sorry! File is too big. I can download only 500MB and this file is of {data['size']} .")
    
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
        head_text = f"{state} `{data['file_name']}`"
        progress_bar = f"[{arrow + spaces}] {percent:.2%}"
        upload_speed = current_downloaded / elapsed_time if elapsed_time > 0 else 0
        speed_line = f"Speed: **{get_formatted_size(upload_speed)}/s**"
        time_remaining = (
            (total_downloaded - current_downloaded) / upload_speed if upload_speed > 0 else 0
        )
        time_line = f"Time Remaining: `{convert_seconds(time_remaining)}`"
        size_line = f"Size: **{get_formatted_size(current_downloaded)}** / **{get_formatted_size(total_downloaded)}**"
        
        await hm.edit(
            f"{head_text}\n{progress_bar}\n{speed_line}\n{time_line}\n{size_line}",
            parse_mode="markdown"
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
File Name: `{data['file_name']}`
Size: **{data["size"]}** 
Direct Link: [Click Here](https://t.me/TeraboxDownloadeRobot?start={uuid})

@ultroid_official
""",
            supports_streaming=True,
            spoiler=True,
        )
    except telethon.errors.rpcerrorlist.WebpageCurlFailedError:
        download = await download_file(
            data["direct_link"], data["file_name"], progress_bar
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
File Name: `{data['file_name']}`
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
        os.unlink(download)
    except Exception as e:
        pass
    
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
                to_peer=m.chat_id,
                top_msg_id=m.id,
                drop_author=True,
                background=True,
                drop_media_captions=False,
                with_my_score=True,
            )
        )
        db.set(m.sender_id, time.monotonic(), ex=60)
        db.set(f"check_{m.sender_id}", int(count) + 1 if count else 1, ex=7200)

@bot.on(
    events.NewMessage(
        pattern="/broadcast (.+)",
        incoming=True,
        outgoing=False,
        from_users=ADMIN_IDS,  # Specify the user IDs of admins who are allowed to use this command
    )
)
async def broadcast_message(m: UpdateNewMessage):
    message = m.pattern_match.group(1)
    # Retrieve all users from the database
    all_users = db.keys("user:*")
    for user_key in all_users:
        user_id = user_key.split(":")[-1]
        try:
            # Send the broadcast message to each user
            await bot.send_message(int(user_id), message)
        except Exception as e:
            print(f"Failed to send message to user {user_id}: {str(e)}")
    await m.reply("Broadcast sent successfully!")

@bot.on(
    events.NewMessage(
        pattern="/total_users",
        incoming=True,
        outgoing=False,
        from_users=ADMIN_IDS,  # Specify the user IDs of admins who are allowed to use this command
    )
)
async def total_users(m: UpdateNewMessage):
    # Retrieve all users from the database
    all_users = db.keys("user:*")
    total_users_count = len(all_users)
    await m.reply(f"Total number of users: {total_users_count}")

bot.start(bot_token=BOT_TOKEN)
bot.run_until_disconnected()


# Start and run the bot
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("Bot is running...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
