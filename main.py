import asyncio
import os
import time
from shortzy import Shortzy
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
import os
import logging
from telethon.errors.rpcerrorlist import FloodWaitError, FilePartsInvalidError

import motor.motor_asyncio
from config import DB_URI, DB_NAME

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration for rate limiting (example: 60 seconds)
RATE_LIMIT = 20

# Define the bot variable here
bot = TelegramClient("tele", API_ID, API_HASH)

db = redis.Redis(
    host=HOST,
    port=PORT,
    password=PASSWORD,
    decode_responses=True,
)

ADMINS = [6695586027, 6020516635]
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

async def get_verify_status(user_id):
    verify = await db_verify_status(user_id)
    return verify

async def update_verify_status(user_id, verify_token="", is_verified=False, verified_time=0, link=""):
    current = await db_verify_status(user_id)
    current['verify_token'] = verify_token
    current['is_verified'] = is_verified
    current['verified_time'] = verified_time
    current['link'] = link
    await db_update_verify_status(user_id, current)

async def start_bot():
    print("Bot is running...")
    await bot.start(bot_token=BOT_TOKEN)
    bot.add_event_handler(handle_verification_link)
    bot.add_event_handler(handle_terabox_link)
    bot.add_event_handler(handle_message)
    bot.add_event_handler(handle_reset)
    bot.add_event_handler(handle_broadcast)
    bot.add_event_handler(handle_total_users)
    bot.run_until_disconnected()

# Handle verification link
@bot.on(events.NewMessage(pattern="start=verify_[a-zA-Z0-9]+", incoming=True, outgoing=False, func=lambda x: x.is_private))
async def handle_verification_link(event: UpdateNewMessage):
    user_id = event.sender_id
    token = event.text.split("start=verify_")[1]
    is_valid = await verify_token(token, user_id)
    if is_valid:
        await event.reply("Your token has been verified successfully. You can now proceed.")
    else:
        await event.reply("Invalid token. Please try again or contact support.")

# Handle Terabox links
@bot.on(events.NewMessage(pattern="https://terabox.com/[a-zA-Z0-9]+", incoming=True, outgoing=False, func=lambda x: x.is_private))
async def handle_terabox_link(event: UpdateNewMessage):
    user_id = event.sender_id
    verify_status = await get_verify_status(user_id)
    
    if IS_VERIFY and not verify_status['is_verified']:
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        await update_verify_status(user_id, verify_token=token, link="")
        link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://telegram.dog/TeraboxDownloadeRobot?start=verify_{token}')
        btn = [
            [Button.url("Click here", url=link)],
            [Button.url('How to use the bot', url=TUT_VID)]
        ]
        await event.reply(f"Your Ads token is expired, refresh your token and try again.\n\nToken Timeout: {get_exp_time(VERIFY_EXPIRE)}\n\nWhat is the token?\n\nThis is an ads token. If you pass 1 ad, you can use the bot for 24 hours after passing the ad.", buttons=btn)
        return

    link = event.text
    await event.reply("Processing your Terabox link...")

    try:
        terabox_data = await get_data(link)
        filename = terabox_data['filename']
        filesize = terabox_data['filesize']
        filelink = terabox_data['filelink']
        formatted_size = get_formatted_size(filesize)

        reply = f"""
**Filename:** {filename}
**Filesize:** {formatted_size}

**Downloading...**
"""
        await event.reply(reply)
        
        file_path = await download_file(filelink, filename)
        await bot.send_file(event.sender_id, file_path, caption=f"**{filename}**\n**Size:** {formatted_size}")

        # Cleanup the downloaded file
        os.remove(file_path)
        logger.info(f"File {filename} sent and deleted from the server.")

    except FilePartsInvalidError as e:
        logger.error(f"File parts invalid: {str(e)}")
        await event.reply("Error: The file could not be downloaded properly. Please try again later.")
    except FloodWaitError as e:
        logger.warning(f"Flood wait: {str(e)}")
        await event.reply(f"Bot is being rate limited. Please try again after {e.seconds} seconds.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await event.reply("An unexpected error occurred while processing your request. Please try again later or contact support.")

# Handle normal messages
@bot.on(events.NewMessage(func=lambda x: True))
async def handle_message(event: UpdateNewMessage):
    sender_id = event.sender_id
    message_text = event.text.strip().lower()

    if message_text == "/start":
        await event.reply("Welcome to the Telegram Downloader Bot! Send me a Terabox link to download files from Terabox.")
    elif message_text == "/reset" and sender_id in ADMINS:
        await reset_bot(event)
    elif message_text == "/broadcast" and sender_id in ADMINS:
        await broadcast_message(event)
    elif message_text == "/total_users" and sender_id in ADMINS:
        await total_users(event)
    else:
        await event.reply("I don't understand this command. Send me a Terabox link to download files from Terabox.")

# Handle reset command
async def handle_reset(event: UpdateNewMessage):
    sender_id = event.sender_id
    message_text = event.text.strip().lower()

    if message_text == "/reset" and sender_id in ADMINS:
        await reset_bot(event)

async def reset_bot(event: UpdateNewMessage):
    await event.reply("Bot has been reset successfully.")

# Handle broadcast command
async def handle_broadcast(event: UpdateNewMessage):
    sender_id = event.sender_id
    message_text = event.text.strip().lower()

    if message_text == "/broadcast" and sender_id in ADMINS:
        await broadcast_message(event)

async def broadcast_message(event: UpdateNewMessage):
    await event.reply("Broadcasting message to all users...")

    total_users_count = 0
    async for user_id in full_userbase():
        try:
            await bot.send_message(user_id, "Broadcast message here")
            total_users_count += 1
        except Exception as e:
            logger.error(f"Error broadcasting to user {user_id}: {str(e)}")
            continue
    
    await event.reply(f"Broadcast message sent to {total_users_count} users.")

# Handle total_users command
async def handle_total_users(event: UpdateNewMessage):
    sender_id = event.sender_id
    message_text = event.text.strip().lower()

    if message_text == "/total_users" and sender_id in ADMINS:
        await total_users(event)

async def total_users(event: UpdateNewMessage):
    total_users_count = await user_data.count_documents({})
    await event.reply(f"Total users: {total_users_count}")

async def verify_token(token, user_id):
    verify_status = await get_verify_status(user_id)
    if token == verify_status['verify_token']:
        await update_verify_status(user_id, is_verified=True, verified_time=int(time.time()))
        return True
    else:
        return False

async def get_shortlink(url, api, link):
    shortner = Shortzy(api, url)
    short_link = await shortner.shorten(link)
    return short_link

async def get_exp_time(exp_time):
    current_time = int(time.time())
    expiry_time = current_time + exp_time
    formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry_time))
    return formatted_time

async def main():
    await start_bot()

if __name__ == "__main__":
    asyncio.run(main())
