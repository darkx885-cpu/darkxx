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
# 🤖 BOT CONFIGURATION
# =====================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8966472325:AAHNDkup2W4Zo6ja_70eSiEI7zdPq-PF5mw")
bot = telebot.TeleBot(BOT_TOKEN)

# =====================================================================
# 🌐 YOYOMEDIA SMM PANEL CONFIGURATION (ONLY DRIP-FEED)
# =====================================================================
YOYO_PANEL_URL = "https://yoyomedia.com/api/v2"
YOYO_API_KEY = os.environ.get("YOYO_API_KEY", "cef0c6f45b80971e384b69f61608ab4a9e76ff52d7e14a3954ef19f44ea300d1")
YOYO_SERVICE_VIEWS = 3508  # Instagram Reel/Video Views [Best Views] [Non Drop]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded',
}

# =====================================================================
# 🌊 DRIP-FEED SETTINGS (125 Views Per Run | 16 Min Interval | 16 Min Delay)
# =====================================================================
CONFIG_FILE = "drip_config.json"

def load_drip_config():
    default_config = {
        "qty_per_run": 125,    # Har run me theek 125 views
        "runs": 8,             # 8 Runs (8 x 125 = 1,000 Views)
        "interval": 16,        # Har 16 minute me ek run (Panel Interval)
        "initial_delay": 16    # Link paste karne ke theek 16 min baad start
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                if "qty_per_run" not in cfg:
                    cfg["qty_per_run"] = 125
                return cfg
        except Exception:
            pass
    return default_config

def save_drip_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")

drip_config = load_drip_config()

# =====================================================================
# 👥 ADMIN & AUTHORIZATION
# =====================================================================
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
ALLOWED_USERS = [8207879798]

active_timers = {}

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
# 📡 YOYOMEDIA API FUNCTIONS
# =====================================================================
def fetch_balance():
    try:
        resp = requests.post(YOYO_PANEL_URL, data={"key": YOYO_API_KEY, "action": "balance"}, headers=HEADERS, timeout=12)
        data = resp.json()
        return f"{data.get('balance', 'N/A')} {data.get('currency', 'USD')}"
    except Exception as e:
        return f"Error ({e})"

def place_yoyo_dripfeed_order(link, quantity, runs, interval):
    try:
        payload = {
            "key": YOYO_API_KEY,
            "action": "add",
            "service": YOYO_SERVICE_VIEWS,
            "link": link,
            "quantity": quantity,
            "runs": runs,
            "interval": interval
        }
        resp = requests.post(YOYO_PANEL_URL, data=payload, headers=HEADERS, timeout=15)
        data = resp.json()
        if "order" in data:
            return True, data["order"]
        elif "error" in data:
            return False, data["error"]
        return False, str(data)
    except Exception as e:
        return False, str(e)

# =====================================================================
# ⏳ 16-MINUTE DELAY WORKER & ORDER TRIGGER
# =====================================================================
def execute_order_now(chat_id, link):
    qty_per_run = drip_config.get("qty_per_run", 125)
    r_runs = drip_config["runs"]
    i_interval = drip_config["interval"]
    actual_total = qty_per_run * r_runs
    total_hours = (r_runs * i_interval) / 60

    send_safe_msg(chat_id, f"⏳ Placing <b>{actual_total} Views Drip-Feed</b> on YoyoMedia...")
    success, order_res = place_yoyo_dripfeed_order(link, qty_per_run, r_runs, i_interval)

    if success:
        txt = (
            f"🎉 <b>Drip-Feed Order Successful!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>Order ID:</b> <code>#{order_res}</code>\n"
            f"🔗 <b>Reel:</b> <code>{link}</code>\n"
            f"👁️ <b>Total Views:</b> <code>{actual_total} Views</code>\n"
            f"🔁 <b>Runs:</b> <code>{r_runs} runs</code> ({qty_per_run} views/run)\n"
            f"⏱️ <b>Interval:</b> Har <code>{i_interval} minute</code> me\n"
            f"⌛ <b>Duration:</b> ~{total_hours:.1f} Hours Wave\n"
            f"🛡️ <b>Bot Score Protection:</b> Active (Safe S-Curve)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_safe_msg(chat_id, txt)
    else:
        send_safe_msg(chat_id, f"❌ <b>Drip-Feed Order Failed:</b>\n<code>{order_res}</code>")

def delay_timer_worker(chat_id, link, delay_mins):
    active_timers[chat_id] = {"cancel": False, "skip": False}
    seconds = delay_mins * 60

    while seconds > 0:
        if active_timers.get(chat_id, {}).get("cancel", False):
            send_safe_msg(chat_id, "🛑 <b>Order Cancelled!</b> Timer stop ho gaya hai.")
            del active_timers[chat_id]
            return
        if active_timers.get(chat_id, {}).get("skip", False):
            break
        chunk = min(seconds, 3)
        time.sleep(chunk)
        seconds -= chunk

    if active_timers.get(chat_id, {}).get("cancel", False):
        del active_timers[chat_id]
        return

    send_safe_msg(
        chat_id,
        f"🚨🚨 <b>{delay_mins} MINUTE HO GAYE HAIN!</b> 🚨🚨\n"
        f"Abhi YoyoMedia par Drip-Feed order lag raha hai... 🚀"
    )
    execute_order_now(chat_id, link)
    if chat_id in active_timers:
        del active_timers[chat_id]

def start_drip_pipeline(chat_id, raw_url):
    clean_url = clean_instagram_url(raw_url)
    delay_mins = drip_config.get("initial_delay", 16)
    qty_per_run = drip_config.get("qty_per_run", 125)
    r_runs = drip_config["runs"]
    i_interval = drip_config["interval"]
    actual_total = qty_per_run * r_runs

    target_utc = datetime.now(timezone.utc) + timedelta(minutes=delay_mins)
    target_ist = get_ist_time_str(target_utc)

    if chat_id in active_timers:
        active_timers[chat_id]["cancel"] = True
        time.sleep(1)

    th = threading.Thread(target=delay_timer_worker, args=(chat_id, clean_url, delay_mins), daemon=True)
    th.start()

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_skip = types.InlineKeyboardButton("⚡ Skip (Abhi Lagao)", callback_data=f"skip|{clean_url}")
    btn_cancel = types.InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel|{clean_url}")
    markup.add(btn_skip, btn_cancel)

    msg_txt = (
        f"🎯 <b>Instagram Reel Link Received!</b>\n"
        f"<code>{clean_url}</code>\n\n"
        f"⏳ <b>{delay_mins}-Minute Delay Timer Shuru!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <b>Order Execution Time:</b> <b>{target_ist} IST</b> (Theek {delay_mins} min baad)\n"
        f"🌊 <b>Drip Plan:</b> {actual_total} Views ({r_runs} runs x {i_interval}m interval)\n"
        f"📦 <b>Per Run:</b> <b>{qty_per_run} views/run</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"😴 <i>Aap aaram karein! Theek {delay_mins} minute baad bot khud YoyoMedia par order lagayega aur phone par alert bhejega! 🔔</i>"
    )
    send_safe_msg(chat_id, msg_txt, reply_markup=markup)

# =====================================================================
# ⚙️ SETTINGS MENU
# =====================================================================
def get_settings_markup():
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn_d15 = types.InlineKeyboardButton("⏱️ Delay: 15m", callback_data="cfg_delay_15")
    btn_d16 = types.InlineKeyboardButton("⏱️ Delay: 16m", callback_data="cfg_delay_16")
    btn_d18 = types.InlineKeyboardButton("⏱️ Delay: 18m", callback_data="cfg_delay_18")

    btn_i16 = types.InlineKeyboardButton("🔄 Gap: 16m", callback_data="cfg_interval_16")
    btn_i30 = types.InlineKeyboardButton("🔄 Gap: 30m", callback_data="cfg_interval_30")
    btn_i45 = types.InlineKeyboardButton("🔄 Gap: 45m", callback_data="cfg_interval_45")
    
    btn_r8 = types.InlineKeyboardButton("🔁 8 Runs (1k Views)", callback_data="cfg_runs_8")
    btn_r12 = types.InlineKeyboardButton("🔁 12 Runs (1.5k)", callback_data="cfg_runs_12")
    btn_r16 = types.InlineKeyboardButton("🔁 16 Runs (2k)", callback_data="cfg_runs_16")

    markup.row(btn_d15, btn_d16, btn_d18)
    markup.row(btn_i16, btn_i30, btn_i45)
    markup.row(btn_r8, btn_r12, btn_r16)
    return markup

def format_settings_text():
    qty = drip_config.get("qty_per_run", 125)
    r = drip_config["runs"]
    i = drip_config["interval"]
    d = drip_config.get("initial_delay", 16)
    actual_total = qty * r
    hours = (r * i) / 60
    return (
        f"⚙️ <b>Drip-Feed Live Settings:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ <b>Initial Delay:</b> <code>{d} minutes</code> (Link aane ke {d} min baad)\n"
        f"📦 <b>Views per run:</b> <code>{qty} views</code>\n"
        f"🔁 <b>Number of Runs:</b> <code>{r} runs</code>\n"
        f"⏱️ <b>Interval (Runs Gap):</b> <code>{i} minutes</code>\n"
        f"👁️ <b>Total Views:</b> <code>{actual_total} Views</code>\n"
        f"⌛ <b>Total Campaign Duration:</b> <code>~{hours:.1f} Hours</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Neeche buttons par tap karke kisi bhi waqt badal sakte hain:</i>"
    )

# =====================================================================
# 💬 TELEGRAM COMMANDS
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    if not check_authorized(message):
        send_safe_msg(message.chat.id, "⛔ Access Denied.")
        return
    d = drip_config.get("initial_delay", 16)
    r = drip_config.get("runs", 8)
    i = drip_config.get("interval", 16)
    q = drip_config.get("qty_per_run", 125)
    tot = q * r
    txt = (
        f"🌊 <b>Instagram Drip-Feed Automation Bot</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>Ye Bot Kaise Kaam Karta Hai?</b>\n"
        f"1. Instagram par reel post karein.\n"
        f"2. <b>Seedha Reel ka link yahan bhej dein!</b>\n"
        f"3. Bot theek <b>{d} minute ka timer</b> chalayega aur {d} min baad <b>YoyoMedia par Drip-Feed Order (#3508)</b> khud laga dega!\n\n"
        f"⚙️ <b>Active Setup:</b>\n"
        f"• Per Run Views: <b>{q} Views</b>\n"
        f"• Number of Runs: <b>{r} Runs</b>\n"
        f"• Interval: Har <b>{i} Minute</b> me\n"
        f"• Total Views: <b>{tot} Views</b>\n\n"
        f"📌 <b>Commands:</b>\n"
        f"• <code>/settings</code> - Runs, Delay & Interval change karein\n"
        f"• <code>/balance</code> - YoyoMedia wallet balance\n"
        f"• <code>/stop</code> - Active timer cancel karein\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>Bas Instagram Reel ka link paste karo, baaki kaam bot karega!</i>"
    )
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['settings', 'config'])
def cmd_settings(message):
    if not check_authorized(message):
        return
    send_safe_msg(message.chat.id, format_settings_text(), reply_markup=get_settings_markup())

@bot.message_handler(commands=['balance'])
def cmd_balance(message):
    if not check_authorized(message):
        return
    bal = fetch_balance()
    send_safe_msg(message.chat.id, f"💰 <b>YoyoMedia Wallet Balance:</b> <code>{bal}</code>")

@bot.message_handler(commands=['stop', 'cancel'])
def cmd_stop(message):
    if not check_authorized(message):
        return
    if message.chat.id in active_timers:
        active_timers[message.chat.id]["cancel"] = True
        send_safe_msg(message.chat.id, "🛑 Active timer cancel kar diya gaya hai.")
    else:
        send_safe_msg(message.chat.id, "ℹ️ Koi active timer nahi chal raha hai.")

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
# 🔗 DIRECT INSTAGRAM LINK HANDLER (100% AUTOMATIC)
# =====================================================================
@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    if not check_authorized(message):
        return
    text = message.text.strip()
    if "instagram.com" in text:
        start_drip_pipeline(message.chat.id, text)
    else:
        send_safe_msg(message.chat.id, "❓ Unknown message. Kripya Instagram Reel ka link paste karein ya /help type karein.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    bot.answer_callback_query(call.id)

    if data.startswith("cfg_"):
        parts = data.split("_")
        key = parts[1]
        val = int(parts[2])
        if key == "interval":
            drip_config["interval"] = val
        elif key == "runs":
            drip_config["runs"] = val
        elif key == "delay":
            drip_config["initial_delay"] = val
        save_drip_config(drip_config)

        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"✅ <b>Setting Updated!</b>\n\n{format_settings_text()}",
                parse_mode="HTML",
                reply_markup=get_settings_markup()
            )
        except Exception:
            send_safe_msg(chat_id, f"✅ <b>Setting Updated!</b>\n\n{format_settings_text()}", reply_markup=get_settings_markup())
        return

    if data.startswith("skip|"):
        link = data.split("|", maxsplit=1)[1]
        if chat_id in active_timers:
            active_timers[chat_id]["skip"] = True
        else:
            execute_order_now(chat_id, link)
    elif data.startswith("cancel|"):
        if chat_id in active_timers:
            active_timers[chat_id]["cancel"] = True
            send_safe_msg(chat_id, "🛑 Order cancelled.")

# =====================================================================
# 🌐 KEEP-ALIVE DUMMY HTTP SERVER (For Render Free Web Service)
# =====================================================================
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Drip-Feed Bot is Active and Healthy!")
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
    print("🌊 Pure Instagram Drip-Feed Bot Started (125 Views / 16 Min Interval)...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)
