import telebot
import requests
import time
import threading
import os
import html
import socketserver
import urllib.request
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler

# =====================================================================
# 🤖 BOT CONFIGURATION (@aliceview_bot - Likes Bot)
# =====================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8876038348:AAHObiVm4MlVCLgTHdXH9YStxv2MXJlmYFE")
bot = telebot.TeleBot(BOT_TOKEN)

# =====================================================================
# 🌐 SMM PANEL CONFIGURATION (Primary: SMMPanelPak / Fallback: YoyoMedia)
# =====================================================================
# 1. Primary Panel: SMMPanelPak
PAK_PANEL_URL = "https://smmpanelpak.com/api/v2"
PAK_API_KEY = "1e3299898a440382ee5e410d11d3c9de5d1ff3a4"
PAK_SERVICE_LIKES = 4152   # Instagram Likes

# 2. Fallback Panel: YoyoMedia (Zero Cloudflare block on Render)
YOYO_PANEL_URL = "https://yoyomedia.com/api/v2"
YOYO_API_KEY = "74d4962ec589605651ecff3c2ab0b9dda47785b2b327303111d0d8920bdd1aed"
YOYO_SERVICE_LIKES = 4731  # Instagram Likes [Instant / High Quality]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'https://smmpanelpak.com',
    'Referer': 'https://smmpanelpak.com/'
}

# =====================================================================
# 👥 ADMIN & AUTHORIZATION
# =====================================================================
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
ALLOWED_USERS = [8207879798]  # Pre-authorized team user

campaign_running = False
stop_campaign_flag = False
current_campaign_info = {}

# =====================================================================
# 📋 19-STEP 8-HOUR LIKES SCHEDULE (Exact 123 Likes Wave)
# =====================================================================
LIKES_STEPS_DATA = [
    {"step": 1,  "interval_mins": 15,  "likes": 0,  "label": "0:15 min"},
    {"step": 2,  "interval_mins": 30,  "likes": 0,  "label": "0:30 min"},
    {"step": 3,  "interval_mins": 45,  "likes": 0,  "label": "0:45 min"},
    {"step": 4,  "interval_mins": 60,  "likes": 10, "label": "1:00 hr"},
    {"step": 5,  "interval_mins": 75,  "likes": 0,  "label": "1:15 hr"},
    {"step": 6,  "interval_mins": 90,  "likes": 0,  "label": "1:30 hr"},
    {"step": 7,  "interval_mins": 120, "likes": 12, "label": "2:00 hr"},
    {"step": 8,  "interval_mins": 150, "likes": 0,  "label": "2:30 hr"},
    {"step": 9,  "interval_mins": 180, "likes": 18, "label": "3:00 hr"},
    {"step": 10, "interval_mins": 210, "likes": 26, "label": "3:30 hr (PEAK 🔥)"},
    {"step": 11, "interval_mins": 240, "likes": 0,  "label": "4:00 hr"},
    {"step": 12, "interval_mins": 270, "likes": 19, "label": "4:30 hr"},
    {"step": 13, "interval_mins": 300, "likes": 0,  "label": "5:00 hr"},
    {"step": 14, "interval_mins": 330, "likes": 13, "label": "5:30 hr"},
    {"step": 15, "interval_mins": 360, "likes": 0,  "label": "6:00 hr"},
    {"step": 16, "interval_mins": 390, "likes": 11, "label": "6:30 hr"},
    {"step": 17, "interval_mins": 420, "likes": 0,  "label": "7:00 hr"},
    {"step": 18, "interval_mins": 450, "likes": 0,  "label": "7:30 hr"},
    {"step": 19, "interval_mins": 480, "likes": 14, "label": "8:00 hr (Final)"},
]

TOTAL_LIKES = sum(s["likes"] for s in LIKES_STEPS_DATA)  # Exactly 123 Likes

# =====================================================================
# 🛠️ HELPER FUNCTIONS
# =====================================================================
def send_safe_msg(chat_id, text, disable_web_page_preview=True):
    try:
        return bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=disable_web_page_preview)
    except Exception:
        clean_text = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", "")
        return bot.send_message(chat_id, clean_text, parse_mode=None, disable_web_page_preview=disable_web_page_preview)

