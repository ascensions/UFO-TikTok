import os
import json
import glob
import textwrap
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from tqdm import tqdm

# Constants
BASE_DIR = "/home/chance/Desktop/ufo_project"
SIGHTINGS_FOLDER = os.path.join(BASE_DIR, "sightings")
RENDERS_FOLDER = os.path.join(BASE_DIR, "renders", "images")
FONT_PATH = os.path.join(BASE_DIR, 'VCR_OSD_MONO.ttf')
MAX_IMAGES_PER_FOLDER = 10
MAX_DESC_LENGTH = 4000  # Maximum characters in description file

if not os.path.exists(RENDERS_FOLDER):
    os.makedirs(RENDERS_FOLDER)

def wrap_text(text, max_width):
    return '\n'.join(textwrap.wrap(text, max_width))

def process_image(image_file, location, date_text, output_path):
    try:
        with Image.open(image_file) as img:
            img_width, img_height = img.size
            desired_aspect_ratio = 9 / 16  # Aspect ratio for 1080x1920
            img_aspect_ratio = img_width / img_height

            if img_aspect_ratio > desired_aspect_ratio:
                # Crop width
                new_width = int(img_height * desired_aspect_ratio)
                left = (img_width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img_height))
            else:
                # Crop height
                new_height = int(img_width / desired_aspect_ratio)
                top = (img_height - new_height) // 2
                img = img.crop((0, top, img_width, top + new_height))

            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)

            draw = ImageDraw.Draw(img)
            font_size = 72
            font = ImageFont.truetype(FONT_PATH, size=font_size)

            # Location text
            location_text_lines = wrap_text(location, 18).split('\n')
            text_y = 50  # Top padding
            for line in location_text_lines:
                text_width = draw.textlength(line, font=font)
                text_x = (1080 - text_width) // 2
                draw.text((text_x, text_y), line, font=font, fill="white")
                text_y += font_size + 10  # Space between lines

            # Date text
            date_text_lines = wrap_text(date_text, 18).split('\n')
            for line in date_text_lines:
                text_width = draw.textlength(line, font=font)
                text_x = (1080 - text_width) // 2
                draw.text((text_x, text_y), line, font=font, fill="white")
                text_y += font_size + 10  # Space between lines

            img.save(output_path)
    except Exception as e:
        print(f"An error occurred when trying to process the image: {e}")

def get_sighting_details(sighting_folder):
    details_path = os.path.join(sighting_folder, 'details.json')
    with open(details_path, 'r') as file:
        details = json.load(file)

    location = details.get('Location', '').upper()
    occurred = details.get('Occurred', '')
    comment = details.get('Comment', '')

    try:
        date_obj = datetime.strptime(occurred.split(' ')[0], "%Y-%m-%d")
        date_text = date_obj.strftime("%b %d, %Y").upper()
    except ValueError:
        date_text = ''

    return location, date_text, comment

def create_image_folders():
    sighting_folders = [os.path.join(SIGHTINGS_FOLDER, folder) 
                        for folder in os.listdir(SIGHTINGS_FOLDER) 
                        if os.path.isdir(os.path.join(SIGHTINGS_FOLDER, folder))]
    folder_index = 1
    image_count = 0
    total_images = sum(len(glob.glob(os.path.join(folder, 'images', '*.jpg'))) 
                       for folder in sighting_folders)
    descriptions = []

    # Initialize the first render folder
    render_folder = os.path.join(RENDERS_FOLDER, f"folder_{folder_index}")
    os.makedirs(render_folder, exist_ok=True)

    with tqdm(total=total_images, desc="Overall Progress") as pbar:
        for sighting_folder in sighting_folders:
            image_files = glob.glob(os.path.join(sighting_folder, 'images', '*.jpg'))
            location, date_text, comment = get_sighting_details(sighting_folder)

            for image_file in image_files:
                if image_count >= MAX_IMAGES_PER_FOLDER:
                    write_descriptions_to_file(render_folder, descriptions[:MAX_IMAGES_PER_FOLDER])
                    folder_index += 1
                    image_count = 0
                    descriptions = descriptions[MAX_IMAGES_PER_FOLDER:]

                    render_folder = os.path.join(RENDERS_FOLDER, f"folder_{folder_index}")
                    os.makedirs(render_folder, exist_ok=True)

                output_path = os.path.join(render_folder, f"image_{image_count + 1}.jpg")
                process_image(image_file, location, date_text, output_path)
                descriptions.append(comment)
                image_count += 1
                pbar.update(1)

        write_descriptions_to_file(render_folder, descriptions)

def write_descriptions_to_file(folder, descriptions):
    if descriptions:
        with open(os.path.join(folder, 'description.txt'), 'w') as file:
            for i, desc in enumerate(descriptions):
                file.write(f"Image {i + 1}: {desc}\n")

if __name__ == "__main__":
    create_image_folders()
