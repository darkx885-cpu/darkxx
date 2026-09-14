import telebot
import requests
import time
import threading
import os
import socketserver
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler

# Bot Token & Config
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8959503657:AAFutbdLkq8YW9y6d5C3gqcdmNk0UzDd2yI")
bot = telebot.TeleBot(BOT_TOKEN)

API_KEY = "74d4962ec589605651ecff3c2ab0b9dda47785b2b327303111d0d8920bdd1aed"  # ✅ New API Key
API_URL = "https://yoyomedia.com/api/v2"

SERVICE_VIEWS = 4480
SERVICE_LIKES = 4731

ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

campaign_running = False
stop_campaign_flag = False
current_campaign_info = {}

# Views & Likes Quantities for 8 Steps
STEPS_DATA = [
    {"views": 117,  "likes": 0},   # Step 1
    {"views": 348,  "likes": 0},   # Step 2
    {"views": 765,  "likes": 0},   # Step 3
    {"views": 1630, "likes": 10},  # Step 4
    {"views": 2404, "likes": 12},  # Step 5
    {"views": 2736, "likes": 15},  # Step 6
    {"views": 2896, "likes": 16},  # Step 7
    {"views": 3003, "likes": 17},  # Step 8
]

def check_admin(message):
    global ADMIN_ID
    if ADMIN_ID == 0:
        ADMIN_ID = message.chat.id
    return message.chat.id == ADMIN_ID

def place_order(service_id, link, quantity):
    if quantity <= 0:
        return None
    payload = {
        "key": API_KEY, "action": "add",
        "service": service_id, "link": link, "quantity": quantity
    }
    try:
        res = requests.post(API_URL, data=payload, timeout=30)  # ✅ timeout fix
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def get_balance():
    payload = {"key": API_KEY, "action": "balance"}
    try:
        res = requests.post(API_URL, data=payload, timeout=30)  # ✅ timeout fix
        data = res.json()
        if "balance" in data:
            usd_bal = float(data['balance'])
            inr_bal = usd_bal * 83.50
            return (
                f"💵 <b>Panel Balance:</b>\n"
                f"🇮🇳 <b>₹{inr_bal:.2f} INR</b>\n"
                f"🇺🇸 <code>${usd_bal:.2f} USD</code>"
            )
        else:
            return "❌ Unable to fetch balance."
    except Exception as e:
        return f"❌ Error fetching balance: {e}"

def get_ist_now():
    # ✅ Fixed: datetime.utcnow() deprecated → use timezone.utc
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5, minutes=30)

def smart_sleep(seconds):
    global stop_campaign_flag
    elapsed = 0
    while elapsed < seconds:
        if stop_campaign_flag:
            break
        chunk = min(0.5, seconds - elapsed)
        time.sleep(chunk)
        elapsed += chunk

def run_campaign(chat_id, link, start_time_str, start_step):
    global campaign_running, stop_campaign_flag, current_campaign_info
    campaign_running = True
    stop_campaign_flag = False

    now = get_ist_now()

    # ✅ Smart Time Parsing
    if start_time_str:
        try:
            sh, sm = map(int, start_time_str.split(":"))
            start_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            if start_dt < now and (now - start_dt).total_seconds() > 300:
                start_dt = start_dt + timedelta(days=1)
        except Exception:
            start_dt = now
    else:
        start_dt = now

    steps_to_run = STEPS_DATA[start_step - 1:]

    current_campaign_info = {
        "link": link,
        "start_time": start_dt.strftime('%I:%M %p'),
        "completed_steps": start_step - 1,
        "total_steps": 8
    }

    msg_start = (
        f"🚀 <b>Campaign Scheduled!</b>\n"
        f"🔗 <b>Link:</b> {link}\n"
        f"⏰ <b>Start Time:</b> <code>{start_dt.strftime('%I:%M %p')} IST</code>\n"
        f"🔢 <b>Starting from Step:</b> <code>{start_step}</code>"
    )
    bot.send_message(chat_id, msg_start, parse_mode="HTML")

    for relative_idx, step in enumerate(steps_to_run):
        if stop_campaign_flag:
            break

        actual_step_num = start_step + relative_idx
        target_dt = start_dt + timedelta(hours=relative_idx)
        target_time_str = target_dt.strftime("%I:%M %p")

        current_campaign_info["completed_steps"] = actual_step_num - 1
        current_campaign_info["next_step_time"] = target_time_str

        v_qty = step["views"]
        l_qty = step["likes"]

        # ✅ Wait loop with max 15s chunks (prevents Render freeze)
        while True:
            if stop_campaign_flag:
                break
            current_ist = get_ist_now()
            if current_ist >= target_dt:
                msg = f"⏰ <b>Step {actual_step_num}/8 ({target_time_str} IST)</b>\n"

                if v_qty > 0:
                    v_res = place_order(SERVICE_VIEWS, link, v_qty)
                    if v_res and "order" in v_res:
                        msg += f"👁️ Views (+{v_qty}): ✅ [ID: {v_res['order']}]\n"
                    else:
                        msg += f"👁️ Views (+{v_qty}): ❌ Failed\n"

                if l_qty > 0:
                    l_res = place_order(SERVICE_LIKES, link, l_qty)
                    if l_res and "order" in l_res:
                        msg += f"❤️ Likes (+{l_qty}): ✅ [ID: {l_res['order']}]"
                    else:
                        msg += f"❤️ Likes (+{l_qty}): ❌ Failed"

                bot.send_message(chat_id, msg, parse_mode="HTML")
                smart_sleep(5)
                break
            else:
                # ✅ Max 15s sleep chunks — prevents Render thread freeze
                wait_seconds = (target_dt - current_ist).total_seconds()
                sleep_chunk = min(wait_seconds, 15)
                smart_sleep(sleep_chunk)

    if stop_campaign_flag:
        bot.send_message(chat_id, "🛑 <b>Campaign Stopped!</b>", parse_mode="HTML")
    else:
        bot.send_message(chat_id, "🎉 <b>Campaign Completed Successfully!</b>", parse_mode="HTML")

    campaign_running = False

