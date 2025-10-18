# check_alive.py (نسخه به‌روزرسانی‌شده)
import os
import json
import time
import requests
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
RECIPIENT_IDS = [int(x) for x in os.getenv("RECIPIENT_IDS", "").split(",") if x]
DAYS_LIMIT = int(os.getenv("DAYS_LIMIT", "3"))
STATE_FILE = "state.json"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"last_checkin": None, "last_update_id": None, "alert_sent": False}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    resp = requests.post(url, data={"chat_id": chat_id, "text": text})
    return resp.ok

def fetch_updates(offset=None, timeout=1):
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    url = f"{TELEGRAM_API}/getUpdates"
    r = requests.get(url, params=params, timeout=10)
    return r.json()

def iso_to_dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s)

def now_iso():
    return datetime.utcnow().isoformat()

def main():
    state = load_state()
    last_checkin = iso_to_dt(state.get("last_checkin"))
    last_update_id = state.get("last_update_id")
    alert_sent = state.get("alert_sent", False)

    # 1) گرفتن آپدیت‌های جدید از تلگرام با استفاده از offset
    updates = fetch_updates(offset=last_update_id)
    max_update_id = last_update_id
    for upd in updates.get("result", []):
        update_id = upd.get("update_id")
        if max_update_id is None or update_id >= max_update_id:
            max_update_id = update_id + 1  # offset should be last seen + 1

        msg = upd.get("message") or upd.get("edited_message") or {}
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = (msg.get("text") or "").strip().lower()

        # اگر صاحب حساب checkin فرستاد
        if chat_id == OWNER_ID and text == "checkin":
            state["last_checkin"] = now_iso()
            state["alert_sent"] = False
            save_state(state)
            send_message(OWNER_ID, "✅ وضعیت ثبت شد و تایمر ریست شد.")
            # برو بیرون؛ چون فرایند تایید تموم شد.
            return

        # (می‌تونیم دستورات مدیریت دیگه‌ای هم اینجا اضافه کنیم، مثلا "status" یا "stop")
    # اگر آپدیتی دریافت شد، آخرین id را ذخیره کن
    if max_update_id is not None:
        state["last_update_id"] = max_update_id
        save_state(state)

    # 2) بررسی تاریخ آخرین چکین
    if state.get("last_checkin"):
        last_checkin = iso_to_dt(state["last_checkin"])
    else:
        last_checkin = None

    if last_checkin:
        now = datetime.utcnow()
        if now - last_checkin > timedelta(days=DAYS_LIMIT) and not state.get("alert_sent", False):
            # ارسال پیام هشدار به همه گیرنده‌ها
            text = "⚠️ هشدار: از صاحب حساب برای بیش از {} روز خبری نشده. لطفاً بررسی کنید.".format(DAYS_LIMIT)
            for rid in RECIPIENT_IDS:
                send_message(rid, text)
            # یک‌بار اعلام شد — تا وقتی checkin نشه مجدداً ارسال نشه
            state["alert_sent"] = True
            save_state(state)
        else:
            print("✅ هنوز در محدوده امن هستید یا هشدار قبلا فرستاده شده.")
    else:
        # اگر هیچ‌وقت checkin نداشتیم، می‌تونیم تصمیم بگیریم که هشدار بفرستیم یا نه.
        print("⚠️ هنوز هیچ checkin اولیه‌ای ثبت نشده است.")

if __name__ == "__main__":
    main()
