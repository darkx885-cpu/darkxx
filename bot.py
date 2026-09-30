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
# 🤖 BOT CONFIGURATION (@Danielview_bot)
# =====================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8631983010:AAFc466k0LIu10i_wErRu5CU2f6tulz3AsM")
bot = telebot.TeleBot(BOT_TOKEN)

# =====================================================================
# 🌐 DUAL SMM PANEL CONFIGURATION
# =====================================================================
# 1. VIEWS PANEL (PakFollowers)
VIEWS_PANEL_URL = "https://yoyomedia.com/api/v2"
VIEWS_API_KEY = "74d4962ec589605651ecff3c2ab0b9dda47785b2b327303111d0d8920bdd1aed"
SERVICE_VIEWS = 4322   # ⚡ 4322: [ Fastest Delivery ] Instant [Premium]

# 2. LIKES PANEL (SMMPanelPak)
LIKES_PANEL_URL = "https://smmpanelpak.com/api/v2"
LIKES_API_KEY = "1e3299898a440382ee5e410d11d3c9de5d1ff3a4"
SERVICE_LIKES = 4152   # Instagram Likes

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
ALLOWED_USERS = []

campaign_running = False
stop_campaign_flag = False
current_campaign_info = {}

# =====================================================================
# 📋 23-STEP 10-HOUR WAVE SCHEDULE (15,000 Views • 312 Likes)
# =====================================================================
STEPS_DATA = [
    {"step": 1,  "interval_mins": 15,  "views": 115,   "likes": 0,  "label": "0:15 min"},
    {"step": 2,  "interval_mins": 30,  "views": 175,   "likes": 0,  "label": "0:30 min"},
    {"step": 3,  "interval_mins": 45,  "views": 285,   "likes": 10, "label": "0:45 min"},
    {"step": 4,  "interval_mins": 60,  "views": 395,   "likes": 0,  "label": "1:00 hr"},
    {"step": 5,  "interval_mins": 75,  "views": 565,   "likes": 11, "label": "1:15 hr"},
    {"step": 6,  "interval_mins": 90,  "views": 715,   "likes": 12, "label": "1:30 hr"},
    {"step": 7,  "interval_mins": 120, "views": 925,   "likes": 14, "label": "2:00 hr"},
    {"step": 8,  "interval_mins": 150, "views": 1265,  "likes": 17, "label": "2:30 hr"},
    {"step": 9,  "interval_mins": 180, "views": 1640,  "likes": 22, "label": "3:00 hr"},
    {"step": 10, "interval_mins": 210, "views": 1960,  "likes": 32, "label": "3:30 hr (PEAK 🔥)"},
    {"step": 11, "interval_mins": 240, "views": 1710,  "likes": 25, "label": "4:00 hr"},
    {"step": 12, "interval_mins": 270, "views": 1380,  "likes": 24, "label": "4:30 hr"},
    {"step": 13, "interval_mins": 300, "views": 1050,  "likes": 23, "label": "5:00 hr"},
    {"step": 14, "interval_mins": 330, "views": 770,   "likes": 21, "label": "5:30 hr"},
    {"step": 15, "interval_mins": 360, "views": 530,   "likes": 20, "label": "6:00 hr"},
    {"step": 16, "interval_mins": 390, "views": 380,   "likes": 19, "label": "6:30 hr"},
    {"step": 17, "interval_mins": 420, "views": 270,   "likes": 18, "label": "7:00 hr"},
    {"step": 18, "interval_mins": 450, "views": 210,   "likes": 16, "label": "7:30 hr"},
    {"step": 19, "interval_mins": 480, "views": 165,   "likes": 15, "label": "8:00 hr"},
    {"step": 20, "interval_mins": 510, "views": 145,   "likes": 0,  "label": "8:30 hr"},
    {"step": 21, "interval_mins": 540, "views": 130,   "likes": 13, "label": "9:00 hr"},
    {"step": 22, "interval_mins": 570, "views": 118,   "likes": 0,  "label": "9:30 hr"},
    {"step": 23, "interval_mins": 600, "views": 102,   "likes": 0,  "label": "10:00 hr (Final)"},
]

