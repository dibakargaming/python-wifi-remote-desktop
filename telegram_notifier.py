import socket
import subprocess
import requests
import configparser
import os
import time

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

    # Gather System Information
    ip_address = get_local_ip()
    ssid, signal = get_wifi_info()

    # Format the message
    message = (
        "<b>💻 PC is Online!</b>\n\n"
        f"<b>Remote Desktop IP:</b> <code>http://{ip_address}:5000</code>\n\n"
        f"<b>WiFi Network:</b> {ssid}\n"
        f"<b>Signal Strength:</b> {signal}\n"
    )

    # Send Notification
    print("Sending Telegram Notification...")
    send_telegram_message(bot_token, chat_id, message)
