from datetime import datetime, timedelta
import os
import re
import glob
import json
import random
import time
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from uploadYt import youtube_main_upload

def init_driver():
    print("Initializing the web driver...")
    options = uc.ChromeOptions()
    options.add_argument("--log-level=3")
    options.add_argument('disable-infobars')
    options.add_argument('--headless=new')
    options.add_argument("--no-sandbox");
    options.add_argument("--disable-dev-shm-usage");
    options.add_argument('--enable-logging')
    options.add_argument('--v=1')

    # Path to your chromedriver executable
    chromedriver_path = os.path.join(os.path.expanduser('~/Desktop/ufo_project'), 'chromedriver-linux64', 'chromedriver')
    service = Service(chromedriver_path)
    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(25)
    driver.set_window_size(1920, 1080)
    return driver

def find_latest_log(log_directory):
    log_files = glob.glob(os.path.join(log_directory, 'log_*.txt'))
    latest_log = max(log_files, key=os.path.getctime)
    return latest_log

def read_log_file(log_file_path):
    with open(log_file_path, 'r') as file:
        return [line.strip() for line in file.readlines()]

def find_matching_videos(render_directory, sighting_ids):
    video_files = glob.glob(os.path.join(render_directory, '*_video_*.mp4'))
    matching_videos = [video for video in video_files if any(sighting_id in video for sighting_id in sighting_ids)]
    return matching_videos