TOTAL_VIEWS = sum(s["views"] for s in STEPS_DATA)  # Exactly 15,000
TOTAL_LIKES = sum(s["likes"] for s in STEPS_DATA)  # Exactly 312

# =====================================================================
# 🛠️ HELPER FUNCTIONS (Crash-Proof Messaging)
# =====================================================================
def send_safe_msg(chat_id, text, disable_web_page_preview=True):
    """Safely sends HTML message; falls back to plain text if any tag error occurs."""
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

def clean_instagram_link(raw_link: str) -> str:
    """Cleans Instagram URL and strips any surrounding angle brackets or whitespace."""
    raw_link = raw_link.strip().strip("<>").strip()
    if not raw_link.startswith("http://") and not raw_link.startswith("https://"):
        raw_link = "https://" + raw_link
    try:
        parsed = urlparse(raw_link)
        path = parsed.path
        if "/reel/" in path or "/p/" in path or "/tv/" in path:
            parts = path.strip("/").split("/")
            if len(parts) >= 2:
                return f"https://www.instagram.com/{parts[0]}/{parts[1]}/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    except Exception:
        return raw_link

def place_views_order(link, quantity):
    """Place Views Order on PakFollowers"""
    if quantity <= 0:
        return None
    payload = {
        "key": VIEWS_API_KEY,
        "action": "add",
        "service": SERVICE_VIEWS,
        "link": link,
        "quantity": quantity
    }
    try:
        res = requests.post(VIEWS_PANEL_URL, data=payload, headers=HEADERS, timeout=30)
        try:
            return res.json()
        except Exception:
            return {"error": res.text[:200]}
    except Exception as e:
        return {"error": str(e)}

def place_likes_order(link, quantity):
    """Place Likes Order on SMMPanelPak"""
    if quantity <= 0:
        return None
    payload = {
        "key": LIKES_API_KEY,
        "action": "add",
        "service": SERVICE_LIKES,
        "link": link,
        "quantity": quantity
    }
    try:
        res = requests.post(LIKES_PANEL_URL, data=payload, headers=HEADERS, timeout=30)
        try:
            return res.json()
        except Exception:
            return {"error": res.text[:200]}
    except Exception as e:
        return {"error": str(e)}

def get_dual_balance():
    # 1. PakFollowers Views Balance
    v_msg = "❌ Error"
    try:
        res_v = requests.post(VIEWS_PANEL_URL, data={"key": VIEWS_API_KEY, "action": "balance"}, headers=HEADERS, timeout=20)
        data_v = res_v.json()
        if "balance" in data_v:
            v_msg = f"{data_v['balance']} {data_v.get('currency', 'PKR')}"
        elif "error" in data_v:
            v_msg = data_v["error"]
    except Exception as e:
        v_msg = str(e)

    # 2. SMMPanelPak Likes Balance
    l_msg = "❌ Error"
    try:
        res_l = requests.post(LIKES_PANEL_URL, data={"key": LIKES_API_KEY, "action": "balance"}, headers=HEADERS, timeout=20)
        data_l = res_l.json()
        if "balance" in data_l:
            l_msg = f"{data_l['balance']} {data_l.get('currency', 'PKR')}"
        elif "error" in data_l:
            l_msg = data_l["error"]
    except Exception as e:
        l_msg = str(e)

    return (
        f"💵 <b>Dual-Panel Balances:</b>\n\n"
        f"👁️ <b>PakFollowers (Views):</b> <code>{v_msg}</code>\n"
        f"❤️ <b>SMMPanelPak (Likes):</b> <code>{l_msg}</code>"
    )

def get_ist_now():
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

