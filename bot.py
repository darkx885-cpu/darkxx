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
# 🤖 BOT CONFIGURATION (Dedicated Views Bot)
# =====================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8631983010:AAFc466k0LIu10i_wErRu5CU2f6tulz3AsM")
bot = telebot.TeleBot(BOT_TOKEN)

# =====================================================================
# 🌐 VIEWS SMM PANEL (PakFollowers - Service #18999)
# =====================================================================
VIEWS_PANEL_URL = "https://pakfollowers.com/api/v2"
VIEWS_API_KEY = os.environ.get("VIEWS_API_KEY", "889732601d1ae132911f3a68534acef6950a37eb")
SERVICE_VIEWS = 18999  # Instagram Views fast [100k/h]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Content-Type': 'application/x-www-form-urlencoded'
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
# 📋 23-STEP 10-HOUR VIEWS SCHEDULE (Total: 15,000 Views)
# =====================================================================
STEPS_DATA = [
    {"step": 1,  "interval_mins": 15,  "views": 115,   "label": "0:15 min"},
    {"step": 2,  "interval_mins": 30,  "views": 175,   "label": "0:30 min"},
    {"step": 3,  "interval_mins": 45,  "views": 285,   "label": "0:45 min"},
    {"step": 4,  "interval_mins": 60,  "views": 395,   "label": "1:00 hr"},
    {"step": 5,  "interval_mins": 75,  "views": 565,   "label": "1:15 hr"},
    {"step": 6,  "interval_mins": 90,  "views": 715,   "label": "1:30 hr"},
    {"step": 7,  "interval_mins": 120, "views": 925,   "label": "2:00 hr"},
    {"step": 8,  "interval_mins": 150, "views": 1265,  "label": "2:30 hr"},
    {"step": 9,  "interval_mins": 180, "views": 1640,  "label": "3:00 hr"},
    {"step": 10, "interval_mins": 210, "views": 1960,  "label": "3:30 hr (PEAK 🔥)"},
    {"step": 11, "interval_mins": 240, "views": 1710,  "label": "4:00 hr"},
    {"step": 12, "interval_mins": 270, "views": 1380,  "label": "4:30 hr"},
    {"step": 13, "interval_mins": 300, "views": 1050,  "label": "5:00 hr"},
    {"step": 14, "interval_mins": 330, "views": 770,   "label": "5:30 hr"},
    {"step": 15, "interval_mins": 360, "views": 530,   "label": "6:00 hr"},
    {"step": 16, "interval_mins": 390, "views": 380,   "label": "6:30 hr"},
    {"step": 17, "interval_mins": 420, "views": 270,   "label": "7:00 hr"},
    {"step": 18, "interval_mins": 450, "views": 210,   "label": "7:30 hr"},
    {"step": 19, "interval_mins": 480, "views": 165,   "label": "8:00 hr"},
    {"step": 20, "interval_mins": 510, "views": 145,   "label": "8:30 hr"},
    {"step": 21, "interval_mins": 540, "views": 130,   "label": "9:00 hr"},
    {"step": 22, "interval_mins": 570, "views": 118,   "label": "9:30 hr"},
    {"step": 23, "interval_mins": 600, "views": 102,   "label": "10:00 hr (Final)"},
]

TOTAL_VIEWS = sum(s["views"] for s in STEPS_DATA)  # Exactly 15,000 Views

# =====================================================================
# 🛠️ HELPER FUNCTIONS (Crash-Proof Messaging)
# =====================================================================
def send_safe_msg(chat_id, text, disable_web_page_preview=True):
    """Safely sends HTML message; falls back to plain text if parse error occurs."""
    try:
        return bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=disable_web_page_preview)
    except Exception:
        clean_text = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", "")
        try:
            return bot.send_message(chat_id, clean_text, parse_mode=None, disable_web_page_preview=disable_web_page_preview)
        except Exception as e:
            print(f"Error sending message: {e}")

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
    raw_url = raw_url.strip().strip("<>").strip()
    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        raw_url = "https://" + raw_url
    try:
        parsed = urlparse(raw_url)
        path = parsed.path
        if "/reel/" in path or "/p/" in path or "/tv/" in path:
            parts = path.strip("/").split("/")
            if len(parts) >= 2:
                return f"https://www.instagram.com/{parts[0]}/{parts[1]}/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    except Exception:
        return raw_url

