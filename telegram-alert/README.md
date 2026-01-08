# Telegram Alert Notifier

CLI tool to send instant alerts and notifications to your Telegram account via a bot.

Part of [automata-lab](https://github.com/danieltonad/automata-lab).

---

## 🔧 Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/danieltonad/automata-lab.git
   cd automata-lab/telegram-alert
   ```

2. **Create a virtual environment** (optional but recommended):

   ```bash
   python -m venv env
   env\Scripts\activate.bat  # For CMD on Windows
   # or
   "env/Scripts/Activate.ps1"  # For PowerShell on Windows
   ```

3. **Install Python dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your Telegram Bot**:

   Create a `.env` file in the `telegram-alert` directory:

   ```env
   BOT_TOKEN=your_bot_token_here
   CHAT_ID=your_chat_id_here
   ```

   - **BOT_TOKEN**: Get this from [@BotFather](https://t.me/botfather) on Telegram by creating a new bot
   - **CHAT_ID**: Your Telegram user ID (use [@userinfobot](https://t.me/userinfobot) to find your ID)

## 📖 Usage

Send a notification to your Telegram:

```bash
python notify.py "Your alert message here"
```

### Examples:

```bash
# Simple alert
python notify.py "Server is running!"

# Status update
python notify.py "Build completed successfully ✅"

# Error notification
python notify.py "⚠️ Database connection failed"
```

## ✨ Features

- Instant message delivery to Telegram
- Markdown formatting support
- Simple command-line interface
- Error handling with informative messages
- Lightweight and fast

## 🚀 Integration

You can easily integrate this into your scripts, cron jobs, or automation workflows:

```bash
# Example: Notify when a script completes
python your_script.py && python notify.py "Script completed successfully"

# Example: Notify on errors
python your_script.py || python notify.py "⚠️ Script failed"
```

## 🛠️ Troubleshooting

- **"Failed to send message"**: Check that your `BOT_TOKEN` and `CHAT_ID` are correct in the `.env` file
- **Missing `.env` file**: Create one in the `telegram-alert` directory with your bot credentials
- **"Usage: python notify.py <alert_message>"**: Remember to provide a message as an argument
- **Bot not responding**: Make sure you've started a conversation with your bot on Telegram first
