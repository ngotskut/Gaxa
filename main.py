# Created By @Lohit_69
import time
import re
import threading
import random
import requests
import phonenumbers
import html
from datetime import datetime, timedelta
from phonenumbers import geocoder
from playwright.sync_api import sync_playwright
import telebot
from telebot import types

# ================ CONFIGURATION ================
BOT_TOKEN = "8756794417:AAHzwO8OgC2s902dHdWP1aM_mpqEPDVdORU"
ADMIN_ID = 1725468809
GROUP_CHAT_ID = "-1003725931679"
PANEL_URL = "http://144.217.71.192/ints/login"
DATA_URL = "http://144.217.71.192/ints/agent/res/data_smscdr.php"
MONITOR_PAGE = "http://144.217.71.192/ints/agent/SMSCDRStats"

MY_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
PANEL_USER = "atik9900"
PANEL_PASS = "atik9900"

bot = telebot.TeleBot(BOT_TOKEN)
session = requests.Session()
session.headers.update({"User-Agent": MY_USER_AGENT})

seen_messages = set()
IS_SCRAPPING = False
TOTAL_FORWARDED = 0
LAST_CHECK_TIME = "Never"
SESSION_STATUS = "🔴 Not Logged In"
HUD_MESSAGE_ID = None

# Logic Control
is_initial_run = True
CMD_LOGIN_REQUESTED = False
CMD_LOGOUT_REQUESTED = False
CMD_PREV_DAY_REQUESTED = False
PANEL_CURRENT_DATE = None # Dynamic Date Tracker
PLAYWRIGHT_INST = None
BROWSER = None
CONTEXT = None
PAGE = None

# ================ EMOJI DATABASE ================
EMOJI_MAP = {
    "WHATSAPP": "5334998226636390258", "TELEGRAM": "5330237710655306682",
    "FACEBOOK": "5323261730283863478", "INSTAGRAM": "5319160079465857105",
    "TIKTOK": "5327982530702359565", "PINTEREST": "5346103513120258857",
    "YOUTUBE": "5334681713316479679", "TWITTER": "5330337435500951363",
    " X ": "5330337435500951363", "DISCORD": "5325612636467903082",
    "SNAPCHAT": "5330248916224983855", "SKYPE": "5328175271654736902",
    "TWITCH": "5334678011054669335", "APPLE": "5334955749409834455",
    "SPOTIFY": "5346074681004801565", "VIBER": "5332449498553663205",
    "ONLYFANS": "5346213374088723754", "LINKEDIN": "5346024520081751155",
    "MICROSOFT": "5370857634440170316", "CHATGPT": "5359726582447487916",
    "TINDER": "5328029650788563621", "NETFLIX": "5318911503938634641",
    "AMAZON": "5346056560537779652", "REDDIT": "5330321861949539755",
    "GITHUB": "5346181118884331907", "MESSENGER": "5323687726615119535",
    "XBOX": "5373019729566908647", "STEAM": "5373144051690258848",
    "WECHAT": "5332524123610430820", "GOOGLE": "5359758030198031389",
    "MEGA": "5373246052868571826", "BINANCE": "6111627832440396096"
}
UNIVERSAL_EMOJI = "5798420477705719523"
PERMANENT_HEADER_EMOJI = "6300794117894965201"
SERVICE_LABEL_EMOJI = "6298751564592973547"
OTP_LABEL_EMOJI = "6300834821300029148"

# ================ HELPER FUNCTIONS ================

def get_flag_emoji(country_code):
    if not country_code or not isinstance(country_code, str): return "🌍"
    return "".join(chr(127397 + ord(c)) for c in country_code.upper())

def get_country_info(phone):
    try:
        phone_str = str(phone).lstrip('+')
        parsed_number = phonenumbers.parse("+" + phone_str)
        country_name = geocoder.description_for_number(parsed_number, "en")
        region_code = phonenumbers.region_code_for_number(parsed_number)
        return (country_name or "International"), get_flag_emoji(region_code)
    except: return "International", "🌍"

def get_custom_emoji_tag(service_name):
    if not service_name: return f"<tg-emoji emoji-id='{UNIVERSAL_EMOJI}'>🔔</tg-emoji>"
    service_name = str(service_name).upper()
    emoji_id = UNIVERSAL_EMOJI
    for key, val in EMOJI_MAP.items():
        if key in service_name:
            emoji_id = val
            break
    return f"<tg-emoji emoji-id='{emoji_id}'>🔔</tg-emoji>"

