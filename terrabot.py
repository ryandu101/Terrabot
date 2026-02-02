import discord
import subprocess
import asyncio
import sys
import os
import ctypes
from ctypes import wintypes
from collections import deque
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
try:
    CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
except:
    sys.exit("Error: Check DISCORD_CHANNEL_ID")

SERVER_PATH = os.getenv('TERRARIA_EXE_PATH')
SERVER_ARGS = ['-config', 'serverconfig.txt']

ALLOWED_COMMANDS = {
    '!save': 'save',
    '!playing': 'playing',
    '!morning': 'dawn',
    '!noon': 'noon',
    '!night': 'dusk',
    '!midnight': 'midnight',
    '!settle': 'settle'
}

# --- WINDOWS KERNEL CONSTANTS ---
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
STD_INPUT_HANDLE = -10
KEY_EVENT = 0x0001

# Define C Structures for Input Injection
class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bKeyDown", wintypes.BOOL),
        ("wRepeatCount", wintypes.WORD),
        ("wVirtualKeyCode", wintypes.WORD),
        ("wVirtualScanCode", wintypes.WORD),
        ("uChar", ctypes.c_wchar), # Unicode character
        ("dwControlKeyState", wintypes.DWORD),
    ]

class INPUT_RECORD_EVENT(ctypes.Union):
    _fields_ = [("KeyEvent", KEY_EVENT_RECORD)]

class INPUT_RECORD(ctypes.Structure):
    _fields_ = [
        ("EventType", wintypes.WORD),
        ("Event", INPUT_RECORD_EVENT),
    ]

# --- THE MAGIC FUNCTION ---
def inject_input(pid, text):
    """
    Attaches to the Terraria console and injects keystrokes directly 
    into the buffer. Does NOT require window focus.
    """
    if not pid: return False
    
    # 1. Detach from our own console (so we can attach to the server's)
    kernel32.FreeConsole()
    
    # 2. Attach to the Server's Console
    if not kernel32.AttachConsole(pid):
        print("Failed to attach to server console.")
        return False
        
    # 3. Get the Input Handle of that console
    hStdIn = kernel32.GetStdHandle(STD_INPUT_HANDLE)
    
    # 4. Create the records (Key Down + Key Up for every char)
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
        
    # 5. Write them to the buffer
    written = wintypes.DWORD(0)
    kernel32.WriteConsoleInputW(hStdIn, ctypes.byref(records), len(records), ctypes.byref(written))
    
    # 6. Detach so we don't crash the bot or the server
    kernel32.FreeConsole()
    
    # 7. Re-allocate a console for Python (Optional, for debugging)
    # kernel32.AllocConsole() 
    return True

# --- DISCORD SETUP ---
intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

log_queue = deque()
server_process = None 

# --- TASKS ---
async def read_local_console():
    # NOTE: Since we detach/attach consoles, local typing might get buggy.
    # This function is kept for logic but might lose visibility in VS Code.
    while True:
        await asyncio.sleep(1) 

async def run_server_and_capture_output():
    global server_process
    print(f"Launching: {SERVER_PATH}")
    
    try:
        # Launch with a NEW CONSOLE so it has a buffer we can attach to
        server_process = subprocess.Popen(
            [SERVER_PATH] + SERVER_ARGS,
            stdin=None,                 # Let it manage its own input
            stdout=subprocess.PIPE,     # We still capture output via pipe
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
            output = await asyncio.to_thread(server_process.stdout.readline)
            if output:
                log_queue.append(output)
                # Note: 'print' might fail if we are currently attached to the other console
                # so we rely on Discord logs.
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

    # The command to send (either the command itself or a 'say' chat)
    final_cmd = ""
    
    if command_text.startswith("!"):
        if command_text in ALLOWED_COMMANDS:
            final_cmd = ALLOWED_COMMANDS[command_text]
            await message.add_reaction("✅")
    else:
        clean_msg = content.replace("\n", " ").replace("\r", "")
        final_cmd = f"say <Discord-{message.author.display_name}> {clean_msg}"

    # INJECT THE INPUT IF WE HAVE A COMMAND
    if final_cmd and server_process:
        # We must add \r (Return) for the server to process the line
        await asyncio.to_thread(inject_input, server_process.pid, final_cmd + "\r")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    client.loop.create_task(run_server_and_capture_output())
    client.loop.create_task(send_logs_to_discord())
    # read_local_console is disabled because console-hopping breaks local input

if __name__ == "__main__":
    client.run(TOKEN)