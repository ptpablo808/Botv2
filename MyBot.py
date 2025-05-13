# Importing libraries and modules
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import sqlite3
from keep_alive import keep_alive
import random

# --- Paths & Database ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "user_warnings.db")

# --- Word lists ---
warn_words = ["fuck", "lexis", "nword", "nigger"]
reaction_words = ["damn", "xd", "cringe"]

# --- Create warning table ---
def create_user_table():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_per_guild (
            user_id INTEGER,
            warning_count INTEGER,
            guild_id INTEGER,
            PRIMARY KEY(user_id, guild_id)
        )
    """)
    connection.commit()
    connection.close()

create_user_table()

# --- Increase and fetch warning count ---
def increase_and_get_warnings(user_id: int, guild_id: int):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        SELECT warning_count FROM users_per_guild WHERE user_id = ? AND guild_id = ?
    """, (user_id, guild_id))

    result = cursor.fetchone()

    if result is None:
        cursor.execute("""
            INSERT INTO users_per_guild (user_id, warning_count, guild_id)
            VALUES (?, 1, ?)
        """, (user_id, guild_id))
        connection.commit()
        connection.close()
        return 1
    else:
        new_count = result[0] + 1
        cursor.execute("""
            UPDATE users_per_guild SET warning_count = ? WHERE user_id = ? AND guild_id = ?
        """, (new_count, user_id, guild_id))
        connection.commit()
        connection.close()
        return new_count

# --- Load environment variables ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# --- Keep bot alive on Render ---
keep_alive()

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Sync slash commands on bot ready ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is online!")

# --- Handle messages ---
@bot.event
async def on_message(msg):
    if msg.author.id == bot.user.id:
        return

    msg_content = msg.content.lower()

    # --- Warnings ---
    for term in warn_words:
        if term in msg_content:
            num_warnings = increase_and_get_warnings(msg.author.id, msg.guild.id)
            if num_warnings >= 3:
                await msg.channel.send(f"{msg.author.mention} has reached 3 warnings! 🚨 Please take appropriate action.")
            else:
                await msg.channel.send(
                    f"⚠️ Warning {num_warnings}/3 {msg.author.mention}. You will be at 3 warnings!"
                )
            await msg.delete()
            return

    # --- Reactions ---
    reaction_responses = [
        "Wow <:bravadosc:1371947415019589632>",
        "😳",
        "<:bravadosc:1371947415019589632>",
        "{mention}!",
        "👀"
    ]

    for term in reaction_words:
        if term in msg_content:
            response = random.choice(reaction_responses).format(mention=msg.author.mention)
            await msg.channel.send(response)
            break

    await bot.process_commands(msg)

# --- Slash command: greet ---
greetings = [
    "Hey {mention}, great to see you!",
    "What’s up, {mention}? 👋",
    "Yooo, {mention}!",
    "{mention}, damn!"
]

@bot.tree.command(name="greet", description="Sends a greeting to the selected user")
@app_commands.describe(user="The user you want to greet")
async def greet(interaction: discord.Interaction, user: discord.User):
    greeting = random.choice(greetings).format(mention=user.mention)
    await interaction.response.send_message(greeting)

# --- Slash command: add reaction word ---
@bot.tree.command(name="addreactionword", description="Adds a new reaction word")
@app_commands.describe(word="The word that should trigger a reaction")
async def addreactionword(interaction: discord.Interaction, word: str):
    word = word.lower()
    if word in reaction_words:
        await interaction.response.send_message(f"`{word}` is already in the reaction list.", ephemeral=True)
    else:
        reaction_words.append(word)
        await interaction.response.send_message(f"`{word}` has been added to the reaction list ✅", ephemeral=True)

# --- Slash command: add check reaction to rules message ---
@bot.tree.command(name="addcheckreaction", description="Adds ✅ reaction to the rules message")
async def add_check_reaction(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        channel = interaction.channel
        message = await channel.fetch_message(1371278510391427143)
        await message.add_reaction("\u2705")
        await interaction.followup.send("\u2705 Reaction added to the message!", ephemeral=True)
    except discord.NotFound:
        await interaction.followup.send("❌ Message not found. Check the ID.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to react to that message.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

# --- Give role when member reacts to rules ---
@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id == 1371278510391427143 and str(payload.emoji) == "✅":
        guild = bot.get_guild(payload.guild_id)
        if guild is None:
            return

        role = guild.get_role(1371194192847700179)
        if role is None:
            return

        member = guild.get_member(payload.user_id)
        if member is None or member.bot:
            return

        try:
            await member.add_roles(role, reason="Accepted rules")
            print(f"Gave role to {member.display_name}")
        except discord.Forbidden:
            print("Missing permissions to add role.")
        except Exception as e:
            print(f"Error adding role: {e}")

# --- Run the bot ---
bot.run(TOKEN)
