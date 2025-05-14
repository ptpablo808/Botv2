# Importing libraries and modules
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import sqlite3
from keep_alive import keep_alive
import random
from image_generator import create_image  # NEU

# --- Paths & Database ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "user_warnings.db")

# --- Word lists ---
warn_words = []
reaction_words = ["damn", "xd", "cringe"]
trigger_words = ["cherax", "chrx"]
emoji_to_react = "<:logo_s:1371984329504329789>"

# --- Create tables ---
def create_warnword_table():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warn_words (
            word TEXT PRIMARY KEY
        )
    """)
    connection.commit()
    connection.close()
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

def create_setup_table():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            rules_message_id INTEGER,
            role_id INTEGER
        )
    """)
    connection.commit()
    connection.close()

def create_reactionword_table():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reaction_words (
            word TEXT PRIMARY KEY
        )
    """)
    connection.commit()
    connection.close()

create_user_table()
create_setup_table()
create_reactionword_table()
create_warnword_table()

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

# --- Utility: get settings from DB ---
def get_guild_settings(guild_id):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("SELECT rules_message_id, role_id FROM guild_settings WHERE guild_id = ?", (guild_id,))
    row = cursor.fetchone()
    connection.close()
    return row

# --- Sync slash commands on bot ready ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is online!")

# --- Reaction Word Helpers ---
def load_reaction_words():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("SELECT word FROM reaction_words")
    rows = cursor.fetchall()
    connection.close()
    return [row[0] for row in rows]

def add_reaction_word(word):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("INSERT OR IGNORE INTO reaction_words (word) VALUES (?)", (word,))
    connection.commit()
    connection.close()

def remove_reaction_word(word):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM reaction_words WHERE word = ?", (word,))
    connection.commit()
    connection.close()

reaction_words = load_reaction_words()

# --- Warn Word Helpers ---
def load_warn_words():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("SELECT word FROM warn_words")
    rows = cursor.fetchall()
    connection.close()
    return [row[0] for row in rows]

def add_warn_word(word):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("INSERT OR IGNORE INTO warn_words (word) VALUES (?)", (word,))
    connection.commit()
    connection.close()

def remove_warn_word(word):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM warn_words WHERE word = ?", (word,))
    connection.commit()
    connection.close()

warn_words = load_warn_words()

# --- Handle messages ---
@bot.event
async def on_message(msg):
    if msg.author.id == bot.user.id:
        return
    msg_content = msg.content.lower()
    for term in warn_words:
        if term in msg_content:
            num_warnings = increase_and_get_warnings(msg.author.id, msg.guild.id)
            if num_warnings >= 3:
                await msg.channel.send(f"{msg.author.mention} has reached 3 warnings! 🚨 Please take appropriate action.")
            else:
                await msg.channel.send(f"⚠️ Warning {num_warnings}/3 {msg.author.mention}. You will be at 3 warnings!")
            await msg.delete()
            return
    for word in trigger_words:
        if word in msg_content:
            await msg.add_reaction(emoji_to_react)
            break
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
@bot.tree.command(name="greet", description="Sends a greeting to the selected user")
@app_commands.describe(user="The user you want to greet")
async def greet(interaction: discord.Interaction, user: discord.User):
    greetings = [
        "Hey {mention}, great to see you!",
        "What’s up, {mention}? 👋",
        "Yooo, {mention}!",
        "{mention}, damn!"
    ]
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
        add_reaction_word(word)
        reaction_words.append(word)
        await interaction.response.send_message(f"`{word}` has been added to the reaction list ✅", ephemeral=True)
    word = word.lower()
    if word in reaction_words:
        await interaction.response.send_message(f"`{word}` is already in the reaction list.", ephemeral=True)
    else:
        reaction_words.append(word)
        await interaction.response.send_message(f"`{word}` has been added to the reaction list ✅", ephemeral=True)

# --- Slash command: add warn word ---
@bot.tree.command(name="addwarnword", description="Adds a new warn word")
@app_commands.describe(word="The word that should trigger a warning")
async def addwarnword(interaction: discord.Interaction, word: str):
    word = word.lower()
    if word in warn_words:
        await interaction.response.send_message(f"`{word}` is already in the warn list.", ephemeral=True)
    else:
        add_warn_word(word)
        warn_words.append(word)
        await interaction.response.send_message(f"`{word}` has been added to the warn list ⚠️", ephemeral=True)

# --- Slash command: list warn words ---
@bot.tree.command(name="listwarnwords", description="Displays all current warn words")
async def listwarnwords(interaction: discord.Interaction):
    if warn_words:
        words = ", ".join(f"`{word}`" for word in warn_words)
        await interaction.response.send_message(f"📃 **Current warn words:** {words}", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ No warn words added yet.", ephemeral=True)

# --- Slash command: remove warn word ---
@bot.tree.command(name="removewarnword", description="Removes a warn word")
@app_commands.describe(word="The word to remove")
async def removewarnword(interaction: discord.Interaction, word: str):
    word = word.lower()
    if word in warn_words:
        remove_warn_word(word)
        warn_words.remove(word)
        await interaction.response.send_message(f"❌ `{word}` has been removed from the warn list.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ `{word}` is not in the warn list.", ephemeral=True)

# --- Slash command: list reaction words ---
@bot.tree.command(name="listreactionwords", description="Displays all current reaction words")
async def listreactionwords(interaction: discord.Interaction):
    if reaction_words:
        words = ", ".join(f"`{word}`" for word in reaction_words)
        await interaction.response.send_message(f"📃 **Current reaction words:** {words}", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ No reaction words added yet.", ephemeral=True)

# --- Slash command: remove reaction word ---
@bot.tree.command(name="removereactionword", description="Removes a reaction word")
@app_commands.describe(word="The word to remove")
async def removereactionword(interaction: discord.Interaction, word: str):
    word = word.lower()
    if word in reaction_words:
        remove_reaction_word(word)
        reaction_words.remove(word)
        await interaction.response.send_message(f"❌ `{word}` has been removed from the list.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ `{word}` is not in the reaction list.", ephemeral=True)

# --- Slash command: setup ---
@bot.tree.command(name="setup", description="Post a placeholder rules message and bind a role")
@app_commands.describe(role="The role to give when reacted")
async def setup(interaction: discord.Interaction, role: discord.Role):
    msg = await interaction.channel.send("📜 **Waiting for Rules...**")
    await msg.add_reaction("✅")
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO guild_settings (guild_id, rules_message_id, role_id)
        VALUES (?, ?, ?)
    """, (interaction.guild.id, msg.id, role.id))
    connection.commit()
    connection.close()
    await interaction.response.send_message("✅ Setup complete! Placeholder message posted. Use `/setrules` to edit the content.", ephemeral=True)

