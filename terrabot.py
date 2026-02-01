import discord
import subprocess
import asyncio
import sys
from collections import deque

# --- CONFIGURATION ---
TOKEN = 'YOUR_BOT_TOKEN_HERE'
CHANNEL_ID = 123456789012345678
SERVER_PATH = r'CPathToTerrariaServer.exe'
SERVER_ARGS = ['-config', 'serverconfig.txt']

# SECURITY Only allow these commands to be passed to the server
# The key is the discord command, the value is the actual terraria command
ALLOWED_COMMANDS = {
    '!save' 'save',
    '!morning' 'dawn',
    '!noon' 'noon',
    '!night' 'dusk',
    '!midnight' 'midnight',
    '!settle' 'settle' # Settle liquids
}

# Initialize Discord Client
intents = discord.Intents.default()
intents.message_content = True # REQUIRED Enable this in Discord Developer Portal
client = discord.Client(intents=intents)

# Global variables
log_queue = deque()
server_process = None # We need to access this from multiple functions

async def run_server_and_capture_output()
    global server_process
    
    # Start the process with access to BOTH input (stdin) and output (stdout)
    server_process = subprocess.Popen(
        [SERVER_PATH] + SERVER_ARGS,
        stdin=subprocess.PIPE,  # Enable writing to the server
        stdout=subprocess.PIPE, # Enable reading from the server
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )

    print(Terraria Server Started. Bridge is open.)

    while True
        # Read output line by line without blocking the bot
        output = await asyncio.to_thread(server_process.stdout.readline)
        
        if output == '' and server_process.poll() is not None
            break 
        
        if output
            print(output.strip())
            log_queue.append(output)

async def send_logs_to_discord()
    Background task to send batched logs to Discord.
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    
    while not client.is_closed()
        if log_queue
            batch = 
            while log_queue and len(batch)  1800
                batch += log_queue.popleft()
            if batch
                try
                    await channel.send(f```{batch}```)
                except Exception as e
                    print(fFailed to send log {e})
        await asyncio.sleep(2)

@client.event
async def on_message(message)
    # Ignore messages from the bot itself
    if message.author == client.user
        return

    # Only listen in the specific console channel
    if message.channel.id != CHANNEL_ID
        return

    # Check if the message is in our whitelist
    command_text = message.content.lower().strip()
    
    if command_text in ALLOWED_COMMANDS
        terraria_cmd = ALLOWED_COMMANDS[command_text]
        
        if server_process and server_process.poll() is None
            print(fSending command to server {terraria_cmd})
            
            # Write to the server's keyboard
            server_process.stdin.write(terraria_cmd + n)
            server_process.stdin.flush() # Force the input to go through immediately
            
            await message.add_reaction(✅) # Confirm receipt
        else
            await message.channel.send(❌ Server is not running.)
    
    # Optional Admin override for raw commands (be careful!)
    elif command_text.startswith(!exec ) and message.author.guild_permissions.administrator
        raw_cmd = message.content[6] # Strip !exec 
        if server_process
            server_process.stdin.write(raw_cmd + n)
            server_process.stdin.flush()
            await message.add_reaction(⚠️)

@client.event
async def on_ready()
    print(f'Logged in as {client.user}')
    client.loop.create_task(run_server_and_capture_output())
    client.loop.create_task(send_logs_to_discord())

client.run(TOKEN)