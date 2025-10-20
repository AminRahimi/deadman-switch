import os
import json
import requests
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
RECIPIENT_IDS = [int(x.strip()) for x in os.getenv("RECIPIENT_IDS", "").split(",") if x.strip()]
DAYS_LIMIT = int(os.getenv("DAYS_LIMIT", "3"))

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

STATE_FILE = "last_checkin.json"
OFFSET_FILE = "last_update.json"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_check": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def load_offset():
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, "r") as f:
            return json.load(f)
    return {"offset": 0}


def save_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        json.dump(offset, f)


def get_updates(offset):
    resp = requests.get(f"{BASE_URL}/getUpdates", params={"offset": offset})
    data = resp.json()
    return data.get("result", [])


def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": text})


def main():
    state = load_state()
    offset_data = load_offset()
    offset = offset_data.get("offset", 0)

    updates = get_updates(offset)
    new_offset = offset

    for update in updates:
        new_offset = max(new_offset, update["update_id"] + 1)
        message = update.get("message")
        if not message:
            continue

        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip().lower()

        if chat_id == OWNER_ID and text in ["checkin", "/checkin"]:
            now = datetime.now(timezone.utc).isoformat()
            state["last_check"] = now
            save_state(state)
            send_message(chat_id, "✅ وضعیتت ثبت شد. تایمر ریست شد.")
            print("Owner check-in recorded.")

    save_offset({"offset": new_offset})

    # بررسی وضعیت آخرین چک‌این
    last_check = state.get("last_check")
    if not last_check:
        print("⚠️ هنوز هیچ checkin اولیه‌ای ثبت نشده است.")
        return

    last_check_dt = datetime.fromisoformat(last_check)
    now = datetime.now(timezone.utc)

    if now - last_check_dt > timedelta(days=DAYS_LIMIT):
        for rid in RECIPIENT_IDS:
            send_message(rid, "⚠️ چند روزه از من خبری نیست. ممکنه حادثه‌ای پیش اومده باشه.")
        print("⚠️ هشدار ارسال شد.")
    else:
        print("✅ هنوز در محدوده‌ی امن هستی.")


if __name__ == "__main__":
    main()