# --- Slash command: setrules ---
@bot.tree.command(name="setrules", description="Updates the content of the rules message")
@app_commands.describe(text="The new content for the rules message")
async def setrules(interaction: discord.Interaction, text: str):
    settings = get_guild_settings(interaction.guild.id)
    if not settings:
        await interaction.response.send_message("⚠️ No setup found for this server. Please run `/setup` first.", ephemeral=True)
        return
    formatted_text = text.replace("\\n", "\n")
    channel = interaction.channel
    try:
        message = await channel.fetch_message(settings[0])
        await message.edit(content=formatted_text)
        await interaction.response.send_message("✅ Rules message successfully updated.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ Message not found. Make sure you're in the correct channel.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to edit that message.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

# --- Slash command: viewsetup ---
@bot.tree.command(name="viewsetup", description="Displays the current setup for this server")
async def viewsetup(interaction: discord.Interaction):
    settings = get_guild_settings(interaction.guild.id)
    if not settings:
        await interaction.response.send_message("ℹ️ No setup found for this server yet.", ephemeral=True)
    else:
        msg_id, role_id = settings
        await interaction.response.send_message(
            f"📌 **Current Setup:**\n• Message ID: `{msg_id}`\n• Role ID: `{role_id}`",
            ephemeral=True
        )

# --- Slash command: announce ---
@bot.tree.command(name="announce", description="Sends an embedded announcement")
@app_commands.describe(
    title="Title of the announcement",
    description="Content of the announcement",
    color="Hex color code (e.g. #ff0000) or name (red, blue, green, etc.)"
)
async def announce(interaction: discord.Interaction, title: str, description: str, color: str = "#00ff00"):
    predefined_colors = {
        "red": 0xFF0000,
        "blue": 0x3498DB,
        "green": 0x2ECC71,
        "yellow": 0xF1C40F,
        "orange": 0xE67E22,
        "purple": 0x9B59B6,
        "gray": 0x95A5A6,
        "default": 0x00FF00
    }

    hex_color = predefined_colors.get(color.lower(), None)
    if hex_color is None:
        try:
            hex_color = int(color.strip("#"), 16)
        except ValueError:
            hex_color = predefined_colors["default"]

    embed_color = discord.Color(hex_color)

    embed = discord.Embed(
    title=title,
    description=description.replace("\n", "
"),
    color=embed_color
),
        color=embed_color
    )
    embed.set_footer(text=f"Announcement by {interaction.user.display_name} · via /announce", icon_url=interaction.user.avatar.url)

    await interaction.channel.send(embed=embed)
    await interaction.followup.send("✅ Announcement sent ✅", ephemeral=True)

# --- Slash command: generate image ---
@bot.tree.command(name="generate", description="Generates an image with text")
@app_commands.describe(
    text="Your text",
    bg="Background color or image (e.g. 'bg_1.png')",
    font="Font name: celsius_flower or high_speed",
    effect="Effect: e.g. glow"
)
async def generate(interaction: discord.Interaction, text: str, bg: str = "white", font: str = "arial", effect: str = "none"):
    await interaction.response.defer()
    image_path = create_image(text, bg, font, effect)
    await interaction.followup.send(file=discord.File(image_path))

# --- React to rules message ---
@bot.event
async def on_raw_reaction_add(payload):
    settings = get_guild_settings(payload.guild_id)
    if not settings:
        return
    rules_msg_id, role_id = settings
    if payload.message_id != rules_msg_id or str(payload.emoji) != "✅":
        return
    guild = bot.get_guild(payload.guild_id)
    role = guild.get_role(role_id)
    member = guild.get_member(payload.user_id)
    if guild and role and member and not member.bot:
        try:
            await member.add_roles(role, reason="Accepted rules")
            print(f"Gave role to {member.display_name}")
        except Exception as e:
            print(f"Error: {e}")

@bot.event
async def on_raw_reaction_remove(payload):
    settings = get_guild_settings(payload.guild_id)
    if not settings:
        return
    rules_msg_id, role_id = settings
    if payload.message_id != rules_msg_id or str(payload.emoji) != "✅":
        return
    guild = bot.get_guild(payload.guild_id)
    role = guild.get_role(role_id)
    member = guild.get_member(payload.user_id)
    if guild and role and member and not member.bot:
        try:
            await member.remove_roles(role, reason="Removed reaction from rules")
            print(f"Removed role from {member.display_name}")
        except Exception as e:
            print(f"Error removing role: {e}")

# --- Run the bot ---
bot.run(TOKEN)
