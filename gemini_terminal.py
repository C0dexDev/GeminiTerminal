import argparse
import sys
import os
import time
import threading
import re
import json
import pyperclip
import subprocess
import os
from google import genai
from PIL import ImageGrab, Image
from io import BytesIO
from urllib.parse import unquote
from pathlib import Path

# --- CONFIGURATION FILENAME ---
CONFIG_FILE = os.path.join(str(Path.home()), ".gemini_config.json")

def load_api_key():
    """Loads the API key from a central hidden file in the Home directory."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get("api_key")
        except (json.JSONDecodeError, IOError):
            return None
    return os.environ.get("GOOGLE_API_KEY")

def save_api_key(key):
    """Saves the API key to the central hidden file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"api_key": key}, f)
        # Set restrictive permissions on Linux (owner read/write only)
        if os.name != 'nt':
            os.chmod(CONFIG_FILE, 0o600)
    except IOError as e:
        print(f"\033[38;5;196m[!] Error saving config: {e}\033[0m")

# Initialize Client
current_key = load_api_key()
client = genai.Client(api_key=current_key) if current_key else None

# --- PALETTE ---
BORDER = '\033[38;5;28m'     
AI_TEXT = '\033[38;5;51m'     
USER_NAME = '\033[1;37m'      
AI_NAME = '\033[1;38;5;45m'   
CODE_BLOCK = '\033[38;5;220m' 
INFO = '\033[38;5;214m'       
SUCCESS = '\033[38;5;82m'      
ERROR = '\033[38;5;196m'      
RESET = '\033[0m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(model_name):
    is_pro = "pro" in model_name.lower()
    tier_label = "PAID TIER" if is_pro else "FREE TIER"
    width = 65
    text_title = f" GEMINI TERMINAL [{tier_label}]"
    text_model = f" Model: {model_name}"
    
    print(f"{BORDER}╔" + "═" * (width - 2) + "╗")
    spaces_title = " " * (width - len(text_title) - 2)
    print(f"{BORDER}║{RESET} {USER_NAME}GEMINI TERMINAL{RESET} {SUCCESS if is_pro else INFO}[{tier_label}]{RESET}{spaces_title}{BORDER}║")
    spaces_model = " " * (width - len(text_model) - 2)
    print(f"{BORDER}║{RESET} {BORDER}Model: {AI_TEXT}{model_name}{RESET}{spaces_model}{BORDER}║")
    print(f"{BORDER}╚" + "═" * (width - 2) + f"╝{RESET}")
    print(f"{INFO}>> 'exit' to quit | 'clear' to wipe | 'choose' to switch models{RESET}")
    print(f"{INFO}>> 'setapikey <key>' to save your key permanently{RESET}")
    print(f"{INFO}>> Append '/cb' to include clipboard (Text/Images/Files){RESET}\n")

def spinner_task(stop_event, message):
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    idx = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r{BORDER}[{spinner[idx]}]{RESET} {AI_TEXT}{message}{RESET}")
        sys.stdout.flush()
        idx = (idx + 1) % len(spinner)
        time.sleep(0.07)
    sys.stdout.write('\r' + ' ' * (len(message) + 12) + '\r')

