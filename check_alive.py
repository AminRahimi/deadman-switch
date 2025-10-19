import os
import json
import requests
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
RECIPIENT_IDS = [int(x) for x in os.getenv("RECIPIENT_IDS", "").split(",") if x]
DAYS_LIMIT = int(os.getenv("DAYS_LIMIT", "3"))
DATA_FILE = "last_checkin.json"
OFFSET_FILE = "last_update.json"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text})

def load_json(filename):
    if not os.path.exists(filename):
        return None
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

def load_last_check():
    data = load_json(DATA_FILE)
    if not data:
        return None
    return datetime.fromisoformat(data["last_checkin"])

def save_last_check():
    save_json(DATA_FILE, {"last_checkin": datetime.utcnow().isoformat()})

def main():
    last_check = load_last_check()
    offset_data = load_json(OFFSET_FILE)
    last_offset = offset_data["offset"] if offset_data else 0

    updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    resp = requests.get(updates_url, params={"offset": last_offset + 1}).json()

    new_offset = last_offset
    for update in resp.get("result", []):
        msg = update.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "").strip().lower()
        update_id = update["update_id"]
        new_offset = max(new_offset, update_id)

        if chat_id == OWNER_ID and text == "checkin":
            save_last_check()
            send_message(OWNER_ID, "✅ وضعیتت ثبت شد. تایمر ریست شد.")

    # ذخیره‌ی آخرین offset برای دفعه بعد
    save_json(OFFSET_FILE, {"offset": new_offset})

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
