# main.py
import logging
import os
import json
import asyncio
import httpx
import secrets
import csv
import tempfile
import shutil
import re
from datetime import datetime, timedelta
from threading import Thread

from flask import Flask
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

import aiosqlite
import config
from database import (
    init_db, add_user, get_user, update_credits,
    create_redeem_code, redeem_code_db, get_all_users,
    set_ban_status, get_bot_stats, get_users_in_range,
    add_admin, remove_admin, get_all_admins, is_admin,
    get_expired_codes, delete_redeem_code, get_top_referrers,
    deactivate_code, get_all_codes, parse_time_string,
    get_user_by_username, get_user_stats,
    get_recent_users, get_active_codes, get_inactive_codes,
    delete_user, reset_user_credits,
    search_users, log_lookup,
    get_total_lookups, get_user_lookups,
    get_low_credit_users, get_inactive_users,
    update_last_active, get_leaderboard,
    bulk_update_credits, set_user_premium, remove_user_premium, is_user_premium,
    get_plan_price, update_plan_price,
    create_discount_code, redeem_discount_code,
    get_premium_users, get_users_with_min_credits
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable not set!")

# Load config (hardcoded values)
OWNER_ID = config.OWNER_ID
ADMIN_IDS = config.ADMIN_IDS
CHANNELS = config.CHANNELS
CHANNEL_LINKS = config.CHANNEL_LINKS
LOG_CHANNELS = config.LOG_CHANNELS
APIS = config.APIS
BACKUP_CHANNEL = config.BACKUP_CHANNEL
DEV_USERNAME = config.DEV_USERNAME
POWERED_BY = config.POWERED_BY

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)

# --- Flask Keep-Alive for Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- FSM States ---
class Form(StatesGroup):
    waiting_for_redeem = State()
    waiting_for_broadcast = State()
    waiting_for_dm_user = State()
    waiting_for_dm_content = State()
    waiting_for_custom_code = State()
    waiting_for_stats_range = State()
    waiting_for_code_deactivate = State()
    waiting_for_api_input = State()
    waiting_for_username = State()
    waiting_for_delete_user = State()
    waiting_for_reset_credits = State()
    waiting_for_bulk_gift = State()
    waiting_for_user_search = State()
    waiting_for_settings = State()
    waiting_for_offer_code = State()
    waiting_for_bulk_dm_users = State()
    waiting_for_bulk_dm_content = State()
    waiting_for_add_premium = State()
    waiting_for_remove_premium = State()
    waiting_for_plan_price = State()
    waiting_for_offer_details = State()
    waiting_for_bulk_file = State()
    waiting_for_code_stats = State()
    waiting_for_user_lookups = State()

# --- Helper Functions ---
def get_branding():
    """Return flattened branding (no meta wrapper)."""
    return {
        "developer": DEV_USERNAME,
        "powered_by": POWERED_BY,
        # timestamp optional – if you want to include, add here
        # "timestamp": datetime.now().isoformat()
    }

def clean_api_response(data, extra_blacklist=None):
    """Remove unwanted strings from API response based on per-API extra_blacklist"""
    if extra_blacklist is None:
        extra_blacklist = []
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            # Check key for unwanted strings
            if any(unwanted.lower() in key.lower() for unwanted in extra_blacklist):
                continue
            if isinstance(value, str):
                if any(unwanted.lower() in value.lower() for unwanted in extra_blacklist):
                    continue
                # Also remove general credit mentions if not ours
                if 'credit' in value.lower() and 'nullprotocol' not in value.lower():
                    continue
                cleaned[key] = value
            elif isinstance(value, dict):
                cleaned[key] = clean_api_response(value, extra_blacklist)
            elif isinstance(value, list):
                cleaned[key] = [clean_api_response(item, extra_blacklist) if isinstance(item, dict) else item for item in value]
            else:
                cleaned[key] = value
        return cleaned
    elif isinstance(data, list):
        return [clean_api_response(item, extra_blacklist) if isinstance(item, dict) else item for item in data]
    return data

def format_json_for_display(data, max_length=3500):
    formatted = json.dumps(data, indent=4, ensure_ascii=False)
    if len(formatted) > max_length:
        truncated = formatted[:max_length]
        truncated += f"\n\n... [Data truncated, {len(formatted) - max_length} characters more]"
        return truncated, True
    return formatted, False

def create_readable_txt_file(raw_data, api_type, input_data):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(f"🔍 {api_type.upper()} Lookup Results\n")
        f.write(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"🔎 Input: {input_data}\n")
        f.write("="*50 + "\n\n")
        def write_readable(obj, indent=0):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    f.write("  " * indent + f"• {key}: ")
                    if isinstance(value, (dict, list)):
                        f.write("\n")
                        write_readable(value, indent + 1)
                    else:
                        f.write(f"{value}\n")
            elif isinstance(obj, list):
                for i, item in enumerate(obj, 1):
                    f.write("  " * indent + f"{i}. ")
                    if isinstance(item, (dict, list)):
                        f.write("\n")
                        write_readable(item, indent + 1)
                    else:
                        f.write(f"{item}\n")
            else:
                f.write(f"{obj}\n")
        write_readable(raw_data)
        f.write("\n" + "="*50 + "\n")
        f.write(f"👨‍💻 Developer: {DEV_USERNAME}\n")
        f.write(f"⚡ Powered by: {POWERED_BY}\n")
        return f.name

async def is_user_owner(user_id):
    return user_id == OWNER_ID

async def is_user_admin(user_id):
    if user_id == OWNER_ID:
        return 'owner'
    if user_id in ADMIN_IDS:
        return 'admin'
    db_admin = await is_admin(user_id)
    return db_admin

async def is_user_banned(user_id):
    user = await get_user(user_id)
    return user[5] == 1 if user else False

async def check_membership(user_id):
    admin_level = await is_user_admin(user_id)
    if admin_level:
        return True
    if await is_user_premium(user_id):
        return True
    try:
        for channel_id in CHANNELS:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status in ['left', 'kicked', 'restricted']:
                return False
        return True
    except:
        return False

