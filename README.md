# Local WiFi Remote Desktop

A lightweight, beginner-friendly Python application that allows you to stream your PC screen to a smartphone over your local WiFi network. You can control your PC's mouse using touch gestures on your phone, completely offline without needing any external services.

## ✨ Features

- **Screen Streaming**: View your PC screen directly on your mobile browser.
- **Touch Mouse Control**: Move your PC's cursor by dragging your finger on the phone screen.
- **Click Actions**: Supports left-click and right-click actions from the mobile interface.
- **Display Controls**: Includes Zoom In/Out and Screen Rotation features to improve visibility on smaller screens.
- **Fully Offline**: Works purely on your local network (LAN/WiFi). No internet connection or third-party servers required.
- **Telegram PC Monitor Bot**: (Optional) Get an automatic Telegram message with your PC's IP and WiFi status whenever your computer turns on.

## 🛠️ Requirements

- Python 3.7 or higher
- The device running the server (PC) and the client (Phone) must be connected to the **same WiFi network**.

## 🚀 Installation

1. **Clone or Download the Repository**
   Download this code to your computer and extract the folder.

2. **Open a Terminal / Command Prompt**
   Navigate to the folder where you saved the files.

3. **Install Dependencies**
   Run the following command to install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```
   *This installs `flask`, `mss`, `pyautogui`, `opencv-python`, `numpy`, and `requests`.*

4. **(Optional) Setup Telegram Startup Bot**
   If you want your PC to automatically message you its IP address when it turns on:
   - Create a Telegram bot via BotFather and get your **Token** and **Chat ID**.
   - Run `setup_startup.bat`. This will automatically add the bot to your Windows startup folder AND create/open your `config.ini` file in Notepad.
   - Paste your Token and Chat ID into the opened `config.ini` file and save it!

## 🎮 How to Use

1. **Start the Server**
   Run the application on your PC:
   ```bash
   python server.py
   ```
   *Note: If your firewall prompts you for network access, make sure to **Allow Access** entirely so that other devices on your local network can connect.*

2. **Connect from your Phone**
   - The terminal will display an IP address.
   - Open a web browser (Chrome, Safari, etc.) on your smartphone.
   - Enter the provided IP address into the address bar.

3. **Control your PC!**
   - You should now see your PC screen on your phone.
   - Swipe and tap to control your mouse. Use the on-screen buttons to perform clicks, zoom, and rotate the view.

## ⚠️ Notes
- Running this script gives the device connecting full control over your mouse. Only run this on a secure, trusted local home network.
