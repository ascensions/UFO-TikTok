#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
import time
import os
import json
import requests
from bs4 import BeautifulSoup
import datetime
import traceback

# Constants
MAIN_PAGE = "https://nuforc.org/subndx/?id=all"
BASE_DIR = "/home/chance/Desktop/ufo_project"
SIGHTINGS_FOLDER = os.path.join(BASE_DIR, "sightings")

# Ensure the sightings directory exists
if not os.path.exists(SIGHTINGS_FOLDER):
    os.makedirs(SIGHTINGS_FOLDER)

# Function to initialize the driver
def init_driver():
    print("Initializing the web driver...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument("--no-sandbox");
    options.add_argument("--disable-dev-shm-usage");
    options.add_argument('--enable-logging')
    options.add_argument('--v=1')

    # Specify the correct path to your chromedriver executable
    chromedriver_path = os.path.join(os.getcwd(), "chromedriver-linux64", "chromedriver")
    service = Service(chromedriver_path)
    # Enable performance logging
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(25)
    driver.set_window_size(1920, 1080)

    return driver
def sort_table_by_occurred(driver):
    print("Loading main page...")
    driver.get(MAIN_PAGE)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "table_1")))
    js_script = """
    var table = document.getElementById("table_1");
    var header = table.querySelector("th.column-occurred");
    var event = document.createEvent("MouseEvents");
    event.initEvent("click", true, false);
    header.dispatchEvent(event);
    """
    driver.execute_script(js_script)
    driver.execute_script(js_script)

def get_sighting_urls(driver, max_pages=20):
    sighting_urls = []
    current_page = 1
    print(f"Preparing to load up to {max_pages} pages of sightings.")

    while current_page <= max_pages:
        print(f"Loading page {current_page}...")
        # Fetch the rows after the page has loaded
        rows = WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "#table_1 tbody tr"))
        )
        for i, row in enumerate(rows):
            try:
                link = row.find_element(By.PARTIAL_LINK_TEXT, "Open")
                href = link.get_attribute("href")
                sighting_urls.append(href)
            except NoSuchElementException:
                # This might be the header row, so skip it
                print("Header row or a row without 'Open' link encountered, skipping.")
                continue
            except (StaleElementReferenceException, TimeoutException) as e:
                print(f"Error in finding link: {e}")
                continue  # You can decide to break if too many errors occur

        # Move to the next page
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "table_1_next"))
            )
            if "disabled" in next_button.get_attribute("class"):
                break  # Stop if Next button is disabled (no more pages)
            driver.execute_script("arguments[0].click();", next_button)
            current_page += 1
        except TimeoutException:
            print(f"Timed out waiting for the Next button on page {current_page}")
            break

    print(f"Finished collecting URLs from {current_page - 1} pages.")
    return sighting_urls