def get_join_keyboard():
    buttons = []
    for i, link in enumerate(CHANNEL_LINKS):
        buttons.append([InlineKeyboardButton(text=f"📢 Join Channel {i+1}", url=link)])
    buttons.append([InlineKeyboardButton(text="✅ Verify Join", callback_data="check_join")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_menu(user_id):
    keyboard = [
        [InlineKeyboardButton(text="📱 Number", callback_data="api_num"),
         InlineKeyboardButton(text="🏦 IFSC", callback_data="api_ifsc")],
        [InlineKeyboardButton(text="📧 Email", callback_data="api_email"),
         InlineKeyboardButton(text="📋 GST", callback_data="api_gst")],
        [InlineKeyboardButton(text="🚗 Vehicle", callback_data="api_vehicle"),
         InlineKeyboardButton(text="📮 Pincode", callback_data="api_pincode")],
        [InlineKeyboardButton(text="📷 Instagram", callback_data="api_instagram"),
         InlineKeyboardButton(text="🐱 GitHub", callback_data="api_github")],
        [InlineKeyboardButton(text="🇵🇰 Pakistan", callback_data="api_pakistan"),
         InlineKeyboardButton(text="🌐 IP Lookup", callback_data="api_ip")],
        [InlineKeyboardButton(text="🎁 Redeem", callback_data="redeem"),
         InlineKeyboardButton(text="🔗 Refer & earn", callback_data="refer_earn")],
        [InlineKeyboardButton(text="👤 Profile", callback_data="profile"),
         InlineKeyboardButton(text="💳 Buy Credits", url="https://t.me/Nullprotocol_X")],
        [InlineKeyboardButton(text="⭐ Premium Plans", callback_data="premium_plans")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def fetch_api_data(api_type, input_data):
    api_info = APIS.get(api_type)
    if not api_info or not api_info.get('url'):
        return {"error": "API not configured", **get_branding()}
    url_template = api_info['url']
    # Ensure URL has placeholder for input
    if '{}' in url_template:
        url = url_template.format(input_data)
    else:
        url = url_template + input_data
    try:
        async with httpx.AsyncClient() as client:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = await client.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                raise Exception(f"API Error {resp.status_code}")
            try:
                raw_data = resp.json()
            except:
                content_type = resp.headers.get('content-type', '').lower()
                if 'html' in content_type:
                    html_text = resp.text
                    json_patterns = [
                        r'var\s+data\s*=\s*({.*?});',
                        r'JSON\.parse\(\'({.*?})\'\)',
                        r'({.*?})'
                    ]
                    for pattern in json_patterns:
                        match = re.search(pattern, html_text, re.DOTALL)
                        if match:
                            try:
                                raw_data = json.loads(match.group(1))
                                break
                            except:
                                continue
                    else:
                        raw_data = {"html_response": "Data received but not in JSON format", "content": html_text[:500]}
                else:
                    raw_data = {"text_response": resp.text[:500]}
        # Clean using per-API extra_blacklist
        extra_blacklist = api_info.get('extra_blacklist', [])
        raw_data = clean_api_response(raw_data, extra_blacklist)
        # Add branding (flattened)
        if isinstance(raw_data, dict):
            raw_data.update(get_branding())
        elif isinstance(raw_data, list):
            raw_data = {"results": raw_data, **get_branding()}
        else:
            raw_data = {"data": str(raw_data), **get_branding()}
        return raw_data
    except Exception as e:
        logging.error(f"API fetch error {api_type}: {e}")
        return {"error": "Server Error", "details": str(e)[:200], **get_branding()}

async def process_api_call(message: types.Message, api_type: str, input_data: str):
    user_id = message.from_user.id
    if await is_user_banned(user_id):
        return
    user = await get_user(user_id)
    if not user:
        await message.reply("❌ <b>User not found!</b>", parse_mode="HTML")
        return
    admin_level = await is_user_admin(user_id)
    is_premium = await is_user_premium(user_id)

    if not admin_level and not is_premium:
        if user[2] < 1:
            await message.reply("❌ <b>Insufficient Credits!</b>", parse_mode="HTML")
            return
        else:
            await update_credits(user_id, -1)

    status_msg = await message.reply("🔄 <b>Fetching Data...</b>", parse_mode="HTML")
    raw_data = await fetch_api_data(api_type, input_data)
    await status_msg.delete()

    formatted_json, is_truncated = format_json_for_display(raw_data, 3500)
    formatted_json = formatted_json.replace('<', '&lt;').replace('>', '&gt;')
    json_size = len(json.dumps(raw_data, ensure_ascii=False))
    should_send_as_file = json_size > 3000 or (isinstance(raw_data, dict) and any(isinstance(v, list) and len(v) > 10 for v in raw_data.values()))

    temp_file = None
    txt_file = None

    if should_send_as_file:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(raw_data, f, indent=4, ensure_ascii=False)
            temp_file = f.name
        txt_file = create_readable_txt_file(raw_data, api_type, input_data)
        try:
            await message.reply_document(
                FSInputFile(temp_file, filename=f"{api_type}_{input_data}.json"),
                caption=(
                    f"🔍 <b>{api_type.upper()} Lookup Results</b>\n\n"
                    f"📊 <b>Input:</b> <code>{input_data}</code>\n"
                    f"📅 <b>Date:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
                    f"📄 <b>File Type:</b> JSON\n\n"
                    f"📝 <i>Data saved as file for better readability</i>\n\n"
                    f"👨‍💻 <b>Developer:</b> {DEV_USERNAME}\n"
                    f"⚡ <b>Powered by:</b> {POWERED_BY}"
                ),
                parse_mode="HTML"
            )
            await message.reply_document(
                FSInputFile(txt_file, filename=f"{api_type}_{input_data}_readable.txt"),
                caption="📄 <b>Readable Text Format</b>\n\n<i>Alternative format for easy reading on mobile</i>",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"File send error: {e}")
            short_msg = (
                f"🔍 <b>{api_type.upper()} Lookup Results</b>\n\n"
                f"📊 <b>Input:</b> <code>{input_data}</code>\n"
                f"📅 <b>Date:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
                f"⚠️ <b>Data too large for message</b>\n"
                f"📄 <i>Attempted to send as file but failed</i>\n\n"
                f"👨‍💻 <b>Developer:</b> {DEV_USERNAME}\n"
                f"⚡ <b>Powered by:</b> {POWERED_BY}"
            )
            await message.reply(short_msg, parse_mode="HTML")
        finally:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
            if txt_file and os.path.exists(txt_file):
                os.unlink(txt_file)
    else:
        colored = (
            f"🔍 <b>{api_type.upper()} Lookup Results</b>\n\n"
            f"📊 <b>Input:</b> <code>{input_data}</code>\n"
            f"📅 <b>Date:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
        )
        if is_truncated:
            colored += "⚠️ <i>Response truncated for display</i>\n\n"
        colored += f"<pre><code class=\"language-json\">{formatted_json}</code></pre>\n\n"
        colored += (
            f"📝 <b>Note:</b> Data is for informational purposes only\n"
            f"👨‍💻 <b>Developer:</b> {DEV_USERNAME}\n"
            f"⚡ <b>Powered by:</b> {POWERED_BY}"
        )
        await message.reply(colored, parse_mode="HTML")

    log_data = raw_data.copy()
    if isinstance(log_data, dict) and json_size > 10000:
        for key in log_data:
            if isinstance(log_data[key], list) and len(log_data[key]) > 5:
                log_data[key] = log_data[key][:5] + [f"... truncated, {len(raw_data[key])-5} more"]
            elif isinstance(log_data[key], str) and len(log_data[key]) > 500:
                log_data[key] = log_data[key][:500] + "... [truncated]"
    await log_lookup(user_id, api_type, input_data, json.dumps(log_data, indent=2))
    await update_last_active(user_id)

    log_channel = LOG_CHANNELS.get(api_type)
    if log_channel and log_channel != "-1000000000000":
        try:
            username = message.from_user.username or 'N/A'
            user_info = f"👤 User: {user_id} (@{username})"
            if should_send_as_file and temp_file and os.path.exists(temp_file):
                await bot.send_document(
                    chat_id=int(log_channel),
                    document=FSInputFile(temp_file, filename=f"{api_type}_{input_data}.json"),
                    caption=(
                        f"📊 <b>Lookup Log - {api_type.upper()}</b>\n\n"
                        f"{user_info}\n"
                        f"🔎 Type: {api_type}\n"
                        f"⌨️ Input: <code>{input_data}</code>\n"
                        f"📅 Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
                        f"📊 Size: {json_size} characters\n"
                        f"📄 Format: JSON File"
                    ),
                    parse_mode="HTML"
                )
                if txt_file and os.path.exists(txt_file):
                    await bot.send_document(
                        chat_id=int(log_channel),
                        document=FSInputFile(txt_file, filename=f"{api_type}_{input_data}_readable.txt"),
                        caption="📄 Readable Text Format"
                    )
            else:
                log_message = (
                    f"📊 <b>Lookup Log - {api_type.upper()}</b>\n\n"
                    f"{user_info}\n"
                    f"🔎 Type: {api_type}\n"
                    f"⌨️ Input: <code>{input_data}</code>\n"
                    f"📅 Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
                    f"📊 Size: {json_size} characters\n\n"
                    f"📄 Result:\n<pre>{formatted_json[:1500]}</pre>"
                )
                if len(formatted_json) > 1500:
                    log_message += "\n... [⚡ Powered by: NULL PROTOCOL]"
                await bot.send_message(int(log_channel), log_message, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Log channel error: {e}")
            try:
                await bot.send_message(
                    int(log_channel),
                    f"📊 <b>Lookup Failed to Log</b>\n\n"
                    f"👤 User: {user_id}\n"
                    f"🔎 Type: {api_type}\n"
                    f"⌨️ Input: {input_data}\n"
                    f"📅 Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
                    f"❌ Error: {str(e)[:200]}",
                    parse_mode="HTML"
                )
            except:
                pass

# --- Start & Join ---
@dp.message(CommandStart())
async def start_command(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    if await is_user_banned(user_id):
        await message.answer("🚫 <b>You are BANNED from using this bot.</b>", parse_mode="HTML")
        return
    existing = await get_user(user_id)
    if not existing:
        referrer = None
        args = command.args
        if args and args.startswith("ref_"):
            try:
                referrer = int(args.split("_")[1])
                if referrer == user_id:
                    referrer = None
            except:
                pass
        await add_user(user_id, message.from_user.username, referrer)
        if referrer:
            await update_credits(referrer, 3)
            try:
                await bot.send_message(referrer, "🎉 <b>Referral +3 Credits!</b>", parse_mode="HTML")
            except:
                pass
    if not await check_membership(user_id):
        await message.answer(
            "👋 <b>Welcome to OSINT FATHER</b>\n\n"
            "⚠️ <b>Bot use karne ke liye channels join karein:</b>",
            reply_markup=get_join_keyboard(),
            parse_mode="HTML"
        )
        return
    welcome_msg = f"""
🔓 <b>Access Granted!</b>

Welcome <b>{message.from_user.first_name}</b>,

<b>OSINT FATHER</b> - Premium Lookup Services
Select a service from menu below:
"""
    await message.answer(welcome_msg, reply_markup=get_main_menu(user_id), parse_mode="HTML")
    await update_last_active(user_id)

@dp.callback_query(F.data == "check_join")
async def verify_join(callback: types.CallbackQuery):
    if await check_membership(callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer("✅ <b>Verified!</b>", reply_markup=get_main_menu(callback.from_user.id), parse_mode="HTML")
    else:
        await callback.answer("❌ Abhi bhi kuch channels join nahi kiye!", show_alert=True)

# --- Profile ---
@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    user_data = await get_user(callback.from_user.id)
    if not user_data:
        return
    admin_level = await is_user_admin(callback.from_user.id)
    is_premium = await is_user_premium(callback.from_user.id)
    credits = "♾️ Unlimited" if (admin_level or is_premium) else user_data[2]
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_data[0]}"
    stats = await get_user_stats(callback.from_user.id)
    referrals = stats[0] if stats else 0
    codes_claimed = stats[1] if stats else 0
    total_from_codes = stats[2] if stats else 0
    msg = (f"👤 <b>User Profile</b>\n\n"
           f"🆔 <b>ID:</b> <code>{user_data[0]}</code>\n"
           f"👤 <b>Username:</b> @{user_data[1] or 'N/A'}\n"
           f"💰 <b>Credits:</b> {credits}\n"
           f"📊 <b>Total Earned:</b> {user_data[6]}\n"
           f"👥 <b>Referrals:</b> {referrals}\n"
           f"🎫 <b>Codes Claimed:</b> {codes_claimed}\n"
           f"📅 <b>Joined:</b> {datetime.fromtimestamp(float(user_data[3])).strftime('%d-%m-%Y')}\n"
           f"🔗 <b>Referral Link:</b>\n<code>{link}</code>")
    await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=get_main_menu(callback.from_user.id))

# --- Refer & Earn ---
@dp.callback_query(F.data == "refer_earn")
async def refer_earn_handler(callback: types.CallbackQuery):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    msg = (
        "🔗 <b>Refer & Earn Program</b>\n\n"
        "Apne dosto ko invite karein aur free credits paayein!\n"
        "Per Referral: <b>+3 Credits</b>\n\n"
        "👇 <b>Your Link:</b>\n"
        f"<code>{link}</code>\n\n"
        "📊 <b>How it works:</b>\n"
        "1. Apna link share karein\n"
        "2. Jo bhi is link se join karega\n"
        "3. Aapko milenge <b>3 credits</b>"
    )
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]])
    await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=back_kb)

@dp.callback_query(F.data == "back_home")
async def go_home(callback: types.CallbackQuery):
    await callback.message.edit_text("🔓 <b>Main Menu</b>", reply_markup=get_main_menu(callback.from_user.id), parse_mode="HTML")

# --- Redeem Code ---
@dp.callback_query(F.data == "redeem")
async def redeem_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🎁 <b>Redeem Code</b>\n\n"
        "Enter your redeem code below:\n\n"
        "📌 <i>Note: Each code can be used only once per user</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_redeem")]]),
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_for_redeem)
    await callback.answer()

