from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

def create_image(text, bg, font_key, effect):
    width, height = 1080, 1080

    # --- Hintergrund: entweder Farbe oder Bild ---
    bg_path = f"./assets/backgrounds/{bg}"
    if os.path.exists(bg_path):
        img = Image.open(bg_path).convert("RGB").resize((width, height))
    else:
        img = Image.new("RGB", (width, height), color=bg)

    draw = ImageDraw.Draw(img)

    # --- Schriftarten ---
    font_map = {
        "celsius_flower": "Celsius Flower.ttf",
        "high_speed": "HIGH SPEED.ttf"
    }

    font_file = font_map.get(font_key.lower(), "arial.ttf")
    font_path = f"./assets/fonts/{font_file}"
    try:
        font = ImageFont.truetype(font_path, 80)
    except:
        font = ImageFont.truetype("arial.ttf", 80)

    # --- Textposition berechnen ---
    text_width, text_height = draw.textsize(text, font=font)
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    position = (x, y)

    # --- Effekt: glow ---
    if effect == "glow":
        glow = Image.new("RGB", (width, height), img.getpixel((0, 0)))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.text(position, text, font=font, fill="white")
        glow = glow.filter(ImageFilter.GaussianBlur(10))
        img = Image.blend(glow, img, 0.5)

    # --- Finaler Text ---
    draw.text(position, text, font=font, fill="black")

    save_path = f"./generated/generated_{text[:5].replace(' ', '_')}.png"
    img.save(save_path)
    return save_path
