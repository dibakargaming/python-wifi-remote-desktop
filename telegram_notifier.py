import socket
import subprocess
import requests
import configparser
import os
import time
import random
import string
server_process = None
tunnel_process = None

def log_message(msg):
    with open("bot_log.txt", "a") as f:
        f.write(f"{time.ctime()}: {msg}\n")
    print(msg)

def get_local_ip():
    """Finds the local IP address of this PC."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Use a public IP to ensure the OS selects the active internet interface
        s.connect(('8.8.8.8', 80))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def wait_for_network(timeout=60):
    """Waits for an active internet connection by pinging a public DNS."""
    start_time = time.time()
    print("Waiting for network connection...")
    while time.time() - start_time < timeout:
        try:
            # Try to connect to Google DNS on port 53 (DNS)
            socket.create_connection(("8.8.8.8", 53), timeout=1)
            print("Network connection established!")
            return True
        except OSError:
            time.sleep(1)
    print("Warning: Network timeout reached.")
    return False

def get_wifi_info():
    """Extracts the active WiFi SSID and Signal Strength using Windows netsh command."""
    try:
        # Run the netsh command and capture the output
        result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True)
        output = result.stdout

        ssid = "Unknown"
        signal = "Unknown"
        
        # Parse the output for SSID and Signal
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith("SSID") and not line.startswith("BSSID"):
                ssid = line.split(":", 1)[1].strip()
            elif line.startswith("Signal"):
                signal = line.split(":", 1)[1].strip()
                
        return ssid, signal
    except Exception as e:
        print(f"Error getting WiFi info: {e}")
        return "Error", "Error"

def is_server_running(port=5000):
    """Check if the streaming server is running by trying to connect to its port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_server():
    global server_process
    if not is_server_running():
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(script_dir, 'server.py')
        try:
            CREATE_NO_WINDOW = 0x08000000
            server_process = subprocess.Popen(['python', server_path], creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Failed to start server with creationflags: {e}")
            server_process = subprocess.Popen(['python', server_path])
        return True
    return False

def stop_server():
    global server_process
    stop_tunnel() # Also stop tunnel if server stops
    if server_process:
        try:
            server_process.terminate()
            server_process.wait(timeout=3)
        except Exception:
            try:
                server_process.kill()
            except:
                pass
        server_process = None
        return True
    
    # Fallback: kill any python process running server.py
    try:
        subprocess.run('wmic process where "name=\'python.exe\' and commandline like \'%server.py%\'" call terminate', capture_output=True, shell=True)
        return True
    except:
        pass
    return False

def start_tunnel():
    global tunnel_process
    if tunnel_process and tunnel_process.poll() is None:
        stop_tunnel()
    
    # Generate random 10-character token
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    # Cloudflared path
    cf_path = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
    if not os.path.exists(cf_path):
        cf_path = "cloudflared" # Fallback to PATH
        
    try:
        CREATE_NO_WINDOW = 0x08000000
        # Start Cloudflare Quick Tunnel
        tunnel_process = subprocess.Popen(
            [cf_path, 'tunnel', '--url', 'http://localhost:5000'], 
            creationflags=CREATE_NO_WINDOW,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        
        # We need to read stderr to find the URL
        public_url = None
        start_time = time.time()
        while time.time() - start_time < 20: # Wait up to 20s for URL
            if not tunnel_process or not tunnel_process.stderr:
                break
            line = tunnel_process.stderr.readline()
            if not line:
                if tunnel_process.poll() is not None:
                    break
                time.sleep(0.5)
                continue
                
            log_message(f"CF Log: {line.strip()}")
            if "trycloudflare.com" in line:
                # Extract URL: INF |  https://random-words.trycloudflare.com
                parts = line.split("https://")
                if len(parts) > 1:
                    public_url = "https://" + parts[1].split()[0]
                    break
        
        if not public_url:
            stderr_out = tunnel_process.stderr.read() if tunnel_process.stderr else "No stderr"
            log_message(f"Cloudflare failed to provide URL: {stderr_out}")
            return f"Error: Could not retrieve tunnel URL.", None
            
        # Set the token on the local server
        try:
            requests.post("http://127.0.0.1:5000/set_token", json={"token": token}, timeout=5)
            log_message(f"Security token set: {token}")
        except Exception as e:
            log_message(f"Failed to set token on server: {e}")
            return f"Error: Server not responding to token set.", None
            
        log_message(f"Cloudflare tunnel started: {public_url}")
        return public_url, token
    except Exception as e:
        log_message(f"Failed to start cloudflared: {e}")
        return str(e), None

def stop_tunnel():
    global tunnel_process
    if tunnel_process:
        try:
            tunnel_process.terminate()
            tunnel_process.wait(timeout=3)
        except:
            try:
                tunnel_process.kill()
            except:
                pass
        tunnel_process = None
    
    # Force kill any remaining cloudflared
    try:
        subprocess.run('taskkill /f /im cloudflared.exe', capture_output=True, shell=True)
    except:
        pass
        
    # Clear token on server
    try:
        requests.post("http://127.0.0.1:5000/set_token", json={"token": None}, timeout=2)
    except:
        pass

# Removed Ngrok URL Helper as we handle CF URL in start_tunnel

def send_telegram_message(bot_token, chat_id, message):
    """Sends a text message to a specific Telegram Chat ID."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Message sent successfully!")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def send_telegram_keyboard(bot_token, chat_id, text):
    """Sends a message with an inline keyboard depending on server status."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    if is_server_running():
        keyboard = {"inline_keyboard": [
            [{"text": "🛑 Stop Stream", "callback_data": "stop_stream"}],
            [{"text": "🌍 Anywhere", "callback_data": "anywhere"}, {"text": "🏠 Home", "callback_data": "home"}]
        ]}
    else:
        keyboard = {"inline_keyboard": [[{"text": "▶️ Start Stream", "callback_data": "start_stream"}]]}

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Keyboard sent successfully!")
    except Exception as e:
        print(f"Failed to send keyboard: {e}")

def handle_updates(bot_token, valid_chat_ids, ip_address, ssid, signal):
    """Long polling loop for Telegram updates."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    # Drain old updates on startup to avoid spamming replies to old messages
    offset = 0
    try:
        startup_resp = requests.get(url, params={"offset": 0, "timeout": 5})
        startup_data = startup_resp.json()
        if startup_data.get("ok") and startup_data.get("result"):
            offset = startup_data["result"][-1]["update_id"] + 1
            requests.get(url, params={"offset": offset, "timeout": 5})
    except Exception as e:
        print(f"Failed to drain old updates: {e}")

    print("Listening for Telegram messages...")
    
    last_telegram_interaction = time.time()
    
    while True:
        try:
            params = {"offset": offset, "timeout": 30}
            response = requests.get(url, params=params, timeout=40)
            data = response.json()
            
            if data.get("ok"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    
                    if "callback_query" in update:
                        callback_id = update["callback_query"]["id"]
                        callback_data = update["callback_query"]["data"]
                        msg_chat_id = str(update["callback_query"]["message"]["chat"]["id"])
                        
                        if msg_chat_id not in valid_chat_ids:
                            continue
                        
                        last_telegram_interaction = time.time()
                        
                        if callback_data == "start_stream":
                            if start_server():
                                text = "✅ Server started."
                            else:
                                text = "⚠️ Server is already running."
                        elif callback_data == "stop_stream":
                            if stop_server():
                                text = "🛑 Server stopped."
                            else:
                                text = "⚠️ Server is already offline."
                        elif callback_data == "anywhere":
                            log_message("Anywhere button clicked. Starting Cloudflare Tunnel.")
                            public_url, token = start_tunnel()
                            if public_url and not public_url.startswith("Error"):
                                full_url = f"{public_url}/?token={token}"
                                text = (
                                    f"🌍 <b>Anywhere Access (Secured):</b>\n\n"
                                    f"🔗 <b>Link:</b> {full_url}\n\n"
                                    f"⚠️ <i>This is a bandwidth-free link. Clicking 'Anywhere' again will regenerate the link and token.</i>"
                                )
                                send_telegram_message(bot_token, msg_chat_id, text)
                                text = "Bandwidth-free link generated! 🔓"
                            else:
                                log_message(f"Start Tunnel failed: {public_url}")
                                text = "⚠️ Failed to start Tunnel."
                                send_telegram_message(bot_token, msg_chat_id, f"❌ <b>Tunnel Error:</b>\n{public_url}")
                        elif callback_data == "home":
                            stop_tunnel()
                            log_message("Home button clicked. Tunnel stopped.")
                            local_url = f"http://{ip_address}:5000"
                            text = f"🏠 <b>Home Access:</b>\n{local_url}"
                            send_telegram_message(bot_token, msg_chat_id, text)
                            text = "Home mode active!"
                                
                        requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": callback_id, "text": text})
                        send_telegram_keyboard(bot_token, msg_chat_id, "<b>Remote Desktop Control</b>")
                        
                    elif "message" in update and "text" in update["message"]:
                        msg_chat_id = str(update["message"]["chat"]["id"])
                        msg_text_raw = update["message"]["text"]
                        
                        if msg_chat_id not in valid_chat_ids:
                            continue
                        
                        last_telegram_interaction = time.time()
                        msg_text = msg_text_raw.lower()
                        
                        if msg_text in ["hi", "hello", "hey", "start", "/start", "help", "menu", "?", "status"]:
                            welcome_msg = (
                                "👋 Hello! I am your PC Monitor Bot.\n\n"
                                "<b>🏠 Default Connection: Home Network</b>\n"
                                f"<b>Local IP:</b> <code>http://{ip_address}:5000</code>\n\n"
                                "Click <b>Anywhere</b> to enable remote access."
                            )
                            send_telegram_keyboard(bot_token, msg_chat_id, welcome_msg)
                        else:
                            reply_text = "I received your message! Send 'Menu' or 'Hi' to see the Remote Desktop controls."
                            send_telegram_message(bot_token, msg_chat_id, reply_text)
            else:
                print(f"Telegram API Error: {data}")
                time.sleep(5)
                            
        except requests.exceptions.Timeout:
            pass  # Proceed to check inactivity even on timeout
        except Exception as e:
            print(f"Error checking updates: {e}")
            time.sleep(5)
            
        # Check for inactivity
        if is_server_running():
            try:
                status_resp = requests.get("http://127.0.0.1:5000/status", timeout=2)
                if status_resp.status_code == 200:
                    server_last_interaction = status_resp.json().get("last_interaction", time.time())
                    
                    time_since_telegram = time.time() - last_telegram_interaction
                    time_since_server = time.time() - server_last_interaction
                    
                    # 600 seconds = 10 minutes
                    if time_since_telegram > 600 and time_since_server > 600:
                        print("Auto-stopping server due to 10 minutes of inactivity.")
                        stop_server()
                        for cid in valid_chat_ids:
                            send_telegram_message(bot_token, cid, "🛑 <b>Server auto-stopped</b> due to 10 minutes of inactivity.")
            except Exception as e:
                pass  # Server might not be fully up yet or is busy

if __name__ == "__main__":
    # Ensure the script runs in its own directory (important for autostart/boot)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Wait for active internet connection to avoid bot crashing immediately on boot
    wait_for_network(timeout=60)
    
    # Read configuration file
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config = configparser.ConfigParser()
    
    if not os.path.exists(config_path):
        example_path = os.path.join(os.path.dirname(__file__), 'config.example.ini')
        if os.path.exists(example_path):
            import shutil
            shutil.copy(example_path, config_path)
            print("Created config.ini from template. Please update it with your credentials.")
            try:
                subprocess.run(['start', '', config_path], shell=True)
            except Exception:
                pass
        else:
            print("Error: config.ini not found! Please create it with your Bot Token and Chat ID.")
        exit(1)
        
    config.read(config_path)
    
    try:
        bot_token = config.get('telegram', 'BOT_TOKEN')
        chat_id_str = config.get('telegram', 'CHAT_ID')
        chat_ids = [c.strip() for c in chat_id_str.split(',') if c.strip()]
        chat_ids = list(set(chat_ids))  # Remove duplicates to prevent spamming!
        
        if bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE" or not chat_ids or chat_ids[0] == "YOUR_TELEGRAM_CHAT_ID_HERE":
            print("Error: You must update config.ini with your actual Token and Chat ID.")
            exit(1)
            
    except (configparser.NoSectionError, configparser.NoOptionError):
        print("Error: config.ini is missing the [telegram] section, BOT_TOKEN, or CHAT_ID.")
        exit(1)

    # Gather System Information
    ip_address = get_local_ip()
    ssid, signal = get_wifi_info()

    # Format the message
    welcome_msg = (
        "<b>💻 PC is Online!</b>\n\n"
        "<b>🏠 Default Connection: Home Network</b>\n"
        f"<b>Remote Desktop IP:</b> <code>http://{ip_address}:5000</code>\n\n"
        f"<b>WiFi Network:</b> {ssid}\n"
        f"<b>Signal Strength:</b> {signal}\n\n"
        "Click <b>Anywhere</b> to enable remote access."
    )

    # Send Notification
    print("Sending Telegram Notification...")
    for cid in chat_ids:
        send_telegram_keyboard(bot_token, cid, welcome_msg)

    # Start the listening loop and keep script running
    handle_updates(bot_token, chat_ids, ip_address, ssid, signal)