def get_ist_time_str(dt=None):
    if dt is None:
        dt = datetime.now(timezone.utc)
    ist_dt = dt + timedelta(hours=5, minutes=30)
    return ist_dt.strftime("%I:%M %p")

# =====================================================================
# 📡 SMM API FUNCTIONS (PakFollowers)
# =====================================================================
def fetch_balance():
    try:
        payload = {"key": VIEWS_API_KEY, "action": "balance"}
        resp = requests.post(VIEWS_PANEL_URL, data=payload, headers=HEADERS, timeout=15)
        data = resp.json()
        bal = data.get("balance", "N/A")
        cur = data.get("currency", "PKR")
        return f"{bal} {cur}"
    except Exception as e:
        return f"Error: {e}"

def place_views_order(link, quantity, max_retries=3):
    payload = {
        "key": VIEWS_API_KEY,
        "action": "add",
        "service": SERVICE_VIEWS,
        "link": link,
        "quantity": quantity
    }
    last_err = "Unknown error"
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(VIEWS_PANEL_URL, data=payload, headers=HEADERS, timeout=15)
            data = resp.json()
            if "order" in data:
                return True, data["order"]
            elif "error" in data:
                last_err = data["error"]
            else:
                last_err = str(data)
        except Exception as e:
            last_err = str(e)
        if attempt < max_retries:
            time.sleep(2)
    return False, last_err

