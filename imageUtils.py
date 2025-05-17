import os
from collections import namedtuple
import random

# ---------------------------- CHANGE IMAGE HUE ---------------------------- 

def change_hue(result_image, target_hue):
    # Open the image
    img = result_image

    # Convert the image to the HSV color space
    hsv_img = img.convert('HSV')

    # Get the pixel data
    pixels = hsv_img.load()

    # Change the hue of each pixel
    for i in range(hsv_img.size[0]):
        for j in range(hsv_img.size[1]):
            h, s, v = pixels[i, j]
            h = int((h + target_hue) % 256)
            pixels[i, j] = (h, s, v)

    # Convert the image back to RGB
    result_img = hsv_img.convert('RGB')

    # Save the result
    return result_img

# ---------------------------- SELECT COLOR HUE ---------------------------- 
Color = namedtuple('Color', ['name', 'value'])

COLORS = [
    Color('purple', (128, 0, 128)),
    Color('pink', (255, 182, 193)),
    Color('orange', (255, 165, 0)),
    Color('green', (0, 128, 0)),
    Color('aqua', (0, 255, 255)),
    Color('light blue', (173, 216, 230)),
    Color('blue', (0, 0, 255)),
    Color('red', (255, 0, 0)),
]

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def calculate_distance(color1, color2):
    return sum((a - b) ** 2 for a, b in zip(color1, color2)) ** 0.5

def categorize_color(hex_code):
    target_color = hex_to_rgb(hex_code)
    closest_color = min(COLORS, key=lambda x: calculate_distance(x.value, target_color))
    return closest_color.name

def color2hue(hex_code):
    target_color = hex_to_rgb(hex_code)
    closest_color = min(COLORS, key=lambda x: calculate_distance(x.value, target_color))
    
    base_hue_map = {
        "purple": 0,
        "pink": 35,
        "orange": 80,
        "green": 140,
        "aqua": 180,
        "light blue": 200,
        "blue": 215,
        "red": 315,
    }

    return base_hue_map.get(closest_color.name, 0)


