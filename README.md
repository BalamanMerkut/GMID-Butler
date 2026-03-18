# GMID Butler — The Noble Discord Assistant

GMID Butler is a sophisticated Discord bot powered by Google's Gemini AI. Designed with the persona of a noble head butler, it serves your server with elegance, handling everything from AI-driven conversations to automatic channel management.

## 🌟 Features

- **🧠 Advanced AI Conversations**: Powered by Gemini 2.0 Flash, providing intelligent and contextual responses.
- **🌍 Multi-language Support**: Supports **English**, **Turkish**, **Spanish**, **Italian**, **German**, **French**, **Russian**, and **Chinese**. Use `!language [code]` to switch.
- **🔐 Private Channels**: Users can create temporary secret channels with `!priv` that automatically delete after a set time.
- **🧹 Automatic Cleanup**: Schedule daily message purging for any channel with `!set clear [hour]`.
- **🎩 Butler Persona**: A refined, polite, and respectful tone in every interaction.

## 🚀 Setup Instructions

### 1. Prerequisites
- Python 3.9 or higher
- A Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- A Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))

### 2. Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/gmid-butler.git
   cd gmid-butler
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   - Rename `.env.example` to `.env`.
   - Fill in your `DISCORD_TOKEN` and `GEMINI_KEY`.

### 3. Running the Bot
```bash
python main.py
```

## 📜 Key Commands

| Command | Description |
| :--- | :--- |
| `!<question>` | Ask the Butler a question |
| `!help` | Show all available commands |
| `!priv [hours]` | Create a private temporary channel |
| `!add @user` | Add a member to your private channel |
| `!close` | Close your private channel immediately |
| `!set clear [hour]` | Schedule daily cleanup (0-23 UTC) |
| `!set control` | List all active cleanups |
| `!language [lang]` | Change server language |

## 🛡️ License
This project is open-source and available under the MIT License.

---
*GMID Butler • Always at your service, Sir.*
