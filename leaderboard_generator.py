from PIL import Image, ImageDraw, ImageFont
import os
from io import BytesIO
from rankcard_config import (
    RANK_STYLES,
    FONT_BIG_PATH, FONT_SMALL_PATH, FONT_XP_PATH, FONT_RANK_PATH,
    FONT_SMALL_SIZE, FONT_XP_SIZE
)

FONT_USERNAME_PATH = "assets/fonts/Manrope-Bold.ttf"


def generate_leaderboard_image(top_users):
    width = 900
    row_height = 60
    base_offset = 80
    footer_height = 40
    height = base_offset + row_height * len(top_users) + footer_height

    # Custom Background
    bg_path = "assets/leaderboard_bg.png"
    if os.path.exists(bg_path):
        card = Image.open(bg_path).convert("RGBA").resize((width, height))
    else:
        card = Image.new("RGBA", (width, height), (24, 24, 32))
    draw = ImageDraw.Draw(card)

    try:
        font_name = ImageFont.truetype(FONT_USERNAME_PATH, FONT_SMALL_SIZE)
        font_stats = ImageFont.truetype(FONT_SMALL_PATH, FONT_SMALL_SIZE)
        font_position = ImageFont.truetype(FONT_SMALL_PATH, FONT_SMALL_SIZE + 4)
        title_font = ImageFont.truetype(FONT_RANK_PATH, 30)
        footer_font = ImageFont.truetype(FONT_SMALL_PATH, 16)
    except Exception as e:
        raise RuntimeError(f"Font loading failed: {e}")

    # Titel zentriert
    title_text = "L E A D E R B O A R D"
    title_bbox = title_font.getbbox(title_text)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_w) // 2, 25), title_text, font=title_font, fill="#ffffff")

    y = base_offset
    for idx, user in enumerate(top_users):
        position = user["position"]
        rank_name = user["rank"]
        rank_style = RANK_STYLES.get(rank_name, RANK_STYLES.get("Carbon"))

        pos_color = "#FFD700" if position == 1 else "#C0C0C0" if position == 2 else "#cd7f32" if position == 3 else "#ffffff"

        row_y = y + idx * row_height

        if idx % 2 == 1:
            stripe = Image.new("RGBA", (width, row_height), (255, 255, 255, 10))
            card.paste(stripe, (0, row_y - 5), stripe)

        if idx > 0:
            overlay = Image.new("RGBA", (width - 70, 1), (255, 255, 255, 40))
            card.paste(overlay, (30, row_y - 5), overlay)

        draw.text((30, row_y + 9), f"#{position}", font=font_position, fill=pos_color)

        if user.get("avatar_bytes"):
            avatar = Image.open(BytesIO(user["avatar_bytes"])).convert("RGBA").resize((40, 40))
            mask = Image.new("L", (40, 40), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, 40, 40), fill=255)
            avatar.putalpha(mask)
            card.paste(avatar, (80, row_y + 5), avatar)

        icon_path = f"assets/rank_icons/{rank_name}.png"
        if os.path.exists(icon_path):
            icon = Image.open(icon_path).resize((32, 32)).convert("RGBA")
            card.paste(icon, (130, row_y + 8), icon)

        name_text = f"{user['username']}#{user['discriminator']}"
        draw.text((175, row_y + 10), name_text, font=font_name, fill="#ffffff")

        stats_text = f"Level {user['level']} – XP: {user['xp']}"
        bbox = font_stats.getbbox(stats_text)
        tw = bbox[2] - bbox[0]
        draw.text((width - tw - 40, row_y + 11), stats_text, font=font_stats, fill=rank_style["xp_color"])

    # Footer
    footer_text = "Made by Purpp"
    footer_bbox = footer_font.getbbox(footer_text)
    footer_w = footer_bbox[2] - footer_bbox[0]
    draw.text(((width - footer_w) // 2, height - footer_height + 10), footer_text, font=footer_font, fill="#888888")

    return card
