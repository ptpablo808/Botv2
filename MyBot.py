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
warn_words = ["fuck", "lexis", "nword", "nigger"]
reaction_words = ["damn", "xd", "cringe"]
trigger_words = ["cherax", "chrx"]  # Beispiel für Wörter, auf die der Bot reagiert
emoji_to_react = "<:logo_s:1371984329504329789>"  # Emoji, das der Bot als Reaktion hinzufügen soll

# --- Create tables ---
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

create_user_table()
create_setup_table()

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

# --- Update rules message ---
def update_rules_text(guild_id, message_id, new_text):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("SELECT rules_message_id FROM guild_settings WHERE guild_id = ?", (guild_id,))
    result = cursor.fetchone()
    connection.close()
    return result and result[0] == message_id

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

# --- Slash command: setup ---
@bot.tree.command(name="setup", description="Post a placeholder rules message and bind a role")
@app_commands.describe(role="The role to give when reacted")
async def setup(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    msg = await interaction.channel.send("📜 **Regeln folgen...**")
    await msg.add_reaction("✅")

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO guild_settings (guild_id, rules_message_id, role_id)
        VALUES (?, ?, ?)
    """, (interaction.guild.id, msg.id, role.id))
    connection.commit()
    connection.close()

    await interaction.followup.send("✅ Setup abgeschlossen! Nachricht wurde gepostet. Verwende nun `/setrules`, um den Text zu ändern.", ephemeral=True)

# --- Slash command: setrules ---
@bot.tree.command(name="setrules", description="Aktualisiert den Inhalt der Regel-Nachricht")
@app_commands.describe(text="Der neue Text für die Regel-Nachricht")
async def setrules(interaction: discord.Interaction, text: str):
    settings = get_guild_settings(interaction.guild.id)
    if not settings:
        await interaction.response.send_message("⚠️ Kein Setup für diesen Server gefunden. Bitte zuerst `/setup` ausführen.", ephemeral=True)
        return

formatted_text = text.replace("\\n", "\n")
channel = interaction.channel
    try:
        message = await channel.fetch_message(settings[0])
        await message.edit(content=formatted_text)
        await interaction.response.send_message("✅ Regeltext erfolgreich aktualisiert.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ Nachricht nicht gefunden. Stelle sicher, dass der Befehl im richtigen Kanal verwendet wird.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Ich habe keine Berechtigung, um die Nachricht zu bearbeiten.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Fehler: {e}", ephemeral=True)

# --- Slash command: viewsetup ---
@bot.tree.command(name="viewsetup", description="Zeigt das aktuelle Setup für diesen Server")
async def viewsetup(interaction: discord.Interaction):
    settings = get_guild_settings(interaction.guild.id)
    if not settings:
        await interaction.response.send_message("ℹ️ Für diesen Server wurde noch kein Setup gespeichert.", ephemeral=True)
    else:
        msg_id, role_id = settings
        await interaction.response.send_message(
            f"📌 **Aktuelles Setup:**\n• Nachricht ID: `{msg_id}`\n• Rolle ID: `{role_id}`",
            ephemeral=True
        )

# --- Slash command: announce (Embed-Nachrichten senden) ---
@bot.tree.command(name="announce", description="Sendet eine Embed-Announcement-Nachricht")
@app_commands.describe(
    title="Titel der Ankündigung",
    description="Beschreibungstext der Ankündigung",
    color="Hex-Farbcode (z.B. #ff0000 für rot)"
)
async def announce(interaction: discord.Interaction, title: str, description: str, color: str = "#00ff00"):
    await interaction.response.defer(ephemeral=True)

    try:
        embed_color = discord.Color(int(color.strip("#"), 16))
    except ValueError:
        embed_color = discord.Color.green()

    embed = discord.Embed(
        title=title,
        description=description.replace("\n", "
"),
        color=embed_color
    )

    embed.set_footer(text=f"Ankündigung von {interaction.user.display_name}", icon_url=interaction.user.avatar.url)

    await interaction.channel.send(embed=embed)
    await interaction.followup.send("✅ Announcement gesendet!", ephemeral=True)

# --- Slash command: generate image ---
@bot.tree.command(name="generate", description="Erstellt ein Bild mit Text")
@app_commands.describe(
    text="Dein Text",
    bg="Farbname oder Hintergrundbild (z. B. 'bg_1.png')",
    font="Schriftname: celsius_flower oder high_speed",
    effect="Effekt: z. B. glow"
)
async def generate(
    interaction: discord.Interaction,
    text: str,
    bg: str = "white",
    font: str = "arial",
    effect: str = "none"
):
    await interaction.response.defer()
    image_path = create_image(text, bg, font, effect)
    await interaction.followup.send(file=discord.File(image_path))

# --- Give role when member reacts to rules ---
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

# --- Remove role when member removes reaction ---
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
