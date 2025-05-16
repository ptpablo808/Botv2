from PIL import Image
import os

def generate_image(text: str, font_index: int, bg_index: int, overlay_index: int = None, output_path: str = "generated/generated_image.png"):
    text = text.upper()
    font_folder = os.path.join("assets", "Letters", str(font_index))
    bg_path = os.path.join("assets", "Backgrounds", f"BackGround{bg_index}.png")
    overlay_path = os.path.join("assets", "walpaperSub", f"{overlay_index}.png") if overlay_index is not None else None

    # Hintergrund laden
    bg = Image.open(bg_path).convert("RGBA")
    width = height = min(bg.size)
    bg = bg.crop((0, 0, width, height))  # quadratisch machen

    # Buchstabenbilder laden
    letter_images = []
    for char in text:
        if char == " ":
            letter_images.append(None)
            continue
        letter_file = os.path.join(font_folder, f"{char}.png")
        if os.path.exists(letter_file):
            letter_img = Image.open(letter_file).convert("RGBA")
            letter_images.append(letter_img)
        else:
            print(f"[WARN] Missing char: {char}")
            letter_images.append(None)

    # Text zentriert zusammensetzen
    spacing = 10
    total_width = sum((img.width if img else 40) + spacing for img in letter_images)
    x = (width - total_width) // 2
    y = height // 2 - 50

    for img in letter_images:
        if img:
            bg.paste(img, (x, y), img)
            x += img.width + spacing
        else:
            x += 40

    # Overlay drüberlegen (falls angegeben)
    if overlay_path and os.path.exists(overlay_path):
        overlay = Image.open(overlay_path).convert("RGBA").resize(bg.size)
        bg.alpha_composite(overlay)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bg.save(output_path)
    return output_path
