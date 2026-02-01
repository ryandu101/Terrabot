import discord
import subprocess
import asyncio
import sys
import os
from collections import deque
from dotenv import load_dotenv

# --- LOAD CONFIGURATION ---
# This looks for the .env file and loads it
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
# We must convert the ID to an integer for Discord
try:
    CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
except TypeError:
    print("ERROR: DISCORD_CHANNEL_ID not found in .env file.")
    sys.exit(1)

SERVER_PATH = os.getenv('TERRARIA_EXE_PATH')
# This points to the config file we just made in the same folder as the script
SERVER_ARGS = ['-config', 'serverconfig.txt']

# --- VALIDATION ---
if not TOKEN or not SERVER_PATH:
    print("ERROR: specific variables missing from .env file.")
    print("Ensure you have DISCORD_TOKEN and TERRARIA_EXE_PATH set.")
    sys.exit(1)

# SECURITY: Discord commands allowed
ALLOWED_COMMANDS = {
    '!save': 'save',
    '!playing': 'playing',
    '!morning': 'dawn',
    '!noon': 'noon',
    '!night': 'dusk',
    '!midnight': 'midnight',
    '!settle': 'settle'
}

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

log_queue = deque()
server_process = None 

# --- TASKS ---
async def read_local_console():
    """Reads input from the local terminal and forwards it to the server."""
    print(">>> Local Console Bridge Active. Type commands here directly. <<<")
    while True:
        cmd = await asyncio.to_thread(sys.stdin.readline)
        if cmd:
            if server_process and server_process.poll() is None:
                server_process.stdin.write(cmd)
                server_process.stdin.flush()
            else:
                print("Cannot send command: Server is not running.")

async def run_server_and_capture_output():
    global server_process
    print(f"Attempting to launch server from: {SERVER_PATH}")
    
    try:
        server_process = subprocess.Popen(
            [SERVER_PATH] + SERVER_ARGS,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
            # This ensures the server looks for the config in the current folder
            cwd=os.getcwd() 
        )
        print("Terraria Server Started.")
    except FileNotFoundError:
        print(f"CRITICAL ERROR: Could not find TerrariaServer.exe at: {SERVER_PATH}")
        return

    while True:
        if server_process.poll() is not None:
            remaining = server_process.stdout.read()
            if remaining: log_queue.append(remaining)
            print("Server has stopped.")
            break

        try:
            output = await asyncio.to_thread(server_process.stdout.readline)
            if output:
                print(output.strip())
                log_queue.append(output)
        except Exception as e:
            print(f"Error reading server output: {e}")
            break

async def send_logs_to_discord():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    
    if not channel:
        print(f"CRITICAL: Bot cannot find channel ID {CHANNEL_ID}. Check permissions or ID.")
        return

    while not client.is_closed():
        if log_queue:
            batch = ""
            while log_queue and len(batch) < 1800:
                batch += log_queue.popleft()
            if batch:
                try:
                    await channel.send(f"```{batch}```")
                except Exception as e:
                    print(f"Failed to send log: {e}")
        await asyncio.sleep(2)

@client.event
async def on_message(message):
    if message.author == client.user or message.channel.id != CHANNEL_ID:
        return

    command_text = message.content.lower().strip()
    
    if command_text in ALLOWED_COMMANDS:
        terraria_cmd = ALLOWED_COMMANDS[command_text]
        if server_process and server_process.poll() is None:
            print(f"[Discord] {message.author}: {terraria_cmd}")
            server_process.stdin.write(terraria_cmd + "\n")
            server_process.stdin.flush()
            await message.add_reaction("✅")
        else:
            await message.channel.send("❌ Server is not running.")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    client.loop.create_task(run_server_and_capture_output())
    client.loop.create_task(send_logs_to_discord())
    client.loop.create_task(read_local_console())

if __name__ == "__main__":
    client.run(TOKEN)