@dp.callback_query(F.data == "cancel_redeem")
async def cancel_redeem(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Operation Cancelled.", reply_markup=get_main_menu(callback.from_user.id))

@dp.message(Form.waiting_for_redeem)
async def process_redeem(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    result = await redeem_code_db(message.from_user.id, code)
    user_data = await get_user(message.from_user.id)
    if isinstance(result, int):
        new_balance = user_data[2] + result if user_data else result
        await message.answer(
            f"✅ <b>Code Redeemed Successfully!</b>\n"
            f"➕ <b>{result} Credits</b> added to your account.\n\n"
            f"💰 <b>New Balance:</b> {new_balance}",
            parse_mode="HTML",
            reply_markup=get_main_menu(message.from_user.id)
        )
    elif result == "already_claimed":
        await message.answer(
            "❌ <b>You have already claimed this code!</b>\n"
            "Each user can claim a code only once.",
            parse_mode="HTML",
            reply_markup=get_main_menu(message.from_user.id)
        )
    elif result == "invalid":
        await message.answer(
            "❌ <b>Invalid Code!</b>\n"
            "Please check the code and try again.",
            parse_mode="HTML",
            reply_markup=get_main_menu(message.from_user.id)
        )
    elif result == "inactive":
        await message.answer(
            "❌ <b>Code is Inactive!</b>\n"
            "This code has been deactivated by admin.",
            parse_mode="HTML",
            reply_markup=get_main_menu(message.from_user.id)
        )
    elif result == "limit_reached":
        await message.answer(
            "❌ <b>Code Limit Reached!</b>\n"
            "This code has been used by maximum users.",
            parse_mode="HTML",
            reply_markup=get_main_menu(message.from_user.id)
        )
    elif result == "expired":
        await message.answer(
            "❌ <b>Code Expired!</b>\n"
            "This code is no longer valid.",
            parse_mode="HTML",
            reply_markup=get_main_menu(message.from_user.id)
        )
    else:
        await message.answer(
            "❌ <b>Error processing code!</b>\n"
            "Please try again later.",
            parse_mode="HTML",
            reply_markup=get_main_menu(message.from_user.id)
        )
    await state.clear()

# --- API Input ---
@dp.callback_query(F.data.startswith("api_"))
async def ask_api_input(callback: types.CallbackQuery, state: FSMContext):
    if await is_user_banned(callback.from_user.id):
        return
    if not await check_membership(callback.from_user.id):
        await callback.answer("❌ Join channels first!", show_alert=True)
        return
    api_type = callback.data.split('_')[1]
    if api_type not in APIS or not APIS[api_type].get('url'):
        await callback.answer("❌ This service is temporarily unavailable", show_alert=True)
        return
    await state.set_state(Form.waiting_for_api_input)
    await state.update_data(api_type=api_type)
    prompts = {
        'num': "📱 Enter Mobile Number (10 digits)",
        'ifsc': "🏦 Enter IFSC Code (11 characters)",
        'email': "📧 Enter Email Address",
        'gst': "📋 Enter GST Number (15 characters)",
        'vehicle': "🚗 Enter Vehicle RC Number",
        'pincode': "📮 Enter Pincode (6 digits)",
        'instagram': "📷 Enter Instagram Username (without @)",
        'github': "🐱 Enter GitHub Username",
        'pakistan': "🇵🇰 Enter Pakistan Mobile Number (with country code)",
        'ip': "🌐 Enter IP Address",
    }
    instructions = prompts.get(api_type, "Enter input")
    await callback.message.answer(
        f"<b>{instructions}</b>\n\n"
        f"<i>Type /cancel to cancel</i>\n\n"
        f"📄 <i>Note: Large responses will be sent as files</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_api")]])
    )