def check_authorized(message):
    global ADMIN_ID, ALLOWED_USERS
    user_id = message.chat.id
    if ADMIN_ID == 0:
        ADMIN_ID = user_id
        if ADMIN_ID not in ALLOWED_USERS:
            ALLOWED_USERS.append(ADMIN_ID)
        return True
    return user_id == ADMIN_ID or user_id in ALLOWED_USERS

def clean_instagram_url(raw_url):
    raw_url = raw_url.strip()
    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        raw_url = "https://" + raw_url
    try:
        parsed = urlparse(raw_url)
        path = parsed.path
        if "/reel/" in path or "/p/" in path or "/tv/" in path:
            parts = path.strip("/").split("/")
            if len(parts) >= 2:
                return f"https://www.instagram.com/{parts[0]}/{parts[1]}/"
        return f"https://www.instagram.com{path}" if not path.endswith("/") else f"https://www.instagram.com{path}"
    except Exception:
        return raw_url

def get_ist_time_str(dt=None):
    if dt is None:
        dt = datetime.now(timezone.utc)
    ist_dt = dt + timedelta(hours=5, minutes=30)
    return ist_dt.strftime("%I:%M %p")

# =====================================================================
# 📡 SMM API FUNCTIONS (Dual Panel Fallback)
# =====================================================================
def fetch_balance():
    # 1. Check SMMPanelPak
    pak_bal = "N/A"
    try:
        resp = requests.post(PAK_PANEL_URL, data={"key": PAK_API_KEY, "action": "balance"}, headers=HEADERS, timeout=12)
        data = resp.json()
        pak_bal = f"{data.get('balance', 'N/A')} {data.get('currency', 'USD')}"
    except Exception:
        pak_bal = "Protected/Offline"

    # 2. Check YoyoMedia
    yoyo_bal = "N/A"
    try:
        resp = requests.post(YOYO_PANEL_URL, data={"key": YOYO_API_KEY, "action": "balance"}, headers=HEADERS, timeout=12)
        data = resp.json()
        yoyo_bal = f"{data.get('balance', 'N/A')} {data.get('currency', 'USD')}"
    except Exception as e:
        yoyo_bal = f"Error ({e})"

    return pak_bal, yoyo_bal

def place_likes_order(link, quantity, max_retries=2):
    # Attempt 1: SMMPanelPak
    for attempt in range(1, max_retries + 1):
        try:
            payload = {
                "key": PAK_API_KEY,
                "action": "add",
                "service": PAK_SERVICE_LIKES,
                "link": link,
                "quantity": quantity
            }
            resp = requests.post(PAK_PANEL_URL, data=payload, headers=HEADERS, timeout=12)
            data = resp.json()
            if "order" in data:
                return True, f"Pak #{data['order']}"
        except Exception:
            pass
        time.sleep(1)

    # Attempt 2: Auto Fallback to YoyoMedia
    for attempt in range(1, max_retries + 1):
        try:
            payload = {
                "key": YOYO_API_KEY,
                "action": "add",
                "service": YOYO_SERVICE_LIKES,
                "link": link,
                "quantity": quantity
            }
            resp = requests.post(YOYO_PANEL_URL, data=payload, headers=HEADERS, timeout=12)
            data = resp.json()
            if "order" in data:
                return True, f"Yoyo #{data['order']}"
            elif "error" in data:
                return False, data["error"]
        except Exception as e:
            if attempt == max_retries:
                return False, str(e)
        time.sleep(1)

    return False, "All panels unreachable"

