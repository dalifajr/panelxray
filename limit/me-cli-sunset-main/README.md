# MYnyak Engsel Sunset

![banner](bnr.png)

CLI client for a certain Indonesian mobile internet service provider.

# How to get environtment Variables
Go to [OUR TELEGRAM CHANNEL](https://t.me/alyxcli)
Copy the provided environment variables and paste it into a text file named `.env` in the same directory as `main.py`.
You can use nano or any text editor to create the file.

# How to run with TERMUX
1. Install Git
```
pkg install git -y
```
2. Clone this repo
```
git clone https://github.com/dalifajr/xl-cli
```
3. Open the folder
```
cd me-cli-sunset
```
4. Setup
```
bash setup.sh
```
5. Run the script
```
python main.py
```

# How to run with Ubuntu 25
1. Install Git
```bash
sudo apt update
sudo apt install -y git
```
2. Clone this repo
```bash
git clone https://github.com/dalifajr/xl-cli
```
3. Open the folder
```bash
cd me-cli-sunset
```
4. Setup
```bash
bash setup.sh
```
5. Open control panel
```bash
paneldor
```
6. Run the script manually (optional)
```bash
./.venv/bin/python main.py
```

# How to run with Windows
1. Install Git and Python 3.10+ (add Python to PATH)
2. Clone this repo
```powershell
git clone https://github.com/dalifajr/xl-cli
```
3. Open the folder
```powershell
cd me-cli-sunset
```
4. Setup (PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```
5. Open Windows panel
```powershell
paneldor
```
6. Run the script manually (optional)
```powershell
.\.venv\Scripts\python.exe .\main.py
```

# Setup script note
`setup.sh` auto-detects your platform:
- Uses `pkg` on Termux.
- Uses `apt-get` on Ubuntu/Debian.

For Windows, use `setup.ps1`.

Windows note:
- If you only have Python 3.14, some native packages may try to compile from source.
- This repo uses `brotlicffi` to avoid manual C++ Build Tools setup for Brotli support.
- `paneldor` can start bot/CLI as background process so it keeps running after terminal is closed.
- `paneldor` includes auto-update task option (Task Scheduler) and auto-start bot option.

# Telegram bot integration (button-first)
You can run the full CLI flow from Telegram using buttons and symbols.

1. Add bot token to `.env`
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```
2. Install dependencies
```bash
python3 -m pip install -r requirements.txt
```
3. Run the bot
```bash
python3 telegram_main.py
```

4. Restrict bot access with `user_allow.txt`
- Add allowed Telegram user ids (one id per line).
- Users not listed in `user_allow.txt` will be denied.

On Windows:
```powershell
.\.venv\Scripts\python.exe .\telegram_main.py
```

How it works:
- Use `/start` once to show the keyboard.
- Use `🧩 Native` for contextual buttons (menu changes based on current flow).
- Use `🚀 Bridge` for full CLI bridge mode.
- In bridge mode, start with `▶️ Mulai Session` then use context buttons shown for that mode.
- Tap `🛑 Stop Session` to end bridge session.

Notes:
- This mode bridges `main.py` directly, so all existing menu features are available from Telegram.
- Keyboard now appears contextually to reduce clutter and improve UX.

# Info

## PS for Certain Indonesian mobile internet service provider

Instead of just delisting the package from the app, ensure the user cannot purchase it.
What's the point of strong client side security when the server don't enforce it?

## Terms of Service
By using this tool, the user agrees to comply with all applicable laws and regulations and to release the developer from any and all claims arising from its use.

## Contact

contact@mashu.lol
