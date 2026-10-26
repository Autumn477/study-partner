import tkinter as tk
from tkinter import messagebox
from openai import OpenAI
from pynput import mouse, keyboard
import threading
import time
import csv
import os
from datetime import datetime

# ==========================================
# 1. THEME SETTINGS (ASTON MARTIN DBS)
# ==========================================
BG_COLOR = "#1c1f22"       
ACCENT_COLOR = "#4a151b"   
TEXT_MAIN = "#e8e4db"      
TEXT_HIGHLIGHT = "#ffffff" 
INPUT_BG = "#2a2e33"
FONT_MAIN = ("Georgia", 9) 
FONT_TITLE = ("Georgia", 11, "bold")
FONT_SMALL = ("Georgia", 8, "italic")

API_KEY = "sk-0134adf5b34f4fcabda80014578643b4"
LOG_FILE = "romanova_focus_log.csv"

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# ==========================================
# 2. STATE & TRACKING
# ==========================================
is_studying = False
current_mission = ""
last_activity = time.time()
drift_count = 0
start_time = 0

def reset_activity(*args):
    global last_activity
    last_activity = time.time()

mouse_listener = mouse.Listener(on_move=reset_activity, on_click=reset_activity)
keyboard_listener = keyboard.Listener(on_press=reset_activity)
mouse_listener.start()
keyboard_listener.start()

# ==========================================
# 3. AI & LOGIC FUNCTIONS
# ==========================================
def get_ai_nudge():
    prompt = f"You are the Romanova Mission Partner. The user is supposed to be focusing on: '{current_mission}'. She has drifted off for 3 minutes. Give her a short, strict, but elegant 1-2 sentence reminder in English to get back to work. Do not be polite, be commanding."
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Romanova, you are drifting. Return to your mission immediately."

def show_nudge_popup():
    nudge_window = tk.Toplevel(root)
    nudge_window.title("DRIFT DETECTED")
    nudge_window.geometry("350x180")
    nudge_window.attributes("-topmost", True)
    nudge_window.configure(bg=BG_COLOR)
    
    # Center the popup on the screen
    nudge_window.update_idletasks()
    width = nudge_window.winfo_width()
    height = nudge_window.winfo_height()
    x = (nudge_window.winfo_screenwidth() // 2) - (width // 2)
    y = (nudge_window.winfo_screenheight() // 2) - (height // 2)
    nudge_window.geometry(f'{width}x{height}+{x}+{y}')
    
    msg = get_ai_nudge()
    
    # White line
    tk.Frame(nudge_window, bg=TEXT_HIGHLIGHT, height=2, width=300).pack(pady=(15, 0))
    
    # CHANGED: fg=TEXT_HIGHLIGHT (white) and font slightly bigger
    lbl = tk.Label(nudge_window, text=msg, wraplength=300, bg=BG_COLOR, fg=TEXT_HIGHLIGHT, font=("Georgia", 11))
    lbl.pack(pady=15)
    
    btn = tk.Button(nudge_window, text="RETURN TO MISSION", bg=ACCENT_COLOR, fg=TEXT_HIGHLIGHT, 
                    font=("Georgia", 10, "bold"), relief="flat", activebackground=ACCENT_COLOR, activeforeground=TEXT_HIGHLIGHT, 
                    command=nudge_window.destroy)
    btn.pack(pady=5)

def check_inactivity():
    global last_activity, is_studying, drift_count
    while True:
        time.sleep(5) 
        if is_studying:
            if time.time() - last_activity > 180: 
                drift_count += 1
                show_nudge_popup()
                last_activity = time.time() 

def save_log():
    global start_time, drift_count, current_mission
    end_time = time.time()
    duration_mins = round((end_time - start_time) / 60, 1)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Mission", "Duration (mins)", "Drifts"])
        writer.writerow([date_str, current_mission, duration_mins, drift_count])

# ==========================================
# 4. UI FUNCTIONS
# ==========================================
def start_session():
    global is_studying, current_mission, drift_count, start_time
    mission = entry_mission.get().strip()
    if not mission:
        status_label.config(text="Error: Enter a mission.", fg="#ff4d4d")
        return
    
    current_mission = mission
    is_studying = True
    drift_count = 0
    start_time = time.time()
    last_activity = time.time()
    
    status_label.config(text=f"FOCUSING on {current_mission}", fg=TEXT_MAIN)
    btn_start.config(state=tk.DISABLED, bg="#333333")
    btn_stop.config(state=tk.NORMAL, bg=ACCENT_COLOR)
    entry_mission.config(state=tk.DISABLED)

def stop_session():
    global is_studying
    if is_studying:
        save_log()
        is_studying = False
        status_label.config(text="IDLE. Session saved.", fg=TEXT_MAIN)
        btn_start.config(state=tk.NORMAL, bg=ACCENT_COLOR)
        btn_stop.config(state=tk.DISABLED, bg="#333333")
        entry_mission.config(state=tk.NORMAL)

def send_chat():
    user_text = chat_entry.get().strip()
    if not user_text:
        return
    
    chat_entry.delete(0, tk.END)
    chat_history.config(state=tk.NORMAL)
    chat_history.insert(tk.END, f"\nYou: {user_text}\n", "user")
    chat_history.config(state=tk.DISABLED)
    chat_history.see(tk.END)
    
    chat_entry.config(state=tk.DISABLED)
    send_btn.config(state=tk.DISABLED, text="...")
    
    def get_response():
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": f"You are a study assistant. The user is currently studying: {current_mission}. Be concise, helpful, and direct."},
                    {"role": "user", "content": user_text}
                ]
            )
            reply = response.choices[0].message.content.strip()
        except Exception as e:
            reply = "Connection error."
        
        root.after(0, display_response, reply)

    threading.Thread(target=get_response, daemon=True).start()

