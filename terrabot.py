import sys
import os
import subprocess
import ctypes
from ctypes import wintypes
import time
import asyncio
from collections import deque
from dotenv import load_dotenv

# --- 1. FAST-LOAD CHECK (Injector Mode) ---
if len(sys.argv) > 1 and sys.argv[1] == "inject":
    # Kernel Definitions for Injection
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    STD_INPUT_HANDLE = -10
    KEY_EVENT = 0x0001

    class KEY_EVENT_RECORD(ctypes.Structure):
        _fields_ = [("bKeyDown", wintypes.BOOL), ("wRepeatCount", wintypes.WORD),
                    ("wVirtualKeyCode", wintypes.WORD), ("wVirtualScanCode", wintypes.WORD),
                    ("uChar", ctypes.c_wchar), ("dwControlKeyState", wintypes.DWORD)]

    class INPUT_RECORD_EVENT(ctypes.Union):
        _fields_ = [("KeyEvent", KEY_EVENT_RECORD)]

    class INPUT_RECORD(ctypes.Structure):
        _fields_ = [("EventType", wintypes.WORD), ("Event", INPUT_RECORD_EVENT)]

    def run_injector(pid, text):
        try:
            pid = int(pid)
            kernel32.FreeConsole()
            if not kernel32.AttachConsole(pid): return
            hStdIn = kernel32.GetStdHandle(STD_INPUT_HANDLE)
            
            records = (INPUT_RECORD * (len(text) * 2))()
            idx = 0
            for char in text:
                # Key Down
                records[idx].EventType = KEY_EVENT
                records[idx].Event.KeyEvent.bKeyDown = True
                records[idx].Event.KeyEvent.wRepeatCount = 1
                records[idx].Event.KeyEvent.uChar = char
                idx += 1
                # Key Up
                records[idx].EventType = KEY_EVENT
                records[idx].Event.KeyEvent.bKeyDown = False
                records[idx].Event.KeyEvent.wRepeatCount = 1
                records[idx].Event.KeyEvent.uChar = char
                idx += 1

            written = wintypes.DWORD(0)
            kernel32.WriteConsoleInputW(hStdIn, ctypes.byref(records), len(records), ctypes.byref(written))
            kernel32.FreeConsole()
        except:
            pass

    run_injector(sys.argv[2], sys.argv[3])
    sys.exit(0)

# ==========================================
# --- MAIN BOT MODE ---
# ==========================================

import discord
import msvcrt # <--- REQUIRED for non-blocking input on Windows

# --- CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))
SERVER_PATH = os.getenv('TERRARIA_EXE_PATH')
SERVER_ARGS = ['-config', 'serverconfig.txt']

ALLOWED_COMMANDS = {
    '!help': 'help',
    '!players': 'playing',
    '!list': 'playing',
    '!online': 'playing',
    '!who': 'playing',
    '!playing': 'playing',
    '!time': 'time',
    '!motd': 'motd',
    '!seed': 'seed',
    '!version': 'version',
    '!password': 'password',
    '!maxplayers': 'maxplayers'
}

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

log_queue = deque()
server_process = None 

async def send_command_to_server(cmd_text):
    """Spawns the lightweight injector."""
    if not server_process:
        print("❌ Server not running.")
        return

    full_cmd = cmd_text + "\r"
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, __file__, "inject", str(server_process.pid), full_cmd
        )
        await proc.wait()
    except Exception as e:
        print(f"Failed to spawn injector: {e}")

async def read_local_console():
    """
    NON-BLOCKING INPUT READER using msvcrt.
    This prevents the bot from freezing while waiting for you to type.
    """
    print(">>> Local Console Active. Type commands here. <<<")
    
    cmd_buffer = []
    
    while True:
        # 1. Check if a key was pressed (Non-blocking check)
        if msvcrt.kbhit():
            # 2. Read the key (blocking for microseconds only)
            char = msvcrt.getwche() # getwche echoes the char to screen
            
            # Check for Enter key (\r)
            if char == '\r':
                print() # Print new line to make terminal look nice
                full_cmd = "".join(cmd_buffer).strip()
                cmd_buffer = [] # Clear buffer
                
                if full_cmd:
                    print(f"[Local] Sending: {full_cmd}")
                    await send_command_to_server(full_cmd)
            
            # Check for Backspace (\b)
            elif char == '\b':
                if cmd_buffer:
                    cmd_buffer.pop()
                    # Visual backspace hack (overwrite char with space then backspace again)
                    sys.stdout.write(" \b") 
            
            # Normal character
            else:
                cmd_buffer.append(char)
        
        # 3. CRITICAL: Sleep to let Discord bot process network events
        await asyncio.sleep(0.05)

async def run_server_and_capture_output():
    global server_process
    print(f"Launching Server: {SERVER_PATH}")
    
    try:
        server_process = subprocess.Popen(
            [SERVER_PATH] + SERVER_ARGS,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_CONSOLE, 
            universal_newlines=True,
            bufsize=1,
            cwd=os.getcwd() 
        )
        print("Terraria Server Started.")
        
    except FileNotFoundError:
        print("CRITICAL ERROR: Executable not found.")
        return

    while True:
        if server_process.poll() is not None:
            print("Server has stopped.")
            break

        try:
            # We still use to_thread here as pipe reading is generally safe
            output = await asyncio.to_thread(server_process.stdout.readline)
            if output:
                if "Terraria Server" not in output: 
                    print(output.strip())
                log_queue.append(output)
        except Exception as e:
            break

async def send_logs_to_discord():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    while not client.is_closed():
        if log_queue:
            batch = ""
            while log_queue and len(batch) < 1800:
                batch += log_queue.popleft()
            if batch:
                try:
                    await channel.send(f"```{batch}```")
                except:
                    pass
        await asyncio.sleep(2)

@client.event
async def on_message(message):
    if message.author == client.user or message.channel.id != CHANNEL_ID:
        return

    content = message.content.strip()
    command_text = content.lower()
    
    if command_text.startswith("!"):
        if command_text in ALLOWED_COMMANDS:
            terraria_cmd = ALLOWED_COMMANDS[command_text]
            await message.add_reaction("✅")
            await send_command_to_server(terraria_cmd)
    else:
        clean_msg = content.replace("\n", " ").replace("\r", "")
        chat_cmd = f"say <Discord-{message.author.display_name}> {clean_msg}"
        await send_command_to_server(chat_cmd)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    client.loop.create_task(run_server_and_capture_output())
    client.loop.create_task(send_logs_to_discord())
    client.loop.create_task(read_local_console())

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN missing from .env")
    else:
        client.run(TOKEN)