# =====================================================================
# 🚀 23-STEP DUAL-PANEL CAMPAIGN WORKER (10 Hours)
# =====================================================================
def run_campaign(chat_id, raw_link, start_time_str, start_step):
    global campaign_running, stop_campaign_flag, current_campaign_info
    campaign_running = True
    stop_campaign_flag = False

    link = clean_instagram_link(raw_link)
    now = get_ist_now()

    # Time Parsing
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
        "total_steps": len(STEPS_DATA),
        "views_sent": 0,
        "likes_sent": 0
    }

    msg_start = (
        f"🚀 <b>Dual-Panel 23-Step Wave Started!</b>\n\n"
        f"🔗 <b>Link:</b> <code>{link}</code>\n"
        f"⏰ <b>Start Time:</b> <code>{start_dt.strftime('%I:%M %p')} IST</code>\n"
        f"🔢 <b>Starting Step:</b> <code>{start_step}/23</code>\n\n"
        f"👁️ <b>Views Panel:</b> PakFollowers (Service #{SERVICE_VIEWS}) ➔ {TOTAL_VIEWS:,} Views\n"
        f"❤️ <b>Likes Panel:</b> SMMPanelPak (Service #{SERVICE_LIKES}) ➔ {TOTAL_LIKES} Likes\n"
        f"⏱️ <b>Schedule:</b> 23 Steps over 10 Hours"
    )
    send_safe_msg(chat_id, msg_start, disable_web_page_preview=True)

    total_views = 0
    total_likes = 0

    for relative_idx, step in enumerate(steps_to_run):
        if stop_campaign_flag:
            break

        actual_step_num = start_step + relative_idx
        target_mins = step["interval_mins"]
        target_dt = start_dt + timedelta(minutes=target_mins)
        target_time_str = target_dt.strftime("%I:%M %p")

        current_campaign_info["completed_steps"] = actual_step_num - 1
        current_campaign_info["next_step_time"] = target_time_str

        v_qty = step["views"]
        l_qty = step["likes"]

        while True:
            if stop_campaign_flag:
                break
            current_ist = get_ist_now()
            if current_ist >= target_dt:
                msg = f"⏰ <b>Step {actual_step_num}/23 ({target_time_str} IST) — {step['label']}</b>\n"

                # 1. Place Views on PakFollowers
                if v_qty > 0:
                    v_res = place_views_order(link, v_qty)
                    if v_res and "order" in v_res:
                        msg += f"👁️ PakFollowers Views (+{v_qty:,}): ✅ [ID: <code>{v_res['order']}</code>]\n"
                        total_views += v_qty
                    else:
                        err = v_res.get("error", "Failed") if v_res else "Failed"
                        msg += f"👁️ PakFollowers Views (+{v_qty:,}): ❌ {err}\n"

                # 2. Place Likes on SMMPanelPak
                if l_qty > 0:
                    time.sleep(2)
                    l_res = place_likes_order(link, l_qty)
                    if l_res and "order" in l_res:
                        msg += f"❤️ SMMPanelPak Likes (+{l_qty}): ✅ [ID: <code>{l_res['order']}</code>]\n"
                        total_likes += l_qty
                    else:
                        err = l_res.get("error", "Failed") if l_res else "Failed"
                        msg += f"❤️ SMMPanelPak Likes (+{l_qty}): ❌ {err}\n"

                current_campaign_info["views_sent"] = total_views
                current_campaign_info["likes_sent"] = total_likes

                msg += f"📈 <b>Progress:</b> {total_views:,}/{TOTAL_VIEWS:,} views • {total_likes}/{TOTAL_LIKES} likes"

                send_safe_msg(chat_id, msg)
                smart_sleep(5)
                break
            else:
                wait_seconds = (target_dt - current_ist).total_seconds()
                smart_sleep(min(wait_seconds, 15))

    if stop_campaign_flag:
        send_safe_msg(chat_id, f"🛑 <b>Campaign Stopped!</b> Delivered {total_views:,} views & {total_likes} likes.")
    else:
        send_safe_msg(
            chat_id,
            f"🎉 <b>Dual-Panel 23-Step Campaign Completed!</b>\n\n"
            f"🔗 <b>Link:</b> <code>{link}</code>\n"
            f"👁️ Total Views (PakFollowers): <b>{total_views:,}</b>\n"
            f"❤️ Total Likes (SMMPanelPak): <b>{total_likes}</b>\n"
            f"🏆 All 23 steps finished successfully over 10 Hours!",
            disable_web_page_preview=True
        )

    campaign_running = False

