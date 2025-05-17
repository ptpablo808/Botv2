# Importing libraries and modules
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import sqlite3
from keep_alive import keep_alive
import random
from image_generator import generate_image, FONT_CHOICES, BG_CHOICES
import traceback

# --- Load environment variables ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

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
            role_id INTEGER,
            reaction_emoji TEXT DEFAULT '✅'
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
    cursor.execute("SELECT rules_message_id, role_id, reaction_emoji FROM guild_settings WHERE guild_id = ?", (guild_id,))
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
@app_commands.describe(
    role="The role to give when reacted",
    emoji="The emoji users must react with (default ✅)"
)
async def setup(interaction: discord.Interaction, role: discord.Role, emoji: str = "✅"):
    msg = await interaction.channel.send("📜 **Waiting for Rules...**")
    await msg.add_reaction(emoji)
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO guild_settings (guild_id, rules_message_id, role_id, reaction_emoji)
        VALUES (?, ?, ?, ?)
    """, (interaction.guild.id, msg.id, role.id, emoji))
    connection.commit()
    connection.close()
    await interaction.response.send_message("✅ Setup complete! Placeholder message posted. Use `/setrules` to edit the content.", ephemeral=True)

# --- Slash command: setrules ---
@bot.tree.command(name="setrules", description="Edit the posted rules message")
@app_commands.describe(text="New rules text (use *n for newlines)")
async def setrules(interaction: discord.Interaction, text: str):
    rs = get_guild_settings(interaction.guild.id)
    if not rs:
        await interaction.response.send_message("⚠️ No rules setup found.", ephemeral=True)
        return

    channel = interaction.channel
    msg = await channel.fetch_message(rs[0])
    # Replace placeholder with actual newline
    formatted_text = text.replace("\\n", "\n")

    # Edit message or fallback to file
    if len(formatted_text) <= 2000:
        await msg.edit(content=formatted_text)
        await interaction.response.send_message("✅ Rules updated.", ephemeral=True)
    else:
        filename = f"rules_{interaction.guild.id}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(formatted_text)
        await msg.edit(content="📄 Rules are too long; see attached file.")
        await interaction.followup.send(file=discord.File(filename), ephemeral=True)
        os.remove(filename)

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
    color="Hex color code (e.g. #ff0000) or name (red, blue, green, etc.)",
    image_url="Optional image URL for the embed",
    image_file="Optional image file to include"
)
async def announce(
    interaction: discord.Interaction,
    title: str,
    description: str,
    color: str = "#8D0AF5",
    image_url: str = None,
    image_file: discord.Attachment = None
):
    await interaction.response.defer(ephemeral=True)

    predefined_colors = {
        "red": 0xFF0000,
        "blue": 0x3498DB,
        "green": 0x2ECC71,
        "yellow": 0xF1C40F,
        "orange": 0xE67E22,
        "purple": 0x9B59B6,
        "gray": 0x95A5A6,
        "default": 0x8D0AF5
    }

    hex_color = predefined_colors.get(color.lower())
    if hex_color is None:
        try:
            hex_color = int(color.lstrip("#"), 16)
        except ValueError:
            hex_color = predefined_colors["default"]

    embed = discord.Embed(
        title=title,
        description=description.replace("\\n", "\n"),
        color=discord.Color(hex_color)
    )
    embed.set_footer(
        text=f"Announcement by {interaction.user.display_name}",
        icon_url=bot.user.display_avatar.url
    )

    file = None

    if image_url:
        embed.set_image(url=image_url)
    elif image_file and image_file.content_type.startswith("image/"):
        file = await image_file.to_file()
        embed.set_image(url=f"attachment://{file.filename}")

    if file:
        await interaction.channel.send(embed=embed, file=file)
    else:
        await interaction.channel.send(embed=embed)

    await interaction.followup.send("✅ Announcement sent ✅", ephemeral=True)


# --- React to rules message ---
@bot.event
async def on_raw_reaction_add(payload):
    settings = get_guild_settings(payload.guild_id)
    if not settings:
        return
    rules_msg_id, role_id, reaction_emoji = settings
    if payload.message_id != rules_msg_id or str(payload.emoji) != reaction_emoji:
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
    rules_msg_id, role_id, reaction_emoji = settings
    if payload.message_id != rules_msg_id or str(payload.emoji) != reaction_emoji:
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

@bot.tree.command(name="imagegen", description="Erzeugt ein Bild mit Text und Overlays")
@app_commands.describe(
    text="Der Text, der auf dem Bild erscheinen soll",
    font="Wähle einen Font",
    bg="Wähle einen Hintergrund",
    overlay_index="Overlay-Index (z. B. 0, 1, 2...)",
    color="Hex-Farbe (z. B. #ff0000)",
    colorful="Zusätzlicher Farbeffekt"
)
@app_commands.choices(
    font=[discord.app_commands.Choice(name=name, value=value) for name, value in FONT_CHOICES.items()],
    bg=[discord.app_commands.Choice(name=name, value=value) for name, value in BG_CHOICES.items()]
)
async def imagegen(
    interaction: discord.Interaction,
    text: str,
    font: app_commands.Choice[int],
    bg: app_commands.Choice[int],
    overlay_index: int = 0,
    color: str = "#ffffff",
    colorful: bool = False
):
    await interaction.response.defer()

    output_path = f"generated/generated_{interaction.id}.png"

    try:
        generate_image(
            text=text,
            font_index=font.value,
            bg_index=bg.value,
            overlay_index=overlay_index,
            color=color,
            colorful=colorful,
            output_path=output_path
        )
        await interaction.followup.send(file=discord.File(output_path))
    except discord.HTTPException as http_err:
        await interaction.followup.send("❌ Discord API blockiert dich temporär (429). Warte kurz und versuche es erneut.", ephemeral=True)
        print("HTTPException:", http_err)
    except Exception as e:
        await interaction.followup.send("❌ Unerwarteter Fehler beim Generieren des Bildes.", ephemeral=True)
        traceback.print_exc()
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

# --- Run the bot ---
bot.run(TOKEN)
