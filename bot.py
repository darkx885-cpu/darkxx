import telebot
import requests
import time
import threading
import os
import socketserver
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler

# Bot Token & Config
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7880836150:AAE_g3LC9ZY3Vy9wwhgL7znE0ei4lvfstXk")
bot = telebot.TeleBot(BOT_TOKEN)

API_KEY = "e162df9b7dce5201f22c0decd4d4dff931c9904c708e1342b9da9b086e32b1ac"
API_URL = "https://yoyomedia.com/api/v2"

SERVICE_VIEWS = 4480
SERVICE_LIKES = 4731

# 6:50 PM (18:50 IST) se shuru hone wala Exact Schedule
SCHEDULE = [
    {"time": "18:50", "views": 117, "likes": 0},   # 1st hour (6:50 PM)
    {"time": "19:50", "views": 348, "likes": 0},   # 2nd hour (7:50 PM)
    {"time": "20:50", "views": 765, "likes": 0},   # 3rd hour (8:50 PM)
    {"time": "21:50", "views": 1630, "likes": 10}, # 4th hour (9:50 PM)
    {"time": "22:50", "views": 2404, "likes": 12}, # 5th hour (10:50 PM)
    {"time": "23:50", "views": 2736, "likes": 15}, # 6th hour (11:50 PM)
    {"time": "00:50", "views": 2896, "likes": 16}, # 7th hour (12:50 AM - Next day)
    {"time": "01:50", "views": 3003, "likes": 17}, # 8th hour (1:50 AM - Next day)
]

def place_order(service_id, link, quantity):
    if quantity <= 0:
        return None
    payload = {
        "key": API_KEY, "action": "add", 
        "service": service_id, "link": link, "quantity": quantity
    }
    try:
        res = requests.post(API_URL, data=payload)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def get_ist_now():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

def run_campaign(chat_id, link):
    bot.send_message(chat_id, "🚀 *Campaign Started!*\nBot 6:50 PM (18:50 IST) se orders lagana shuru karega.", parse_mode="Markdown")
    
    for step in SCHEDULE:
        target_time_str = step["time"]
        v_qty = step["views"]
        l_qty = step["likes"]
        
        while True:
            now = get_ist_now()
            current_time_str = now.strftime("%H:%M")
            
            if current_time_str >= target_time_str:
                msg = f"⏰ *Time Slot: {target_time_str} (IST)*\n"
                
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
                        msg += f"❤️ Likes (+{l_qty}): ❌ Panel Error"
                        
                bot.send_message(chat_id, msg, parse_mode="Markdown")
                time.sleep(60) # Prevent multiple triggers in same minute
                break
            else:
                time.sleep(15) # Efficient sleep to prevent high CPU usage
            
    bot.send_message(chat_id, "🎉 *Full Campaign Successfully Completed!*", parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome Bot!\nOrder lagane ke liye aise bhejein:\n\n`/run <link>`", parse_mode="Markdown")

@bot.message_handler(commands=['run'])
def handle_run(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Link missing! Aise bhejein:\n`/run https://www.instagram.com/reel/xyz/`", parse_mode="Markdown")
        return
    link = parts[1]
    threading.Thread(target=run_campaign, args=(message.chat.id, link)).start()

# --- FIXED DUMMY SERVER FOR RENDER & CRON-JOB.ORG ---
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), DummyServer) as httpd:
        httpd.serve_forever()

threading.Thread(target=keep_alive, daemon=True).start()
# ----------------------------------------------------

print("🤖 Telegram Bot is Active!")
while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Connection lost: {e}. Reconnecting in 5 seconds...")
        time.sleep(5)
