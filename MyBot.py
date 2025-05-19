# Importing libraries and modules
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import sqlite3
from keep_alive import keep_alive
import random
from image_generator import generate_image, FONT_CHOICES, BG_CHOICES, COLOR_CHOICES, OVERLAY_CHOICES
import traceback
from functools import wraps
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from io import BytesIO

RANK_STYLES = {
    "Gold": {
        "name_color": "#FFD700",
        "rank_color": "#FFD700",
        "bar_start": "#ffcc00",
        "bar_end": "#ffee00",
        "xp_color": "#eeeecc"
    },
    "Platinum": {
        "name_color": "#e5e4e2",
        "rank_color": "#e5e4e2",
        "bar_start": "#c0c0c0",
        "bar_end": "#ffffff",
        "xp_color": "#f0f0f0"
    },
    "Diamond": {
        "name_color": "#b9f2ff",
        "rank_color": "#b9f2ff",
        "bar_start": "#00e5ff",
        "bar_end": "#8be9fd",
        "xp_color": "#cceeff"
    },
    "Ruby": {
        "name_color": "#e0115f",
        "rank_color": "#e0115f",
        "bar_start": "#ff3f80",
        "bar_end": "#ff6f91",
        "xp_color": "#ffc1cc"
    },
    "Sapphire": {
        "name_color": "#0f52ba",
        "rank_color": "#0f52ba",
        "bar_start": "#1e90ff",
        "bar_end": "#87cefa",
        "xp_color": "#cceeff"
    },
    "Krypton": {
        "name_color": "#00ffd5",
        "rank_color": "#aaffaa",
        "bar_start": "#00d2ff",
        "bar_end": "#3aff00",
        "xp_color": "#dddddd"
    }
}


def check_roles(allowed_roles: list[str]):
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if not any(role.name in allowed_roles for role in interaction.user.roles):
                await interaction.response.send_message(
                    "❌ You don't have permission to use this command.", ephemeral=True
                )
                return
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

with open("token.txt", "r") as f:
    TOKEN = f.read().strip()

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

# --- XP Functions ---
def add_xp_and_get_level(user_id: int, guild_id: int, amount: int = 5):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT xp, level FROM users_per_guild
        WHERE user_id = ? AND guild_id = ?
    """, (user_id, guild_id))
    result = cursor.fetchone()

    if result is None:
        # Neuer Nutzer → initialisieren
        cursor.execute("""
            INSERT INTO users_per_guild (user_id, warning_count, guild_id, xp, level)
            VALUES (?, 0, ?, ?, 1)
        """, (user_id, guild_id, amount))
        connection.commit()
        connection.close()
        return 1, amount

    xp, level = result
    xp += amount
    required_xp = 100 + (level - 1) * 50  # XP-Schwelle steigt pro Level

    if xp >= required_xp:
        level += 1
        xp -= required_xp  # Überschüssige XP behalten

    cursor.execute("""
        UPDATE users_per_guild SET xp = ?, level = ?
        WHERE user_id = ? AND guild_id = ?
    """, (xp, level, user_id, guild_id))
    connection.commit()
    connection.close()
    return level, xp


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

# --- rank roles ---
def get_rank_title(level: int) -> str:
    if level >= 35:
        return "🧪 Krypton"
    elif level >= 30:
        return "🔵 Sapphire"
    elif level >= 25:
        return "🔴 Ruby"
    elif level >= 20:
        return "🔷 Diamond"
    elif level >= 15:
        return "⚪ Platinum"
    elif level >= 10:
        return "🟡 Gold"
    elif level >= 5:
        return "⚫ Carbon"
    else:
        return "🟫 Newbie"

def set_rank_role(guild_id: int, rank_name: str, role_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO rank_roles (guild_id, rank_name, role_id)
        VALUES (?, ?, ?)
    """, (guild_id, rank_name, role_id))
    conn.commit()
    conn.close()

