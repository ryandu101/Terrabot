# Terraria Discord Bridge (Wrapper)

This project is a Python-based wrapper for the Terraria Dedicated Server. It acts as a bridge between your local server console and a Discord channel.

**Features:**

* **Live Log Streaming:** Captures the Terraria server console output and streams it to a specific Discord channel in real-time (batched to respect Discord rate limits).
* **Remote Administration:** Allows you to send commands (e.g., `!save`, `!dawn`) from Discord directly to the server console.
* **Chat Integration:** (Optional) Can forward Discord messages into the in-game chat.
* **Crash Detection:** Because the bot wraps the process, it knows immediately if the server closes or crashes.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed/available:

1. **Python 3.8 or newer**: [Download Here](https://www.python.org/downloads/) (Make sure to check "Add Python to PATH" during installation).
2. **Terraria Dedicated Server**: Usually found in your Steam folder or downloaded from the Terraria website. You need the `TerrariaServer.exe` file.
3. **A Discord Account**: With "Developer Mode" enabled (to see IDs).

---

## ⚙️ Step 1: Discord Bot Setup

To get your `TOKEN` and enable the necessary permissions:

1. Go to the [Discord Developer Portal](https://www.google.com/search?q=https://discord.com/developers/applications).
2. Click **New Application** and give it a name (e.g., "Terraria Console").
3. On the left sidebar, click **Bot**.
4. Click **Reset Token** (or "View Token") to reveal your bot token. **Copy this immediately**; you will need it for the configuration step.
5. **CRITICAL STEP:** Scroll down to the **Privileged Gateway Intents** section.
* Enable **Message Content Intent**.
* Enable **Server Members Intent** (Optional, but good practice).
* *If you do not enable Message Content Intent, the bot will not be able to read your commands.*


6. On the left sidebar, click **OAuth2** -> **URL Generator**.
* Check the box: `bot`.
* Check the permissions: `Send Messages`, `Read Messages/View Channels`, `Manage Messages` (optional, for cleanup).


7. Copy the generated URL at the bottom, paste it into your browser, and invite the bot to your server.

---

## 🛠️ Step 2: Installation

1. **Create a Project Folder:**
Create a new folder on your computer (e.g., `C:\TerrariaBot`).
2. **Place the Script:**
Save your Python code (the wrapper script provided previously) into this folder as `bot.py`.
3. **Install Dependencies:**
Open your command prompt (cmd) or terminal in this folder and run:
```bash
pip install discord.py

```



---

## 📝 Step 3: Configuration

Open `bot.py` in a text editor (Notepad, VS Code, etc.) and update the **Configuration Section** at the top:

### 1. The Token

```python
TOKEN = 'MTAw...' # Paste the token you copied in Step 1

```

### 2. The Channel ID

To get the Channel ID where the bot will live:

* Open Discord.
* Go to **User Settings** -> **Advanced** -> Enable **Developer Mode**.
* Right-click the text channel you want the bot to use.
* Click **Copy ID**.
* Paste it into the script:
```python
CHANNEL_ID = 123456789012345678 # Make sure this is an integer (no quotes)

```



### 3. Server Path

Point the script to your `TerrariaServer.exe`.

* *Note:* On Windows, use `r''` strings to handle backslashes correctly.

```python
SERVER_PATH = r'C:\Program Files (x86)\Steam\steamapps\common\Terraria\TerrariaServer.exe'

```

### 4. Server Arguments

If you use a config file (recommended for automatic startup), specify it here:

```python
SERVER_ARGS = ['-config', 'serverconfig.txt']

```

---

## 🚀 Step 4: Running the Server

Instead of double-clicking `TerrariaServer.exe`, you will now launch the **Python script**.

1. Open Command Prompt / Terminal.
2. Navigate to your folder:
```bash
cd C:\TerrariaBot

```


3. Run the bot:
```bash
python bot.py

```



**What happens next:**

* The bot will log into Discord.
* The bot will silently launch Terraria in the background.
* You should see "Terraria Server Started" in your terminal.
* Logs should immediately start appearing in your Discord channel.

---

## 🎮 Commands & Usage

### Whitelisted Commands

To prevent abuse, only commands defined in the `ALLOWED_COMMANDS` dictionary in `bot.py` will work. Default examples:

* **`!save`** -> Triggers the server `save` command.
* **`!morning`** -> Triggers `dawn`.
* **`!noon`** -> Triggers `noon`.
* **`!night`** -> Triggers `dusk`.
* **`!midnight`** -> Triggers `midnight`.
* **`!settle`** -> Triggers `settle` (Settles all liquids).

### Chatting (Optional)

If you added the chat logic to `on_message`:

* Typing anything without a `!` prefix in the Discord channel will send it to the in-game chat as: `<Discord-User> Hello World!`.

### Admin Override

* **`!exec <command>`**: Sends a raw command to the server console.
* *Example:* `!exec kick PlayerName`
* *Security Note:* Ensure your code checks for `message.author.guild_permissions.administrator` before allowing this.



---

## ⚠️ Troubleshooting

**The bot is online, but commands aren't working:**

* Did you enable **Message Content Intent** in the Discord Developer Portal? This is the #1 cause of this issue.
* Did you restart the Python script after enabling the intent?

**The server "hangs" or doesn't output logs:**

* Ensure `universal_newlines=True` and `bufsize=1` are set in the `subprocess.Popen` call.
* Ensure you aren't clicking inside the command prompt window (Windows "Quick Edit" mode can pause scripts if you highlight text).

**"File Not Found" Error:**

* Double-check your `SERVER_PATH`. If the path has spaces, ensure it is enclosed in quotes or handled correctly by the OS.

---

## 🔒 Security Best Practices

1. **Keep the Channel Private:**
Terraria logs can contain **IP addresses** of players joining. Do not let public users view this channel. Restrict the channel permissions in Discord to "Admins Only."
2. **Hide your Token:**
Never share your `bot.py` file with the `TOKEN` filled in. If you upload this code to GitHub, use a `.env` file or delete the token before uploading.
3. **Sanitize Inputs:**
The provided code includes basic whitelisting. Be very careful adding commands that allow users to input raw text into the server console.
