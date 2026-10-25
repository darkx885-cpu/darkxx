import telebot
from telebot import types
import requests
import time
import threading
import os
import json
import socketserver
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler

# =====================================================================
# 🤖 TELEGRAM BOT CONFIGURATION
# =====================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8966472325:AAHNDkup2W4Zo6ja_70eSiEI7zdPq-PF5mw")
bot = telebot.TeleBot(BOT_TOKEN)

# =====================================================================
# 🌐 XMEDIASMM PANEL CONFIGURATION (TIKTOK SERVICE 1364)
# =====================================================================
PANEL_URL = "https://xmediasmm.in/api/v2"
API_KEY = os.environ.get("XMEDIA_API_KEY", "31b2e3bd9cc353a811ae37d72d56586a")
SERVICE_ID = 1364  # Tiktok Views [No Refill] [Instant Start] - Rs 0.70 / 1000

# ⚙️ EXACT SETTINGS (Fixed as requested)
QTY_PER_RUN = 125    # 125 views per order
TOTAL_RUNS = 16      # 16 runs
INTERVAL_MINS = 45   # Har 45 minute me agla order
TOTAL_VIEWS = QTY_PER_RUN * TOTAL_RUNS  # 2,000 Views Total

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded',
}

# =====================================================================
# 👥 ADMIN & STATE TRACKING
# =====================================================================
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
ALLOWED_USERS = [8207879798]

campaign_running = False
stop_campaign_flag = False
current_campaign_info = {}

# =====================================================================
# 🛠️ HELPER FUNCTIONS
# =====================================================================
def send_safe_msg(chat_id, text, disable_web_page_preview=True, reply_markup=None):
    try:
        return bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=disable_web_page_preview, reply_markup=reply_markup)
    except Exception:
        clean_text = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", "")
        return bot.send_message(chat_id, clean_text, parse_mode=None, disable_web_page_preview=disable_web_page_preview, reply_markup=reply_markup)

def check_authorized(message):
    global ADMIN_ID, ALLOWED_USERS
    user_id = message.chat.id
    if ADMIN_ID == 0:
        ADMIN_ID = user_id
        if ADMIN_ID not in ALLOWED_USERS:
            ALLOWED_USERS.append(ADMIN_ID)
        return True
    return user_id == ADMIN_ID or user_id in ALLOWED_USERS

def clean_url(raw_url):
    raw_url = raw_url.strip()
    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        raw_url = "https://" + raw_url
    return raw_url

def get_ist_time_str(dt=None):
    if dt is None:
        dt = datetime.now(timezone.utc)
    ist_dt = dt + timedelta(hours=5, minutes=30)
    return ist_dt.strftime("%I:%M %p")

# =====================================================================
# 📡 SMM API FUNCTIONS
# =====================================================================
def fetch_balance():
    try:
        resp = requests.post(PANEL_URL, data={"key": API_KEY, "action": "balance"}, headers=HEADERS, timeout=12)
        data = resp.json()
        return f"{data.get('balance', 'N/A')} {data.get('currency', 'INR')}"
    except Exception as e:
        return f"Error ({e})"

def place_order(link, quantity):
    try:
        payload = {
            "key": API_KEY,
            "action": "add",
            "service": SERVICE_ID,
            "link": link,
            "quantity": quantity
        }
        resp = requests.post(PANEL_URL, data=payload, headers=HEADERS, timeout=15)
        data = resp.json()
        if "order" in data:
            return True, data["order"]
        elif "error" in data:
            return False, data["error"]
        return False, str(data)
    except Exception as e:
        return False, str(e)