# =====================================================================
# 🌊 VIEWS CAMPAIGN RUNNER (Supports Starting from any Batch/Step)
# =====================================================================
def campaign_worker(chat_id, link, start_step=1):
    global campaign_running, stop_campaign_flag, current_campaign_info

    # Filter steps from start_step onwards
    selected_steps = [s for s in STEPS_DATA if s["step"] >= start_step]
    if not selected_steps:
        selected_steps = STEPS_DATA
        start_step = 1

    # Base minutes offset so start_step executes immediately
    base_mins_offset = selected_steps[0]["interval_mins"]
    remaining_total_views = sum(s["views"] for s in selected_steps)

    start_utc = datetime.now(timezone.utc)
    current_campaign_info = {
        "link": link,
        "start_time": start_utc,
        "start_step": start_step,
        "current_step": start_step,
        "views_sent": 0,
        "total_views_target": remaining_total_views,
        "chat_id": chat_id
    }

    first_step_label = selected_steps[0]["label"]
    send_safe_msg(
        chat_id,
        f"🚀 <b>10-Hour Views Wave Campaign Started!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Target:</b> <code>{link}</code>\n"
        f"📍 <b>Starting From:</b> Step {start_step}/23 [{first_step_label}]\n"
        f"👁️ <b>Target Views:</b> <code>{remaining_total_views:,} Views</code>\n"
        f"⏱️ <b>Schedule:</b> {len(selected_steps)} Steps over 10 Hours\n"
        f"🇵🇰 <b>Panel:</b> PakFollowers [Service #{SERVICE_VIEWS}]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"▶️ <i>Running Step {start_step}/23 now...</i>"
    )

    for i, step in enumerate(selected_steps):
        if stop_campaign_flag:
            send_safe_msg(chat_id, f"🛑 <b>Campaign Stopped Manually!</b> at Step {step['step']}/23.")
            campaign_running = False
            stop_campaign_flag = False
            return

        step_num = step["step"]
        step_original_mins = step["interval_mins"]
        views_qty = step["views"]
        step_label = step["label"]
        current_campaign_info["current_step"] = step_num

        # First executed step runs immediately without waiting
        if i == 0:
            sleep_seconds = 0
        else:
            relative_mins = step_original_mins - base_mins_offset
            target_time_utc = start_utc + timedelta(minutes=relative_mins)
            now_utc = datetime.now(timezone.utc)
            sleep_seconds = (target_time_utc - now_utc).total_seconds()

        while sleep_seconds > 0:
            if stop_campaign_flag:
                send_safe_msg(chat_id, f"🛑 <b>Campaign Stopped Manually!</b> before Step {step_num}.")
                campaign_running = False
                stop_campaign_flag = False
                return
            chunk = min(sleep_seconds, 5)
            time.sleep(chunk)
            now_utc = datetime.now(timezone.utc)
            sleep_seconds = (target_time_utc - now_utc).total_seconds()

        # Place Views Order
        success, order_res = place_views_order(link, views_qty)
        exec_time_str = get_ist_time_str()

        if success:
            current_campaign_info["views_sent"] += views_qty
            status_text = f"✅ Order #{order_res}"
        else:
            status_text = f"❌ Failed ({order_res})"

        pct = int((current_campaign_info["views_sent"] / remaining_total_views) * 100) if remaining_total_views > 0 else 100
        progress_bar = "▓" * (pct // 10) + "░" * (10 - (pct // 10))

        msg = (
            f"🌊 <b>Views Step {step_num}/23 [{step_label}]</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👁️ <b>PakFollowers Views:</b> +{views_qty:,} ({status_text})\n"
            f"📈 <b>Total Sent:</b> <code>{current_campaign_info['views_sent']:,} / {remaining_total_views:,}</code>\n"
            f"📊 <b>Progress:</b> [{progress_bar}] {pct}%\n"
            f"🕒 <b>Time:</b> {exec_time_str} IST\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_safe_msg(chat_id, msg)

    campaign_running = False
    current_campaign_info = {}
    send_safe_msg(
        chat_id,
        f"🎉 <b>10-Hour Views Wave Completed Successfully!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Target:</b> <code>{link}</code>\n"
        f"👁️ <b>Total Views Delivered:</b> {remaining_total_views:,}\n"
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
        f"👁️ <b>Instagram Views Wave Bot (PakFollowers 15,000 Views)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Commands:</b>\n"
        f"• <code>/run &lt;link&gt;</code> - Start from Step 1 (15,000 Views over 10 Hrs)\n"
        f"• <code>/batch &lt;step&gt; &lt;link&gt;</code> - <b>Start from specific Step/Batch</b> (e.g. <code>/batch 5 link</code>)\n"
        f"• <code>/instant &lt;qty&gt; &lt;link&gt;</code> - Instant Views (e.g. <code>/instant 1000 link</code>)\n"
        f"• <code>/schedule</code> - View all 23 Steps & View counts\n"
        f"• <code>/balance</code> - Check PakFollowers Wallet Balance\n"
        f"• <code>/status</code> - Current Active Campaign Status\n"
        f"• <code>/stop</code> - Stop Active Campaign\n"
        f"• <code>/auth &lt;id&gt;</code> - Authorize Team User\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>Example:</i> <code>/batch 10 https://instagram.com/reel/xyz</code> (Starts directly from Peak Step 10 (+1,960 views))"
    )
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['schedule'])
def cmd_schedule(message):
    if not check_authorized(message):
        return
    lines = ["📋 <b>23-Step Views Schedule (PakFollowers 15k Total):</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
    for s in STEPS_DATA:
        lines.append(f"<b>Step {s['step']:02d}</b> ({s['label']}): <code>+{s['views']:,} Views</code>")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━\n<b>Total:</b> <code>{TOTAL_VIEWS:,} Views (10 Hours)</code>")
    lines.append("💡 Use <code>/batch &lt;step_no&gt; &lt;link&gt;</code> to start from any step!")
    send_safe_msg(message.chat.id, "\n".join(lines))

@bot.message_handler(commands=['balance'])
def cmd_balance(message):
    if not check_authorized(message):
        return
    bal = fetch_balance()
    txt = (
        f"💰 <b>Views Panel Balance:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🇵🇰 <b>PakFollowers:</b> <code>{bal}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['instant'])
def cmd_instant(message):
    if not check_authorized(message):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        send_safe_msg(message.chat.id, "⚠️ Usage: <code>/instant &lt;quantity&gt; &lt;instagram_link&gt;</code>\nExample: <code>/instant 1000 https://instagram.com/reel/xyz</code>")
        return
    try:
        qty = int(parts[1])
        if qty < 100:
            send_safe_msg(message.chat.id, "⚠️ Minimum quantity for Instant Views is 100.")
            return
        link = clean_instagram_url(parts[2].strip())
        send_safe_msg(message.chat.id, f"⏳ Placing Instant Order for <b>{qty:,} Views</b> on <code>{link}</code>...")
        success, res = place_views_order(link, qty)
        if success:
            send_safe_msg(message.chat.id, f"✅ <b>Order Placed Successfully!</b>\n🆔 Order ID: <code>#{res}</code>\n👁️ Quantity: <code>{qty:,} Views</code>")
        else:
            send_safe_msg(message.chat.id, f"❌ <b>Order Failed:</b> {res}")
    except ValueError:
        send_safe_msg(message.chat.id, "⚠️ Quantity must be a valid number.")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not check_authorized(message):
        return
    if not campaign_running:
        send_safe_msg(message.chat.id, "ℹ️ No Views campaign is currently running.")
        return
    info = current_campaign_info
    total_target = info.get('total_views_target', TOTAL_VIEWS)
    views_sent = info.get('views_sent', 0)
    pct = int((views_sent / total_target) * 100) if total_target > 0 else 100
    txt = (
        f"📊 <b>Views Campaign Status:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Link:</b> <code>{info.get('link', 'N/A')}</code>\n"
        f"📍 <b>Started From:</b> Step {info.get('start_step', 1)}\n"
        f"📍 <b>Current Step:</b> Step {info.get('current_step', 0)} / 23\n"
        f"👁️ <b>Views Sent:</b> <code>{views_sent:,} / {total_target:,}</code> ({pct}%)\n"
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
    send_safe_msg(message.chat.id, "⏳ Stopping Views campaign...")

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

# Parse link and step from command arguments
def parse_link_and_step(text_args):
    tokens = text_args.split()
    link = None
    step = 1

    for token in tokens:
        token_clean = token.strip("<>")
        if "instagram.com" in token_clean or "http://" in token_clean or "https://" in token_clean:
            link = clean_instagram_url(token_clean)
        elif token.isdigit():
            val = int(token)
            if 1 <= val <= 23:
                step = val

    return link, step

@bot.message_handler(commands=['run', 'batch'])
def cmd_run_or_batch(message):
    if not check_authorized(message):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        send_safe_msg(
            message.chat.id,
            "⚠️ <b>Usage:</b>\n"
            "• <code>/run &lt;link&gt;</code> (Starts from Step 1)\n"
            "• <code>/batch &lt;step_no&gt; &lt;link&gt;</code> (e.g. <code>/batch 5 https://instagram.com/reel/xyz</code>)"
        )
        return

    link, step = parse_link_and_step(args[1])
    if not link:
        send_safe_msg(message.chat.id, "⚠️ Valid Instagram link nahi mila!\nExample: <code>/batch 5 https://instagram.com/reel/xyz</code>")
        return

    start_views_campaign(message.chat.id, link, start_step=step)

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    if not check_authorized(message):
        return
    text = message.text.strip().strip("<>")
    if "instagram.com" in text or "http://" in text or "https://" in text:
        link, step = parse_link_and_step(text)
        start_views_campaign(message.chat.id, link, start_step=step)
    else:
        send_safe_msg(message.chat.id, "❓ Unknown command. Send an Instagram link or type /help.")

def start_views_campaign(chat_id, link, start_step=1):
    global campaign_running, stop_campaign_flag
    if campaign_running:
        send_safe_msg(chat_id, "⚠️ A Views campaign is already running! Use /stop first.")
        return
    campaign_running = True
    stop_campaign_flag = False
    th = threading.Thread(target=campaign_worker, args=(chat_id, link, start_step), daemon=True)
    th.start()

# =====================================================================
# 🌐 KEEP-ALIVE DUMMY HTTP SERVER (For Render Free Web Service)
# =====================================================================
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"PakFollowers Views Wave Bot is Active and Healthy!")
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
    print("🤖 Instagram Views Wave Bot (PakFollowers 15k / 23 Steps) Started...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)
