import os
import pygame
import threading
from pynput import keyboard
import tkinter as tk
from tkinter import ttk
import sys
import winreg

# base_path 세팅
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    exe_path = sys.executable
else:
    base_path = os.path.dirname(__file__)
    exe_path = os.path.abspath(__file__)

SOUND_DIR = os.path.join(base_path, "sounds")
ICON_PATH = os.path.join(base_path, "icon.ico")

# 초기 설정
current_volume = 0.5
last_volume = 0.5
is_muted = False
is_shift_pressed = False

# pygame 초기화
pygame.mixer.init()

# 문자 매핑
char_sound_map = {ch: f"{ch}.wav" for ch in 'abcdefghijklmnopqrstuvwxyz0123456789'}
safe_filename_map = {
    '?': 'question.wav', '/': 'slash.wav', '\\': 'backslash.wav',
    '*': 'asterisk.wav', ':': 'colon.wav', '"': 'quote.wav',
    '<': 'less_than.wav', '>': 'greater_than.wav', '|': 'pipe.wav'
}
shift_combos = {
    '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
    '6': '^', '7': '&', '8': '*', '9': '(', '0': ')',
    '-': '_', '=': '+', '[': '{', ']': '}', '\\': '|',
    ';': ':', "'": '"', ',': '<', '.': '>', '/': '?'
}
special_keys = {
    'space': 'space.wav', 'enter': 'enter.wav', 'tab': 'tab.wav',
    'backspace': 'backspace.wav', 'caps_lock': 'caps_lock.wav',
    'shift': 'shift.wav', 'shift_r': 'shift.wav', 'esc': 'esc.wav'
}

sounds = {}

def load_sound(key, filename):
    final_filename = filename
    name_only = filename.replace(".wav", "")
    if name_only in safe_filename_map:
        final_filename = safe_filename_map[name_only]
    path = os.path.join(SOUND_DIR, final_filename)
    if os.path.exists(path):
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(current_volume)
            sounds[key] = sound
        except Exception: pass

for key, filename in {**char_sound_map, **special_keys}.items():
    load_sound(key, filename)
for k, symbol in shift_combos.items():
    load_sound(symbol, f"{symbol}.wav")

def set_all_volume(vol):
    for snd in sounds.values(): snd.set_volume(vol)

def on_press(key):
    global is_shift_pressed, is_muted
    if is_muted: return
    target_key = None
    try:
        k = key.char
        if k is None: return 
        if is_shift_pressed:
            target_key = shift_combos.get(k, k.lower())
        else: target_key = k.lower()
    except AttributeError:
        k = str(key).replace("Key.", "").lower()
        if k in ['shift', 'shift_r']: is_shift_pressed = True
        target_key = k

    if target_key in sounds: sounds[target_key].play()

def on_release(key):
    global is_shift_pressed
    try:
        name = getattr(key, 'name', str(key).replace("Key.", "")).lower()
        if name in ['shift', 'shift_r']: is_shift_pressed = False
    except AttributeError: pass

# --- 레지스트리 설정 ---
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "AC_Keyboard_Sound"

def check_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return val == exe_path
    except WindowsError: return False

def set_startup(enable):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
        if enable: winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try: winreg.DeleteValue(key, APP_NAME)
            except WindowsError: pass
        winreg.CloseKey(key)
    except Exception: pass

