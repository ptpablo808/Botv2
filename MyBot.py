# Importing libraries and modules
import os # Allows interaction with the operating system
import discord # Provides methods to interact with the Discord API
from discord.ext import commands # Extends discord.py and allows creation and handling of commands
from discord import app_commands # Allows parameters to be used for slash-commands
from dotenv import load_dotenv # Allows the use of environment variables (this is what we'll use to manage our
                               # tokens and keys)
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

profanity = ["fuck", "lexis", "nword"]


def create_user_table():
    connection = sqlite3.connect(f"{BASE_DIR}\\user_warnings.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "users_per_guild" (
            "user_id"   INTEGER,
            "warning_count" INTEGER,
            "guild_id"  INTEGER,
            PRIMARY KEY("user_id","guild_id")
        )
    """)

    connection.commit()
    connection.close()


create_user_table()

def increase_and_get_warnings(user_id: int, guild_id: int):
    connection = sqlite3.connect(f"{BASE_DIR}\\user_warnings.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT warning_count
        FROM users_per_guild
        WHERE (user_id = ?) AND (guild_id = ?);
    """, (user_id, guild_id))

    result = cursor.fetchone()

    if result == None:
        cursor.execute("""
            INSERT INTO users_per_guild (user_id, warning_count, guild_id)
            VALUES (?, 1, ?);
        """, (user_id, guild_id))
        
        connection.commit()
        connection.close()

        return 1
    
    cursor.execute("""
        UPDATE users_per_guild
        SET warning_count = ?
        WHERE (user_id = ?) AND (guild_id = ?);
    """, (result[0] + 1, user_id, guild_id))

    connection.commit()
    connection.close()

    return result [0] + 1

from keep_alive import keep_alive # NEW

load_dotenv() # Loads and reads the .env file
TOKEN = os.getenv("DISCORD_TOKEN") # Reads and stores the Discord Token from the .env file

keep_alive() # NEW

# Setup of intents. Intents are permissions the bot has on the server
intents = discord.Intents.default() # Intents can be set through this object
intents.message_content = True  # This intent allows you to read and handle messages from users

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents) # Creates a bot and uses the intents created earlier

# Bot ready-up code
@bot.event # Decorator
async def on_ready():
    await bot.tree.sync() # Syncs the commands with Discord so that they can be displayed
    print(f"{bot.user} is online!") # Appears when the bot comes online

@bot.event
async def on_message(msg):
    if msg.author.id != bot.user.id:
        for term in profanity:
            if term.lower() in msg.content.lower():
                num_warnings = increase_and_get_warnings(msg.author.id, msg.guild.id)

                if num_warnings >= 3:
                    await msg.author.ban(reason="Exceeded 3 strikes for using profanity.")
                    await msg.channel.send(f"{msg.author.mention} has been banned for repeated profanity.")
                else:
                    await msg.channel.send(
                        f"Warning {num_warnings}/3 {msg.author.mention}. If you reach 3 warnings, you will be banned"
                    )

                    await msg.delete()

                break

    await bot.process_commands(msg)


@bot.event
async def on_message(msg):
    if msg.author.id != bot.user.id:
        await msg.channel.send(f"Wow, {msg.author.mention}")

@bot.tree.command(name="greet", description="Sends a greeting to the user")
async def greet(interaction: discord.Interaction):
    username = interaction.user.mention
    await interaction.response.send_message(f"Yooo, {username}")



# Run the bot
bot.run(TOKEN) # This code uses your bot's token to run the bot