# =====================================================================
# 🤖 TELEGRAM BOT COMMAND HANDLERS
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not check_authorized(message):
        send_safe_msg(message.chat.id, f"⛔ Access Denied!\nAapka User ID: <code>{message.chat.id}</code>\nAdmin se access maangein.")
        return
    welcome_txt = (
        "👋 <b>Welcome Boss! @Danielview_bot Dual-Panel Control Panel</b>\n\n"
        "📋 <b>23-Step 10-Hour Wave Schedule:</b>\n"
        f"👁️ <b>Views Panel:</b> PakFollowers (Service #{SERVICE_VIEWS}) ➔ {TOTAL_VIEWS:,} Views\n"
        f"❤️ <b>Likes Panel:</b> SMMPanelPak (Service #{SERVICE_LIKES}) ➔ {TOTAL_LIKES} Likes\n\n"
        "📌 <b>Campaign Commands:</b>\n"
        "🔹 Send any <b>Instagram Reel/Post Link</b> to start instantly!\n"
        "🔹 <code>/run &lt;link&gt;</code> — Immediate start from Step 1\n"
        "🔹 <code>/run &lt;link&gt; &lt;time&gt;</code> — Specific time par start karein (e.g. <code>/run https://... 16:30</code>)\n"
        "🔹 <code>/run &lt;link&gt; &lt;step&gt;</code> — Specific step/batch se shuru karein (e.g. <code>/run https://... 5</code>)\n"
        "🔹 <code>/run &lt;link&gt; &lt;time&gt; &lt;step&gt;</code> — Time + Step\n\n"
        "🔹 <code>/balance</code> — Check Dual-Panel Balances\n"
        "🔹 <code>/status</code> — Check Live Progress & Next Step Time\n"
        "🔹 <code>/stop</code> — Stop Active Campaign\n\n"
        "👥 <b>Admin Team Access:</b>\n"
        "🔹 <code>/adduser &lt;id&gt;</code> — Add user access\n"
        "🔹 <code>/removeuser &lt;id&gt;</code> — Remove user access\n"
        "🔹 <code>/users</code> — List authorized users\n"
        f"🆔 <b>Your Telegram ID:</b> <code>{message.chat.id}</code>"
    )
    send_safe_msg(message.chat.id, welcome_txt)

