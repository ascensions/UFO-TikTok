import os
import json
import glob
import textwrap
from PIL import Image, ImageDraw, ImageFont

# Constants
BASE_DIR = "/home/chance/Desktop/ufo_project"
SIGHTINGS_FOLDER = os.path.join(BASE_DIR, "sightings")
RENDERS_FOLDER = os.path.join(BASE_DIR, "renders", "images")
FONT_PATH = os.path.join(BASE_DIR, 'VCR_OSD_MONO.ttf')
MAX_IMAGES_PER_FOLDER = 10

if not os.path.exists(RENDERS_FOLDER):
    os.makedirs(RENDERS_FOLDER)

def wrap_text(text, max_width):
    return '\n'.join(textwrap.wrap(text, max_width))

def process_image(image_path, location_text, output_path):
    with Image.open(image_path) as img:
        # Calculate dimensions for cropping to 1080x1920
        target_aspect_ratio = 1080 / 1920
        img_width, img_height = img.size
        img_aspect_ratio = img_width / img_height

        if img_aspect_ratio > target_aspect_ratio:
            # Image is wider than target aspect ratio
            new_width = int(img_height * target_aspect_ratio)
            left = (img_width - new_width) // 2
            top = 0
            right = left + new_width
            bottom = img_height
        else:
            # Image is taller than target aspect ratio
            new_height = int(img_width / target_aspect_ratio)
            left = 0
            top = (img_height - new_height) // 2
            right = img_width
            bottom = top + new_height

        img = img.crop((left, top, right, bottom))
        img = img.resize((1080, 1920), Image.Resampling.LANCZOS)

        # Draw location text
        draw = ImageDraw.Draw(img)
        font_size = 72
        font = ImageFont.truetype(FONT_PATH, font_size)
        wrapped_location_text = wrap_text(location_text, 18)
        
        # Calculate size for each line
        max_width = 0
        total_height = 0
        for line in wrapped_location_text.split('\n'):
            text_width = draw.textlength(line, font=font)
            text_height = font_size
            max_width = max(max_width, text_width)
            total_height += text_height

        # Determine start position
        start_y = 1920 - total_height - 240
        for i, line in enumerate(wrapped_location_text.split('\n')):
            text_width = draw.textlength(line, font=font)
            text_position = ((1080 - text_width) // 2, start_y)
            draw.text(text_position, line, font=font, fill="white")
            start_y += font_size

        img.save(output_path)

def get_sighting_details(sighting_folder):
    details_path = os.path.join(sighting_folder, 'details.json')
    with open(details_path, 'r') as file:
        details = json.load(file)
    location = details.get('Location', '').upper()
    return location

def create_image_folders():
    sighting_folders = [os.path.join(SIGHTINGS_FOLDER, folder) for folder in os.listdir(SIGHTINGS_FOLDER) if os.path.isdir(os.path.join(SIGHTINGS_FOLDER, folder))]
    folder_index = 1
    image_count = 0
    render_folder = os.path.join(RENDERS_FOLDER, f"folder_{folder_index}")
    os.makedirs(render_folder, exist_ok=True)
    descriptions = []

    for sighting_folder in sighting_folders:
        image_files = glob.glob(os.path.join(sighting_folder, 'images', '*.jpg'))
        location_text = get_sighting_details(sighting_folder)

        for image_file in image_files:
            if image_count >= MAX_IMAGES_PER_FOLDER:
                # Write descriptions for the previous folder
                with open(os.path.join(render_folder, 'description.txt'), 'w') as file:
                    file.write('\n'.join(descriptions))

                # Reset for the next folder
                folder_index += 1
                render_folder = os.path.join(RENDERS_FOLDER, f"folder_{folder_index}")
                os.makedirs(render_folder, exist_ok=True)
                descriptions = []
                image_count = 0

            output_path = os.path.join(render_folder, f"image_{image_count + 1}.jpg")
            process_image(image_file, location_text, output_path)
            descriptions.append(f"Image {image_count + 1}: {location_text}")
            image_count += 1

    # Handle last batch of images
    if descriptions:
        with open(os.path.join(render_folder, 'description.txt'), 'w') as file:
            file.write('\n'.join(descriptions))

if __name__ == "__main__":
    create_image_folders()
