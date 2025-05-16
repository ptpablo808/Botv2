from image_generator import generate_image

generate_image(
    text="DISCORD",
    font_index=1,
    bg_index=2,
    overlay_index=3,
    output_path="generated/test_image.png"
)
print("✅ Testbild generiert!")
