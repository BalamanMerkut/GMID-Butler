# GMID Butler — Discord AI Bot

A smart Discord bot powered by **Google Gemini AI**. It remembers conversations, manages private channels, and keeps your bot-commands channel clean automatically.

---

## Features

- 🧠 **Conversation Memory** — The bot remembers each user's last 10 messages across a session
- 🔐 **Private Channels** (`!priv`) — Creates a hidden text channel visible only to you
- ➕ **Add Members** (`!add @user`) — Invite someone into your private channel
- 🔒 **Close Channel** (`!close`) — Delete the private channel instantly
- ⏰ **Auto-Delete** — Private channels are automatically deleted after 12 hours
- 🧹 **Daily Cleanup** — Purges a bot-commands channel once every 24 hours
- 🗑️ **Reset Memory** (`!unuttun`) — Clears your AI conversation history

---

## Requirements

- Python 3.10 or higher
- A Discord bot token → [Discord Developer Portal](https://discord.com/developers/applications)
- A Gemini API key → [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## Setup Guide

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/gmid-butler.git
cd gmid-butler
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your `.env` file

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Then open `.env` and edit it:

```env
DISCORD_TOKEN=your_discord_bot_token_here
GEMINI_KEY=your_gemini_api_key_here
BOT_COMMANDS_CHANNEL_ID=your_channel_id_here
CLEANUP_HOUR=0
PRIV_CHANNEL_LIFETIME_HOURS=12
```

> **How to get a Channel ID:** In Discord, go to Settings → Advanced → enable **Developer Mode**. Then right-click any channel and click **Copy ID**.

### 4. Give the bot the right permissions

In the Discord Developer Portal, under your bot's **OAuth2 → URL Generator**, make sure it has these permissions:

| Permission | Why |
|---|---|
| Read Messages / View Channels | Read user commands |
| Send Messages | Reply to users |
| Manage Channels | Create and delete private channels |
| Manage Permissions | Set who can see private channels |
| Manage Messages | Purge bot-commands channel |
| Read Message History | Required for bulk-delete |

### 5. Run the bot

```bash
python main.py
```

You should see:
```
✅ GMID Butler#1234 olarak giriş yapıldı!
```

---

## Commands

| Command | Description |
|---|---|
| `!your message` or `@bot` | Chat with the AI |
| `!priv` | Open a private channel just for you |
| `!add @user` | Add someone to your private channel |
| `!close` | Delete your private channel now |
| `!unuttun` | Clear the bot's memory of your conversation |
| `!temizle` | *(Admins only)* Manually trigger the channel cleanup |

---

## Notes

- The bot creates a **🔐 Priv Kanallar** category automatically on first `!priv` use — no setup needed.
- A SQLite database (`conversations.db`) is created automatically in the project folder.
- The Flask server (`keep_alive`) is included for hosting on platforms like [Render](https://render.com).

---

## License

MIT — free to use and modify.