def display_response(reply):
    chat_history.config(state=tk.NORMAL)
    chat_history.insert(tk.END, f"AI: {reply}\n", "ai")
    chat_history.config(state=tk.DISABLED)
    chat_history.see(tk.END)
    
    chat_entry.config(state=tk.NORMAL)
    send_btn.config(state=tk.NORMAL, text="SEND")
    chat_entry.focus()

# ==========================================
# 5. MAIN GUI & AUTO-POSITIONING
# ==========================================
root = tk.Tk()
root.title("Romanova")
root.configure(bg=BG_COLOR)
root.attributes("-topmost", True) 

window_width = 300
window_height = 600
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

x_position = screen_width - window_width - 20 
y_position = (screen_height - window_height) // 2 

root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

# --- TOP SECTION: MISSION ---
tk.Label(root, text="THE ROMANOVA PROTOCOL", bg=BG_COLOR, fg=TEXT_MAIN, font=FONT_TITLE).pack(pady=(10, 5))
tk.Frame(root, bg=TEXT_MAIN, height=1, width=250).pack(pady=5)

tk.Label(root, text="Current Mission:", bg=BG_COLOR, fg=TEXT_MAIN, font=FONT_MAIN).pack(pady=(5, 0))
entry_mission = tk.Entry(root, width=28, font=FONT_MAIN, bg=INPUT_BG, fg=TEXT_HIGHLIGHT, insertbackground=TEXT_HIGHLIGHT, relief="flat")
entry_mission.pack(pady=5, ipady=3)

btn_start = tk.Button(root, text="START MISSION", bg=ACCENT_COLOR, fg=TEXT_HIGHLIGHT, font=FONT_MAIN, relief="flat", command=start_session)
btn_start.pack(pady=(10, 5), fill=tk.X, padx=20)

btn_stop = tk.Button(root, text="END SESSION", bg="#333333", fg=TEXT_MAIN, font=FONT_MAIN, relief="flat", state=tk.DISABLED, command=stop_session)
btn_stop.pack(pady=5, fill=tk.X, padx=20)

status_label = tk.Label(root, text="Status: IDLE", bg=BG_COLOR, fg=TEXT_MAIN, font=FONT_SMALL)
status_label.pack(pady=5)

# --- BOTTOM SECTION: CHAT ---
tk.Frame(root, bg=INPUT_BG, height=1, width=250).pack(pady=10)
tk.Label(root, text="AI ASSISTANT", bg=BG_COLOR, fg=TEXT_MAIN, font=("Georgia", 9, "bold")).pack()

chat_history = tk.Text(root, height=12, width=32, bg=INPUT_BG, fg=TEXT_MAIN, font=FONT_MAIN, relief="flat", wrap=tk.WORD)
chat_history.pack(pady=5, padx=10)
chat_history.config(state=tk.DISABLED)
chat_history.tag_config("user", foreground="#ff9999")
chat_history.tag_config("ai", foreground=TEXT_MAIN)

chat_frame = tk.Frame(root, bg=BG_COLOR)
chat_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

chat_entry = tk.Entry(chat_frame, font=FONT_MAIN, bg=INPUT_BG, fg=TEXT_HIGHLIGHT, insertbackground=TEXT_HIGHLIGHT, relief="flat")
chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
chat_entry.bind("<Return>", lambda event: send_chat())

send_btn = tk.Button(chat_frame, text="SEND", bg=ACCENT_COLOR, fg=TEXT_HIGHLIGHT, font=("Georgia", 8, "bold"), relief="flat", command=send_chat)
send_btn.pack(side=tk.RIGHT, padx=(5, 0), ipadx=5, ipady=1)

threading.Thread(target=check_inactivity, daemon=True).start()

root.mainloop()