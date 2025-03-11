import os
import asyncpg
import logging
import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.enums import ChatType, ChatMemberStatus

# Fetch sensitive info from environment variables
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
GROUP_1_ID = -1002341293170  # Replace with your first group ID
GROUP_2_ID = -1002446627849  # Replace with your second group ID
GROUP_1_LINK = "https://t.me/Icon_buysell"
GROUP_2_LINK = "https://t.me/GenVpremiumShop"

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

FIXED_DETAILS = "Scammer, be careful!"

# Database Connection
async def connect_db():
    return await asyncpg.connect(DATABASE_URL)

# Initialize Database
async def init_db():
    conn = await connect_db()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS scammers (
            user_id TEXT PRIMARY KEY,
            number TEXT UNIQUE,
            details TEXT
        );
        CREATE TABLE IF NOT EXISTS groups (
            group_id BIGINT PRIMARY KEY
        );
    """)
    await conn.close()

# Add Scammer
async def add_scammer(user_id, number):
    conn = await connect_db()
    await conn.execute("""
        INSERT INTO scammers (user_id, number, details) 
        VALUES ($1, $2, $3) ON CONFLICT DO NOTHING;
    """, user_id, number, FIXED_DETAILS)
    await conn.close()

# Search Scammer
async def search_scammer(query):
    conn = await connect_db()
    result = await conn.fetchrow("SELECT * FROM scammers WHERE user_id = $1 OR number = $1", query)
    await conn.close()
    return result

# Add Group
async def add_group(group_id):
    conn = await connect_db()
    await conn.execute("INSERT INTO groups (group_id) VALUES ($1) ON CONFLICT DO NOTHING;", group_id)
    await conn.close()

# Get All Groups
async def get_groups():
    conn = await connect_db()
    groups = await conn.fetch("SELECT group_id FROM groups")
    await conn.close()
    return [g['group_id'] for g in groups]

# Check if user is in both groups
async def is_user_in_groups(user_id):
    try:
        member_1 = await bot.get_chat_member(GROUP_1_ID, user_id)
        member_2 = await bot.get_chat_member(GROUP_2_ID, user_id)
        return member_1.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR] and \
               member_2.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except:
        return False

# Start Command
async def start(message: Message):
    user_id = message.from_user.id
    is_member = await is_user_in_groups(user_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔹 Join Group", url=GROUP_1_LINK),
                                                       InlineKeyboardButton(text="🔹 Join Group", url=GROUP_2_LINK)]])
    if is_member:
        await message.reply("🚨 Use /scminf <user_id or number> to check scammers!")
    else:
        await message.reply("⚠️ You must join both groups to use this bot!", reply_markup=keyboard)

# Add Scammer Command
async def add_scammer_handler(message: Message):
    args = message.text.split(" ", 2)
    if len(args) < 3:
        await message.reply("⚠️ Usage: /add_scammer <user_id> <number>")
        return
    await add_scammer(args[1], args[2])
    await message.reply(f"✅ Scammer with User ID '{args[1]}' and Number '{args[2]}' added successfully!")

# Search Scammer Command
async def search_scammer_handler(message: Message):
    args = message.text.split(" ", 1)
    if len(args) < 2:
        await message.reply("⚠️ Usage: /scminf <user_id or number>")
        return
    scammer = await search_scammer(args[1])
    if scammer:
        await message.reply(f"🚨 Scammer Found!\n🆔 User ID: {scammer['user_id']}\n📞 Number: {scammer['number']}\n📌 Details: {scammer['details']}")
    else:
        await message.reply("✅ No scammer found!")

# Auto Detect Scammer Numbers
async def auto_detect_scammer(message: Message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        message_text = message.text.lower()
        numbers_in_message = re.findall(r'\b\d{5,15}\b', message_text)
        conn = await connect_db()
        scammers = await conn.fetch("SELECT * FROM scammers WHERE number = ANY($1)", numbers_in_message)
        await conn.close()
        for scammer in scammers:
            await message.reply(f"⚠️ Warning! This number is flagged as a scammer!\n📞 Number: {scammer['number']}\n📌 Details: {scammer['details']}")

# Bot Joined a Group
@dp.my_chat_member()
async def on_chat_joined(event: ChatMemberUpdated):
    if event.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if event.new_chat_member.status != ChatMemberStatus.LEFT:
            await add_group(event.chat.id)
            await bot.send_message(event.chat.id, "👋 Thanks for adding me! I'll help protect this group by identifying scammers.")

# Main Function
async def main():
    logging.info("Starting bot...")
    await init_db()
    dp.message.register(start, lambda message: message.text == '/start')
    dp.message.register(add_scammer_handler, lambda message: message.text.startswith('/add_scammer'))
    dp.message.register(search_scammer_handler, lambda message: message.text.startswith('/scminf'))
    dp.message.register(auto_detect_scammer)
    await dp.start_polling(bot)

# Run Bot
if __name__ == "__main__":
    asyncio.run(main())
