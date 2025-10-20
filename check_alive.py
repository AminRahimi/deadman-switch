import os
import json
import requests
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
RECIPIENT_IDS = [int(x) for x in os.getenv("RECIPIENT_IDS", "").split(",") if x]
DAYS_LIMIT = int(os.getenv("DAYS_LIMIT", "3"))
DATA_FILE = "last_checkin.json"
OFFSET_FILE = "last_update.json"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] send_message to {chat_id} failed: {e}")
        return False

def load_json(filename):
    if not os.path.exists(filename):
        return None
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_last_check():
    data = load_json(DATA_FILE)
    if not data:
        return None
    try:
        return datetime.fromisoformat(data["last_checkin"])
    except Exception:
        return None

def save_last_check():
    now_iso = datetime.utcnow().isoformat()
    save_json(DATA_FILE, {"last_checkin": now_iso})
    return datetime.fromisoformat(now_iso)

def main():
    if not BOT_TOKEN:
        print("[FATAL] BOT_TOKEN not set")
        return

    last_check = load_last_check()
    offset_data = load_json(OFFSET_FILE)
    last_offset = offset_data.get("offset", 0) if offset_data else 0

    # دریافت آپدیت‌های جدید با offset = last_offset + 1
    try:
        resp = requests.get(f"{TELEGRAM_API}/getUpdates", params={"offset": last_offset + 1, "timeout": 1}, timeout=15)
        data = resp.json()
    except Exception as e:
        print(f"[ERROR] getUpdates failed: {e}")
        data = {"ok": False, "result": []}

    new_offset = last_offset
    for update in data.get("result", []):
        update_id = update.get("update_id")
        # offset باید آخرین update_id + 1 باشه
        if update_id is not None:
            new_offset = max(new_offset, update_id + 1)

        # پیام (ممکنه edited_message یا callback باشه؛ ما فقط message رو می‌گیریم)
        msg = update.get("message") or update.get("edited_message") or {}
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = (msg.get("text") or "").strip().lower()

        print(f"[DEBUG] update_id={update_id}, from={chat_id}, text={text}")

        if chat_id == OWNER_ID and text == "checkin":
            # ذخیره و بلافاصله مقدار last_check محلی را هم بروزرسانی کن
            last_check = save_last_check()
            send_message(OWNER_ID, "✅ وضعیتت ثبت شد. تایمر ریست شد.")
            # توجه: ادامه بررسی بقیه آپدیت‌ها مهم است چون ممکنه چند پیام جدید باشد

    # ذخیره offset جدید برای اجراهای بعدی
    save_json(OFFSET_FILE, {"offset": new_offset})

    # اگر هنوز هیچ checkin اولیه‌ای وجود ندارد، اطلاع بده و تمام کن
    if not last_check:
        print("⚠️ هنوز هیچ checkin اولیه‌ای ثبت نشده است.")
        return

    now = datetime.utcnow()
    if now - last_check > timedelta(days=DAYS_LIMIT):
        print(f"[ALERT] Last checkin was {(now - last_check).days} days ago; sending alerts.")
        for rid in RECIPIENT_IDS:
            send_message(rid, "⚠️ چند روزه از من خبری نیست. ممکنه حادثه‌ای پیش اومده باشه.")
    else:
        print("✅ هنوز در محدوده‌ی امن هستی.")

if __name__ == "__main__":
    main()