def get_rank_roles(guild_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rank_name, role_id FROM rank_roles
        WHERE guild_id = ?
    """, (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    return {name: role_id for name, role_id in rows}


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


    level, xp = add_xp_and_get_level(msg.author.id, msg.guild.id)
    if xp == 0:
        await msg.channel.send(f"🎉 {msg.author.mention} ist jetzt Level {level}!")

        new_rank = get_rank_title(level)
        rank_roles = get_rank_roles(msg.guild.id)
        role_id = rank_roles.get(new_rank)

        if role_id:
            role = msg.guild.get_role(role_id)
            if role:
                old_roles = [msg.guild.get_role(rid) for rid in rank_roles.values()]
                await msg.author.remove_roles(*filter(None, old_roles))
                await msg.author.add_roles(role)
                await msg.channel.send(f"🏅 {msg.author.mention} hat den Rang **{new_rank}** erhalten!")


    await bot.process_commands(msg)



# --- Slash command: setrankrole ---
@bot.tree.command(name="setrankrole", description="Verknüpft einen Rang mit einer Discord-Rolle")
@app_commands.describe(rank="Rangname (z. B. Gold, Diamond, etc.)", role="Discord-Rolle, die zugewiesen werden soll")
@check_roles(["Moderator", "Admin", "Staff"])
async def setrankrole(interaction: discord.Interaction, rank: str, role: discord.Role):
    set_rank_role(interaction.guild.id, rank.strip(), role.id)
    await interaction.response.send_message(
        f"🔗 Rang **{rank}** wurde mit Rolle **{role.name}** verknüpft.",
        ephemeral=True
    )

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
@check_roles(["Moderator", "Admin", "Staff"])
async def addreactionword(interaction: discord.Interaction, word: str):
    word = word.lower()
    if word in reaction_words:
        await interaction.response.send_message(f"`{word}` is already in the reaction list.", ephemeral=True)
    else:
        add_reaction_word(word)
        reaction_words.append(word)
        await interaction.response.send_message(f"`{word}` has been added to the reaction list ✅", ephemeral=True)

# --- Slash command: add warn word ---
@bot.tree.command(name="addwarnword", description="Adds a new warn word")
@app_commands.describe(word="The word that should trigger a warning")
@check_roles(["Moderator", "Admin", "Staff"])
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
@check_roles(["Moderator", "Admin", "Staff"])
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
@check_roles(["Moderator", "Admin", "Staff"])
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
@check_roles(["Moderator", "Admin", "Staff"])
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
@check_roles(["Moderator", "Admin", "Staff"])
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

# --- rank command ---
@bot.tree.command(name="rank", description="Show XP and Level")
async def rank(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        SELECT xp, level FROM users_per_guild
        WHERE user_id = ? AND guild_id = ?
    """, (user_id, guild_id))
    result = cursor.fetchone()
    connection.close()

    if result is None:
        await interaction.response.send_message("📭 You have no XP!", ephemeral=True)
    else:
        xp, level = result
        needed = 100 + (level - 1) * 50
        rank = get_rank_title(level)
        await interaction.response.send_message(
            f"📈 **Level {level}** – XP: `{xp}/{needed}`\n🏅 Rank: **{rank}**",
            ephemeral=True
        )

# --- rankcard command ---