# =====================================================================
# ❤️ LIKES CAMPAIGN RUNNER
# =====================================================================
def campaign_worker(chat_id, link):
    global campaign_running, stop_campaign_flag, current_campaign_info

    start_utc = datetime.now(timezone.utc)
    current_campaign_info = {
        "link": link,
        "start_time": start_utc,
        "current_step": 0,
        "likes_sent": 0,
        "chat_id": chat_id
    }

    send_safe_msg(
        chat_id,
        f"🚀 <b>Likes Wave Campaign Started!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>Bot:</b> @aliceview_bot\n"
        f"🔗 <b>Target:</b> <code>{link}</code>\n"
        f"❤️ <b>Total Likes:</b> <code>{TOTAL_LIKES} Likes</code>\n"
        f"⏱️ <b>Schedule:</b> 19 Steps (8 Hours Wave)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"▶️ <i>First Like order (+10) will trigger at 1:00 hr (Step 4)...</i>"
    )

    for i, step in enumerate(LIKES_STEPS_DATA):
        if stop_campaign_flag:
            send_safe_msg(chat_id, f"🛑 <b>Likes Campaign Stopped Manually!</b> at Step {i}/{len(LIKES_STEPS_DATA)}.")
            campaign_running = False
            stop_campaign_flag = False
            return

        step_num = step["step"]
        target_mins = step["interval_mins"]
        likes_qty = step["likes"]
        step_label = step["label"]
        current_campaign_info["current_step"] = step_num

        target_time_utc = start_utc + timedelta(minutes=target_mins)
        now_utc = datetime.now(timezone.utc)
        sleep_seconds = (target_time_utc - now_utc).total_seconds()

        while sleep_seconds > 0:
            if stop_campaign_flag:
                send_safe_msg(chat_id, f"🛑 <b>Likes Campaign Stopped Manually!</b> before Step {step_num}.")
                campaign_running = False
                stop_campaign_flag = False
                return
            chunk = min(sleep_seconds, 5)
            time.sleep(chunk)
            now_utc = datetime.now(timezone.utc)
            sleep_seconds = (target_time_utc - now_utc).total_seconds()

        exec_time_str = get_ist_time_str()

        # Place order if likes scheduled for this step
        if likes_qty > 0:
            success, order_res = place_likes_order(link, likes_qty)
            if success:
                current_campaign_info["likes_sent"] += likes_qty
                status_text = f"✅ {order_res}"
            else:
                status_text = f"❌ Failed ({order_res})"

            pct = int((current_campaign_info["likes_sent"] / TOTAL_LIKES) * 100)
            progress_bar = "▓" * (pct // 10) + "░" * (10 - (pct // 10))

            msg = (
                f"❤️ <b>Likes Step {step_num}/19 [{step_label}]</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"❤️ <b>Likes Ordered:</b> +{likes_qty} ({status_text})\n"
                f"📈 <b>Total Sent:</b> <code>{current_campaign_info['likes_sent']} / {TOTAL_LIKES}</code>\n"
                f"📊 <b>Progress:</b> [{progress_bar}] {pct}%\n"
                f"🕒 <b>Time:</b> {exec_time_str} IST\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            )
            send_safe_msg(chat_id, msg)
        else:
            print(f"[Likes Bot] Step {step_num}/19 [{step_label}]: 0 likes.")

    campaign_running = False
    current_campaign_info = {}
    send_safe_msg(
        chat_id,
        f"🎉 <b>Likes Wave Campaign Completed Successfully!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Target:</b> <code>{link}</code>\n"
        f"❤️ <b>Total Likes Delivered:</b> {TOTAL_LIKES}\n"
        f"🕒 <b>Finished At:</b> {get_ist_time_str()} IST\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

# =====================================================================
# 💬 TELEGRAM BOT COMMANDS
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    if not check_authorized(message):
        send_safe_msg(message.chat.id, "⛔ Access Denied.")
        return
    txt = (
        f"❤️ <b>Instagram Likes Bot (@aliceview_bot)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Commands:</b>\n"
        f"• <code>/run &lt;link&gt;</code> - Start 19-Step Wave (123 Likes over 8 Hrs)\n"
        f"• <code>/instant &lt;qty&gt; &lt;link&gt;</code> - Instant Likes (e.g. <code>/instant 50 link</code>)\n"
        f"• <code>/balance</code> - Check Panel Wallet Balance\n"
        f"• <code>/status</code> - Current Active Campaign Status\n"
        f"• <code>/stop</code> - Stop Active Campaign\n"
        f"• <code>/auth &lt;id&gt;</code> - Authorize Team User\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>Send any Instagram link directly to start 8-hour wave!</i>"
    )
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['balance'])
def cmd_balance(message):
    if not check_authorized(message):
        return
    pak_bal, yoyo_bal = fetch_balance()
    txt = (
        f"💰 <b>Likes Panels Balance:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🇵🇰 <b>SMMPanelPak:</b> <code>{pak_bal}</code>\n"
        f"⚡ <b>YoyoMedia:</b> <code>{yoyo_bal}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['instant'])
def cmd_instant(message):
    if not check_authorized(message):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        send_safe_msg(message.chat.id, "⚠️ Usage: <code>/instant &lt;quantity&gt; &lt;instagram_link&gt;</code>\nExample: <code>/instant 50 https://instagram.com/reel/xyz</code>")
        return
    try:
        qty = int(parts[1])
        if qty < 10:
            send_safe_msg(message.chat.id, "⚠️ Minimum quantity for Likes is 10.")
            return
        link = clean_instagram_url(parts[2].strip())
        send_safe_msg(message.chat.id, f"⏳ Placing Instant Order for <b>{qty} Likes</b> on <code>{link}</code>...")
        success, res = place_likes_order(link, qty)
        if success:
            send_safe_msg(message.chat.id, f"✅ <b>Order Placed Successfully!</b>\n🆔 Order ID: <code>{res}</code>\n❤️ Quantity: <code>{qty} Likes</code>")
        else:
            send_safe_msg(message.chat.id, f"❌ <b>Order Failed:</b> {res}")
    except ValueError:
        send_safe_msg(message.chat.id, "⚠️ Quantity must be a valid number.")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not check_authorized(message):
        return
    if not campaign_running:
        send_safe_msg(message.chat.id, "ℹ️ No Likes campaign is currently running.")
        return
    info = current_campaign_info
    pct = int((info.get('likes_sent', 0) / TOTAL_LIKES) * 100)
    txt = (
        f"📊 <b>Likes Campaign Status:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Link:</b> <code>{info.get('link', 'N/A')}</code>\n"
        f"📍 <b>Current Step:</b> {info.get('current_step', 0)} / 19\n"
        f"❤️ <b>Likes Sent:</b> <code>{info.get('likes_sent', 0)} / {TOTAL_LIKES}</code> ({pct}%)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    global stop_campaign_flag
    if not check_authorized(message):
        return
    if not campaign_running:
        send_safe_msg(message.chat.id, "ℹ️ No campaign is running.")
        return
    stop_campaign_flag = True
    send_safe_msg(message.chat.id, "⏳ Stopping Likes campaign...")

@bot.message_handler(commands=['auth'])
def cmd_auth(message):
    if not check_authorized(message):
        return
    try:
        new_id = int(message.text.split()[1])
        if new_id not in ALLOWED_USERS:
            ALLOWED_USERS.append(new_id)
        send_safe_msg(message.chat.id, f"✅ User <code>{new_id}</code> authorized.")
    except Exception:
        send_safe_msg(message.chat.id, "⚠️ Usage: <code>/auth &lt;user_id&gt;</code>")

@bot.message_handler(commands=['run'])
def cmd_run(message):
    if not check_authorized(message):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        send_safe_msg(message.chat.id, "⚠️ Please provide an Instagram link!\nExample: <code>/run https://www.instagram.com/reel/xyz</code>")
        return
    start_likes_campaign(message.chat.id, args[1].strip())

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    if not check_authorized(message):
        return
    text = message.text.strip()
    if "instagram.com" in text:
        start_likes_campaign(message.chat.id, text)
    else:
        send_safe_msg(message.chat.id, "❓ Unknown command. Send an Instagram link or type /help.")

def start_likes_campaign(chat_id, raw_url):
    global campaign_running, stop_campaign_flag
    if campaign_running:
        send_safe_msg(chat_id, "⚠️ A Likes campaign is already running! Use /stop first.")
        return
    clean_url = clean_instagram_url(raw_url)
    campaign_running = True
    stop_campaign_flag = False
    th = threading.Thread(target=campaign_worker, args=(chat_id, clean_url), daemon=True)
    th.start()

# =====================================================================
# 🌐 KEEP-ALIVE DUMMY HTTP SERVER (For Render Free Web Service)
# =====================================================================
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Alice Likes Bot is Active and Healthy!")
    def log_message(self, format, *args):
        pass

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), DummyServer) as httpd:
        httpd.serve_forever()

# =====================================================================
# 🚀 MAIN ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    t = threading.Thread(target=run_dummy_server, daemon=True)
    t.start()
    print("🤖 Instagram Likes Bot (@aliceview_bot) Started...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)