def parse_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', f'{USER_NAME}\\1{RESET}{AI_TEXT}', text)
    text = re.sub(r'```(.*?)```', f'{CODE_BLOCK}```\\1```{RESET}{AI_TEXT}', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', f'{CODE_BLOCK}\\1{AI_TEXT}', text)
    return text

def get_clipboard_content():
    items = []
    
    # --- WINDOWS LOGIC ---
    if os.name == 'nt':
        raw_cb = ImageGrab.grabclipboard()
        if isinstance(raw_cb, list):
            for path in raw_cb:
                if os.path.isfile(path):
                    items.extend(read_file_safe(path))
        elif isinstance(raw_cb, Image.Image):
            items.append(raw_cb)
            print(f"{SUCCESS}[+] Attached Screenshot.{RESET}")
    
    # --- LINUX LOGIC ---
    else:
        # 1. Try to grab Image first
        try:
            process = subprocess.Popen(['xclip', '-selection', 'clipboard', '-t', 'image/png', '-o'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            img_data, _ = process.communicate()
            if img_data:
                items.append(Image.open(BytesIO(img_data)))
                print(f"{SUCCESS}[+] Attached Image from Clipboard.{RESET}")
        except: pass

        # 2. Try to grab Files (URI List)
        if not items:
            try:
                process = subprocess.Popen(['xclip', '-selection', 'clipboard', '-t', 'text/uri-list', '-o'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                uri_data, _ = process.communicate()
                if uri_data:
                    # Clean paths: remove 'file://', unquote URL encoding, and strip whitespace
                    paths = [unquote(p.decode('utf-8').strip().replace('file://', '')) for p in uri_data.splitlines()]
                    for path in paths:
                        if os.path.isfile(path):
                            items.extend(read_file_safe(path))
            except: pass

    # --- GENERIC TEXT FALLBACK ---
    if not items:
        txt = pyperclip.paste().strip()
        if txt:
            # Check if the pasted text itself is a valid path (just in case)
            potential_path = unquote(txt.replace('file://', ''))
            if os.path.isfile(potential_path):
                items.extend(read_file_safe(potential_path))
            else:
                items.append(f"\n[Clipboard Content]\n{txt}\n")
                print(f"{SUCCESS}[+] Attached Text Fragment.{RESET}")
            
    return items

def read_file_safe(path):
    """Helper to read file content based on extension."""
    filename = os.path.basename(path)
    ext = filename.lower().split('.')[-1]
    
    if ext in ['png', 'jpg', 'jpeg', 'webp', 'bmp']:
        try:
            print(f"{SUCCESS}[+] Reading Image: {filename}{RESET}")
            return [Image.open(path)]
        except: return []
    else:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"{SUCCESS}[+] Reading Source: {filename}{RESET}")
                return [f"\n--- File: {filename} ---\n{content}\n"]
        except UnicodeDecodeError:
            print(f"{ERROR}[!] Skipping binary file: {filename}{RESET}")
            return []

def main():
    global client
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--flash", action="store_true")
    group.add_argument("-t", "--tough", action="store_true")
    args = parser.parse_args()

    current_model = 'gemini-2.5-flash' if args.flash else 'gemini-2.5-pro'

    clear_screen()
    print_header(current_model)

    if not client:
        print(f"{ERROR}[!] No API Key found. Use 'setapikey <key>' to start.{RESET}")
    
    chat_session = client.chats.create(model=current_model) if client else None

    while True:
        try:
            user_input = input(f"{USER_NAME}User > {RESET}").strip()
        except (KeyboardInterrupt, EOFError): break

        if not user_input: continue
        cmd_parts = user_input.split()
        cmd = cmd_parts[0].lower()

        if cmd in ['exit', 'quit']: break
        if cmd == 'clear':
            clear_screen()
            print_header(current_model)
            continue
        
        if cmd == 'setapikey':
            if len(cmd_parts) > 1:
                new_key = cmd_parts[1]
                save_api_key(new_key)
                client = genai.Client(api_key=new_key)
                chat_session = client.chats.create(model=current_model)
                print(f"{SUCCESS}[+] API Key saved!{RESET}")
            continue

        if cmd == 'choose':
            try:
                models = [m.name for m in client.models.list() if 'gemini' in m.name.lower()]
                for i, m in enumerate(models): print(f"[{i:02d}] {m}")
                choice = input(f"\n{USER_NAME}Select # (Enter to cancel): {RESET}")
                if choice.isdigit() and int(choice) < len(models):
                    current_model = models[int(choice)]
                    chat_session = client.chats.create(model=current_model)
                    clear_screen()
                    print_header(current_model)
            except Exception as e:
                print(f"{ERROR}[!] Error: {e}{RESET}")
            continue

        if not chat_session: continue

        attach = False
        if user_input.endswith('/cb'):
            attach = True
            user_input = user_input[:-3].strip()

        parts = [user_input] if user_input else []
        if attach: parts.extend(get_clipboard_content())
        if not parts: continue

        stop_ev = threading.Event()
        t = threading.Thread(target=spinner_task, args=(stop_ev, "Analyzing..."))
        t.start()

        try:
            resp = chat_session.send_message(parts)
            stop_ev.set()
            t.join()
            print(f"{AI_NAME}Gemini >{RESET}")
            print(f"{BORDER}━" * 65 + f"{RESET}")
            print(f"{AI_TEXT}{parse_markdown(resp.text.strip())}{RESET}")
            print(f"{BORDER}━" * 65 + f"{RESET}")
        except Exception as e:
            stop_ev.set()
            t.join()
            print(f"\n{ERROR}[!] API Error: {e}{RESET}")

if __name__ == "__main__":
    main()