def extract_otp(text):
    if not text: return "N/A"
    match = re.search(r'\d{4,8}', text.replace('-', '').replace(' ', ''))
    return match.group() if match else "N/A"

# ================ CORE ACTIONS ================

def handle_login():
    global SESSION_STATUS, BROWSER, CONTEXT, PAGE, PLAYWRIGHT_INST, session
    SESSION_STATUS = "🟡 Initializing..."
    update_active_hud()
    try:
        if not PLAYWRIGHT_INST:
            PLAYWRIGHT_INST = sync_playwright().start()
            BROWSER = PLAYWRIGHT_INST.chromium.launch(headless=True)
            CONTEXT = BROWSER.new_context(user_agent=MY_USER_AGENT)
            PAGE = CONTEXT.new_page()

        PAGE.goto(PANEL_URL, wait_until="networkidle", timeout=60000)
        if "login" in PAGE.url.lower():
            PAGE.wait_for_selector('input[name="username"]', timeout=20000)
            captcha_label = PAGE.locator('div.wrap-input100', has_text="What is").first
            match = re.search(r'(\d+)\s*\+\s*(\d+)', captcha_label.inner_text())
            if match:
                answer = str(int(match.group(1)) + int(match.group(2)))
                PAGE.type('input[name="username"]', PANEL_USER)
                PAGE.type('input[name="password"]', PANEL_PASS)
                PAGE.type('input[name="capt"]', answer)
                PAGE.click('button.login100-form-btn')
                time.sleep(10)

        PAGE.goto(MONITOR_PAGE, wait_until="networkidle")
        if "login" not in PAGE.url.lower():
            for cookie in CONTEXT.cookies(): session.cookies.set(cookie['name'], cookie['value'])
            SESSION_STATUS = "🟢 Valid"
            bot.send_message(ADMIN_ID, "✅ Auth Success: Panel Synced.")
            return True
    except Exception as e:
        SESSION_STATUS = "❌ Auth Error"
        bot.send_message(ADMIN_ID, f"❌ Login Error: <code>{str(e)[:50]}</code>")
    return False

def handle_logout():
    global SESSION_STATUS, BROWSER, IS_SCRAPPING, PLAYWRIGHT_INST, PAGE, CONTEXT
    IS_SCRAPPING = False
    try:
        if BROWSER: BROWSER.close()
        if PLAYWRIGHT_INST: PLAYWRIGHT_INST.stop()
    except: pass
    finally:
        BROWSER = CONTEXT = PAGE = PLAYWRIGHT_INST = None
        session.cookies.clear()
        SESSION_STATUS = "🔴 Logged Out"
        update_active_hud()

# ================ MONITOR WORKER (FIXED WITH SMART TIMING) ================

