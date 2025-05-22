from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import os
from rankcard_config import (
    RANK_STYLES,
    FONT_BIG_PATH, FONT_SMALL_PATH, FONT_XP_PATH, FONT_RANK_PATH, FONT_LEVEL_LABEL_PATH,
    FONT_BIG_SIZE, FONT_SMALL_SIZE, FONT_XP_SIZE, FONT_RANK_SIZE, FONT_LEVEL_LABEL_SIZE,  # ⬅️ Diese Zeile sicherstellen
    BADGE_FONT_PATH, BADGE_FONT_SIZE, BADGE_PADDING_X, BADGE_PADDING_Y, BADGE_OFFSET_Y,
    BADGE_TEXT_OFFSET_X, BADGE_TEXT_OFFSET_Y,
    BAR_X, BAR_Y, BAR_WIDTH, BAR_HEIGHT, BAR_RADIUS
)

# Neue Font-Pfade für Rank und XP
FONT_RANK_PATH = "assets/fonts/Manrope-ExtraBold.ttf"
FONT_XP_PATH = "assets/fonts/Retro-Gaming.ttf"


def generate_rankcard_image(username, discriminator, avatar_bytes, xp, level, position, rank):
    needed = 100 + (level - 1) * 50
    style = RANK_STYLES.get(rank, {
        "name_gradient_start": "#ffffff",
        "name_gradient_end": "#0CA7A7",
        "rank_color": "#cccccc",
        "bar_start": "#000000",
        "bar_end": "#04D1D1",
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
    font_big = ImageFont.truetype(FONT_BIG_PATH, FONT_BIG_SIZE)
    font_small = ImageFont.truetype(FONT_SMALL_PATH, FONT_SMALL_SIZE)
    font_badge = ImageFont.truetype(BADGE_FONT_PATH, BADGE_FONT_SIZE)
    font_medium = ImageFont.truetype(FONT_SMALL_PATH, FONT_SMALL_SIZE + 4)
    font_rank = ImageFont.truetype(FONT_RANK_PATH, FONT_RANK_SIZE)
    font_xp = ImageFont.truetype(FONT_XP_PATH, FONT_SMALL_SIZE - 2)
    font_level_label = ImageFont.truetype(FONT_LEVEL_LABEL_PATH, FONT_LEVEL_LABEL_SIZE)



    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((160, 160))
    mask = Image.new("L", (160, 160), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 160, 160), fill=255)
    avatar.putalpha(mask)
    card.paste(avatar, (40, 50), avatar)

    name_text = f"{username}#{discriminator}"
    name_pos = (240, 25)

    # Name Gradient Rendering
    bbox = font_big.getbbox(name_text)
    name_w = bbox[2] - bbox[0]
    name_h = bbox[3] - bbox[1]
    gradient_h = name_h + 20
    gradient = Image.new("RGBA", (int(name_w), gradient_h), color=0)
    grad_draw = ImageDraw.Draw(gradient)
    for i in range(int(name_w)):
        ratio = i / name_w
        r1, g1, b1 = tuple(int(style["name_gradient_start"].lstrip("#")[j:j+2], 16) for j in (0, 2, 4))
        r2, g2, b2 = tuple(int(style["name_gradient_end"].lstrip("#")[j:j+2], 16) for j in (0, 2, 4))
        r = int(r1 * (1 - ratio) + r2 * ratio)
        g = int(g1 * (1 - ratio) + g2 * ratio)
        b = int(b1 * (1 - ratio) + b2 * ratio)
        grad_draw.line([(i, 0), (i, gradient_h)], fill=(r, g, b))

    txt = Image.new("L", (int(name_w), gradient_h))
    txt_draw = ImageDraw.Draw(txt)
    txt_draw.text((0, 5), name_text, font=font_big, fill=255)
    gradient.putalpha(txt)
    card.paste(gradient, name_pos, gradient)

    # --- Server-Rank Badge ---
    position_text = f"#{position}"
    bbox = font_badge.getbbox(position_text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    badge_w = text_w + BADGE_PADDING_X * 2
    badge_h = text_h + BADGE_PADDING_Y * 2
    badge_x = name_pos[0] + name_w + 12
    badge_y = name_pos[1] + BADGE_OFFSET_Y

    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
        radius=badge_h // 2,
        fill=(0, 0, 0, 160),
        outline=(255, 255, 255, 80),
        width=1
    )
    draw.text(
        (badge_x + BADGE_PADDING_X + BADGE_TEXT_OFFSET_X, badge_y + BADGE_PADDING_Y + BADGE_TEXT_OFFSET_Y),
        position_text,
        font=font_badge,
        fill="#ffffff"
    )

    # --- Rank größer, Level darunter kleiner ---
    icon_path = f"assets/rank_icons/{rank}.png"
    rank_text = f"{rank}"
    rank_x, rank_y = 240, 87
    level_y = rank_y + 30 # level
    if os.path.exists(icon_path):
        icon = Image.open(icon_path).convert("RGBA").resize((30, 30))
        card.paste(icon, (rank_x, rank_y), icon)
        draw.text((rank_x + 35, rank_y - 2), rank_text, font=font_rank, fill=style["rank_color"]) # rank
        draw.text((rank_x + 3, level_y + 10), "L E V E L", font=font_level_label, fill="#ffffff") 
        draw.text((rank_x + 68, level_y + 8), str(level), font=font_badge, fill="#ffffff")  # level nr
    else:
        draw.text((rank_x, rank_y), f"Rank: {rank}", font=font_rank, fill=style["rank_color"])
        draw.text((rank_x, level_y), f"Level: {level}", font=font_small, fill="#ffffff")

    # --- XP Bar Background ---
    bar_x, bar_y = BAR_X, BAR_Y
    bar_w, bar_h = BAR_WIDTH, BAR_HEIGHT + 6
    bar_radius = bar_h // 2

    bar_bg_layer = Image.new("RGBA", (bar_w, bar_h), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bar_bg_layer)
    bg_draw.rounded_rectangle([(0, 0), (bar_w, bar_h)], radius=bar_radius, fill=(0, 0, 0, 100))
    card.paste(bar_bg_layer, (bar_x, bar_y), bar_bg_layer)

    fill_ratio = min(xp / needed, 1.0)
    fill_w = int(bar_w * fill_ratio)

    if fill_w > 0:
        fill_layer = Image.new("RGBA", (fill_w, bar_h), (0, 0, 0, 0))
        fill_draw = ImageDraw.Draw(fill_layer)

        for i in range(fill_w):
            blend = i / bar_w
            r = int(int(style["bar_start"][1:3], 16) * (1 - blend) + int(style["bar_end"][1:3], 16) * blend)
            g = int(int(style["bar_start"][3:5], 16) * (1 - blend) + int(style["bar_end"][3:5], 16) * blend)
            b = int(int(style["bar_start"][5:7], 16) * (1 - blend) + int(style["bar_end"][5:7], 16) * blend)
            fill_draw.line([(i, 0), (i, bar_h - 1)], fill=(r, g, b))

        mask = Image.new("L", (fill_w, bar_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (fill_w, bar_h)], radius=bar_radius, fill=255)
        fill_layer.putalpha(mask)
        card.paste(fill_layer, (bar_x, bar_y), fill_layer)

    # --- XP Text linksbündig über der Leiste ---
    xp_text = f"XP: {xp} / {needed}"
    xp_text_x = bar_x + 15
    xp_text_y = bar_y + 4

    draw.text((xp_text_x, xp_text_y), xp_text, font=font_xp, fill=style["xp_color"])

    return card