@dp.callback_query(F.data == "cancel_api")
async def cancel_api(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Operation Cancelled.", reply_markup=get_main_menu(callback.from_user.id))

@dp.message(Form.waiting_for_api_input)
async def handle_api_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    api_type = data.get('api_type')
    if api_type:
        await process_api_call(message, api_type, message.text.strip())
    await state.clear()

# --- Premium Plans ---
@dp.callback_query(F.data == "premium_plans")
async def show_premium_plans(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await is_user_premium(user_id):
        await callback.message.edit_text(
            "⭐ <b>You are already a Premium User!</b>\n\n✅ Unlimited searches\n✅ No channel join",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]])
        )
        return
    weekly_price = await get_plan_price('weekly') or 69
    monthly_price = await get_plan_price('monthly') or 199
    text = (
        f"⭐ <b>Premium Plans</b>\n\n"
        f"📅 Weekly Plan – ₹{weekly_price}\n"
        f"• 7 days unlimited access\n"
        f"• No channel join required\n"
        f"📆 Monthly Plan – ₹{monthly_price}\n"
        f"• 30 days unlimited access\n\n"
        f"💳 <b>How to Buy:</b>\n"
        f"Contact @Nullprotocol_X to purchase.\n"
        f"After payment, admin will activate your premium."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📅 Buy Weekly (₹{weekly_price})", callback_data="buy_weekly")],
        [InlineKeyboardButton(text=f"📆 Buy Monthly (₹{monthly_price})", callback_data="buy_monthly")],
        [InlineKeyboardButton(text="🎟️ Redeem Offer Code", callback_data="redeem_offer")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("buy_"))
async def buy_plan_handler(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1]
    price = await get_plan_price(plan) or (69 if plan == "weekly" else 199)
    text = (
        f"🛒 <b>Purchase {plan.capitalize()} Plan</b>\n\n"
        f"Amount: ₹{price}\n\n"
        "📲 <b>Payment Instructions:</b>\n"
        "1. Send payment to [UPI ID / QR code]\n"
        "2. Take a screenshot\n"
        "3. Forward screenshot to @Nullprotocol_X\n"
        "4. Your premium will be activated within 24 hours\n\n"
        "Or click below to contact admin directly:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Contact Admin", url="https://t.me/Nullprotocol_X")],
        [InlineKeyboardButton(text="🔙 Back to Plans", callback_data="premium_plans")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "redeem_offer")
