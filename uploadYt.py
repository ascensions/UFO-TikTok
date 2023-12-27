import os
import shutil
import glob
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tempfile
import google.auth
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def find_most_recent_file(directory, pattern):
    list_of_files = glob.glob(os.path.join(directory, pattern)) 
    if not list_of_files:  # No file found
        return None
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def setup_download_path():
    options = Options()
    # Determine the default download directory
    base_download_path = os.path.join(os.getcwd(), "renders")
    download_path = tempfile.mkdtemp(dir=base_download_path)

    # Set the download directory in the browser options
    options.add_experimental_option("prefs", {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True
    })

    return download_path, options
def generate_video_description(comment_text, tags):
    # Add your existing description generation logic here
    description = comment_text

    # Add hashtags to the end of the description
    hashtags = ' '.join([f'#{tag}' for tag in tags])
    description += "\n\n" + hashtags

    return description

def upload_video_to_youtube(video_path, comment_text, video_url):
    # Your YouTube API credentials file (client_secrets.json) path
    CLIENT_SECRETS_FILE = 'credentials/client_secrets.json'

    # The title and tags for your video
    VIDEO_TITLE = 'SKYWATCHER REPORT'
    VIDEO_TAGS = ['UFO', 'Skywatcher', 'Disclosure', 'Aliens', 'UAPS', 'shorts']

    # Set the privacy status to public
    PRIVACY_STATUS = 'public'

    # Generate the dynamic video description
    VIDEO_DESCRIPTION = generate_video_description(comment_text, VIDEO_TAGS)

    # Authenticate using the YouTube API credentials
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/youtube.upload'])
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, ['https://www.googleapis.com/auth/youtube.upload'])
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Build the YouTube Data API service
    youtube = build('youtube', 'v3', credentials=creds)

    # Create a video resource with the specified properties
    video = {
        'snippet': {
            'title': VIDEO_TITLE,
            'description': VIDEO_DESCRIPTION,
            'tags': VIDEO_TAGS
        },
        'status': {
            'privacyStatus': PRIVACY_STATUS
        }
    }

    try:
        # Upload the video to YouTube
        request = youtube.videos().insert(part='snippet,status', body=video, media_body=video_path)
        response = request.execute()

        # Get the video ID of the uploaded video
        video_id = response['id']

        print(f'Successfully uploaded video with ID: {video_id}')
        save_uploaded_url('last_uploaded_url.txt', video_url)

    except Exception as e:
        print(f'Error uploading video: {e}')

def wait_for_download_complete(download_path, file_pattern):
    """
    Wait for the download to complete in the given download directory.

    Args:
        download_path (str): The path to the download directory.
        file_pattern (str): The glob pattern to match the downloaded file.

    Returns:
        str: The path of the downloaded file.
    """
    max_wait_time = 60  # Maximum wait time in seconds
    wait_interval = 1  # Wait interval in seconds

    elapsed_time = 0
    while elapsed_time < max_wait_time:
        matching_files = glob.glob(os.path.join(download_path, file_pattern))
        if matching_files:
            return matching_files[0]  # Return the first matching file
        time.sleep(wait_interval)
        elapsed_time += wait_interval

    raise TimeoutError("Download did not complete within the allotted time.")

# Usage in your function
def download_video(video_url, download_service_url):
    print("Downloading video from ssstik.io...")