# =====================================================================
# 🌊 TIKTOK DRIP-FEED ENGINE (Link paste karte hi start)
# =====================================================================
def drip_campaign_worker(chat_id, link):
    global campaign_running, stop_campaign_flag, current_campaign_info

    start_utc = datetime.now(timezone.utc)
    total_hours = (TOTAL_RUNS * INTERVAL_MINS) / 60

    current_campaign_info = {
        "link": link,
        "start_time": start_utc,
        "current_run": 0,
        "views_sent": 0,
        "chat_id": chat_id,
        "next_run_ist": get_ist_time_str()
    }

    send_safe_msg(
        chat_id,
        f"🚀 <b>TikTok Drip-Feed Campaign Started!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Target:</b> <code>{link}</code>\n"
        f"👁️ <b>Total Target:</b> <code>{TOTAL_VIEWS} Views</code>\n"
        f"🔁 <b>Structure:</b> <code>{TOTAL_RUNS} Runs</code> (125 views/run)\n"
        f"⏱️ <b>Interval:</b> Har <code>{INTERVAL_MINS} minute</code> me\n"
        f"⌛ <b>Duration:</b> ~{total_hours:.1f} Hours Wave\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"▶️ <i>Run 1/16 abhi turant place ho raha hai...</i>"
    )

    for run_idx in range(1, TOTAL_RUNS + 1):
        if stop_campaign_flag:
            send_safe_msg(chat_id, f"🛑 <b>Campaign Stopped Manually!</b> at Run {run_idx - 1}/{TOTAL_RUNS}.")
            campaign_running = False
            stop_campaign_flag = False
            return

        current_campaign_info["current_run"] = run_idx
        exec_time_str = get_ist_time_str()

        # Place Order for this Run (125 views)
        success, order_res = place_order(link, QTY_PER_RUN)

        if success:
            current_campaign_info["views_sent"] += QTY_PER_RUN
            status_text = f"✅ Order #{order_res}"
        else:
            status_text = f"❌ Failed ({order_res})"

        pct = int((current_campaign_info["views_sent"] / TOTAL_VIEWS) * 100)
        progress_bar = "▓" * (pct // 10) + "░" * (10 - (pct // 10))

        # Calculate next run time
        if run_idx < TOTAL_RUNS:
            next_time_utc = datetime.now(timezone.utc) + timedelta(minutes=INTERVAL_MINS)
            next_str = get_ist_time_str(next_time_utc)
            current_campaign_info["next_run_ist"] = next_str
            next_info = f"🕒 <b>Next Run ({run_idx + 1}/{TOTAL_RUNS}):</b> At <b>{next_str} IST</b> (in {INTERVAL_MINS}m)"
        else:
            next_info = "🏁 <b>Final Run Completed!</b>"

        msg = (
            f"🌊 <b>TikTok Drip Run {run_idx}/{TOTAL_RUNS}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Views Ordered:</b> +{QTY_PER_RUN} ({status_text})\n"
            f"📈 <b>Total Sent:</b> <code>{current_campaign_info['views_sent']} / {TOTAL_VIEWS} Views</code>\n"
            f"📊 <b>Progress:</b> [{progress_bar}] {pct}%\n"
            f"🕒 <b>Time:</b> {exec_time_str} IST\n"
            f"{next_info}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_safe_msg(chat_id, msg)

        # Wait 45 minutes for next run
        if run_idx < TOTAL_RUNS:
            sleep_seconds = INTERVAL_MINS * 60
            while sleep_seconds > 0:
                if stop_campaign_flag:
                    send_safe_msg(chat_id, f"🛑 <b>Campaign Stopped Manually!</b> during Run {run_idx} cooldown.")
                    campaign_running = False
                    stop_campaign_flag = False
                    return
                chunk = min(sleep_seconds, 5)
                time.sleep(chunk)
                sleep_seconds -= chunk

    campaign_running = False
    current_campaign_info = {}
    send_safe_msg(
        chat_id,
        f"🎉 <b>TikTok 16-Run Drip Campaign Finished!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Target:</b> <code>{link}</code>\n"
        f"👁️ <b>Total Views Delivered:</b> {TOTAL_VIEWS}\n"
        f"🕒 <b>Finished At:</b> {get_ist_time_str()} IST\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

def start_campaign(chat_id, raw_url):
    global campaign_running, stop_campaign_flag
    if campaign_running:
        send_safe_msg(chat_id, "⚠️ Ek TikTok Drip Campaign pehle se chal raha hai! Naya shuru karne ke liye pehle /stop karein.")
        return
    c_url = clean_url(raw_url)
    campaign_running = True
    stop_campaign_flag = False
    th = threading.Thread(target=drip_campaign_worker, args=(chat_id, c_url), daemon=True)
    th.start()

# =====================================================================
# 💬 TELEGRAM COMMANDS
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    if not check_authorized(message):
        send_safe_msg(message.chat.id, "⛔ Access Denied.")
        return
    txt = (
        f"🎵 <b>TikTok 16-Step Drip-Feed Bot</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ <b>Fixed Configuration:</b>\n"
        f"• Panel: <code>xmediasmm.in</code> (Service 1364)\n"
        f"• Quantity per Run: <b>125 Views</b>\n"
        f"• Number of Runs: <b>16 Runs</b>\n"
        f"• Interval: Har <b>45 Minute</b> me\n"
        f"• Total Target: <b>2,000 Views</b>\n"
        f"• Start: <b>Link paste karte hi Run 1 shuru!</b>\n\n"
        f"📌 <b>Commands:</b>\n"
        f"• <code>/status</code> - Active campaign progress & next run time\n"
        f"• <code>/balance</code> - Check xmediasmm.in wallet balance\n"
        f"• <code>/stop</code> - Stop current campaign\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>Bas TikTok ka link paste karo, Run 1 turant start ho jayega!</i>"
    )
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['balance'])
def cmd_balance(message):
    if not check_authorized(message):
        return
    bal = fetch_balance()
    send_safe_msg(message.chat.id, f"💰 <b>xmediasmm.in Wallet Balance:</b> <code>{bal}</code>")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not check_authorized(message):
        return
    if not campaign_running:
        send_safe_msg(message.chat.id, "ℹ️ Abhi koi campaign nahi chal raha hai.")
        return
    info = current_campaign_info
    pct = int((info.get('views_sent', 0) / TOTAL_VIEWS) * 100)
    txt = (
        f"📊 <b>Active Campaign Status:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Link:</b> <code>{info.get('link', 'N/A')}</code>\n"
        f"📍 <b>Current Run:</b> {info.get('current_run', 0)} / {TOTAL_RUNS}\n"
        f"👁️ <b>Views Sent:</b> <code>{info.get('views_sent', 0)} / {TOTAL_VIEWS}</code> ({pct}%)\n"
        f"🕒 <b>Next Run:</b> {info.get('next_run_ist', 'In Progress')} IST\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['stop', 'cancel'])
def cmd_stop(message):
    global stop_campaign_flag
    if not check_authorized(message):
        return
    if not campaign_running:
        send_safe_msg(message.chat.id, "ℹ️ Koi campaign nahi chal raha hai.")
        return
    stop_campaign_flag = True
    send_safe_msg(message.chat.id, "⏳ Campaign stop kiya ja raha hai...")

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

# =====================================================================
# 🔗 DIRECT LINK HANDLER (Paste link -> Starts immediately)
# =====================================================================
@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    if not check_authorized(message):
        return
    text = message.text.strip()
    if "tiktok.com" in text or "http://" in text or "https://" in text:
        start_campaign(message.chat.id, text)
    else:
        send_safe_msg(message.chat.id, "❓ Unknown message. Kripya video/TikTok link paste karein ya /help type karein.")

# =====================================================================
# 🌐 KEEP-ALIVE DUMMY HTTP SERVER (For Render Free Web Service)
# =====================================================================
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"TikTok Drip Bot is Active and Healthy!")
    def log_message(self, format, *args):
        pass

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        with socketserver.TCPServer(("", port), DummyServer) as httpd:
            httpd.serve_forever()
    except Exception as e:
        print(f"Server error on port {port}: {e}")

# =====================================================================
# 🚀 MAIN ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    t = threading.Thread(target=run_dummy_server, daemon=True)
    t.start()
    print("🎵 TikTok 16-Step Drip-Feed Bot Started (xmediasmm.in)...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)
