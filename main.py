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
        await m.reply(f"Your Ads token is expired, refresh your token and try again.\n\nToken Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\nWhat is the token?\n\nThis is an ads token. If you pass 1 ad, you can use the bot for 24 hours after passing the ad.", buttons=btn, protect_content=False, quote=True)
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

# Start and run the bot
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("Bot is running...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