def monitor():
    global LAST_CHECK_TIME, seen_messages, IS_SCRAPPING, CMD_LOGIN_REQUESTED, CMD_LOGOUT_REQUESTED, SESSION_STATUS, is_initial_run, CMD_PREV_DAY_REQUESTED, PANEL_CURRENT_DATE
    
    headers = {
        "User-Agent": MY_USER_AGENT,
        "Referer": MONITOR_PAGE,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    while True:
        try:
            if CMD_LOGOUT_REQUESTED:
                handle_logout()
                CMD_LOGOUT_REQUESTED = False

            if CMD_LOGIN_REQUESTED:
                handle_login()
                CMD_LOGIN_REQUESTED = False

            if SESSION_STATUS == "🟢 Valid":
                # --- PREVIOUS DAY LOGIC ---
                if CMD_PREV_DAY_REQUESTED:
                    try:
                        ref_date_str = PANEL_CURRENT_DATE if (PANEL_CURRENT_DATE and len(PANEL_CURRENT_DATE) == 10) else datetime.now().strftime("%Y-%m-%d")
                        prev_date_obj = datetime.strptime(ref_date_str, "%Y-%m-%d") - timedelta(days=1)
                        prev_date = prev_date_obj.strftime("%Y-%m-%d")
                        
                        p_params = {
                            "fdate1": f"{prev_date} 00:00:00", 
                            "fdate2": f"{prev_date} 23:59:59",
                            "fg": "0", "sEcho": "1", "iDisplayStart": "0", "iDisplayLength": "100",
                            "iSortCol_0": "0", "sSortDir_0": "desc"
                        }
                        # Added longer timeout for stability
                        r = session.get(DATA_URL, params=p_params, headers=headers, timeout=25)
                        if r.status_code == 200:
                            p_data = r.json().get("aaData", [])
                            if p_data:
                                target_latest = p_data[:2] 
                                bot.send_message(ADMIN_ID, f"✅ <b>Prev Day Found ({prev_date}). Sending Latest 2...</b>")
                                for item in reversed(target_latest):
                                    send_otp_to_telegram({"num": item[3], "message": item[5], "cli": item[2]})
                                    time.sleep(2.5) # Anti-spam delay between forwards
                            else: 
                                bot.send_message(ADMIN_ID, f"⚠️ <b>No OTP for {prev_date}.</b>")
                    except Exception as e:
                        print(f"❌ Prev Day Logic Error: {e}")
                    CMD_PREV_DAY_REQUESTED = False

                # --- NORMAL SCRAPPING (REAL-TIME) ---
                if IS_SCRAPPING:
                    target_date = PANEL_CURRENT_DATE if (PANEL_CURRENT_DATE and len(PANEL_CURRENT_DATE) == 10) else datetime.now().strftime("%Y-%m-%d")
                    
                    params = {
                        "fdate1": f"{target_date} 00:00:00",
                        "fdate2": f"{target_date} 23:59:59",
                        "fg": "0", "sEcho": "1", "iDisplayStart": "0", "iDisplayLength": "50",
                        "iSortCol_0": "0", "sSortDir_0": "desc", "_" : str(int(time.time() * 1000))
                    }

                    try:
                        r = session.get(DATA_URL, params=params, headers=headers, timeout=25)
                        
                        if r.status_code == 200:
                            resp_data = r.json()
                            data_list = resp_data.get("aaData", [])
                            LAST_CHECK_TIME = datetime.now().strftime("%H:%M:%S")

                            if data_list:
                                try:
                                    first_row_ts = str(data_list[0][0])
                                    if " " in first_row_ts and len(first_row_ts) >= 10:
                                        extracted_date = first_row_ts.split(" ")[0]
                                        if PANEL_CURRENT_DATE != extracted_date:
                                            PANEL_CURRENT_DATE = extracted_date
                                except: pass 

                                if is_initial_run:
                                    for item in data_list:
                                        seen_messages.add(f"{item[0]}-{item[3]}-{item[5]}")
                                    is_initial_run = False

                                for item in reversed(data_list):
                                    uid = f"{item[0]}-{item[3]}-{item[5]}" 
                                    if uid not in seen_messages:
                                        seen_messages.add(uid)
                                        send_otp_to_telegram({"num": item[3], "message": item[5], "cli": item[2]})
                                        # Random delay between telegram forwards to look human
                                        time.sleep(random.uniform(2.5, 4.5))

                            update_active_hud()
                        else:
                            # If session disconnected, auto-request login
                            print(f"⚠️ Connection glitch (Status {r.status_code}), retrying...")
                            SESSION_STATUS = "🔴 Session Crashed"
                            CMD_LOGIN_REQUESTED = True
                    
                    except Exception as conn_err:
                        # Handle RemoteDisconnected or Timeout errors silently
                        print(f"⚠️ Network lag, retrying in 8s... {conn_err}")
                        time.sleep(8)
                        continue

        except Exception as e:
            print(f"❌ Worker Global Error: {e}")
            time.sleep(10) # Wait before retry on heavy errors

        # SMART DYNAMIC SLEEP: Avoid Panel Ban/Block
        # Range 10-15 seconds as requested to appear human
        time.sleep(random.uniform(10.0, 15.0))

# ================ BRANDING LAYOUT ================

def send_otp_to_telegram(item):
    global TOTAL_FORWARDED
    try:
        raw_cli = str(item.get("cli", "")).strip()
        raw_num = str(item.get("num", "")).strip()
        msg = str(item.get("message", "0")).strip()

        if any(char.isdigit() for char in raw_cli) and not any(char.isdigit() for char in raw_num):
            num, cli = raw_cli, raw_num
        else:
            num, cli = raw_num, raw_cli

        if not num or num == "0" or not msg or msg == "0": return

        msg_upper = msg.upper()
        for s_name in EMOJI_MAP.keys():
            if s_name in msg_upper:
                cli = s_name
                break

        otp = extract_otp(msg)
        country_name, flag_icon = get_country_info(num)
        service_emoji = get_custom_emoji_tag(cli)
        
        safe_msg = html.escape(msg)
        
        header_p = f"<tg-emoji emoji-id='{PERMANENT_HEADER_EMOJI}'>✨</tg-emoji>"
        service_l = f"<tg-emoji emoji-id='{SERVICE_LABEL_EMOJI}'>⚙️</tg-emoji>"
        otp_l = f"<tg-emoji emoji-id='{OTP_LABEL_EMOJI}'>🔐</tg-emoji>"
        
        text = (
            f"{header_p} <b>{country_name} {flag_icon} {cli} {service_emoji} OTP Received</b> {header_p}\n\n"
            f"{service_l} Service ⋮ <b>{cli}</b> {service_emoji}\n"
            f"🌎 Country ⋮ {country_name} {flag_icon}\n"
            f"☎️ Number ⋮ <code>{num}</code>\n\n"
            f"{otp_l} Your OTP ➤ <code>{otp}</code>\n\n"
            f"💌 <b>Full Message</b> ⋮\n"
            f"<pre>{safe_msg}</pre>"
        )
        
        while True:
            try:
                bot.send_message(GROUP_CHAT_ID, text, parse_mode="HTML")
                TOTAL_FORWARDED += 1
                break 
            except telebot.apihelper.ApiTelegramException as e:
                if e.error_code == 429:
                    wait_time = int(re.search(r'\d+', str(e)).group()) + 2
                    time.sleep(wait_time)
                else: 
                    print(f"❌ Telegram API Error on sending message: {e}")
                    break
    except Exception as e:
        print(f"❌ Formatting/Send Error: {e}")

# ================ HUD & COMMANDS ================

def build_hud_text():
    status = "🟢 SCRAPING" if IS_SCRAPPING else "🔴 STOPPED"
    display_date = PANEL_CURRENT_DATE if (PANEL_CURRENT_DATE and len(PANEL_CURRENT_DATE) == 10) else datetime.now().strftime("%Y-%m-%d")
    return (f"🎮 <b>PANEL HUD</b>\n━━━━━━━━━━━━━━━━━━━━\n🛰 Status: <code>{status}</code>\n"
            f"📅 Panel Date: <code>{display_date}</code>\n🕒 Check: <code>{LAST_CHECK_TIME}</code>\n"
            f"📩 Total: <code>{TOTAL_FORWARDED}</code>\n"
            f"🔑 Session: <code>{SESSION_STATUS}</code>\n━━━━━━━━━━━━━━━━━━━━")

def build_hud_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("▶️ START", callback_data="start_sc"),
               types.InlineKeyboardButton("⏸ STOP", callback_data="stop_sc"),
               types.InlineKeyboardButton("🔄 REFRESH", callback_data="refresh_sess"),
               types.InlineKeyboardButton("🚪 LOGOUT", callback_data="logout_panel"),
               types.InlineKeyboardButton("⏮ PREV DAY", callback_data="prev_day"))
    return markup