# GUI
def run_gui():
    global current_volume, last_volume, is_muted
    BG_COLOR, FG_COLOR = "#FDF6E3", "#5B8C5A"

    root = tk.Tk()
    root.title("동물의 숲 키보드")
    root.geometry("340x220")
    root.resizable(False, False)
    root.configure(bg=BG_COLOR)

    if os.path.exists(ICON_PATH):
        try: root.iconbitmap(ICON_PATH)
        except Exception: pass

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TScale", background=BG_COLOR, troughcolor="#E0DBC5", sliderlength=20)
    style.configure("TCheckbutton", background=BG_COLOR, font=("Malgun Gothic", 9))

    # [중요] 프로그램이 값을 바꿀 때는 이벤트를 무시하기 위한 플래그
    is_programmatic_change = False

    def on_slider_change(val):
        nonlocal is_programmatic_change
        # 프로그램이 내부적으로 값을 바꾸는 중이면 무시 (무한루프 방지)
        if is_programmatic_change:
            return

        global current_volume, is_muted
        val = float(val)

        # 사용자가 슬라이더를 0 이상으로 움직였는데 음소거 상태라면 해제
        if is_muted and val > 0:
            toggle_mute(force_unmute=True, target_val=val)
            return # toggle_mute 안에서 처리하므로 여기선 종료

        current_volume = val
        set_all_volume(current_volume)
        volume_label.config(text=f"볼륨: {int(current_volume*100)}%")

    def toggle_mute(force_unmute=False, target_val=None):
        global is_muted, current_volume, last_volume
        nonlocal is_programmatic_change
        
        # 슬라이더 값 변경 시 이벤트가 발생하지 않도록 잠금
        is_programmatic_change = True

        if force_unmute:
            # 강제 음소거 해제 (슬라이더 조작 시)
            is_muted = False
            current_volume = target_val if target_val is not None else last_volume
            if current_volume == 0: current_volume = 0.5
            
            mute_btn.config(text="🔊")
            volume_slider.set(current_volume) # 여기서 이벤트 발생하지만 위 플래그로 무시됨
            volume_label.config(text=f"볼륨: {int(current_volume*100)}%")
        
        elif not is_muted:
            # 음소거 켜기
            last_volume = current_volume
            current_volume = 0
            is_muted = True
            
            mute_btn.config(text="🔇")
            volume_slider.set(0)
            volume_label.config(text="볼륨: 0%")
            
        else:
            # 음소거 끄기 (버튼 클릭 시)
            is_muted = False
            if last_volume == 0: last_volume = 0.5
            current_volume = last_volume
            
            mute_btn.config(text="🔊")
            volume_slider.set(current_volume)
            volume_label.config(text=f"볼륨: {int(current_volume*100)}%")
        
        set_all_volume(current_volume)
        
        # 잠금 해제
        is_programmatic_change = False

    def on_startup_toggle():
        set_startup(startup_var.get())

    title_label = tk.Label(root, text="Animal Crossing Key Sound", 
                           font=("Malgun Gothic", 12, "bold"), bg=BG_COLOR, fg=FG_COLOR)
    title_label.pack(pady=(20, 10))

    vol_frame = tk.Frame(root, bg=BG_COLOR)
    vol_frame.pack(fill="x", padx=40)

    top_row = tk.Frame(vol_frame, bg=BG_COLOR)
    top_row.pack(fill="x", pady=5)
    
    volume_label = tk.Label(top_row, text=f"볼륨: {int(current_volume*100)}%", 
                            font=("Malgun Gothic", 10), bg=BG_COLOR, fg="#888888")
    volume_label.pack(side="left")

    mute_btn = tk.Button(top_row, text="🔊", command=lambda: toggle_mute(), 
                         font=("Malgun Gothic", 10), bg="#E0DBC5", bd=0, cursor="hand2")
    mute_btn.pack(side="right")

    volume_slider = ttk.Scale(vol_frame, from_=0, to=1, orient="horizontal",
                              value=current_volume, command=on_slider_change, style="TScale")
    volume_slider.pack(fill="x")

    startup_var = tk.BooleanVar(value=check_startup())
    chk_startup = ttk.Checkbutton(root, text="윈도우 시작 시 자동 실행", 
                                  variable=startup_var, command=on_startup_toggle,
                                  style="TCheckbutton")
    chk_startup.pack(pady=20)

    info_label = tk.Label(root, text="프로그램을 닫으면 소리가 안 납니다!", 
                          font=("Malgun Gothic", 8), bg=BG_COLOR, fg="#AAAAAA")
    info_label.pack(side="bottom", pady=10)

    root.mainloop()

def main():
    threading.Thread(target=run_listener, daemon=True).start()
    run_gui()

def run_listener():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    main()