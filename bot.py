import telebot
from telebot import types
import requests
import time
import threading
import os
import sys
import socketserver
from urllib.parse import urlparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# =====================================================================
# 🤖 BOT CONFIGURATION (@Darkzzzo_bot)
# =====================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8901542723:AAFd54ZpaMc9DyOdqEKp6KFsEXlFMzgygYU")
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
ALLOWED_USERS = [8207879798]

# =====================================================================
# 🌐 YOYOMEDIA.COM PANEL
# =====================================================================
PANEL_URL = "https://yoyomedia.com/api/v2"
API_KEY = "1504b2badaa2238f4dc062d7b36264d2d53687386a63e9ef706befa91878d3d6"

SERVICE_INSTA_VIEWS = 4322   # Instagram Video/Reel Views [100M] [Fast]
SERVICE_INSTA_LIKES = 4731   # Instagram Likes [100k] [10K P/H]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded',
}

# =====================================================================
# 🌊 8-BATCH SCHEDULE (2,101 Views + 42 Likes | 5 Hr 15 Min)
# =====================================================================
SCHEDULE_8_BATCHES = [
    (0,    293,  0,  "Batch #1: Initial Hook (+293 Views)"),
    (15,   254,  0,  "Batch #2: Follow-up Surge (+254 Views)"),
    (135,  365, 15,  "Batch #3: Mid Surge (+365 Views) + Wave 1 (+15 Likes)"),
    (210,  257,  0,  "Batch #4: Exploration Push (+257 Views)"),
    (240,  209, 11,  "Batch #5: Steady Momentum (+209 Views) + Wave 2 (+11 Likes)"),
    (270,  357,  0,  "Batch #6: Viral Climb (+357 Views)"),
    (300,  207, 16,  "Batch #7: Final Surge (+207 Views) + Wave 3 (+16 Likes)"),
    (315,  159,  0,  "Batch #8: Soft Landing (+159 Views)"),
]

TARGET_VIEWS = sum(item[1] for item in SCHEDULE_8_BATCHES)
TARGET_LIKES = sum(item[2] for item in SCHEDULE_8_BATCHES)

active_tasks = {}

# =====================================================================
# HELPERS
# =====================================================================
def send_safe_msg(chat_id, text, disable_web_page_preview=True, reply_markup=None):
    try:
        return bot.send_message(chat_id, text, parse_mode="HTML",
                                disable_web_page_preview=disable_web_page_preview,
                                reply_markup=reply_markup)
    except Exception as e:
        print(f"Message send error: {e}")
        try:
            clean = text.replace("<b>","").replace("</b>","").replace("<code>","").replace("</code>","").replace("<i>","").replace("</i>","")
            return bot.send_message(chat_id, clean, disable_web_page_preview=disable_web_page_preview)
        except:
            return None

def check_authorized(message):
    global ADMIN_ID, ALLOWED_USERS
    user_id = message.chat.id
    if ADMIN_ID == 0:
        ADMIN_ID = user_id
        if ADMIN_ID not in ALLOWED_USERS:
            ALLOWED_USERS.append(ADMIN_ID)
        return True
    return user_id == ADMIN_ID or user_id in ALLOWED_USERS

def clean_instagram_url(text):
    for word in text.split():
        if "instagram.com" in word:
            url = word.strip().strip('<>').strip('"').strip("'")
            if not url.startswith("http"):
                url = "https://" + url
            try:
                parsed = urlparse(url)
                clean_path = parsed.path.rstrip('/') + '/'
                return f"https://www.instagram.com{clean_path}"
            except:
                return url
    return None

def fetch_balance():
    try:
        resp = requests.post(PANEL_URL, data={"key": API_KEY, "action": "balance"},
                             headers=HEADERS, timeout=12)
        data = resp.json()
        return f"${data.get('balance','N/A')} {data.get('currency','USD')}"
    except Exception as e:
        return f"Error ({e})"

