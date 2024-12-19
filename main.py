import discord
from discord.ext import commands, tasks
import requests
import json
import asyncio
from datetime import datetime, timedelta

with open (r"C:\Users\aless\Desktop\discord ping thing\token.txt","r") as keys:  
    token = keys.readline().strip()

app_id = 375600

description = "shows players online" 

print('discord version: ', discord.__version__)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
command_prefix = "/"

last_notification_time = datetime.utcnow() - timedelta(minutes=5)  # Ensure no initial spam

bot = commands.Bot(command_prefix=command_prefix, description=description, intents=intents, case_insensitive=True)

# Persistent storage for role and channel
try:
    with open(r"C:\Users\aless\Desktop\discord ping thing\config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}

def save_config():
    with open("config.json", "w") as f:
        json.dump(config, f)

def get_player_count(app_id):
    try:
        url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
        params = {"appid": app_id}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "response" in data and "player_count" in data["response"]:
            player_count = data["response"]["player_count"]
            print(f"[{datetime.utcnow()}] Player count fetched: {player_count}")
            return player_count
        
        return 0
    except Exception as e:
        print(f"[{datetime.utcnow()}] Error fetching player count: {e}")
        return None



@bot.event
async def on_ready():
    print('\n------------------------------------------------------------------------------------------------------------------------------------------')
    print(f'session: {bot.user}\nID.....: {bot.user.id}')
    print('prefix.: ',command_prefix)
    print('author.: Tekad#2295')
    await bot.tree.sync()
    print("Slash commands synced.")
    print('------------------------------------------------------------------------------------------------------------------------------------------')
    # Start the player count check loop
    if not check_player_count.is_running():
        check_player_count.start()
    print("Background task started.")
    print('\nconsole:')



# Command to set the ping role
@bot.tree.command(name="set_ping_role", description="Set the role to be pinged when player count exceeds a threshold.")
@discord.app_commands.describe(role="The role to ping")
async def set_ping_role(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    if guild_id not in config:
        config[guild_id] = {}
    config[guild_id]["ping_role"] = role.id
    save_config()
    await interaction.response.send_message(f"Role <@&{role.id}> has been set to be pinged when player count exceeds the threshold.")



@bot.tree.command(name="whos_on",description="shows the players online")
async def whos_on(interaction: discord.Interaction):
    playerCount = get_player_count(app_id)
    await interaction.response.send_message(f"players online: {playerCount}")



@bot.tree.command(name="set_ping_channel", description="Set the channel for player count notifications.")
@discord.app_commands.describe(channel="The channel to send notifications to")
async def set_ping_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    if guild_id not in config:
        config[guild_id] = {}
    config[guild_id]["ping_channel"] = channel.id
    save_config()
    await interaction.response.send_message(f"Channel {channel.mention} has been set for player count notifications.")



# Background task to check player count every 5 minutes
@tasks.loop(minutes=5)
async def check_player_count():
    global last_notification_time
    player_count = get_player_count(app_id)
    if player_count is None:
        print("Failed to fetch player count.")
        await bot.change_presence(activity=discord.Game(name="Offline"))
        return

    # Update bot activity with player count
    activity_text = f"{player_count} players online"
    await bot.change_presence(activity=discord.Game(name=activity_text))

    if player_count >= 5:
        now = datetime.utcnow()
        if now - last_notification_time >= timedelta(minutes=5):  # Prevent spamming
            for guild_id, settings in config.items():
                try:
                    # Check if notifications are enabled
                    if not settings.get("notifications_enabled", True):  # Default to True if not set
                        print(f"Skipping guild {guild_id}: Notifications are disabled.")
                        continue

                    ping_channel_id = settings.get("ping_channel")
                    ping_role_id = settings.get("ping_role")

                    # Skip if either the ping channel or role is not configured
                    if not ping_channel_id or not ping_role_id:
                        print(f"Skipping guild {guild_id}: Missing ping role or channel.")
                        continue

                    channel = bot.get_channel(ping_channel_id)
                    if not channel:
                        print(f"Skipping guild {guild_id}: Channel with ID {ping_channel_id} not found.")
                        continue

                    # Send appropriate message based on player count
                    if player_count >= 20:
                        await channel.send(
                            f"Players online: {player_count}\n<@&{ping_role_id}> **This has to be some sort of record!**"
                        )
                    elif player_count >= 10:
                        await channel.send(
                            f"Players online: {player_count}\n<@&{ping_role_id}> **There's a lot of activity right now!**"
                        )
                    else:
                        await channel.send(
                            f"**Players online: {player_count}!**"
                        )

                    last_notification_time = now
                except Exception as e:
                    print(f"Error handling guild {guild_id}: {e}")
    else:
        print(f"Player count is below threshold: {player_count}")




@bot.tree.command(name="toggle_notifications", description="Enable or disable player count notifications.")
@discord.app_commands.describe(state="Choose 'enable' to turn on notifications or 'disable' to turn them off.")
async def toggle_notifications(interaction: discord.Interaction, state: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if state.lower() not in ["enable", "disable"]:
        await interaction.response.send_message(
            "Invalid option. Please use 'enable' or 'disable' to toggle notifications.", ephemeral=True
        )
        return

    guild_id = str(interaction.guild.id)
    if guild_id not in config:
        config[guild_id] = {}

    # Set notification state
    config[guild_id]["notifications_enabled"] = (state.lower() == "enable")
    save_config()

    status = "enabled" if config[guild_id]["notifications_enabled"] else "disabled"
    await interaction.response.send_message(f"Player count notifications have been **{status}**.")



bot.run(token=token)