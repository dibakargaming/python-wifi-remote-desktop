@echo off
setlocal

:: Get the directory of this script
set SCRIPT_DIR=%~dp0

:: Define the target VBScript wrapper file in the Startup folder
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set TARGET_VBS="%STARTUP_DIR%\RemoteDesktopBot.vbs"

echo Creating Startup task for Telegram Bot...

:: Create a VBScript to run the Python script completely hidden (no console window)
echo Set WshShell = CreateObject("WScript.Shell") > %TARGET_VBS%
echo WshShell.Run "pythonw.exe """ & "%SCRIPT_DIR%telegram_notifier.py" & """", 0, False >> %TARGET_VBS%

echo.
echo =========================================================
echo Success! The Telegram Bot has been added to your Startup folder.
echo It will now run silently every time you turn on your PC.
echo.
echo Make sure you have updated config.ini with your Bot Token and Chat ID!
echo =========================================================
pause