@bot.tree.command(name="rankcard", description="Show Rankcard")
async def rankcard(interaction: discord.Interaction):
    await interaction.response.defer()

    user_id = interaction.user.id
    guild_id = interaction.guild.id

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        SELECT xp, level FROM users_per_guild
        WHERE user_id = ? AND guild_id = ?
    """, (user_id, guild_id))
    result = cursor.fetchone()

    cursor.execute("""
        SELECT user_id, xp FROM users_per_guild
        WHERE guild_id = ? ORDER BY level DESC, xp DESC
    """, (guild_id,))
    rows = cursor.fetchall()
    position = next((i for i, row in enumerate(rows, 1) if row[0] == user_id), None)

    connection.close()

    if result is None:
        await interaction.followup.send("\U0001f4ed You haven't earned any XP yet!", ephemeral=True)
        return

    xp, level = result
    needed = 100 + (level - 1) * 50
    rank = get_rank_title(level).replace("🟡 ", "").replace("🔷 ", "").replace("🧪 ", "").replace("⚫ ", "").replace("🔴 ", "").replace("🔵 ", "").replace("⚪ ", "").replace("🟫 ", "")

    style = RANK_STYLES.get(rank, {
        "name_color": "#ffffff",
        "rank_color": "#cccccc",
        "bar_start": "#888888",
        "bar_end": "#aaaaaa",
        "xp_color": "#bbbbbb"
    })

    width, height = 900, 260
    card = Image.new("RGBA", (width, height))

    bg_path = f"assets/rank_backgrounds/{rank}.png"
    if os.path.exists(bg_path):
        bg = Image.open(bg_path).resize((width, height)).convert("RGBA")
        card.paste(bg, (0, 0))
    else:
        card.paste((30, 40, 50), [0, 0, width, height])

    draw = ImageDraw.Draw(card)

    font_big = ImageFont.truetype("assets/fonts/Manrope-Bold.ttf", 40)
    font_small = ImageFont.truetype("assets/fonts/Manrope-Medium.ttf", 22)

    avatar_url = interaction.user.display_avatar.url
    response = requests.get(avatar_url)
    avatar = Image.open(BytesIO(response.content)).convert("RGBA").resize((160, 160))
    mask = Image.new("L", (160, 160), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 160, 160), fill=255)
    avatar.putalpha(mask)
    card.paste(avatar, (40, 50), avatar)

    # Username
    name_text = f"{interaction.user.name}#{interaction.user.discriminator}"
    name_pos = (230, 40)
    draw.text(name_pos, name_text, font=font_big, fill=style["name_color"])

    # Server Rank Badge
    position_text = f"#{position}"
    badge_padding_x = 10
    badge_padding_y = 5

    bbox = font_small.getbbox(position_text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    badge_w = text_w + badge_padding_x * 2
    badge_h = text_h + badge_padding_y * 2
    badge_x = name_pos[0] + font_big.getlength(name_text) + 12
    badge_y = name_pos[1] + 0  # slightly above center

    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
        radius=badge_h // 2,
        fill=(0, 0, 0, 80),
        outline=(255, 255, 255, 80),
        width=1
    )

    text_x = badge_x + badge_padding_x
    text_y = badge_y + badge_padding_y - 1
    draw.text((text_x, text_y), position_text, font=font_small, fill="#ffffff")

    draw.text((230, 90), f"Level: {level}", font=font_small, fill="#ffffff")
    draw.text((230, 120), f"Rank: {rank}", font=font_small, fill=style["rank_color"])

    bar_x, bar_y, bar_w, bar_h = 230, 190, 600, 25
    bar_radius = 12
    bar_bg_layer = Image.new("RGBA", (bar_w, bar_h), (0, 0, 0, 100))
    bar_mask = Image.new("L", (bar_w, bar_h), 0)
    bar_draw_mask = ImageDraw.Draw(bar_mask)
    bar_draw_mask.rounded_rectangle([(0, 0), (bar_w, bar_h)], radius=bar_radius, fill=255)
    bar_bg_layer.putalpha(bar_mask)
    card.paste(bar_bg_layer, (bar_x, bar_y), bar_bg_layer)

    fill_ratio = min(xp / needed, 1.0)
    fill_w = int(bar_w * fill_ratio)
    for i in range(fill_w):
        blend = i / bar_w
        r = int(int(style["bar_start"][1:3], 16) * (1 - blend) + int(style["bar_end"][1:3], 16) * blend)
        g = int(int(style["bar_start"][3:5], 16) * (1 - blend) + int(style["bar_end"][3:5], 16) * blend)
        b = int(int(style["bar_start"][5:7], 16) * (1 - blend) + int(style["bar_end"][5:7], 16) * blend)
        draw.line([(bar_x + i, bar_y), (bar_x + i, bar_y + bar_h - 1)], fill=(r, g, b))

    draw.text((bar_x, bar_y - 38), f"XP: {xp} / {needed}", font=font_small, fill=style["xp_color"])

    border = Image.new("RGBA", (width, height))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle([(0, 0), (width - 1, height - 1)], radius=18, outline=(255, 255, 255, 40), width=1)
    card = Image.alpha_composite(card, border)

    path = f"rankcard_{interaction.user.id}.png"
    card.save(path)
    await interaction.followup.send(file=discord.File(path))
    os.remove(path)



# --- givexp ---
@bot.tree.command(name="givexp", description="Give XP (incl. Level-Up & Role)")
@app_commands.describe(user="User", amount="XP-Amount")
@check_roles(["Admin", "Moderator"])
async def givexp(interaction: discord.Interaction, user: discord.Member, amount: int):
    level, xp = add_xp_and_get_level(user.id, interaction.guild.id, amount)

    new_rank = get_rank_title(level)
    rank_roles = get_rank_roles(interaction.guild.id)
    role_id = rank_roles.get(new_rank)

    if role_id:
        role = interaction.guild.get_role(role_id)
        old_roles = [interaction.guild.get_role(rid) for rid in rank_roles.values()]
        await user.remove_roles(*filter(None, old_roles))
        await user.add_roles(role)

    await interaction.response.send_message(
        f"✅ {user.mention} received **{amount} XP** and is now level {level}!",
        ephemeral=True
    )


# --- set user rank command ---

@bot.tree.command(name="setuserrank", description="Set user rank incl. Level & XP")
@app_commands.describe(user="User")
@app_commands.choices(rank=[
    app_commands.Choice(name="🟫 Newbie", value="🟫 Newbie"),
    app_commands.Choice(name="⚫ Carbon", value="⚫ Carbon"),
    app_commands.Choice(name="🟡 Gold", value="🟡 Gold"),
    app_commands.Choice(name="⚪ Platinum", value="⚪ Platinum"),
    app_commands.Choice(name="🔷 Diamond", value="🔷 Diamond"),
    app_commands.Choice(name="🔴 Ruby", value="🔴 Ruby"),
    app_commands.Choice(name="🔵 Sapphire", value="🔵 Sapphire"),
    app_commands.Choice(name="🧪 Krypton", value="🧪 Krypton")
])
@check_roles(["Admin", "Moderator"])
async def setuserrank(interaction: discord.Interaction, user: discord.Member, rank: app_commands.Choice[str]):
    rank_levels = {
        "🟫 Newbie": 1,
        "⚫ Carbon": 5,
        "🟡 Gold": 10,
        "⚪ Platinum": 15,
        "🔷 Diamond": 20,
        "🔴 Ruby": 25,
        "🔵 Sapphire": 30,
        "🧪 Krypton": 35
    }
    rank_name = rank.value
    level = rank_levels[rank_name]
    xp = 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users_per_guild (user_id, guild_id, warning_count, xp, level)
        VALUES (?, ?, 0, ?, ?)
        ON CONFLICT(user_id, guild_id) DO UPDATE SET xp=?, level=?
    """, (user.id, interaction.guild.id, xp, level, xp, level))
    conn.commit()
    conn.close()

    # Rollen aktualisieren
    rank_roles = get_rank_roles(interaction.guild.id)
    role_id = rank_roles.get(rank_name)
    if role_id:
        role = interaction.guild.get_role(role_id)
        old_roles = [interaction.guild.get_role(rid) for rid in rank_roles.values()]
        await user.remove_roles(*filter(None, old_roles))
        await user.add_roles(role)

    await interaction.response.send_message(f"✅ {user.mention} wurde auf Rang **{rank_name}** gesetzt.", ephemeral=True)