async def redeem_offer_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🎟️ <b>Redeem Offer Code</b>\n\n"
        "Enter your discount code:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_redeem_offer")]]),
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_for_offer_code)
    await callback.answer()

@dp.callback_query(F.data == "cancel_redeem_offer")
async def cancel_offer_redeem(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Offer redemption cancelled.", reply_markup=get_main_menu(callback.from_user.id))

@dp.message(Form.waiting_for_offer_code)
async def process_offer_code(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    await message.answer(
        "✅ Offer code accepted! Now select a plan to apply discount.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Weekly", callback_data="buy_weekly_offer")],
            [InlineKeyboardButton(text="📆 Monthly", callback_data="buy_monthly_offer")]
        ])
    )
    await state.update_data(offer_code=code)
    await state.clear()

# --- Admin Panel (Command) ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    admin_level = await is_user_admin(message.from_user.id)
    if not admin_level:
        return
    panel_text = """🛠 <b>ADMIN CONTROL PANEL</b>

<b>📊 User Management:</b>
📢 <code>/broadcast</code> - Send to all users
📨 <code>/dm</code> - Direct message to user
🎁 <code>/gift ID AMOUNT</code> - Add credits
🎁 <code>/bulkgift AMOUNT ID1 ID2...</code> - Bulk gift
📉 <code>/removecredits ID AMOUNT</code> - Remove credits
🔄 <code>/resetcredits ID</code> - Reset user credits to 0
🚫 <code>/ban ID</code> - Ban user
🟢 <code>/unban ID</code> - Unban user
🗑 <code>/deleteuser ID</code> - Delete user
🔍 <code>/searchuser QUERY</code> - Search users
👥 <code>/users [PAGE]</code> - List users (10 per page)
📈 <code>/recentusers DAYS</code> - Recent users
📊 <code>/userlookups ID</code> - User lookup history
🏆 <code>/leaderboard</code> - Credits leaderboard
💰 <code>/premiumusers</code> - Premium users (100+ credits)
📉 <code>/lowcreditusers</code> - Users with low credits
⏰ <code>/inactiveusers DAYS</code> - Inactive users

<b>🎫 Code Management:</b>
🎲 <code>/gencode AMOUNT USES [TIME]</code> - Random code
🎫 <code>/customcode CODE AMOUNT USES [TIME]</code> - Custom code
📋 <code>/listcodes</code> - List all codes
✅ <code>/activecodes</code> - List active codes
❌ <code>/inactivecodes</code> - List inactive codes
🚫 <code>/deactivatecode CODE</code> - Deactivate code
📊 <code>/codestats CODE</code> - Code usage statistics
⌛️ <code>/checkexpired</code> - Check expired codes
🧹 <code>/cleanexpired</code> - Remove expired codes

<b>📈 Statistics:</b>
📊 <code>/stats</code> - Bot statistics
📅 <code>/dailystats DAYS</code> - Daily statistics
🔍 <code>/lookupstats</code> - Lookup statistics
💾 <code>/backup DAYS</code> - Download user data
🏆 <code>/topref [LIMIT]</code> - Top referrers
"""
    if admin_level == 'owner':
        panel_text += """
<b>👑 Owner Commands:</b>
➕ <code>/addadmin ID</code> - Add admin
➖ <code>/removeadmin ID</code> - Remove admin
👥 <code>/listadmins</code> - List all admins
⚙️ <code>/settings</code> - Bot settings
💾 <code>/fulldbbackup</code> - Full database backup
"""
    panel_text += """
<b>⏰ Time Formats:</b>
• <code>30m</code> = 30 minutes
• <code>2h</code> = 2 hours
• <code>1h30m</code> = 1.5 hours
• <code>1d</code> = 24 hours
"""
    buttons = [
        [InlineKeyboardButton(text="📊 Quick Stats", callback_data="quick_stats"),
         InlineKeyboardButton(text="👥 Recent Users", callback_data="recent_users")],
        [InlineKeyboardButton(text="🎫 Active Codes", callback_data="active_codes"),
         InlineKeyboardButton(text="🏆 Top Referrers", callback_data="top_ref")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="broadcast_now"),
         InlineKeyboardButton(text="📨 Direct Message", callback_data="dm_now")],
        [InlineKeyboardButton(text="👥 Bulk DM", callback_data="bulk_dm_start")],
        [InlineKeyboardButton(text="⭐ Premium Users", callback_data="list_premium"),
         InlineKeyboardButton(text="➕ Add Premium", callback_data="add_premium"),
         InlineKeyboardButton(text="➖ Remove Premium", callback_data="remove_premium")],
        [InlineKeyboardButton(text="💰 Set Plan Price", callback_data="set_plan_price"),
         InlineKeyboardButton(text="🎟️ Create Offer", callback_data="create_offer")],
        [InlineKeyboardButton(text="💾 Manual Backup", callback_data="manual_backup")],
        [InlineKeyboardButton(text="📁 Bulk Lookup", callback_data="bulk_lookup_admin")],
        [InlineKeyboardButton(text="❌ Close", callback_data="close_panel")]
    ]
    await message.answer(panel_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# --- Broadcast ---
@dp.callback_query(F.data == "broadcast_now")
async def broadcast_now(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📢 <b>Send message to broadcast</b> (text, photo, video, etc.):", parse_mode="HTML")
    await state.set_state(Form.waiting_for_broadcast)
    await callback.answer()

@dp.message(Form.waiting_for_broadcast)
async def broadcast_handler(message: types.Message, state: FSMContext):
    users = await get_all_users()
    sent = 0
    failed = 0
    total = len(users)
    status = await message.answer(f"🚀 Broadcasting to {total} users...\n\nSent: 0\nFailed: 0")
    for uid in users:
        try:
            await message.copy_to(uid)
            sent += 1
            if sent % 20 == 0:
                await status.edit_text(f"🚀 Broadcasting...\n✅ Sent: {sent}\n❌ Failed: {failed}\n📊 Progress: {((sent+failed)/total*100):.1f}%")
            await asyncio.sleep(0.05)
        except:
            failed += 1
    await status.edit_text(f"✅ <b>Broadcast Complete!</b>\n\n✅ Sent: {sent}\n❌ Failed: {failed}\n👥 Total: {total}", parse_mode="HTML")
    await state.clear()

# --- Direct Message ---
@dp.callback_query(F.data == "dm_now")
async def dm_now(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("👤 <b>Enter user ID to send message:</b>", parse_mode="HTML")
    await state.set_state(Form.waiting_for_dm_user)
    await callback.answer()

@dp.message(Form.waiting_for_dm_user)
async def dm_user_handler(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text)
        await state.update_data(dm_user_id=uid)
        await message.answer("📨 Now send the message:")
        await state.set_state(Form.waiting_for_dm_content)
    except:
        await message.answer("❌ Invalid user ID. Please enter a numeric ID.")

@dp.message(Form.waiting_for_dm_content)
async def dm_content_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = data.get('dm_user_id')
    try:
        await message.copy_to(uid)
        await message.answer(f"✅ Message sent to user {uid}")
    except Exception as e:
        await message.answer(f"❌ Failed: {str(e)}")
    await state.clear()

# --- Bulk DM ---
@dp.callback_query(F.data == "bulk_dm_start")
async def bulk_dm_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("👥 <b>Enter user IDs separated by spaces:</b>", parse_mode="HTML")
    await state.set_state(Form.waiting_for_bulk_dm_users)
    await callback.answer()

@dp.message(Form.waiting_for_bulk_dm_users)
async def bulk_dm_users_handler(message: types.Message, state: FSMContext):
    ids = []
    for part in message.text.split():
        try:
            ids.append(int(part))
        except:
            await message.reply(f"❌ Invalid ID: {part}")
            return
    if not ids:
        await message.reply("❌ No valid IDs.")
        await state.clear()
        return
    await state.update_data(bulk_dm_users=ids)
    await message.answer("📨 Now send the message to broadcast to these users:")
    await state.set_state(Form.waiting_for_bulk_dm_content)

@dp.message(Form.waiting_for_bulk_dm_content)
async def bulk_dm_send_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ids = data.get('bulk_dm_users', [])
    status = await message.answer(f"📨 Sending to {len(ids)} users...")
    sent = 0
    failed = 0
    for uid in ids:
        try:
            await message.copy_to(uid)
            sent += 1
        except:
            failed += 1
        if (sent+failed) % 10 == 0:
            await status.edit_text(f"📨 Sent {sent}, Failed {failed} of {len(ids)}")
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ <b>Bulk DM done.</b>\n\n✅ Sent: {sent}\n❌ Failed: {failed}", parse_mode="HTML")
    await state.clear()

# --- Premium Users List (via button) ---
@dp.callback_query(F.data == "list_premium")
async def list_premium_callback(callback: types.CallbackQuery):
    admin_level = await is_user_admin(callback.from_user.id)
    if not admin_level:
        await callback.answer("Unauthorized", show_alert=True)
        return
    users = await get_premium_users()
    if not users:
        await callback.message.edit_text("No premium users.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]]))
        return
    text = "⭐ <b>Premium Users</b>\n\n"
    for uid, uname, exp in users:
        exp_str = "Permanent" if exp is None else datetime.fromisoformat(exp).strftime('%d/%m/%Y')
        text += f"• <code>{uid}</code> - @{uname or 'N/A'} - {exp_str}\n"
    if len(users) > 10:
        text += f"\n... and {len(users)-10} more"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]]))

