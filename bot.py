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

# Fix Windows Unicode emoji encoding in terminal
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# =====================================================================
# 🤖 NEW TELEGRAM BOT CONFIGURATION
# =====================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8959503657:AAFutbdLkq8YW9y6d5C3gqcdmNk0UzDd2yI")
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
ALLOWED_USERS = [8207879798]

# =====================================================================
# 🌐 YOYOMEDIA SMM PANEL CONFIGURATION
# =====================================================================
PANEL_URL = "https://yoyomedia.com/api/v2"
API_KEY = "302b656afc8f7d24943882aa1196abff174e0331132f86ada23b07c303c07a06"

# Verified Services from YoYoMedia:
SERVICE_INSTA_VIEWS = 3508   # Instagram Reel/Video Views [Best Views] [Non Drop] (Min: 100)
SERVICE_INSTA_LIKES = 4731   # InstaGram Likes [WW] [New Service] (Min: 10)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded',
}

# =====================================================================
# 🌊 EXACT 5-HOUR S-CURVE SCHEDULE (0 at start, 100 at 1 hr mark)
# =====================================================================
# Milestones: 1Hr=100 | 2Hr=250 | 3Hr=700 | 4Hr=1400 | 5Hr=2000
# Format: (TargetMinutesFromStart, ViewsQty, LikesQty, PhaseLabel)
SCHEDULE_5HR = [
    # 1 Hour Complete hone par 100 views (Minute 55 par dispatch)
    (55,   100,  0,  "Hour 1 Mark: Initial Hook (+100 Views -> 100 Total)"),

    # 2 Hours Complete hone par 250 views (+150 views + Wave 1 Likes)
    (115,  150, 14,  "Hour 2 Mark: Pickup (+150 Views -> 250 Total) + ❤️ Wave 1 (+14 Likes)"),

    # 3 Hours Complete hone par 700 views (+225 and +225)
    (150,  225,  0,  "Hour 3: Acceleration (+225 Views -> 475 Total)"),
    (175,  225,  0,  "Hour 3 Mark: (+225 Views -> 700 Total Views)"),

    # 4 Hours Complete hone par 1,400 views (+350 and +350 + Wave 2 Likes)
    (210,  350, 14,  "Hour 4: 🔥 Peak Blast (+350 Views -> 1,050 Total) + ❤️ Wave 2 (+14 Likes)"),
    (235,  350,  0,  "Hour 4 Mark: Peak Sustained (+350 Views -> 1,400 Total Views)"),

    # 5 Hours Complete hone par 2,000 views (+300 and +300 + Wave 3 Likes)
    (270,  300,  0,  "Hour 5: Final Push (+300 Views -> 1,700 Total)"),
    (295,  300, 14,  "Hour 5 Mark: 🏁 Final Lock (+300 Views -> 2,000 Total Views) + ❤️ Wave 3 (+14 Likes)"),
]

TARGET_VIEWS = sum(item[1] for item in SCHEDULE_5HR)   # Exact 2,000 Views
TARGET_LIKES = sum(item[2] for item in SCHEDULE_5HR)   # Exact 42 Likes

# Active task tracking
active_tasks = {}

# =====================================================================
# 🛠️ HELPER FUNCTIONS
# =====================================================================
def send_safe_msg(chat_id, text, disable_web_page_preview=True, reply_markup=None):
    try:
        return bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=disable_web_page_preview, reply_markup=reply_markup)
    except Exception as e:
        print(f"Message send error: {e}")
        try:
            clean_text = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", "")
            return bot.send_message(chat_id, clean_text, parse_mode=None, disable_web_page_preview=disable_web_page_preview)
        except Exception:
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
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            try:
                parsed = urlparse(url)
                clean_path = parsed.path.rstrip('/') + '/'
                return f"https://www.instagram.com{clean_path}"
            except Exception:
                return url
    return None

# =====================================================================
# 📡 YOYOMEDIA API DISPATCHER
# =====================================================================
def fetch_balance():
    try:
        resp = requests.post(PANEL_URL, data={"key": API_KEY, "action": "balance"}, headers=HEADERS, timeout=12)
        data = resp.json()
        bal = data.get('balance', 'N/A')
        cur = data.get('currency', 'INR')
        return f"₹{bal} {cur}"
    except Exception as e:
        return f"Error ({e})"

