from PIL import Image, ImageEnhance, ImageChops
import os
from imageUtils import color2hue, change_hue

FONT_CHOICES = {
    "Font 1": 1,
    "Font 2": 2,
    "Font 3": 3,
    "Font 4": 4,
    "Font 5 (NEW)": 5,
    "Font 6": 6,
    "Font 7": 7
}

BG_CHOICES = {
    "GTA V City": 1,
    "Dark Fluid Metal": 2,
    "Dark Synthwave": 3,
    "Neon Veins": 4,
    "Nebula Drops": 5,
    "Galaxy": 6,
    "Warp Grid": 7
}

OVERLAY_CHOICES = {
    "Black": 0,
    "Colorful Wave": 1,
    "Particles": 2,
    "Smoke": 3,
    "Lightning FX": 4,
    "Abstract Lines": 5,
    "Grain": 6
}

COLOR_CHOICES = {
    "Purple": "#8D0AF5",
    "Red": "#FF0000",
    "Blue": "#006EFF",
    "Green": "#00FFB3",
    "Yellow": "#FFFF00"
}

def generate_image(text: str, font_index: int, bg_index: int, overlay_index: int = None, color: str = "#8D0AF5", colorful: bool = False, output_path: str = "generated/generated_image.png"):
    width, height = 1024, 1024

    bg_path = os.path.join("assets", "Backgrounds", f"BackGround{bg_index}.png")
    background = Image.open(bg_path).resize((width, height)).convert("RGBA")

    shadow = Image.open("assets/Shadow.png").resize((width, height)).convert("RGBA")

    result_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    result_image.paste(background, (0, 0))
    result_image.paste(shadow, (0, 0), shadow)

    font_margins = {
        1: -10, 2: -20, 3: 10, 4: -10, 5: -20, 6: -10, 7: -15
    }
    margin = font_margins.get(font_index, 20)

    letter_images = []
    total_width = 0
    fixed_height = int(height * 0.25)

    for char in text.upper():
        if char == " ":
            letter_images.append((None, 40))
            total_width += 40 + margin
            continue

        letter_path = os.path.join("assets", "Letters", str(font_index), f"{char}.png")
        if not os.path.exists(letter_path):
            continue

        img = Image.open(letter_path).convert("RGBA")
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        scale = fixed_height / img.height
        new_width = int(img.width * scale)
        img = img.resize((new_width, fixed_height))

        letter_images.append((img, new_width))
        total_width += new_width + margin

    max_width = int(width * 0.85)
    min_width = int(width * 0.6)
    max_scaled_height = int(height * 0.7)
    if total_width > max_width or total_width < min_width:
        scale_factor = (max_width if total_width > max_width else min_width) / total_width
        scaled_letter_images = []
        total_width = 0
        for img, w in letter_images:
            if img:
                new_h = min(int(img.height * scale_factor), max_scaled_height)
                new_w = int(img.width * (new_h / img.height))
                img = img.resize((new_w, new_h))
                scaled_letter_images.append((img, new_w))
                total_width += new_w + margin
            else:
                scaled_letter_images.append((None, w))
                total_width += w + margin
        letter_images = scaled_letter_images
        fixed_height = letter_images[0][0].height if letter_images[0][0] else fixed_height

    x = (width - total_width + margin) // 2
    y = (height - fixed_height) // 2

    for img, w in letter_images:
        if img:
            result_image.paste(img, (x, y), img)
        x += w + margin

    hue = color2hue(color)
    result_image = change_hue(result_image, hue)

    if color in ["#000000", "#ffffff"]:
        result_image = result_image.convert("L").convert("RGBA")

    overlay_path = os.path.join("assets", "walpaperSub", f"{overlay_index}.png")
    if overlay_index is not None and os.path.exists(overlay_path):
        overlay = Image.open(overlay_path).convert("RGBA")
        overlay = overlay.resize(result_image.size).convert(result_image.mode)
        overlay = change_hue(overlay, hue)  # <- Overlay einfärben
        result_image = ImageChops.screen(result_image, overlay)

    if colorful:
        colorful_path = "assets/walpaperSub/COLORFUL.png"
        if os.path.exists(colorful_path):
            overlay_colorful = Image.open(colorful_path).convert("RGBA")
            overlay_colorful = overlay_colorful.resize(result_image.size).convert(result_image.mode)
            result_image = ImageChops.multiply(result_image, overlay_colorful)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result_image.save(output_path)
    return output_path
