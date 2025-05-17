from image_generator import generate_image

generate_image(
    text="POO",
    font_index=5,
    bg_index=5,              # ← hier z. B. 4
    overlay_index=6,         # ← auch 4
    color="#EA02FF",
    colorful=False,
    output_path="generated/00.png"
)