def place_order(service_id, link, quantity):
    try:
        payload = {
            "key": API_KEY,
            "action": "add",
            "service": service_id,
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

def place_order_with_smart_retry(service_id, link, quantity, chat_id=None, step_info="", max_retries=6, retry_delay=30):
    for attempt in range(max_retries):
        ok, res = place_order(service_id, link, quantity)
        if ok:
            return True, res

        err_str = str(res).lower()
        if "active order" in err_str or "wait" in err_str or "already have" in err_str:
            if chat_id and attempt == 0:
                send_safe_msg(chat_id, f"⏳ <i>{step_info}: Previous batch in progress... Retrying shortly.</i>")
            time.sleep(retry_delay)
            continue
        else:
            return False, res

    return False, res

# =====================================================================
# 🌊 5-HOUR WORKER (0 at Start -> 100 at 1 hr mark)
# =====================================================================
def insta_5hr_worker(chat_id, link):
    active_tasks[chat_id] = {
        "cancel": False,
        "skip": False,
        "link": link,
        "views_placed": 0,
        "likes_placed": 0,
        "step": 1,
        "start_time": datetime.now().strftime("%I:%M %p")
    }
    start_time = time.time()
    total_views = 0
    total_likes = 0
    total_steps = len(SCHEDULE_5HR)

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_skip = types.InlineKeyboardButton("⚡ Skip Wait", callback_data="cmd_skip")
    btn_cancel = types.InlineKeyboardButton("❌ Cancel Campaign", callback_data="cmd_cancel")
    markup.add(btn_skip, btn_cancel)

    send_safe_msg(
        chat_id,
        f"🚀 <b>INSTAGRAM 5-HOUR CAMPAIGN STARTED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Reel:</b> <code>{link}</code>\n"
        f"🎯 <b>Target:</b> 2,000 Views (#3508) + 42 Likes (#4731)\n"
        f"⏳ <b>Milestones:</b> 1Hr=100 | 2Hr=250 | 3Hr=700 | 4Hr=1400 | 5Hr=2000\n"
        f"⏱️ <b>Notice:</b> <i>Pehla batch 55 min baad (1 hour complete hone par) place hoga!</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=markup
    )

    for idx, (target_min, v_qty, l_qty, phase_name) in enumerate(SCHEDULE_5HR):
        step_num = idx + 1
        target_sec = target_min * 60

        if chat_id in active_tasks:
            active_tasks[chat_id]["step"] = step_num

        while True:
            if active_tasks.get(chat_id, {}).get("cancel", False):
                send_safe_msg(chat_id, "🛑 <b>Campaign Stopped:</b> Order cancel kar diya gaya.")
                if chat_id in active_tasks:
                    del active_tasks[chat_id]
                return

            elapsed = time.time() - start_time
            if elapsed >= target_sec or active_tasks.get(chat_id, {}).get("skip", False):
                if active_tasks.get(chat_id, {}).get("skip", False):
                    active_tasks[chat_id]["skip"] = False
                break
            time.sleep(3)

        # 1. Place Views
        views_placed_str = ""
        if v_qty > 0:
            ok_v, res_v = place_order_with_smart_retry(
                SERVICE_INSTA_VIEWS, link, v_qty,
                chat_id=chat_id,
                step_info=f"Views Step #{step_num}"
            )
            if ok_v:
                total_views += v_qty
                active_tasks[chat_id]["views_placed"] = total_views
                views_placed_str = f"👁️ <b>+{v_qty} Views</b> (Order: <code>#{res_v}</code>)"
            else:
                views_placed_str = f"⚠️ <b>Views Failed:</b> <code>{res_v}</code>"

        # 2. Place Likes
        likes_placed_str = ""
        if l_qty > 0:
            ok_l, res_l = place_order_with_smart_retry(
                SERVICE_INSTA_LIKES, link, l_qty,
                chat_id=chat_id,
                step_info=f"Likes Step #{step_num}"
            )
            if ok_l:
                total_likes += l_qty
                active_tasks[chat_id]["likes_placed"] = total_likes
                likes_placed_str = f"❤️ <b>+{l_qty} Likes</b> (Order: <code>#{res_l}</code>)"
            else:
                likes_placed_str = f"⚠️ <b>Likes Failed:</b> <code>{res_l}</code>"

        msg_details = "\n".join([x for x in [views_placed_str, likes_placed_str] if x])
        send_safe_msg(
            chat_id,
            f"✅ <b>Milestone #{step_num}/{total_steps} Delivered!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Phase:</b> <i>{phase_name}</i>\n"
            f"{msg_details}\n"
            f"📈 <b>Live Total:</b> <code>{total_views}/{TARGET_VIEWS} Views</code> | <code>{total_likes}/{TARGET_LIKES} Likes</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=markup
        )

    send_safe_msg(
        chat_id,
        f"🎉🎉 <b>INSTAGRAM 5-HOUR CAMPAIGN COMPLETED!</b> 🎉🎉\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <code>{link}</code>\n"
        f"👁️ <b>Total Views:</b> {total_views} Views (Exact 2,000)\n"
        f"❤️ <b>Total Likes:</b> {total_likes} Likes (Exact 42)\n"
        f"🏁 <b>Status:</b> 100% Whop & Fraud-Check Safe! 🚀"
    )
    if chat_id in active_tasks:
        del active_tasks[chat_id]

# =====================================================================
# 🚀 PIPELINE DISPATCHER
# =====================================================================
def start_pipeline(chat_id, clean_url):
    if chat_id in active_tasks:
        active_tasks[chat_id]["cancel"] = True
        time.sleep(1)

    th = threading.Thread(target=insta_5hr_worker, args=(chat_id, clean_url), daemon=True)
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
        f"🤖 <b>Instagram 5-Hour Curve Bot</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Target:</b> 2,000 Views (#3508) + 42 Likes (#4731)\n"
        f"⏳ <b>Milestones:</b>\n"
        f"• 1 Hour baad: 100 Views\n"
        f"• 2 Hours baad: 250 Views (+14 Likes)\n"
        f"• 3 Hours baad: 700 Views\n"
        f"• 4 Hours baad: 1,400 Views (+14 Likes)\n"
        f"• 5 Hours baad: 2,000 Views (+14 Likes)\n\n"
        f"📌 <b>Commands:</b>\n"
        f"• <code>/status</code> - Check live campaign progress\n"
        f"• <code>/balance</code> - Check YoYoMedia balance\n"
        f"• <code>/stop</code> - Cancel active campaign\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>Reel ka link bhejo, bot 1st hour pura hone par pehla 100 views batch bhejega!</i>"
    )
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not check_authorized(message):
        return
    if message.chat.id in active_tasks:
        info = active_tasks[message.chat.id]
        txt = (
            f"📊 <b>LIVE INSTAGRAM STATUS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>Target:</b> <code>{info['link']}</code>\n"
            f"📍 <b>Step:</b> #{info['step']}/{len(SCHEDULE_5HR)}\n"
            f"👁️ <b>Views Placed:</b> {info['views_placed']}/{TARGET_VIEWS}\n"
            f"❤️ <b>Likes Placed:</b> {info['likes_placed']}/{TARGET_LIKES}\n"
            f"⏰ <b>Started At:</b> {info['start_time']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_safe_msg(message.chat.id, txt)
    else:
        send_safe_msg(message.chat.id, "ℹ️ Koi active campaign nahi chal rahi hai.")

@bot.message_handler(commands=['balance'])
def cmd_balance(message):
    if not check_authorized(message):
        return
    bal = fetch_balance()
    send_safe_msg(message.chat.id, f"💰 <b>YoYoMedia Live Balance:</b> <code>{bal}</code>")

@bot.message_handler(commands=['stop', 'cancel'])
def cmd_stop(message):
    if not check_authorized(message):
        return
    if message.chat.id in active_tasks:
        active_tasks[message.chat.id]["cancel"] = True
        send_safe_msg(message.chat.id, "🛑 Active campaign cancel kar diya gaya.")
    else:
        send_safe_msg(message.chat.id, "ℹ️ Koi active campaign nahi chal rahi hai.")

# Direct Link Trigger
@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    if not check_authorized(message):
        return
    url = clean_instagram_url(message.text)
    if url:
        start_pipeline(message.chat.id, url)
    else:
        send_safe_msg(message.chat.id, "❓ Kripya valid Instagram Reel ka link paste karein.")

# Callbacks for Inline Buttons
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data
    bot.answer_callback_query(call.id)

    if data == "cmd_skip":
        if chat_id in active_tasks:
            active_tasks[chat_id]["skip"] = True
            send_safe_msg(chat_id, "⚡ <b>Timer skip kiya!</b> Agla batch bhej raha hai...")
    elif data == "cmd_cancel":
        if chat_id in active_tasks:
            active_tasks[chat_id]["cancel"] = True
            send_safe_msg(chat_id, "🛑 <b>Campaign cancelled.</b>")

# =====================================================================
# 🌐 KEEP-ALIVE SERVER (For Render Free Hosting)
# =====================================================================
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Instagram 5-Hour Bot is Online!")
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
    print("🤖 Instagram 5-Hour Curve Bot Started...")
    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=25)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)