@bot.message_handler(commands=['adduser'])
def handle_adduser(message):
    global ADMIN_ID, ALLOWED_USERS
    if message.chat.id != ADMIN_ID:
        send_safe_msg(message.chat.id, "⛔ Only Main Admin can add users!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        send_safe_msg(message.chat.id, "⚠️ Usage: <code>/adduser &lt;user_id&gt;</code>")
        return
    try:
        new_uid = int(parts[1])
        if new_uid not in ALLOWED_USERS:
            ALLOWED_USERS.append(new_uid)
            send_safe_msg(message.chat.id, f"✅ User <code>{new_uid}</code> ko bot access de diya gaya hai!")
        else:
            send_safe_msg(message.chat.id, f"ℹ️ User <code>{new_uid}</code> already added hai.")
    except ValueError:
        send_safe_msg(message.chat.id, "⚠️ Invalid User ID!")

@bot.message_handler(commands=['removeuser'])
def handle_removeuser(message):
    global ADMIN_ID, ALLOWED_USERS
    if message.chat.id != ADMIN_ID:
        send_safe_msg(message.chat.id, "⛔ Only Main Admin can remove users!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        send_safe_msg(message.chat.id, "⚠️ Usage: <code>/removeuser &lt;user_id&gt;</code>")
        return
    try:
        uid = int(parts[1])
        if uid in ALLOWED_USERS:
            ALLOWED_USERS.remove(uid)
            send_safe_msg(message.chat.id, f"🗑️ User <code>{uid}</code> ka access hata diya gaya!")
        else:
            send_safe_msg(message.chat.id, "ℹ️ User list me nahi hai.")
    except ValueError:
        send_safe_msg(message.chat.id, "⚠️ Invalid User ID!")

@bot.message_handler(commands=['users'])
def handle_list_users(message):
    if not check_authorized(message):
        return
    txt = "👥 <b>Authorized Users:</b>\n"
    txt += f"👑 <b>Admin:</b> <code>{ADMIN_ID}</code>\n"
    for u in ALLOWED_USERS:
        if u != ADMIN_ID:
            txt += f"🔹 <code>{u}</code>\n"
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['balance'])
def handle_balance(message):
    if not check_authorized(message):
        return
    send_safe_msg(message.chat.id, get_dual_balance())

@bot.message_handler(commands=['status'])
def handle_status(message):
    if not check_authorized(message):
        return
    if campaign_running:
        info = (
            f"📊 <b>Active 23-Step Campaign Status:</b>\n\n"
            f"🔗 <b>Link:</b> <code>{current_campaign_info.get('link')}</code>\n"
            f"⏰ <b>Started At:</b> {current_campaign_info.get('start_time')} IST\n"
            f"📈 <b>Completed:</b> Step {current_campaign_info.get('completed_steps', 0)} / 23\n"
            f"⏰ <b>Next Step:</b> {current_campaign_info.get('next_step_time', 'Executing now')}\n"
            f"👁️ <b>PakFollowers Views:</b> {current_campaign_info.get('views_sent', 0):,} / {TOTAL_VIEWS:,}\n"
            f"❤️ <b>SMMPanelPak Likes:</b> {current_campaign_info.get('likes_sent', 0)} / {TOTAL_LIKES}"
        )
    else:
        info = "ℹ️ Koi campaign abhi nahi chal rahi hai."
    send_safe_msg(message.chat.id, info, disable_web_page_preview=True)

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    global stop_campaign_flag, campaign_running
    if not check_authorized(message):
        return
    if campaign_running:
        stop_campaign_flag = True
        send_safe_msg(message.chat.id, "🛑 <b>Stopping campaign...</b>")
    else:
        send_safe_msg(message.chat.id, "ℹ️ No active campaign to stop.")

@bot.message_handler(commands=['run', 'batch'])
def handle_run(message):
    if not check_authorized(message):
        return
    global campaign_running
    if campaign_running:
        send_safe_msg(message.chat.id, "⚠️ Pehle se ek campaign chal rahi hai! Use <code>/stop</code> first.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        send_safe_msg(message.chat.id, "⚠️ Usage: <code>/run &lt;link&gt; [time] [step]</code>\nExample: <code>/run https://instagram.com/reel/xyz 5</code>")
        return

    link = None
    start_time_str = None
    start_step = 1

    for p in parts[1:]:
        p_clean = p.strip("<>")
        if "instagram.com" in p_clean or "http://" in p_clean or "https://" in p_clean:
            link = clean_instagram_link(p_clean)
        elif ":" in p:
            start_time_str = p
        elif p.isdigit():
            val = int(p)
            if 1 <= val <= 23:
                start_step = val

    if not link:
        send_safe_msg(message.chat.id, "⚠️ Please provide a valid Instagram link!")
        return

    threading.Thread(
        target=run_campaign,
        args=(message.chat.id, link, start_time_str, start_step),
        daemon=True
    ).start()

@bot.message_handler(func=lambda msg: True)
def handle_direct_link(message):
    if not check_authorized(message):
        return
    global campaign_running
    text = message.text.strip().strip("<>")
    if "instagram.com" in text or "http://" in text or "https://" in text:
        if campaign_running:
            send_safe_msg(message.chat.id, "⚠️ Pehle se ek campaign chal rahi hai! Use <code>/stop</code> first.")
            return
        link = clean_instagram_link(text)
        threading.Thread(
            target=run_campaign,
            args=(message.chat.id, link, None, 1),
            daemon=True
        ).start()
    else:
        send_safe_msg(message.chat.id, "⚠️ Please send a valid Instagram post/reel link or use /start.")

# =====================================================================
# 🌐 KEEP ALIVE HTTP SERVER (RENDER & CRON-JOB FIX)
# =====================================================================
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', '2')
        self.end_headers()

    def log_message(self, format, *args):
        pass

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), DummyServer) as httpd:
        httpd.serve_forever()

def self_ping():
    time.sleep(20)
    while True:
        try:
            port = int(os.environ.get("PORT", 8080))
            urllib.request.urlopen(f"http://localhost:{port}", timeout=10)
        except Exception:
            pass
        time.sleep(180)

# =====================================================================
# 🏁 MAIN ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()

    print("🤖 @Danielview_bot Dual-Panel 23-Step (15k Views / 312 Likes) Bot is Active!")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Reconnecting: {e}")
            time.sleep(5)