def scrape_sighting_details(driver, url, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            print(f"Scraping details for sighting: {url} (Attempt {retries + 1})")
            driver.get(url)
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            report_details = {}
            primary_content = soup.find('div', id='primary')

            if primary_content:
                # Find all <b> tags - these contain the keys
                bold_tags = primary_content.find_all('b')

                for tag in bold_tags:
                    key = tag.get_text().strip(':')
                    # The next sibling of the <b> tag should be the value
                    value = tag.next_sibling

                    if value and isinstance(value, str):
                        report_details[key.strip()] = value.strip()

                # Handle the comment/description which is outside the <b> tags
                remaining_text = ''.join([str(x) for x in primary_content.contents if not x.name])
                comment_text = BeautifulSoup(remaining_text, 'html.parser').get_text().strip()
                # Remove '#content' tag and fix encoding issues
                comment_text = comment_text.replace('#content', '').replace("â€™", "'")
                report_details['Comment'] = comment_text.strip()

            print("Sighting details scraped successfully.")
            return report_details

        except TimeoutException:
            print(f"Timeout occurred while scraping {url}. Retrying...")
            retries += 1
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()  # Print stack trace
            break  # or retries += 1 to retry on all errors

    print(f"Failed to scrape sighting after {max_retries} attempts.")
    return None

# Function to parse network logs for media (used for both video and audio)
def parse_network_log_for_media(driver, media_type):
    media_url_1080p, media_url_720p, media_url_360p = None, None, None
    audio_url_196k, audio_url_96k = None, None
    logs = driver.get_log("performance")
    for entry in logs:
        log = json.loads(entry["message"])["message"]

        if log.get("method") == "Network.responseReceived" and "response" in log.get("params", {}):
            response_url = log["params"]["response"].get("url", "")

            # Check for different video resolutions
            if media_type == 'video':
                if 'video-1080p-video.mp4' in response_url:
                    media_url_1080p = response_url
                elif 'video-720p-video.mp4' in response_url:
                    media_url_720p = response_url
                elif 'video-360p-video.mp4' in response_url:
                    media_url_360p = response_url
            elif media_type == 'audio':
                if 'audio-196k-stereo.mp4' in response_url:
                    audio_url_196k = response_url
                elif 'audio-96k-stereo.mp4' in response_url:
                    audio_url_96k = response_url

    # Choose the best available resolution for video or the best audio quality
    if media_type == 'video':
        return media_url_1080p or media_url_720p or media_url_360p
    else:
        return audio_url_196k or audio_url_96k

def download_media_from_sighting(driver, sighting_details, sighting_folder):
    try:
        video_elements = find_video_elements(driver)
        video_filenames = []
        audio_filenames = []
        videos_folder = os.path.join(sighting_folder, "videos")
        os.makedirs(videos_folder, exist_ok=True)

        for element in video_elements:
            try:
                interact_with_video_element(driver, element)
                # Wait a bit for network activity to start
                time.sleep(2)

                video_url = parse_network_log_for_media(driver, 'video')
                if video_url:
                    video_filename = download_file(video_url, 'video', videos_folder)
                    if video_filename:  # Wait for download to complete
                        video_filenames.append(video_filename)
                        wait_for_download_complete(videos_folder, video_filename)

                # Handle audio files
                audio_url = parse_network_log_for_media(driver, 'audio')
                if audio_url:
                    audio_filename = download_file(audio_url, 'audio', videos_folder)
                    if audio_filename:  # Wait for download to complete
                        audio_filenames.append(audio_filename)
                        wait_for_download_complete(videos_folder, audio_filename)

            except TimeoutException:
                print("Timeout occurred while downloading media. Skipping this element.")
                continue

        sighting_details['Video_Files'] = video_filenames
        sighting_details['Audio_Files'] = audio_filenames

    except Exception as e:
        print(f"Error while downloading media: {e}")

def wait_for_download_complete(folder, filename):
    file_path = os.path.join(folder, filename)
    while not os.path.exists(file_path):
        time.sleep(1)
    print(f"Download complete for {filename}")

def find_video_elements(driver):
    video_elements = driver.find_elements(By.CSS_SELECTOR, "div[id^='museai-player-']")
    return video_elements

# Function to interact with video element
def interact_with_video_element(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        action = ActionChains(driver)
        action.move_to_element(element).click().perform()
        time.sleep(3)  # Wait for video to load and network log to capture the request        
    except Exception as e:
        print(f"Error interacting with video element: {e}")

def download_file(url, media_type, folder):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Determine the file extension based on the media type
            if media_type == 'video':
                extension = '.mp4'
            elif media_type == 'audio':
                extension = '.mp3'  # You can change this to '.mp4' if it's an mp4 audio
            elif media_type == 'image':
                extension = os.path.splitext(url)[1]  # Use the original image extension
            else:
                extension = '.unknown'  # Handle other media types as needed

            # Create a unique filename
            filename = f"{media_type}_{int(time.time())}{extension}"
            filepath = os.path.join(folder, filename)

            with open(filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)

            print(f"Successfully downloaded {media_type} to {filepath}")
            return filename
        else:
            print(f"Failed to download {media_type}: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error downloading {media_type} from {url}: {e}")
    return None

# Function to download images
def download_images(driver, sighting_folder):
    image_files = []
    try:
        images = WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.TAG_NAME, "img"))
        )
        for img in images:
            img_url = img.get_attribute("src")
            if img_url and "nuforclogo.gif" not in img_url:
                image_filename = os.path.basename(img_url)
                images_folder = os.path.join(sighting_folder, "images")
                os.makedirs(images_folder, exist_ok=True)
                if download_file(img_url, 'image', images_folder):
                    image_files.append(image_filename)

    except TimeoutException:
        print("Timeout occurred while downloading images.")

    return image_files
if __name__ == "__main__":
    print(f"Script started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    processed_sightings = []
    driver = init_driver()

    try:
        sort_table_by_occurred(driver)
        print("Table sorted by 'Occurred'.")
        sighting_urls = get_sighting_urls(driver, max_pages=20)
        print(f"Total unique sighting URLs to process: {len(sighting_urls)}")

        for url in sighting_urls:
            sighting_id = url.split('id=')[-1]
            sighting_folder = os.path.join(SIGHTINGS_FOLDER, sighting_id)

            # Check if the sighting has already been processed
            if os.path.exists(sighting_folder):
                print(f"Sighting {sighting_id} already processed. Skipping.")
                continue

            # Create folder for the sighting
            if not os.path.exists(sighting_folder):
                os.makedirs(sighting_folder)

            # Scrape sighting details
            sighting_details = scrape_sighting_details(driver, url)
            if not sighting_details:
                print(f"Failed to scrape details for {url}")
                continue

            # Download images
            image_files = download_images(driver, sighting_folder)
            sighting_details['Image_Files'] = image_files

            # Interact with and download media from the sighting
            download_media_from_sighting(driver, sighting_details, sighting_folder)

            # Save details to a JSON file
            details_file_path = os.path.join(sighting_folder, 'details.json')
            with open(details_file_path, 'w') as file:
                json.dump(sighting_details, file)

            # Update the list of processed sightings
            processed_sightings.append(sighting_id)

        print("Processing complete.")

        # Write the log file at the end of the script, outside the for loop
        log_file_path = os.path.join(BASE_DIR, f'log_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        with open(log_file_path, 'w') as log_file:
            for sighting_id in processed_sightings:
                log_file.write(f'{sighting_id}\n')
        print(f"Log file created: {log_file_path}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()
