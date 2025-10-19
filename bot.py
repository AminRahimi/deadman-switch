# bot.py
# اجراها:
#   - حالت check فقط:   python bot.py --check
#   - حالت سرور/polling: python bot.py --serve
#
import os
import json
import argparse
import datetime
import asyncio
import sys
import logging

from telegram import __version__ as TG_VER
try:
    from telegram import Bot
    from telegram.ext import ApplicationBuilder, CommandHandler
except Exception:
    print("Please install python-telegram-bot (pip install python-telegram-bot)")
    raise

# تنظیمات از محیط یا مقدار پیش‌فرض
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
YOUR_USER_ID = int(os.getenv("YOUR_USER_ID", "0"))       # آیدی عددی تو
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))     # آیدی گروه (منفی)
DAYS_LIMIT = int(os.getenv("DAYS_LIMIT", "3"))
DATA_FILE = "last_checkin.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_checkin_time():
    now = datetime.datetime.utcnow().isoformat()
    with open(DATA_FILE, "w") as f:
        json.dump({"last_checkin": now}, f)
    logger.info("Saved last_checkin = %s", now)

def load_checkin_time():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE, "r") as f:
        try:
            d = json.load(f)
            return datetime.datetime.fromisoformat(d["last_checkin"])
        except Exception:
            return None

async def cmd_checkin(update, context):
    """Handler for /checkin (private only)"""
    user = update.effective_user
    if user.id != YOUR_USER_ID:
        await update.message.reply_text("⛔ شما مجاز نیستید.")
        return
    save_checkin_time()
    await update.message.reply_text("✅ وضعیتت ثبت شد. تایمر ریست شد.")

async def notify_if_needed():
    """Check last_checkin and send message to group if needed."""
    bot = Bot(BOT_TOKEN)
    last = load_checkin_time()
    if not last:
        logger.warning("No initial checkin found.")
        return {"alert_sent": False, "msg": "no_initial_checkin"}

    now = datetime.datetime.utcnow()
    diff = (now - last).days
    logger.info("Last checkin was %d days ago.", diff)
    if diff >= DAYS_LIMIT:
        text = f"⚠️ هشدار: از صاحب حساب برای بیش از {DAYS_LIMIT} روز خبری نشده. لطفاً بررسی کنید."
        try:
            await bot.send_message(chat_id=GROUP_CHAT_ID, text=text)
            logger.info("Alert sent to group %s", GROUP_CHAT_ID)
            return {"alert_sent": True, "msg": "alert_sent"}
        except Exception as e:
            logger.exception("Failed to send alert: %s", e)
            return {"alert_sent": False, "msg": "send_failed"}
    else:
        logger.info("Within safe window (<= %d days).", DAYS_LIMIT)
        return {"alert_sent": False, "msg": "within_window"}

async def run_check_mode():
    """Function used by GitHub Actions: check once and exit."""
    result = await notify_if_needed()
    # print a short JSON to stdout so logs are clear
    print(json.dumps({"result": result, "timestamp": datetime.datetime.utcnow().isoformat()}))

async def run_serve_mode():
    """Run the bot in polling mode (for local server)."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("checkin", cmd_checkin))
    # start polling (this will run until you stop it)
    logger.info("Starting polling bot (serve mode).")
    await app.run_polling()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Run single check and exit (for GitHub Actions)")
    parser.add_argument("--serve", action="store_true", help="Run bot polling (local always-on)")
    args = parser.parse_args()

    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable not set.")
        sys.exit(1)
    if not YOUR_USER_ID or not GROUP_CHAT_ID:
        print("Error: YOUR_USER_ID and GROUP_CHAT_ID must be set in environment.")
        sys.exit(1)

    if args.serve:
        asyncio.run(run_serve_mode())
    else:
        # default: check mode (also if --check passed)
        asyncio.run(run_check_mode())

if __name__ == "__main__":
    main()
