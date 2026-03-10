import socket
import subprocess
import requests
import configparser
import os
import time
from datetime import datetime

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

def is_server_running():
    """Checks if the remote desktop streaming server is running on port 5000."""
    try:
        # Try to connect to localhost on port 5000
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 5000))
        sock.close()
        return result == 0
    except Exception:
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

def send_telegram_message(bot_token, chat_id, message, reply_markup=None):
    """Sends a text message to a specific Telegram Chat ID."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Message sent successfully!")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def get_main_menu_keyboard(is_running):
    """Returns the inline keyboard markup for the main menu dynamically based on server status."""
    stream_button = {"text": "🛑 Stop Stream", "callback_data": "stop_stream"} if is_running else {"text": "▶️ Start Stream", "callback_data": "start_stream"}
    
    return {
        "inline_keyboard": [
            [
                stream_button,
                {"text": "🔄 Check Status", "callback_data": "check_status"}
            ]
        ]
    }

def start_streaming_server():
    """Starts the server.py script in the background."""
    if is_server_running():
        return "Server is already running!"
        
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(script_dir, "server.py")
        
        # Start the script detached
        if os.name == 'nt':
            # On Windows, use pythonw to hide console and DETACHED_PROCESS flag
            subprocess.Popen(
                ["pythonw.exe", server_path],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                cwd=script_dir
            )
        else:
            # On Linux/Mac
            subprocess.Popen(["python3", server_path], cwd=script_dir, start_new_session=True)
            
        time.sleep(2) # Give it a moment to start up
        if is_server_running():
            return "✅ Stream started successfully!"
        else:
            return "⚠️ Attempted to start stream, but it may have failed."
    except Exception as e:
        return f"❌ Failed to start stream: {e}"

def stop_streaming_server():
    """Stops the server.py script by terminating its process."""
    if not is_server_running():
        return "Server is already offline!"
        
    try:
        if os.name == 'nt':
            # On Windows, finding the process listening on port 5000 and killing it
            cmd = 'netstat -ano | findstr LISTENING | findstr :5000'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            output = result.stdout.strip()
            
            pids_killed = 0
            if output:
                lines = output.split('\n')
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid_str = parts[-1]
                        if pid_str.isdigit() and pid_str != "0":
                            subprocess.run(['taskkill', '/F', '/PID', pid_str], capture_output=True)
                            pids_killed += 1
                            
            if pids_killed > 0:
                time.sleep(1)
                if not is_server_running():
                    return "🛑 Stream stopped successfully!"
                else:
                    return "⚠️ Attempted to stop stream, but port is still active."
            return "Could not find the server process to stop."
        else:
            # Basic fallback for Linux/Mac using pkill
            subprocess.run(["pkill", "-f", "server.py"])
            time.sleep(1)
            if not is_server_running():
                return "🛑 Stream stopped successfully!"
            else:
                return "⚠️ Attempted to stop stream, but it failed."
    except Exception as e:
        return f"❌ Failed to stop stream: {e}"

def answer_callback_query(bot_token, callback_query_id, text=None):
    """Answers a callback query to stop the loading spinner on the button."""
    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        requests.post(url, json=payload)
    except Exception:
        pass

def get_status_message():
    """Gathers system information and formats the status message."""
    ip_address = get_local_ip()
    ssid, signal = get_wifi_info()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    server_status = "🟢 Online" if is_server_running() else "🔴 Offline"
    
    message = (
        "<b>💻 PC is Online!</b>\n\n"
        f"<b>Time:</b> {current_time}\n"
        f"<b>Remote Desktop IP:</b> <code>http://{ip_address}:5000</code>\n"
        f"<b>Stream Status:</b> {server_status}\n\n"
        f"<b>WiFi Network:</b> {ssid}\n"
        f"<b>Signal Strength:</b> {signal}\n"
    )
    return message

def poll_telegram(bot_token, chat_id):
    """Continuously polls Telegram for incoming messages."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    offset = None
    
    while True:
        try:
            if offset is not None:
                params = {'timeout': 30, 'offset': offset}
            else:
                params = {'timeout': 30}
                
            response = requests.get(url, params=params, timeout=40)
            data = response.json()
            
            if data.get('ok'):
                for result in data['result']:
                    offset = result['update_id'] + 1
                    
                    # Handle text messages
                    if 'message' in result:
                        message = result.get('message', {})
                        msg_text = message.get('text', '')
                        msg_chat_id = str(message.get('chat', {}).get('id', ''))
                        
                        # Only respond to our configured chat_id
                        if msg_text and msg_chat_id == str(chat_id):
                            print(f"Received message from authorized user: {msg_text}")
                            status_msg = get_status_message()
                            keyboard = get_main_menu_keyboard(is_server_running())
                            send_telegram_message(bot_token, chat_id, status_msg, reply_markup=keyboard)
                            
                    # Handle inline button callbacks
                    elif 'callback_query' in result:
                        callback = result['callback_query']
                        callback_id = callback.get('id')
                        data_cmd = callback.get('data')
                        msg_chat_id = str(callback.get('message', {}).get('chat', {}).get('id', ''))
                        
                        if msg_chat_id == str(chat_id):
                            print(f"Received callback query: {data_cmd}")
                            
                            if data_cmd == "check_status":
                                answer_callback_query(bot_token, callback_id, "Checking status...")
                                status_msg = get_status_message()
                                keyboard = get_main_menu_keyboard(is_server_running())
                                send_telegram_message(bot_token, chat_id, status_msg, reply_markup=keyboard)
                                
                            elif data_cmd == "start_stream":
                                answer_callback_query(bot_token, callback_id, "Starting stream...")
                                result_msg = start_streaming_server()
                                
                                # Send the result followed by the updated status menu
                                send_telegram_message(bot_token, chat_id, result_msg)
                                time.sleep(1)
                                status_msg = get_status_message()
                                keyboard = get_main_menu_keyboard(is_server_running())
                                send_telegram_message(bot_token, chat_id, status_msg, reply_markup=keyboard)
                                
                            elif data_cmd == "stop_stream":
                                answer_callback_query(bot_token, callback_id, "Stopping stream...")
                                result_msg = stop_streaming_server()
                                
                                # Send the result followed by the updated status menu
                                send_telegram_message(bot_token, chat_id, result_msg)
                                time.sleep(1)
                                status_msg = get_status_message()
                                keyboard = get_main_menu_keyboard(is_server_running())
                                send_telegram_message(bot_token, chat_id, status_msg, reply_markup=keyboard)
                            else:
                                answer_callback_query(bot_token, callback_id)
            else:
                print(f"Error from Telegram API: {data.get('description')}")
                time.sleep(5)
                
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Wait a few seconds on startup to ensure network connection is fully established
    print("Waiting 10 seconds for network interfaces to initialize...")
    time.sleep(10)
    
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
                # This automatically opens the file in Notepad on Windows!
                os.startfile(config_path)
            except Exception:
                pass
        else:
            print("Error: config.ini not found! Please create it with your Bot Token and Chat ID.")
        # Exit so it doesn't try to send right now
        exit(1)
        
    config.read(config_path)
    
    try:
        bot_token = config.get('telegram', 'BOT_TOKEN')
        chat_id = config.get('telegram', 'CHAT_ID')
        
        if bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE" or chat_id == "YOUR_TELEGRAM_CHAT_ID_HERE":
            print("Error: You must update config.ini with your actual Token and Chat ID.")
            exit(1)
            
    except (configparser.NoSectionError, configparser.NoOptionError):
        print("Error: config.ini is missing the [telegram] section, BOT_TOKEN, or CHAT_ID.")
        exit(1)

    # Send initial startup notification
    print("Sending Telegram Notification...")
    startup_message = get_status_message()
    keyboard = get_main_menu_keyboard(is_server_running())
    send_telegram_message(bot_token, chat_id, startup_message, reply_markup=keyboard)
    
    # Start long polling to listen for incoming messages
    print("Starting Telegram polling. Send any message to the bot to get the current data...")
    poll_telegram(bot_token, chat_id)
