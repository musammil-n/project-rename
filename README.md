# 🚀 Auto-Delete Pyrogram Bot

A simple Pyrogram-based Telegram bot that **automatically deletes messages** in specified group chats after a delay.

---

## ✨ Features

- ✅ Deletes all non-command messages in allowed group chats
- ⏱️ Delay-based deletion (customizable via environment variable)
- 🔐 Only affects specific groups (whitelisted using environment variable)
- ☁️ Optimized for deployment on [Koyeb](https://www.koyeb.com/)
- 🧩 Clean structure with centralized config

---

## 🧩 Environment Variables

These variables must be set in your **Koyeb dashboard** (or `.env` for local testing):

| Variable         | Description                                    | Example                          |
|------------------|------------------------------------------------|----------------------------------|
| `TOKEN`          | Your bot token from [@BotFather](https://t.me/BotFather) | `123456:ABCDEF...`              |
| `API_ID`         | Telegram API ID (from https://my.telegram.org) | `123456`                         |
| `API_HASH`       | Telegram API hash                              | `abcdef123456...`               |
| `OWNER`          | Your Telegram user ID (optional, for admin features) | `123456789`                    |
| `CHATS`          | Space-separated list of group chat IDs to monitor | `-1001111111111 -1002222222222` |
| `DELETE_DELAY`   | Delay in seconds before deleting messages      | `5`                              |
| `PORT`           | Optional port value if using Flask health check | `8000`                           |

> 💡 **Note:** `CHATS` must contain Telegram **group IDs** (starting with `-100`) separated by spaces.