def upload_to_tiktok(video_path, title, caption, cookies, character_limit=2150, max_retries=3):
    driver = init_driver()
    upload_successful = False  # Set to False by default
    try:
        driver.get('https://www.tiktok.com/')
        print("Opened TikTok.")
        time.sleep(3)
        WebDriverWait(driver, 10).until(lambda d: 'tiktok.com' in d.current_url)
        for cookie in cookies:
            driver.add_cookie({'name': cookie['name'], 'value': cookie['value'], 'domain': '.tiktok.com'})
        print("Cookies added.")
        time.sleep(0.5)
        for attempt in range(max_retries):
            driver.get('https://www.tiktok.com/creator-center/upload')
            print(f"Attempt {attempt + 1} of {max_retries}: Navigated to the creator center upload page.")

            # Move the mouse to the specified hover element
            hover_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-tt="Header_index_HeaderContainer"]')))
            ActionChains(driver).move_to_element(hover_element).perform()
            print("Moved mouse over the specified element.")

            # Wait for the iframe to be available and switch to it
            iframe = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame(iframe)
            print("Iframe found and switched to.")

            file_uploader = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]')))
            file_uploader.send_keys(video_path)
            print("Video file path sent.")

            try:
                # Wait for the upload to show some progress
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.uploading-stage'))
                )
                print("Upload progress indicator appeared.")
                break  # Break the loop if upload indicator appears
            except TimeoutException:
                print("Upload progress indicator not found. Retrying...")
                continue  # Continue the loop to retry

            if attempt == max_retries - 1:
                print("Max retries reached. Skipping to next file.")
                return False  # Return from the function if max retries are reached

        # Wait for the upload to complete, indicated by the disappearance of the progress indicator or the presence of the post-upload message
        upload_complete = EC.invisibility_of_element_located((By.CSS_SELECTOR, '.uploading-stage'))
        post_upload_message = EC.presence_of_element_located((By.CSS_SELECTOR, '.modal-btn.emphasis'))
        WebDriverWait(driver, 300).until(
            lambda driver: upload_complete(driver) or post_upload_message(driver)
        )
        print("Upload likely complete.")
        try:
            print("Searching for additional popups.")
            # Wait for the 'Not now' button to be clickable
            not_now_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.css-1ypeuck'))
            )
            not_now_button.click()
            print("Clicked 'Not now' on the split video pop-up.")
        except TimeoutException:
            print("No split video pop-up found.")
        except Exception as e:
            print(f"An error occurred when trying to close the split video pop-up: {e}")

        print("Adding sound to video.")

        try:
            add_sound_to_video(driver)
        except Exception as e:
            print(f"An error occurred when trying add sound: {e}")

        time.sleep(5)
        caption_field = WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.public-DraftStyleDefault-block.public-DraftStyleDefault-ltr')))
        ActionChains(driver).move_to_element(caption_field).click().key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()

        print('Writing title & tags...')
        tags = ["UFO", "UAP", "Sighting", "Aliens", "fyp", "Disclosure", "Storytime"]
        tags_str = " ".join(["#" + tag for tag in tags])  # Construct a string of tags

        # Calculate available length for the comment
        available_length = character_limit - len(title) - len(tags_str) - 3  # -3 for spaces and colon

        # Use only the relevant part of the caption and remove hashtags and @ symbols
        modified_caption = caption.split('\n', 1)[-1]  # Split at the first newline and take the second part
        modified_caption = re.sub(r"[#@]", "", modified_caption)  # Remove hashtags and @ symbols
        # Adjust the caption text to fit within the character limit
        if len(modified_caption) > available_length:
            modified_caption = modified_caption[:available_length] + "..."  # Add ellipsis to indicate truncation

        # Formulate the full caption with only the title and the modified caption
        full_caption = f"{title}: \"{modified_caption}\""
        print("Caption Text: ", full_caption)  # Debug print statement

        # Send the full caption
        ActionChains(driver).move_to_element(caption_field).click().perform()
        if caption_field.is_enabled():  # Check if the field is interactable
            ActionChains(driver).send_keys(full_caption).perform()
            time.sleep(1)  # Wait after entering the caption
        # Send the hashtags separately
        tags = ["UFO", "UAP", "Sighting", "Aliens", "fyp", "Disclosure", "Storytime"]
        for tag in tags:
            try:
                ActionChains(driver).send_keys(" #" + tag).perform()  # Add a space before the hashtag
                time.sleep(0.5)  # Brief pause between hashtags
                WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.mentionSuggestions')))
                ActionChains(driver).send_keys(Keys.RETURN).perform()  # Confirm the hashtag
                time.sleep(0.5)  # Brief pause between hashtags
            except:
                    pass
        time.sleep(3)
        print("Title and tags entered.")
        time.sleep(1)
        print("Moving to bottom of page.")
        try:
            # Wait for the element to be clickable
            post_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.btn-post>button:not([disabled])')))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", post_button)
            time.sleep(1)
            actions = ActionChains(driver)
            actions.move_to_element(WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.btn-post>button:not([disabled])'))))
            print("Moved to post button")
            time.sleep(1)
            post_button.click()
            print("Clicked post button.")
            time.sleep(1)
            print
        except TimeoutException:
            print("Post button not clickable or not found within the timeout period.")
        except Exception as e:
            print(f"An error occurred: {e}")
        try:
            time.sleep(3)
            WebDriverWait(driver, 300).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Your videos are being uploaded to TikTok!')]"))
            )
            upload_successful = True
            print("Final upload completion message visible.")
            time.sleep(0.2)
        except TimeoutException:
            print("Upload completion message not found within the timeout period.")
            upload_successful = False  # Set to True if upload is successful

        try:
            if upload_successful and os.path.exists(video_path):
                print(f"Deleting the uploaded video file: {video_path}")
                os.remove(video_path)
                print("Video file deleted successfully.")
            else:
                print("Video file not found or upload was not successful, not deleting file.")
        except Exception as e:
            print(f"An error occurred: {e}")

    except Exception as e:
        print(f"An error occurred during the upload process:", str(e))
        return False

    finally:
        driver.quit()
        print("Driver closed.")
        return upload_successful  # Return the status of the upload