# --- BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not check_admin(message):
        bot.reply_to(message, "⛔ Access Denied!")
        return
    welcome_txt = (
        "👋 <b>Welcome Boss! Campaign Bot</b>\n\n"
        "📌 <b>Commands:</b>\n"
        "🔹 <code>/run &lt;link&gt; &lt;time&gt; &lt;step&gt;</code>\n"
        "   <i>Example:</i> <code>/run https://reel_link 10:30 3</code>\n"
        "   <i>Example:</i> <code>/run https://reel_link 3</code> (abhi se step 3)\n\n"
        "🔹 <code>/balance</code> - Balance check\n"
        "🔹 <code>/status</code> - Campaign status\n"
        "🔹 <code>/stop</code> - Stop campaign"
    )
    bot.reply_to(message, welcome_txt, parse_mode="HTML")

@bot.message_handler(commands=['balance'])
def handle_balance(message):
    if not check_admin(message):
        return
    bot.reply_to(message, get_balance(), parse_mode="HTML")

@bot.message_handler(commands=['status'])
def handle_status(message):
    if not check_admin(message):
        return
    if campaign_running:
        info = (
            f"📊 <b>Campaign Status:</b>\n\n"
            f"🔗 {current_campaign_info.get('link')}\n"
            f"📈 Steps: {current_campaign_info.get('completed_steps')}/8\n"
            f"⏰ Next: {current_campaign_info.get('next_step_time', 'Now')}"
        )
    else:
        info = "ℹ️ No campaign running."
    bot.reply_to(message, info, parse_mode="HTML")

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    global stop_campaign_flag, campaign_running
    if not check_admin(message):
        return
    if campaign_running:
        stop_campaign_flag = True
        bot.reply_to(message, "🛑 <b>Stopping...</b>", parse_mode="HTML")
    else:
        bot.reply_to(message, "ℹ️ No active campaign.")

@bot.message_handler(commands=['run'])
def handle_run(message):
    if not check_admin(message):
        return
    global campaign_running
    if campaign_running:
        bot.reply_to(message, "⚠️ Campaign already running! Use /stop first.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Usage: <code>/run &lt;link&gt; &lt;time&gt; &lt;step&gt;</code>", parse_mode="HTML")
        return

    link = parts[1]
    start_time_str = None
    start_step = 1

    if len(parts) == 3:
        # ✅ Smart Parser: /run link TIME_OR_STEP
        param = parts[2]
        if ":" in param:
            start_time_str = param  # It's a time like "10:30"
        else:
            try:
                start_step = int(param)  # It's a step number
            except ValueError:
                start_step = 1

    elif len(parts) >= 4:
        # /run link time step
        start_time_str = parts[2]
        try:
            start_step = int(parts[3])
        except ValueError:
            start_step = 1

    if start_step < 1 or start_step > 8:
        start_step = 1

    threading.Thread(
        target=run_campaign,
        args=(message.chat.id, link, start_time_str, start_step),
        daemon=True
    ).start()

# --- KEEP ALIVE SERVER ---
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b"OK")  # ✅ Minimal response — no "output too large"

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', '2')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # ✅ Logs mute — output too large fix!

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), DummyServer) as httpd:
        httpd.serve_forever()

# ✅ Self-ping thread — Render ko jaagna rakhta hai
def self_ping():
    time.sleep(30)  # Wait for server to start
    while True:
        try:
            port = int(os.environ.get("PORT", 8080))
            urllib.request.urlopen(f"http://localhost:{port}", timeout=10)
        except Exception:
            pass  # ✅ Timeout/error aaye toh crash mat karo
        time.sleep(180)  # Har 3 minute

threading.Thread(target=keep_alive, daemon=True).start()
threading.Thread(target=self_ping, daemon=True).start()

print("🤖 Bot is Active!")
while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Reconnecting: {e}")
        time.sleep(5)