#    options.add_argument('--headless=new')
    options.add_argument("--no-sandbox");
    options.add_argument("--disable-dev-shm-usage");
    options.add_argument('--enable-logging')
    options.add_argument('--v=1')

    chromedriver_path = os.path.join(os.path.expanduser('~/Desktop/ufo_project'), 'chromedriver-linux64', 'chromedriver')
    service = Service(chromedriver_path)
    driver.set_page_load_timeout(25)
    driver.set_window_size(1920, 1080)
    extension_path = os.path.join(os.getcwd(), 'adblock.crx')
    download_path, options = setup_download_path()
    options.add_extension(extension_path)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        test_page = "https://www.google.com/"
        driver.get(test_page)
        original_window = driver.current_window_handle
        time.sleep(5)
        driver.switch_to.window(original_window)

        driver.get(download_service_url)
        input_field = driver.find_element(By.ID, "main_page_text")
        input_field.send_keys(video_url)

        download_button = driver.find_element(By.ID, "submit")
        download_button.click()

        # Wait for the download link to be available
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "download_link"))
        )

        try:
            comment_element = driver.find_element(By.CLASS_NAME, "maintext")  # The actual class for the comment
            comment_text = comment_element.text
            print(f"Comment found: {comment_text}")
        except NoSuchElementException:
            print("No comment found.")
            comment_text = ""

        try:
            download_link = driver.find_element(By.CLASS_NAME, "download_link")
            download_link.click()
        except Exception as e:
            # If normal click fails, try JavaScript click
            print("Normal click failed, trying JavaScript click:", e)
            driver.execute_script("arguments[0].click();", download_link)
        downloaded_video_path = wait_for_download_complete(download_path, 'ssstik.io_*.mp4')

    except Exception as e:
        print(f"Error during download: {e}")
        comment_text = None
    finally:
        driver.quit()

    return downloaded_video_path, comment_text

def click_off_to_the_side(driver):
    window_size = driver.get_window_size()
    width = window_size['width']
    
    # Move to the top right corner of the window
    ActionChains(driver).move_by_offset(width, 0).perform()
    
    # Move left 20 pixels and click
    ActionChains(driver).move_by_offset(-20, 10).click().perform()
    
def get_latest_video_url(tiktok_url):
    print("Initializing the web driver...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument("--no-sandbox");
    options.add_argument("--disable-dev-shm-usage");
    options.add_argument('--enable-logging')
    options.add_argument('--v=1')

    chromedriver_path = os.path.join(os.path.expanduser('~/Desktop/ufo_project'), 'chromedriver-linux64', 'chromedriver')
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(25)
    driver.set_window_size(1920, 1080)
    driver.get('https://www.tiktok.com/')
    time.sleep(3)
    WebDriverWait(driver, 10).until(lambda d: 'tiktok.com' in d.current_url)
    print("Opened TikTok.")
    driver.get(tiktok_url)
    time.sleep(3)
    WebDriverWait(driver, 10).until(lambda d: 'tiktok.com' in d.current_url)
    print("Navigated to UFO Page.")
    time.sleep(3)    
    print("Scanning for latest video link...")
    links = driver.find_elements(By.TAG_NAME, "a")

    for link in links:
        href = link.get_attribute('href')
        if href and re.match(r'https://www\.tiktok\.com/@ufo\.sightings\.daily/video/\d+', href):
            driver.quit()
            return href
    print("No matching video URL found.")
    driver.quit()
    return None

def get_last_uploaded_url(file_path):
    """Read the last uploaded URL from a file."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return file.read().strip()
    return None

def save_uploaded_url(file_path, url):
    """Save the uploaded URL to a file."""
    with open(file_path, 'w') as file:
        file.write(url)

def clean_up_temp_dir(temp_dir):
    shutil.rmtree(temp_dir)
    print(f"Cleaned up temporary directory: {temp_dir}")

def youtube_main_upload():
    print("Crossposting to Youtube and Reels From Tiktok...")
    tiktok_url = "https://www.tiktok.com/@ufo.sightings.daily"
    download_service_url = "https://ssstik.io/en"
    print(f"Accessing TikTok URL: {tiktok_url}")

    # Get the latest video URL from TikTok
    video_url = get_latest_video_url(tiktok_url)
    print(f"Latest Video URL: {video_url}")

    last_uploaded_url = get_last_uploaded_url('last_uploaded_url.txt')
    if video_url == last_uploaded_url:
        print("This video is already uploaded to YouTube. Skipping upload.")
    else:
        # Download the video from ssstik.io and get the comment text
        downloaded_video_path, comment_text = download_video(video_url, download_service_url)
        if downloaded_video_path:
            print("Uploading to Youtube")
            upload_video_to_youtube(downloaded_video_path, comment_text, video_url)

            # Clean up temporary directory on shutdown
            temp_dir = os.path.dirname(downloaded_video_path)
            clean_up_temp_dir(temp_dir)
        else:
            print("Video download failed.")

if __name__ == "__main__":
    youtube_main_upload()
