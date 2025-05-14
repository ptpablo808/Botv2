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
    print("Creating warn_words table...")
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
    print("Creating users_per_guild table...")
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
    print("Creating guild_settings table...")
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
    print("Creating reaction_words table...")
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reaction_words (
            word TEXT PRIMARY KEY
        )
    """)
    connection.commit()
    connection.close()

# Create all tables
create_user_table()
create_setup_table()
create_reactionword_table()
create_warnword_table()

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
        description=description.replace("\\n", "\n"),
        color=embed_color
    )
    embed.set_footer(
        text=f"Announcement by {interaction.user.display_name} · via /announce",
        icon_url=interaction.user.avatar.url
    )

    await interaction.channel.send(embed=embed)
    await interaction.followup.send("✅ Announcement sent ✅", ephemeral=True)

#
# Du kannst hier auf Wunsch sagen: "Füge Protokolle für Funktion XYZ hinzu" oder "zeige mir wo was passiert".