def place_order(service_id, link, quantity):
    try:
        payload = {"key": API_KEY, "action": "add",
                   "service": service_id, "link": link, "quantity": quantity}
        resp = requests.post(PANEL_URL, data=payload, headers=HEADERS, timeout=15)
        data = resp.json()
        if "order" in data:
            return True, data["order"]
        elif "error" in data:
            return False, data["error"]
        return False, str(data)
    except Exception as e:
        return False, str(e)

def place_order_with_smart_retry(service_id, link, quantity, chat_id=None,
                                  step_info="", max_retries=6, retry_delay=30):
    for attempt in range(max_retries):
        ok, res = place_order(service_id, link, quantity)
        if ok:
            return True, res
        err_str = str(res).lower()
        if "active order" in err_str or "wait" in err_str or "already have" in err_str:
            if chat_id and attempt == 0:
                send_safe_msg(chat_id, f"⏳ <i>{step_info}: Retrying...</i>")
            time.sleep(retry_delay)
        else:
            return False, res
    return False, res

# =====================================================================
# 🌊 ORGANIC WORKER
# =====================================================================
def insta_organic_worker(chat_id, link):
    active_tasks[chat_id] = {
        "cancel": False, "skip": False, "link": link,
        "views_placed": 0, "likes_placed": 0, "step": 1,
        "start_time": datetime.now().strftime("%I:%M %p")
    }
    start_time = time.time()
    total_views = 0
    total_likes = 0
    total_steps = len(SCHEDULE_8_BATCHES)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚡ Skip Wait", callback_data="cmd_skip"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cmd_cancel")
    )

    send_safe_msg(
        chat_id,
        f"🚀 <b>8-BATCH CAMPAIGN STARTED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Reel:</b> <code>{link}</code>\n"
        f"🎯 <b>Views:</b> {TARGET_VIEWS} | ❤️ <b>Likes:</b> {TARGET_LIKES}\n"
        f"⏱️ <b>Duration:</b> 5 Hr 15 Min\n"
        f"🌐 <b>Panel:</b> YoYoMedia.com\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Batch #1 abhi place ho raha hai...</i>",
        reply_markup=markup
    )

    for idx, (target_min, v_qty, l_qty, phase_name) in enumerate(SCHEDULE_8_BATCHES):
        step_num = idx + 1
        target_sec = target_min * 60
        if chat_id in active_tasks:
            active_tasks[chat_id]["step"] = step_num

        while True:
            if active_tasks.get(chat_id, {}).get("cancel", False):
                send_safe_msg(chat_id, "🛑 <b>Campaign cancelled.</b>")
                active_tasks.pop(chat_id, None)
                return
            elapsed = time.time() - start_time
            if elapsed >= target_sec or active_tasks.get(chat_id, {}).get("skip", False):
                if active_tasks.get(chat_id, {}).get("skip", False):
                    active_tasks[chat_id]["skip"] = False
                break
            time.sleep(3)

        views_str = ""
        if v_qty > 0:
            ok_v, res_v = place_order_with_smart_retry(
                SERVICE_INSTA_VIEWS, link, v_qty, chat_id=chat_id,
                step_info=f"Views #{step_num}")
            if ok_v:
                total_views += v_qty
                active_tasks[chat_id]["views_placed"] = total_views
                views_str = f"👁️ <b>+{v_qty} Views</b> (Order: <code>#{res_v}</code>)"
            else:
                views_str = f"⚠️ <b>Views Failed:</b> <code>{res_v}</code>"

        likes_str = ""
        if l_qty > 0:
            ok_l, res_l = place_order_with_smart_retry(
                SERVICE_INSTA_LIKES, link, l_qty, chat_id=chat_id,
                step_info=f"Likes #{step_num}")
            if ok_l:
                total_likes += l_qty
                active_tasks[chat_id]["likes_placed"] = total_likes
                likes_str = f"❤️ <b>+{l_qty} Likes</b> (Order: <code>#{res_l}</code>)"
            else:
                likes_str = f"⚠️ <b>Likes Failed:</b> <code>{res_l}</code>"

        details = "\n".join([x for x in [views_str, likes_str] if x])
        send_safe_msg(
            chat_id,
            f"✅ <b>Batch #{step_num}/{total_steps} Done!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 {phase_name}\n"
            f"{details}\n"
            f"📈 <code>{total_views}/{TARGET_VIEWS} Views</code> | <code>{total_likes}/{TARGET_LIKES} Likes</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=markup
        )

    send_safe_msg(
        chat_id,
        f"🎉 <b>CAMPAIGN COMPLETE!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <code>{link}</code>\n"
        f"👁️ <b>Views:</b> {total_views}/{TARGET_VIEWS}\n"
        f"❤️ <b>Likes:</b> {total_likes}/{TARGET_LIKES}\n"
        f"🏁 <b>Status:</b> All Batches Complete! 🚀"
    )
    active_tasks.pop(chat_id, None)

