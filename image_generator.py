from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

def create_image(text, bg, font_key, effect):
    width, height = 1080, 1080

    try:
        # --- Hintergrund ---
        bg_path = os.path.join("assets", "backgrounds", bg)
        if os.path.exists(bg_path):
            img = Image.open(bg_path).convert("RGB").resize((width, height))
        else:
            try:
                img = Image.new("RGB", (width, height), color=bg)
            except ValueError:
                print(f"[create_image] Ungültiger Hintergrund: {bg}")
                img = Image.new("RGB", (width, height), color="white")

        draw = ImageDraw.Draw(img)

        # --- Schrift ---
        font_map = {
            "celsius_flower": "Celsius Flower.ttf",
            "high_speed": "HIGH SPEED.ttf"
        }
        font_file = font_map.get(font_key.lower(), "arial.ttf")
        font_path = os.path.join("assets", "fonts", font_file)

        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, 80)
        else:
            print(f"[create_image] Font nicht gefunden: {font_file}, fallback auf default.")
            font = ImageFont.load_default()

        # --- Textposition ---
        text_width, text_height = draw.textsize(text, font=font)
        position = ((width - text_width) // 2, (height - text_height) // 2)

        # --- Effekt ---
        if effect == "glow":
            glow = Image.new("RGB", (width, height), img.getpixel((0, 0)))
            glow_draw = ImageDraw.Draw(glow)
            glow_draw.text(position, text, font=font, fill="white")
            glow = glow.filter(ImageFilter.GaussianBlur(10))
            img = Image.blend(glow, img, 0.5)

        draw.text(position, text, font=font, fill="black")

        # --- Bild speichern ---
        os.makedirs("generated", exist_ok=True)
        safe_text = "".join(c if c.isalnum() else "_" for c in text[:10])
        save_path = os.path.join("generated", f"{safe_text}.png")
        img.save(save_path)
        return save_path

    except Exception as e:
        print(f"[create_image] Fehler: {e}")
        return None
