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
# 🤖 FRESH BOT CONFIGURATION
# =====================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8631983010:AAFc466k0LIu10i_wErRu5CU2f6tulz3AsM")
bot = telebot.TeleBot(BOT_TOKEN)

# =====================================================================
# 🌐 DUAL SMM PANEL CONFIGURATION
# =====================================================================
# 1. VIEWS PANEL (YoyoMedia)
VIEWS_PANEL_URL = "https://yoyomedia.com/api/v2"
VIEWS_API_KEY = "74d4962ec589605651ecff3c2ab0b9dda47785b2b327303111d0d8920bdd1aed"
SERVICE_VIEWS = 4322   # ⚡ 4322: [ Fastest Delivery ] Instant [Premium]

# 2. LIKES PANEL (SMMPanelPak)
LIKES_PANEL_URL = "https://smmpanelpak.com/api/v2"
LIKES_API_KEY = "1e3299898a440382ee5e410d11d3c9de5d1ff3a4"
SERVICE_LIKES = 4152   # Instagram Likes

# Full Browser Headers for 100% Cloudflare Bypass
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
# 📋 19-STEP 8-HOUR WAVE SCHEDULE (3,900 Views • 123 Likes)
# =====================================================================
STEPS_DATA = [
    {"step": 1,  "interval_mins": 15,  "views": 105, "likes": 0,  "label": "0:15 min"},
    {"step": 2,  "interval_mins": 30,  "views": 110, "likes": 0,  "label": "0:30 min"},
    {"step": 3,  "interval_mins": 45,  "views": 115, "likes": 0,  "label": "0:45 min"},
    {"step": 4,  "interval_mins": 60,  "views": 125, "likes": 10, "label": "1:00 hr"},
    {"step": 5,  "interval_mins": 75,  "views": 135, "likes": 0,  "label": "1:15 hr"},
    {"step": 6,  "interval_mins": 90,  "views": 150, "likes": 0,  "label": "1:30 hr"},
    {"step": 7,  "interval_mins": 120, "views": 220, "likes": 12, "label": "2:00 hr"},
    {"step": 8,  "interval_mins": 150, "views": 310, "likes": 0,  "label": "2:30 hr"},
    {"step": 9,  "interval_mins": 180, "views": 440, "likes": 18, "label": "3:00 hr"},
    {"step": 10, "interval_mins": 210, "views": 530, "likes": 26, "label": "3:30 hr (PEAK 🔥)"},
    {"step": 11, "interval_mins": 240, "views": 420, "likes": 0,  "label": "4:00 hr"},
    {"step": 12, "interval_mins": 270, "views": 300, "likes": 19, "label": "4:30 hr"},
    {"step": 13, "interval_mins": 300, "views": 230, "likes": 0,  "label": "5:00 hr"},
    {"step": 14, "interval_mins": 330, "views": 185, "likes": 13, "label": "5:30 hr"},
    {"step": 15, "interval_mins": 360, "views": 155, "likes": 0,  "label": "6:00 hr"},
    {"step": 16, "interval_mins": 390, "views": 135, "likes": 11, "label": "6:30 hr"},
    {"step": 17, "interval_mins": 420, "views": 120, "likes": 14, "label": "7:00 hr"},
    {"step": 18, "interval_mins": 450, "views": 110, "likes": 0,  "label": "7:30 hr"},
    {"step": 19, "interval_mins": 480, "views": 105, "likes": 0,  "label": "8:00 hr (Final)"},
]

TOTAL_VIEWS = sum(s["views"] for s in STEPS_DATA)  # 3,900
TOTAL_LIKES = sum(s["likes"] for s in STEPS_DATA)  # 123

# =====================================================================
# 🛠️ HELPER FUNCTIONS
# =====================================================================
def send_safe_msg(chat_id, text, disable_web_page_preview=True):
    """Safely sends HTML message; falls back to plain text if parse error occurs."""
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

def clean_instagram_link(link: str) -> str:
    try:
        parsed = urlparse(link.strip())
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if not clean.endswith("/"):
            clean += "/"
        return clean
    except Exception:
        return link.strip()

def place_views_order(link, quantity):
    """Place Views Order on YoyoMedia with 3x Auto-Retry"""
    if quantity <= 0:
        return None
    payload = {
        "key": VIEWS_API_KEY,
        "action": "add",
        "service": SERVICE_VIEWS,
        "link": link,
        "quantity": quantity
    }
    last_err = "Server returned invalid response"
    for attempt in range(3):
        try:
            res = requests.post(VIEWS_PANEL_URL, data=payload, headers=HEADERS, timeout=30)
            try:
                data = res.json()
                if "order" in data or "error" in data:
                    return data
            except Exception:
                pass
        except Exception as e:
            last_err = str(e)
        time.sleep(2)
    return {"error": last_err}

