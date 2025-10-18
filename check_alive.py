import os
import json
import time
import requests
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
RECIPIENT_IDS = [int(x) for x in os.getenv("RECIPIENT_IDS", "").split(",") if x]
DAYS_LIMIT = int(os.getenv("DAYS_LIMIT", "3"))
DATA_FILE = "last_checkin.json"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text})
    print(f"[SEND] to {chat_id}: {r.status_code} {r.text}")

def load_last_check():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE, "r") as f:
        return datetime.fromisoformat(json.load(f)["last_checkin"])

def save_last_check():
    with open(DATA_FILE, "w") as f:
        json.dump({"last_checkin": datetime.utcnow().isoformat()}, f)

def main():
    print(f"[{datetime.utcnow().isoformat()}] Starting check...")

    last_check = load_last_check()
    updates = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates").json()

    # 👇 چاپ پیام‌ها برای بررسی
    print("Recent updates:", json.dumps(updates, indent=2, ensure_ascii=False))

    for update in updates.get("result", []):
        msg = update.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "").strip().lower()
        print(f"Found message from {chat_id}: {text}")

        if chat_id == OWNER_ID and text == "checkin":
            save_last_check()
            send_message(OWNER_ID, "✅ وضعیتت ثبت شد. تایمر ریست شد.")
            return

    if not last_check:
        print("⚠️ هنوز هیچ checkin اولیه‌ای ثبت نشده است.")
        return

    now = datetime.utcnow()
    if now - last_check > timedelta(days=DAYS_LIMIT):
        for rid in RECIPIENT_IDS:
            send_message(rid, "⚠️ چند روزه از من خبری نیست. ممکنه حادثه‌ای پیش اومده باشه.")
    else:
        print("✅ هنوز در محدوده‌ی امن هستی.")

if __name__ == "__main__":
    main()
