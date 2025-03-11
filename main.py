import os
import logging
import aiomysql
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.enums import ChatType, ChatMemberStatus
from keep_alive import keep_alive  # Replit/Railway Keep Alive
import asyncio

TOKEN = os.getenv("BOT_TOKEN")  # Railway Env Variable
DATABASE_URL = os.getenv("DATABASE_URL")  # MySQL Connection URL

AUTHORIZED_USER_IDS = [5531835185, 7428947575]  
GROUP_1_ID = -1002341293170  
GROUP_2_ID = -1002446627849  
GROUP_1_LINK = "https://t.me/Icon_buysell"
GROUP_2_LINK = "https://t.me/GenVpremiumShop"

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

FIXED_DETAILS = "Scammer, be careful!"  # Fixed scammer message

# Connect to MySQL
async def get_db():
    return await aiomysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASS"),
        db=os.getenv("MYSQL_DB"),
        port=int(os.getenv("MYSQL_PORT")),
        autocommit=True
    )

# Create table if not exists
async def init_db():
    db = await get_db()
    async with db.cursor() as cur:
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS scammers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(50) UNIQUE,
                number VARCHAR(20) UNIQUE,
                details TEXT
            )
        """)
    db.close()

# Add scammer
async def add_scammer(message: Message):
    user_id = message.from_user.id
    if not await is_user_in_groups(user_id):
        await message.reply("❌ You need to join both groups first.")
        return

    args = message.text.split(" ", 2)
    if len(args) < 3:
        await message.reply("⚠️ Usage: /add_scammer <user_id> <number>")
        return

    scammer_id, number = args[1], args[2]
    db = await get_db()

    try:
        async with db.cursor() as cur:
            await cur.execute("SELECT * FROM scammers WHERE user_id = %s OR number = %s", (scammer_id, number))
            existing = await cur.fetchone()

            if existing:
                await message.reply(f"⚠️ Scammer already exists!")
            else:
                await cur.execute("INSERT INTO scammers (user_id, number, details) VALUES (%s, %s, %s)", 
                                  (scammer_id, number, FIXED_DETAILS))
                await message.reply(f"✅ Scammer Added: User ID '{scammer_id}', Number '{number}'")
    except Exception as e:
        logging.error(f"Error adding scammer: {e}")
        await message.reply("❌ Error adding scammer!")
    finally:
        db.close()

# Search scammer
async def search_scammer(message: Message):
    args = message.text.split(" ", 1)
    if len(args) < 2:
        await message.reply("⚠️ Usage: /scminf <user_id or number>")
        return

    query = args[1]
    db = await get_db()

    try:
        async with db.cursor() as cur:
            await cur.execute("SELECT * FROM scammers WHERE user_id = %s OR number = %s", (query, query))
            result = await cur.fetchone()

            if result:
                await message.reply(f"🚨 Scammer Found!\n🆔 User ID: {result[1]}\n📞 Number: {result[2]}\n📌 Details: {result[3]}")
            else:
                await message.reply("✅ No scammer found!")
    except Exception as e:
        await message.reply("❌ Error searching scammer!")
    finally:
        db.close()

# Auto-detect scammer numbers
async def auto_detect_scammer(message: Message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        db = await get_db()
        message_text = message.text.lower()
        numbers_in_message = re.findall(r'\b\d{5,15}\b', message_text)

        try:
            async with db.cursor() as cur:
                for number in numbers_in_message:
                    await cur.execute("SELECT * FROM scammers WHERE number = %s", (number,))
                    scammer = await cur.fetchone()
                    if scammer:
                        warning = f"⚠️ **Warning! This number is flagged as a scammer!**\n\n📞 **Number:** {scammer[2]}\n📌 **Details:** {scammer[3]}"
                        await message.reply(warning)
        except Exception as e:
            logging.error(f"Error auto-detecting scammer: {e}")
        finally:
            db.close()

# Bot Start
async def start(message: Message):
    user_id = message.from_user.id
    is_member = await is_user_in_groups(user_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔹 Join Group", url=GROUP_1_LINK),
                InlineKeyboardButton(text="🔹 Join Group", url=GROUP_2_LINK)
            ]
        ]
    )

    if is_member:
        await message.reply("🚨 **USE /scminf 🚨\n\n🔍 **TO GET SCAMMER INFORMATION** OR\n\n👥 **ADD ME TO YOUR GROUP** TO PROTECT YOUR GROUP MEMBERS! 🛡️\n\n💬 Stay safe and avoid scams! 💯")
    else:
        await message.reply("⚠️ **You must join both groups to use this bot!**\n\n➡️ Click the buttons below to join and try again:", reply_markup=keyboard)

async def main():
    print("Starting bot...")
    logging.info("Bot is starting...")

    await init_db()  # Initialize MySQL Database

    dp.message.register(start, lambda message: message.text == '/start')
    dp.message.register(add_scammer, lambda message: message.text and message.text.startswith('/add_scammer'))
    dp.message.register(search_scammer, lambda message: message.text and message.text.startswith('/scminf'))
    dp.message.register(auto_detect_scammer)

    keep_alive()  # Keep Replit running
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