def update_active_hud():
    if HUD_MESSAGE_ID:
        try: bot.edit_message_text(chat_id=ADMIN_ID, message_id=HUD_MESSAGE_ID, text=build_hud_text(), reply_markup=build_hud_markup(), parse_mode="HTML")
        except: pass

@bot.message_handler(commands=['start', 'hud'])
def send_hud(message):
    global HUD_MESSAGE_ID
    if message.from_user.id == ADMIN_ID:
        sent = bot.send_message(message.chat.id, build_hud_text(), reply_markup=build_hud_markup(), parse_mode="HTML")
        HUD_MESSAGE_ID = sent.message_id

@bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID)
def handle_query(call):
    global IS_SCRAPPING, CMD_LOGIN_REQUESTED, CMD_LOGOUT_REQUESTED, CMD_PREV_DAY_REQUESTED
    bot.answer_callback_query(call.id)
    if call.data == "start_sc":
        IS_SCRAPPING = True
        if SESSION_STATUS != "🟢 Valid": CMD_LOGIN_REQUESTED = True
    elif call.data == "stop_sc": IS_SCRAPPING = False
    elif call.data == "refresh_sess": CMD_LOGIN_REQUESTED = True
    elif call.data == "logout_panel": CMD_LOGOUT_REQUESTED = True
    elif call.data == "prev_day": CMD_PREV_DAY_REQUESTED = True
    update_active_hud()

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    bot.infinity_polling()