def add_sound_to_video(driver):
    # Click the 'Edit Video' button
    try:
        edit_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Edit video')]")))
        edit_button.click()
        print("Clicked 'Edit Video' button.")
    except TimeoutException:
        print("Edit Video button not found.")
        return
    time.sleep(2)  # Wait for the edit modal to open
    # Select a random song from songs.txt
    with open(os.path.join(os.path.expanduser('~/Desktop/ufo_project'), 'songs.txt'), 'r') as file:
        songs = file.readlines()
    song = random.choice(songs).strip()
    # Search for the song
    try:
        search_box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Search"]')))
        search_box.send_keys(song)
        search_box.send_keys(Keys.RETURN)
        print(f"Searched for song: {song}")
    except TimeoutException:
        print("Search box not found.")
        return
    time.sleep(2)  # Wait for search results
    # Hover over the song card to make the 'Use' button visible
    try:
        song_card = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.music-card-info')))
        ActionChains(driver).move_to_element(song_card).perform()
        print("Hovered over the song card.")
    except TimeoutException:
        print("Song card not found.")
        return
    # Click the 'Use' button
    try:
        use_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[div/div[contains(text(), 'Use')]]")))
        use_button.click()
        print("Clicked 'Use' button for the song.")
    except TimeoutException:
        print("Use button not found.")
        return
    time.sleep(2)  # Wait for the song to be added
    # Click the sound operation element to open sound scales
    try:
        sound_operation_element = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.audioOperation img.jsx-2730543169")))
        sound_operation_element.click()
        print("Clicked on sound operation element.")
    except Exception as e:
        print(f"Error clicking sound operation element: {e}")
        return
    time.sleep(2)  # Wait for sound scales to become visible
    scale_inputs = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'input.jsx-2730543169.scaleInput[type="range"]')))
    try:
        first_slider = scale_inputs[0]
        ActionChains(driver).click(first_slider).perform()  # Focus on the slider
        for _ in range(50):  # Increase from 50% to 90%
            ActionChains(driver).send_keys(Keys.RIGHT).perform()
        print("First sound scale set to 100%.")
    except Exception as e:
        print(f"Error adjusting first sound scale: {e}")
        return
    try:
        second_slider = scale_inputs[1]
        ActionChains(driver).click(second_slider).perform()  # Focus on the slider
        for _ in range(45):  # Decrease from 50% to 15%
            ActionChains(driver).send_keys(Keys.LEFT).perform()
        print("Second sound scale set to 5%.")
    except Exception as e:
        print(f"Error adjusting second sound scale: {e}")
        return
    print("Sound adjustments and saving completed.")

    # Click the 'Save edit' button
    try:
        save_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Save edit')]")))
        save_button.click()
        print("Clicked 'Save edit' button.")
    except TimeoutException:
        print("Save edit button not found.")
        return

    time.sleep(2)  # Wait for the edit to be saved
    print("Sound added successfully.")

def main():
    ufo_project_path = os.path.expanduser('~/Desktop/ufo_project')
    render_directory = os.path.join(ufo_project_path, 'renders')
    sightings_directory = os.path.join(ufo_project_path, 'sightings')
    log_directory = ufo_project_path

    latest_log = find_latest_log(log_directory)
    sighting_ids = read_log_file(latest_log)
    matching_videos = find_matching_videos(render_directory, sighting_ids)

    print(f"Total reports (videos) to process uploading: {len(matching_videos)}")

    with open(os.path.join(ufo_project_path, 'cookies.json'), 'r') as file:
        tiktok_cookies = json.load(file)

    for video in matching_videos:
        video_name = os.path.basename(video)
        # Extract the sighting ID from the beginning of the video file name
        sighting_id = video_name.split('_')[0]

        sighting_folder = os.path.join(sightings_directory, sighting_id)
        sighting_details_file = os.path.join(sighting_folder, 'details.json')

        if os.path.exists(sighting_details_file):
            with open(sighting_details_file, 'r') as file:
                sighting_details = json.load(file)

            # Extract the caption text
            caption_text = sighting_details.get('Comment', 'No description available.')

            current_time = datetime.now()
            print(f"Uploading {video_name} at {current_time.strftime('%Y-%m-%d %H:%M:%S')}...")
            upload_success = upload_to_tiktok(video, "SKYWATCHER REPORT", caption_text, tiktok_cookies)
            next_upload_time = current_time + timedelta(hours=3)
            if upload_success:
                try:
                    youtube_main_upload()
                except Exception as e:
                    print(f"An error occurred when trying to crosspost: {e}")
            else:
                print("Skipping Youtube Upload.")

            print(f"Total reports (videos) to process uploading: {len(matching_videos)}")
            print(f"Waiting for four hours until next upload, scheduled at {next_upload_time.strftime('%Y-%m-%d %H:%M:%S')}")

            time.sleep(14400)

        else:
            print(f"details.json not found for sighting {sighting_id}")

if __name__ == "__main__":
    main()