def start_pipeline(chat_id, clean_url):
    if chat_id in active_tasks:
        active_tasks[chat_id]["cancel"] = True
        time.sleep(1)
    threading.Thread(target=insta_organic_worker, args=(chat_id, clean_url), daemon=True).start()

# =====================================================================
# COMMANDS
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    if not check_authorized(message):
        send_safe_msg(message.chat.id, "⛔ Access Denied.")
        return
    send_safe_msg(message.chat.id,
        f"🤖 <b>Darkzzzo 8-Batch Bot</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 {TARGET_VIEWS} Views + {TARGET_LIKES} Likes\n"
        f"⏳ 8 Batches | 5 Hr 15 Min\n"
        f"🌐 YoYoMedia.com\n\n"
        f"<code>/status</code> — Live progress\n"
        f"<code>/balance</code> — Wallet balance\n"
        f"<code>/stop</code> — Cancel campaign\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Instagram Reel link paste karo, bot start ho jayega!")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not check_authorized(message):
        return
    info = active_tasks.get(message.chat.id)
    if info:
        send_safe_msg(message.chat.id,
            f"📊 <b>LIVE STATUS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <code>{info['link']}</code>\n"
            f"📍 Batch: #{info['step']}/{len(SCHEDULE_8_BATCHES)}\n"
            f"👁️ Views: {info['views_placed']}/{TARGET_VIEWS}\n"
            f"❤️ Likes: {info['likes_placed']}/{TARGET_LIKES}\n"
            f"⏰ Started: {info['start_time']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━")
    else:
        send_safe_msg(message.chat.id, "ℹ️ Koi campaign nahi chal rahi.")

@bot.message_handler(commands=['balance'])
def cmd_balance(message):
    if not check_authorized(message):
        return
    send_safe_msg(message.chat.id,
        f"💰 <b>Balance:</b> <code>{fetch_balance()}</code>")

@bot.message_handler(commands=['stop', 'cancel'])
def cmd_stop(message):
    if not check_authorized(message):
        return
    if message.chat.id in active_tasks:
        active_tasks[message.chat.id]["cancel"] = True
        send_safe_msg(message.chat.id, "🛑 Campaign cancel kar diya gaya.")
    else:
        send_safe_msg(message.chat.id, "ℹ️ Koi campaign nahi chal rahi.")

@bot.message_handler(func=lambda msg: True)
def handle_all(message):
    if not check_authorized(message):
        return
    url = clean_instagram_url(message.text)
    if url:
        start_pipeline(message.chat.id, url)
    else:
        send_safe_msg(message.chat.id, "❓ Valid Instagram Reel link paste karo.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    if call.data == "cmd_skip" and chat_id in active_tasks:
        active_tasks[chat_id]["skip"] = True
        send_safe_msg(chat_id, "⚡ Skip! Agla batch aa raha hai...")
    elif call.data == "cmd_cancel" and chat_id in active_tasks:
        active_tasks[chat_id]["cancel"] = True
        send_safe_msg(chat_id, "🛑 Campaign cancelled.")

# =====================================================================
# KEEP-ALIVE SERVER
# =====================================================================
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Darkzzzo Bot is Online!")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        with socketserver.TCPServer(("", port), DummyServer) as httpd:
            httpd.serve_forever()
    except Exception as e:
        print(f"Server error: {e}")

# =====================================================================
# MAIN
# =====================================================================
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    print(f"🤖 Darkzzzo Bot Started | Views: {TARGET_VIEWS} | Likes: {TARGET_LIKES}")
    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=25)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)