def place_likes_order(link, quantity):
    """Place Likes Order on SMMPanelPak with 3x Auto-Retry"""
    if quantity <= 0:
        return None
    payload = {
        "key": LIKES_API_KEY,
        "action": "add",
        "service": SERVICE_LIKES,
        "link": link,
        "quantity": quantity
    }
    last_err = "Server returned invalid response"
    for attempt in range(3):
        try:
            res = requests.post(LIKES_PANEL_URL, data=payload, headers=HEADERS, timeout=30)
            try:
                data = res.json()
                if "order" in data or "error" in data:
                    return data
            except Exception:
                pass
        except Exception as e:
            last_err = str(e)
        time.sleep(2)
    return {"error": last_err}

def get_dual_balance():
    # 1. YoyoMedia Views Balance
    v_msg = "❌ Error fetching balance"
    for _ in range(3):
        try:
            res_v = requests.post(VIEWS_PANEL_URL, data={"key": VIEWS_API_KEY, "action": "balance"}, headers=HEADERS, timeout=20)
            data_v = res_v.json()
            if "balance" in data_v:
                usd_bal = float(data_v['balance'])
                inr_bal = usd_bal * 83.50
                v_msg = f"${usd_bal:.2f} USD (₹{inr_bal:.2f} INR)"
                break
            elif "error" in data_v:
                v_msg = f"❌ {html.escape(str(data_v['error']))}"
        except Exception:
            time.sleep(1)

    # 2. SMMPanelPak Likes Balance
    l_msg = "❌ Error fetching balance"
    for _ in range(3):
        try:
            res_l = requests.post(LIKES_PANEL_URL, data={"key": LIKES_API_KEY, "action": "balance"}, headers=HEADERS, timeout=20)
            data_l = res_l.json()
            if "balance" in data_l:
                usd_bal = float(data_l['balance'])
                inr_bal = usd_bal * 83.50
                curr = data_l.get('currency', 'USD')
                if curr.upper() == "PKR":
                    l_msg = f"{usd_bal:.2f} PKR"
                else:
                    l_msg = f"${usd_bal:.2f} USD (₹{inr_bal:.2f} INR)"
                break
            elif "error" in data_l:
                l_msg = f"❌ {html.escape(str(data_l['error']))}"
        except Exception:
            time.sleep(1)

    return (
        f"💳 <b>Dual Panel Live Balances:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👁️ <b>YoyoMedia (Views):</b> <code>{v_msg}</code>\n"
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
# 🚀 CAMPAIGN EXECUTION ENGINE (19 STEPS DUAL PANEL)
# =====================================================================
def run_campaign(chat_id, raw_link, start_time_str=None, start_step=1):
    global campaign_running, stop_campaign_flag, current_campaign_info
    campaign_running = True
    stop_campaign_flag = False

    link = clean_instagram_link(raw_link)
    now = get_ist_now()

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

    while get_ist_now() < start_dt:
        if stop_campaign_flag:
            break
        diff = (start_dt - get_ist_now()).total_seconds()
        smart_sleep(min(diff, 10))

    if stop_campaign_flag:
        campaign_running = False
        send_safe_msg(chat_id, "🛑 <b>Campaign Cancelled before start!</b>")
        return

    initial_views = sum(STEPS_DATA[i]["views"] for i in range(start_step - 1))
    initial_likes = sum(STEPS_DATA[i]["likes"] for i in range(start_step - 1))

    current_campaign_info = {
        "link": link,
        "start_time": start_dt.strftime('%I:%M %p'),
        "completed_steps": start_step - 1,
        "views_sent": initial_views,
        "likes_sent": initial_likes,
        "next_step_time": "Calculating..."
    }

    step1_time = (start_dt + timedelta(minutes=STEPS_DATA[start_step - 1]["interval_mins"])).strftime('%I:%M %p')

    start_msg = (
        f"🚀 <b>19-Step Wave Campaign Started!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Target:</b> <code>{link}</code>\n"
        f"⏰ <b>Start Time:</b> <code>{start_dt.strftime('%I:%M %p')} IST</code>\n"
        f"🏁 <b>Est Completion:</b> <code>{(start_dt + timedelta(minutes=480)).strftime('%I:%M %p')} IST</code>\n"
        f"📈 <b>Starting at:</b> Step {start_step} / 19\n"
        f"⏳ <b>Next: Step {start_step} at:</b> <code>{step1_time} IST</code>\n\n"
        f"📊 <b>Total Target:</b> <code>{TOTAL_VIEWS:,} Views</code> • <code>{TOTAL_LIKES} Likes</code>\n"
        f"🌐 <b>Views Panel:</b> YoyoMedia (Service #{SERVICE_VIEWS})\n"
        f"🌐 <b>Likes Panel:</b> SMMPanelPak (Service #{SERVICE_LIKES})"
    )
    send_safe_msg(chat_id, start_msg)

    step_events = [
        (start_dt + timedelta(minutes=step["interval_mins"]), step["step"], step["views"], step["likes"], step["label"])
        for step in STEPS_DATA
    ]

    for idx in range(start_step - 1, len(step_events)):
        if stop_campaign_flag:
            break

        target_time, step_num, v_qty, l_qty, label = step_events[idx]
        current_campaign_info["next_step_time"] = target_time.strftime('%I:%M %p')

        while get_ist_now() < target_time:
            if stop_campaign_flag:
                break
            diff = (target_time - get_ist_now()).total_seconds()
            smart_sleep(min(diff, 10))

        if stop_campaign_flag:
            break

        # 1. YoyoMedia Views Order (with 3x Retry)
        v_res = place_views_order(link, v_qty)
        if v_res and "order" in v_res:
            v_status = f"✅ YoyoMedia #<code>{v_res['order']}</code>"
        elif v_res and "error" in v_res:
            clean_err = html.escape(str(v_res['error']))[:50]
            v_status = f"❌ Error: <code>{clean_err}</code>"
        else:
            v_status = "⚠️ Response error"

        current_campaign_info["views_sent"] += v_qty

        # 2. SMMPanelPak Likes Order (with 3x Retry)
        l_status = "Skipped (+0)"
        if l_qty > 0:
            time.sleep(2)
            l_res = place_likes_order(link, l_qty)
            if l_res and "order" in l_res:
                l_status = f"✅ SMMPanelPak #<code>{l_res['order']}</code>"
            elif l_res and "error" in l_res:
                clean_l_err = html.escape(str(l_res['error']))[:50]
                l_status = f"❌ Error: <code>{clean_l_err}</code>"
            else:
                l_status = "⚠️ Response error"

            current_campaign_info["likes_sent"] += l_qty

        current_campaign_info["completed_steps"] = step_num

        if idx + 1 < len(step_events):
            next_t = step_events[idx + 1][0].strftime('%I:%M %p')
            next_str = f"⏳ <b>Next:</b> Step {step_num + 1} at <code>{next_t} IST</code>"
        else:
            next_str = "🏁 <b>This was the Final Step!</b>"

        step_msg = (
            f"📦 <b>Step {step_num}/19 Executed ({label})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👁️ <b>Views (+{v_qty}):</b> {v_status}\n"
            f"❤️ <b>Likes (+{l_qty}):</b> {l_status}\n\n"
            f"📊 <b>Delivered Total:</b>\n"
            f"   • Views: <code>{current_campaign_info['views_sent']:,} / {TOTAL_VIEWS:,}</code>\n"
            f"   • Likes: <code>{current_campaign_info['likes_sent']} / {TOTAL_LIKES}</code>\n"
            f"{next_str}"
        )
        send_safe_msg(chat_id, step_msg)

    if stop_campaign_flag:
        send_safe_msg(
            chat_id,
            f"🛑 <b>Campaign Stopped by Admin!</b>\n"
            f"📊 Views Delivered: {current_campaign_info['views_sent']:,}\n"
            f"❤️ Likes Delivered: {current_campaign_info['likes_sent']}"
        )
    else:
        send_safe_msg(
            chat_id,
            f"🎉 <b>19-Step Wave Campaign Completed 100%!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>Target:</b> <code>{link}</code>\n"
            f"👁️ <b>Total Views:</b> <b>{current_campaign_info['views_sent']:,} / {TOTAL_VIEWS:,}</b>\n"
            f"❤️ <b>Total Likes:</b> <b>{current_campaign_info['likes_sent']} / {TOTAL_LIKES}</b>\n"
            f"⏱️ <b>Total Duration:</b> 8 Hours Wave"
        )

    campaign_running = False

# =====================================================================
# 💬 BOT COMMAND HANDLERS
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    if not check_authorized(message):
        send_safe_msg(message.chat.id, "⛔ Access Denied! Please contact the Admin.")
        return
    txt = (
        f"👋 <b>Welcome to Wave Automation Bot!</b>\n"
        f"<i>19-Step Wave (Views: YoyoMedia | Likes: SMMPanelPak)</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 <b>Quick Start:</b> Just paste any Instagram Reel/Post link!\n\n"
        f"📌 <b>Commands:</b>\n"
        f"🔹 <code>/run &lt;link&gt;</code> - Turant start karein\n"
        f"🔹 <code>/run &lt;link&gt; 16:30</code> - Scheduled time par start\n"
        f"🔹 <code>/run &lt;link&gt; 5</code> - Step 5 se start\n"
        f"🔹 <code>/balance</code> - Check Both Panels Balance\n"
        f"🔹 <code>/status</code> - Live Campaign status\n"
        f"🔹 <code>/schedule</code> - 19-Step time table\n"
        f"🔹 <code>/stop</code> - Campaign cancel karein\n"
        f"🔹 <code>/users</code> - Team members list\n"
        f"🔹 <code>/adduser &lt;id&gt;</code> - Naye user ko add karein\n"
        f"🔹 <code>/removeuser &lt;id&gt;</code> - User access revoke karein\n"
        f"🔹 <code>/myid</code> - Telegram Chat ID"
    )
    send_safe_msg(message.chat.id, txt)

@bot.message_handler(commands=['myid'])
def handle_myid(message):
    send_safe_msg(message.chat.id, f"🆔 Aapki Telegram Chat ID hai: <code>{message.chat.id}</code>")

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
            send_safe_msg(message.chat.id, f"✅ User <code>{new_uid}</code> ko access de diya gaya!")
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
def handle_balance_cmd(message):
    if not check_authorized(message):
        return
    send_safe_msg(message.chat.id, get_dual_balance())

@bot.message_handler(commands=['schedule'])
def handle_schedule_cmd(message):
    if not check_authorized(message):
        return
    msg = "📋 <b>19-STEP 8-HOUR WAVE SCHEDULE:</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
    for s in STEPS_DATA:
        likes_str = f"+{s['likes']} Likes" if s['likes'] > 0 else "0 Likes"
        msg += f"<b>Step {s['step']:02d} ({s['label']}):</b> +{s['views']} Views | {likes_str}\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━\n📊 <b>Total:</b> <code>{TOTAL_VIEWS:,} Views</code> • <code>{TOTAL_LIKES} Likes</code>"
    send_safe_msg(message.chat.id, msg)

@bot.message_handler(commands=['status'])
def handle_status(message):
    if not check_authorized(message):
        return
    if campaign_running:
        info = (
            f"📊 <b>Active 19-Step Campaign Status:</b>\n\n"
            f"🔗 <b>Link:</b> {current_campaign_info.get('link')}\n"
            f"⏰ <b>Started At:</b> {current_campaign_info.get('start_time')} IST\n"
            f"📈 <b>Completed:</b> Step {current_campaign_info.get('completed_steps', 0)} / 19\n"
            f"⏰ <b>Next Step:</b> {current_campaign_info.get('next_step_time', 'Executing now')}\n"
            f"👁️ <b>YoyoMedia Views:</b> {current_campaign_info.get('views_sent', 0):,} / {TOTAL_VIEWS:,}\n"
            f"❤️ <b>SMMPanelPak Likes:</b> {current_campaign_info.get('likes_sent', 0)} / {TOTAL_LIKES}"
        )
    else:
        info = "ℹ️ Koi campaign abhi nahi chal rahi hai."
    send_safe_msg(message.chat.id, info)

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

@bot.message_handler(commands=['run'])
def handle_run(message):
    if not check_authorized(message):
        return
    global campaign_running
    if campaign_running:
        send_safe_msg(message.chat.id, "⚠️ Pehle se ek campaign chal rahi hai! Use <code>/stop</code> first.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        send_safe_msg(message.chat.id, "⚠️ Usage: <code>/run &lt;link&gt; [time] [step]</code>")
        return

    link = parts[1]
    start_time_str = None
    start_step = 1

    if len(parts) == 3:
        param = parts[2]
        if ":" in param:
            start_time_str = param
        else:
            try:
                start_step = int(param)
            except ValueError:
                start_step = 1
    elif len(parts) >= 4:
        start_time_str = parts[2]
        try:
            start_step = int(parts[3])
        except ValueError:
            start_step = 1

    if start_step < 1 or start_step > 19:
        start_step = 1

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
    text = message.text.strip()
    if "instagram.com" in text or "http://" in text or "https://" in text:
        if campaign_running:
            send_safe_msg(message.chat.id, "⚠️ Pehle se ek campaign chal rahi hai! Use <code>/stop</code> first.")
            return
        threading.Thread(
            target=run_campaign,
            args=(message.chat.id, text, None, 1),
            daemon=True
        ).start()
    else:
        send_safe_msg(message.chat.id, "⚠️ Please send a valid Instagram post/reel link or use /start.")

# =====================================================================
# 🌐 KEEP ALIVE HTTP SERVER (RENDER 24/7 SUPPORT)
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

    print("🤖 Fresh 19-Step Bot is Active & Protected!")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Reconnecting: {e}")
            time.sleep(5)