# --- Add Premium (via button) ---
@dp.callback_query(F.data == "add_premium")
async def add_premium_callback(callback: types.CallbackQuery, state: FSMContext):
    if not await is_user_owner(callback.from_user.id):
        await callback.answer("Owner only!", show_alert=True)
        return
    await callback.message.answer("➕ Enter user ID and optional days (e.g., 123456 30):")
    await state.set_state(Form.waiting_for_add_premium)
    await callback.answer()

@dp.message(Form.waiting_for_add_premium)
async def add_premium_handler(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split()
        uid = int(parts[0])
        days = int(parts[1]) if len(parts) > 1 else None
        await set_user_premium(uid, days)
        await message.reply(f"✅ Premium added for {uid}" + (f" for {days} days." if days else " permanently."))
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    await state.clear()

# --- Remove Premium (via button) ---
@dp.callback_query(F.data == "remove_premium")
async def remove_premium_callback(callback: types.CallbackQuery, state: FSMContext):
    if not await is_user_owner(callback.from_user.id):
        await callback.answer("Owner only!", show_alert=True)
        return
    await callback.message.answer("➖ Enter user ID:")
    await state.set_state(Form.waiting_for_remove_premium)
    await callback.answer()

@dp.message(Form.waiting_for_remove_premium)
async def remove_premium_handler(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text)
        await remove_user_premium(uid)
        await message.reply(f"✅ Premium removed from {uid}.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    await state.clear()

# --- Set Plan Price (via button) ---
@dp.callback_query(F.data == "set_plan_price")
async def set_plan_price_callback(callback: types.CallbackQuery):
    if not await is_user_owner(callback.from_user.id):
        await callback.answer("Owner only!", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Weekly", callback_data="set_price_weekly")],
        [InlineKeyboardButton(text="📆 Monthly", callback_data="set_price_monthly")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
    ])
    await callback.message.edit_text("💰 Select plan to modify:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("set_price_"))
async def set_price_input(callback: types.CallbackQuery, state: FSMContext):
    plan = callback.data.split("_")[2]
    await state.update_data(plan_type=plan)
    await callback.message.answer(f"Enter new price for {plan.capitalize()} plan (₹):")
    await state.set_state(Form.waiting_for_plan_price)
    await callback.answer()

@dp.message(Form.waiting_for_plan_price)
async def set_price_handler(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
        data = await state.get_data()
        plan = data.get('plan_type')
        await update_plan_price(plan, price)
        await message.reply(f"✅ {plan.capitalize()} plan price set to ₹{price}.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    await state.clear()

# --- Create Offer (via button) ---
@dp.callback_query(F.data == "create_offer")
async def create_offer_callback(callback: types.CallbackQuery, state: FSMContext):
    if not await is_user_owner(callback.from_user.id):
        await callback.answer("Owner only!", show_alert=True)
        return
    await callback.message.answer("🎟️ Enter offer details in format: CODE PLAN DISCOUNT% MAX_USES [EXPIRY]\nExample: OFFER10 weekly 10 5 7d")
    await state.set_state(Form.waiting_for_offer_details)
    await callback.answer()

@dp.message(Form.waiting_for_offer_details)
async def create_offer_handler(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split()
        code = parts[0].upper()
        plan = parts[1].lower()
        discount = int(parts[2])
        if discount < 0 or discount > 100:
            await message.reply("❌ Discount must be between 0 and 100.")
            return
        max_uses = int(parts[3])
        expiry = parse_time_string(parts[4]) if len(parts) > 4 else None
        await create_discount_code(code, plan, discount, max_uses, expiry)
        await message.reply(f"✅ Offer code {code} created for {plan} plan with {discount}% off.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    await state.clear()

# --- Bulk Lookup (Admin/Premium) ---
@dp.callback_query(F.data == "bulk_lookup_admin")
async def bulk_lookup_admin_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    admin = await is_user_admin(user_id)
    premium = await is_user_premium(user_id)
    if not (admin or premium):
        await callback.answer("❌ Admin/Premium only!", show_alert=True)
        return
    # Show API selection
    keyboard = []
    row = []
    for i, api_name in enumerate(APIS.keys(), 1):
        row.append(InlineKeyboardButton(text=api_name.upper(), callback_data=f"bulk_api_{api_name}"))
        if i % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="❌ Cancel", callback_data="admin_back")])
    await callback.message.edit_text("📁 Select API for bulk lookup:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(F.data.startswith("bulk_api_"))
async def bulk_api_selected(callback: types.CallbackQuery, state: FSMContext):
    api_type = callback.data.split("_")[2]
    await state.update_data(bulk_api_type=api_type)
    await callback.message.answer(f"📁 Send a text file with one {api_type.upper()} input per line:")
    await state.set_state(Form.waiting_for_bulk_file)
    await callback.answer()

@dp.message(Form.waiting_for_bulk_file, F.document)
async def bulk_file_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    api_type = data.get('bulk_api_type')
    if not api_type:
        await message.answer("Session expired.")
        await state.clear()
        return
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    await bot.download_file(file_path, "temp_bulk.txt")
    with open("temp_bulk.txt", 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    os.remove("temp_bulk.txt")
    if not lines:
        await message.answer("File is empty.")
        await state.clear()
        return
    status = await message.answer(f"🔄 Processing {len(lines)} lookups...")
    results = []
    for i, inp in enumerate(lines):
        raw = await fetch_api_data(api_type, inp)
        results.append({'input': inp, 'data': raw})
        if (i+1) % 10 == 0:
            await status.edit_text(f"Processed {i+1}/{len(lines)}...")
    out_file = f"bulk_{api_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Input', 'Result (JSON)'])
        for r in results:
            writer.writerow([r['input'], json.dumps(r['data'], ensure_ascii=False)])
    await message.reply_document(FSInputFile(out_file), caption=f"Bulk lookup results for {api_type}")
    os.remove(out_file)
    await status.delete()
    await state.clear()

# --- Manual Backup ---
@dp.callback_query(F.data == "manual_backup")
async def manual_backup_callback(callback: types.CallbackQuery):
    admin_level = await is_user_admin(callback.from_user.id)
    if not admin_level:
        await callback.answer("Unauthorized", show_alert=True)
        return
    await callback.message.edit_text("🔄 Taking backup...")
    await daily_backup()
    await callback.message.edit_text("✅ Backup completed and sent to backup channel.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]]))

# --- Quick Stats Callback ---
@dp.callback_query(F.data == "quick_stats")
async def quick_stats_callback(callback: types.CallbackQuery):
    admin_level = await is_user_admin(callback.from_user.id)
    if not admin_level:
        return
    stats = await get_bot_stats()
    top_ref = await get_top_referrers(3)
    total_lookups = await get_total_lookups()
    stats_text = f"📊 <b>Quick Stats</b>\n\n"
    stats_text += f"👥 <b>Total Users:</b> {stats['total_users']}\n"
    stats_text += f"📈 <b>Active Users:</b> {stats['active_users']}\n"
    stats_text += f"💰 <b>Total Credits:</b> {stats['total_credits']}\n"
    stats_text += f"🔍 <b>Total Lookups:</b> {total_lookups}\n\n"
    if top_ref:
        stats_text += "🏆 <b>Top 3 Referrers:</b>\n"
        for i, (ref_id, cnt) in enumerate(top_ref, 1):
            stats_text += f"{i}. User <code>{ref_id}</code>: {cnt} referrals\n"
    await callback.message.edit_text(stats_text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "recent_users")
async def recent_users_callback(callback: types.CallbackQuery):
    admin_level = await is_user_admin(callback.from_user.id)
    if not admin_level:
        return
    users = await get_recent_users(10)
    text = "📅 <b>Recent Users (Last 10)</b>\n\n"
    if not users:
        text += "No recent users."
    else:
        for user_id, username, joined_date in users:
            join_dt = datetime.fromtimestamp(float(joined_date))
            text += f"• <code>{user_id}</code> - @{username or 'N/A'} - {join_dt.strftime('%d/%m %H:%M')}\n"
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "active_codes")
async def active_codes_callback(callback: types.CallbackQuery):
    admin_level = await is_user_admin(callback.from_user.id)
    if not admin_level:
        return
    codes = await get_active_codes()
    if not codes:
        await callback.answer("✅ No active codes found.", show_alert=True)
        return
    text = "✅ <b>Active Codes</b>\n\n"
    for code, amount, max_uses, current_uses in codes[:5]:
        text += f"🎟 <code>{code}</code> - {amount} credits ({current_uses}/{max_uses})\n"
    if len(codes) > 5:
        text += f"\n... and {len(codes) - 5} more"
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "top_ref")
async def top_ref_callback(callback: types.CallbackQuery):
    admin_level = await is_user_admin(callback.from_user.id)
    if not admin_level:
        return
    top_ref = await get_top_referrers(5)
    if not top_ref:
        await callback.answer("❌ No referrals yet.", show_alert=True)
        return
    text = "🏆 <b>Top 5 Referrers</b>\n\n"
    for i, (ref_id, cnt) in enumerate(top_ref, 1):
        text += f"{i}. User <code>{ref_id}</code>: {cnt} referrals\n"
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "close_panel")
async def close_panel(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# --- Admin Back Button (return to admin panel) ---
@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    await admin_panel(callback.message)

# --- Daily Backup Function (for scheduler) ---
async def daily_backup():
    try:
        db_backup = f"backup_db_{datetime.now().strftime('%Y%m%d')}.db"
        shutil.copy2("nullprotocol.db", db_backup)
        csv_backup = f"backup_users_{datetime.now().strftime('%Y%m%d')}.csv"
        async with aiosqlite.connect("nullprotocol.db") as db:
            async with db.execute("SELECT * FROM users") as cursor:
                rows = await cursor.fetchall()
                col_names = [description[0] for description in cursor.description]
        with open(csv_backup, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(col_names)
            writer.writerows(rows)
        txt_backup = f"backup_stats_{datetime.now().strftime('%Y%m%d')}.txt"
        stats = await get_bot_stats()
        total_lookups = await get_total_lookups()
        with open(txt_backup, 'w', encoding='utf-8') as f:
            f.write(f"Backup Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Users: {stats['total_users']}\n")
            f.write(f"Active Users: {stats['active_users']}\n")
            f.write(f"Total Credits: {stats['total_credits']}\n")
            f.write(f"Credits Distributed: {stats['credits_distributed']}\n")
            f.write(f"Total Lookups: {total_lookups}\n")
        await bot.send_document(BACKUP_CHANNEL, FSInputFile(db_backup))
        await bot.send_document(BACKUP_CHANNEL, FSInputFile(csv_backup))
        await bot.send_document(BACKUP_CHANNEL, FSInputFile(txt_backup))
        os.remove(db_backup)
        os.remove(csv_backup)
        os.remove(txt_backup)
        logging.info("Daily backup successful.")
    except Exception as e:
        logging.error(f"Backup failed: {e}")

# --- Cancel command ---
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ No active operation to cancel.")
        return
    await state.clear()
    await message.answer("✅ Operation cancelled.", reply_markup=get_main_menu(message.from_user.id))

# --- Main function with scheduler ---
async def main():
    keep_alive()
    await init_db()
    for aid in ADMIN_IDS:
        if aid != OWNER_ID:
            await add_admin(aid)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_backup, CronTrigger(hour=0, minute=0))
    scheduler.start()
    print("🚀 OSINT FATHER Pro Bot Started...")
    print(f"👑 Owner ID: {OWNER_ID}")
    print(f"👥 Static Admins: {ADMIN_IDS}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