# --- command imagegen ---

@bot.tree.command(name="imagegen", description="Generate an image with text and overlays")
@app_commands.describe(
    text="The text that will appear on the image",
    font="Choose a font",
    bg="Choose a background",
    overlay="Choose an overlay",
    color="Select a predefined color or enter a hex code",
    colorful="Add an additional colorful effect"
)
@app_commands.choices(
    font=[discord.app_commands.Choice(name=name, value=value) for name, value in FONT_CHOICES.items()],
    bg=[discord.app_commands.Choice(name=name, value=value) for name, value in BG_CHOICES.items()],
    overlay=[discord.app_commands.Choice(name=name, value=value) for name, value in OVERLAY_CHOICES.items()],
    color=[discord.app_commands.Choice(name=name, value=value) for name, value in COLOR_CHOICES.items()]
)
async def imagegen(
    interaction: discord.Interaction,
    text: str,
    font: app_commands.Choice[int],
    bg: app_commands.Choice[int],
    overlay: app_commands.Choice[int],
    color: app_commands.Choice[str] = None,
    colorful: bool = False
):
    if len(text) > 12:
        await interaction.response.send_message("❌ Text too long. Please use max 12 characters.", ephemeral=True)
        return
    await interaction.response.defer()

    hex_color = color.value if color else "#8D0AF5"
    output_path = f"generated/generated_{interaction.id}.png"

    try:
        generate_image(
            text=text,
            font_index=font.value,
            bg_index=bg.value,
            overlay_index=overlay.value,
            color=hex_color,
            colorful=colorful,
            output_path=output_path
        )
        await interaction.followup.send(file=discord.File(output_path))
    except discord.HTTPException as http_err:
        await interaction.followup.send("❌ Discord API temporarily blocked you (429). Please wait and try again.", ephemeral=True)
        print("HTTPException:", http_err)
    except Exception as e:
        await interaction.followup.send("❌ Unexpected error occurred while generating the image.", ephemeral=True)
        traceback.print_exc()
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

# --- Run the bot ---
bot.run(TOKEN)
