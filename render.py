import re
from gtts import gTTS
import os
import subprocess
import json
import glob
from datetime import datetime
import random
import textwrap

# Constants
BASE_DIR = "/home/chance/Desktop/ufo_project"
SIGHTINGS_FOLDER = os.path.join(BASE_DIR, "sightings")
RENDERS_FOLDER = os.path.join(BASE_DIR, "renders")
if not os.path.exists(RENDERS_FOLDER):
    os.makedirs(RENDERS_FOLDER)

FONT_PATH = os.path.join(BASE_DIR, 'VCR_OSD_MONO.ttf')
LUT_FILE = os.path.join(BASE_DIR, "THRILL.cube")

def wrap_text(text, max_width):
    return '\n'.join(textwrap.wrap(text, max_width))

def execute_ffmpeg_command(video_path, audio_to_use_path, tts_audio_path, date_text, location_text, output_path, video_duration, audio_duration):

    # Setup trim filter if needed
    font_size = 72
    crop_width = 1080
    crop_height = 1920

    wrapped_location_text = wrap_text(location_text, 18)
    max_duration = max(video_duration, audio_duration)
    trim_filter = f"[0:v]trim=duration={max_duration},setpts=PTS-STARTPTS[v]"
    video_info = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', video_path], stdout=subprocess.PIPE, text=True).stdout
    video_width, video_height = map(int, video_info.split(','))

    # Calculate crop dimensions
    desired_aspect_ratio = 1080 / 1920
    actual_aspect_ratio = video_width / video_height
    if actual_aspect_ratio > desired_aspect_ratio:
        # Crop width
        crop_width = int(video_height * desired_aspect_ratio)
        crop_height = video_height
        x_offset = int((video_width - crop_width) / 2)
        y_offset = 0
    else:
        # Crop height
        crop_width = video_width
        crop_height = int(video_width / desired_aspect_ratio)
        x_offset = 0
        y_offset = int((video_height - crop_height) / 2)

    # Construct the ffmpeg command
    command = [
        'ffmpeg', '-y', '-i', video_path, '-i', audio_to_use_path, '-i', tts_audio_path,
        '-filter_complex',
        f"{trim_filter}; [v]crop={crop_width}:{crop_height}:(iw-{crop_width})/2:(ih-{crop_height})/2,scale=1080:1920,drawtext=fontfile='{FONT_PATH}':text='{date_text}':x=(w-text_w)/2:y=(h-text_h-180):fontsize={font_size}:fontcolor=white,drawtext=fontfile='{FONT_PATH}':text='{wrapped_location_text}':x=(w-text_w)/2:y=(h-text_h-240):fontsize={font_size}:fontcolor=white[vout]; [1:a][2:a]amix=inputs=2:duration=longest[a]",
        '-map', '[vout]', '-map', '[a]', '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-c:a', 'aac', output_path
    ]


    # Execute the command
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("Video processed.")
    if process.returncode != 0:
        print("FFmpeg command failed with error:")
        print(process.stderr)

def get_sighting_details(sighting_folder):
    details_path = os.path.join(sighting_folder, 'details.json')
    with open(details_path, 'r') as file:
        details = json.load(file)
    occurred = details.get('Occurred', '')
    location = details.get('Location', '').upper()
    try:
        date_obj = datetime.strptime(occurred.split(' ')[0], "%Y-%m-%d")
        return date_obj.strftime("%b %d, %Y").upper(), location
    except ValueError:
        return '', location

def get_latest_log_file(base_dir):
    log_files = glob.glob(os.path.join(base_dir, 'log_*.txt'))
    latest_log_file = max(log_files, key=os.path.getmtime, default=None)
    return latest_log_file

def get_all_sighting_ids_from_log(base_dir):
    latest_log_file = get_latest_log_file(base_dir)
    if not latest_log_file:
        print("No log file found.")
        return []

    with open(latest_log_file, 'r') as file:
        sighting_ids = [line.strip() for line in file]
    return sighting_ids

def get_all_sighting_ids():
    return [os.path.basename(folder) for folder in os.listdir(SIGHTINGS_FOLDER) if os.path.isdir(os.path.join(SIGHTINGS_FOLDER, folder))]

def generate_tts(description, output_path):
    """Generates an MP3 file from the given description using Google TTS."""
    print("Generating TTS from description...")
    tts = gTTS(description, lang='en')
    tts.save(output_path)
    print(f"TTS audio saved to {output_path}")

def get_media_duration(file_path):
    try:
        result = subprocess.run(['ffmpeg', '-i', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        duration_match = re.search(r"Duration: (\d+:\d+:\d+\.\d+)", result.stderr)
        return duration_match.group(1) if duration_match else None
    except Exception as e:
        print(f"Error getting duration for {file_path}: {e}")
        return None

def convert_duration_to_seconds(duration):
    h, m, s = map(float, duration.split(':')) if duration else (0, 0, 0)
    return h * 3600 + m * 60 + s

def find_closest_audio_file(video_file, audio_files):
    video_duration = convert_duration_to_seconds(get_media_duration(video_file))
    return min(audio_files, key=lambda af: abs(video_duration - convert_duration_to_seconds(get_media_duration(af))), default=None)

def process_sighting(sighting_id):
    sighting_folder = os.path.join(SIGHTINGS_FOLDER, sighting_id)
    video_folder = os.path.join(sighting_folder, 'videos')
    temp_folder = os.path.join(RENDERS_FOLDER, 'temp', sighting_id)

    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    # Get all video files
    video_files = glob.glob(os.path.join(video_folder, '*.mp4'))
    if not video_files:
        return False  # Indicates no processing was done

    # Get all audio files (if any)
    audio_files = glob.glob(os.path.join(video_folder, '*.mp3'))

    # Get sighting details
    sighting_details_file = os.path.join(sighting_folder, 'details.json')
    with open(sighting_details_file, 'r') as file:
        sighting_details = json.load(file)

    date_text, location_text = get_sighting_details(sighting_folder)
    description_text = sighting_details.get('Comment', 'No description available.').split('\n', 1)[-1]
    actual_comment = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} Local.*?00:00:00", '', description_text).strip()

    # Generate TTS audio
    tts_audio_path = os.path.join(temp_folder, "description_audio.mp3")
    generate_tts(actual_comment, tts_audio_path)

    # Inside process_sighting function
    for video_file in video_files:
        output_file = os.path.join(RENDERS_FOLDER, f"{sighting_id}_{os.path.basename(video_file)}")

        # Find the closest matching audio file or use TTS if no match is found
        matched_audio_file = find_closest_audio_file(video_file, audio_files) if audio_files else tts_audio_path
        audio_to_use = matched_audio_file if matched_audio_file else tts_audio_path

        video_duration = convert_duration_to_seconds(get_media_duration(video_file))
        audio_duration = convert_duration_to_seconds(get_media_duration(audio_to_use))
        execute_ffmpeg_command(video_file, audio_to_use, tts_audio_path, date_text, location_text, output_file, video_duration, audio_duration)

if __name__ == "__main__":
    BASE_DIR = "/home/chance/Desktop/ufo_project"
    empty_folders_count = 0

    sighting_ids = get_all_sighting_ids_from_log(BASE_DIR)
    
    # Print the total number of reports to process
    print(f"Total reports to process rendering: {len(sighting_ids)}")

    for sighting_id in sighting_ids:
        if not process_sighting(sighting_id):
            empty_folders_count += 1

    if empty_folders_count > 0:
        print(f"Skipped {empty_folders_count} empty folders.")
