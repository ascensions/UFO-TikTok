Project intended to automate pushing the latest NUFORC reports to TikTok and Youtube: https://www.tiktok.com/@ufo.sightings.daily

Currently in development - many tweaks and optimizations required as it is only really been setup on my own server lol - use at your own discretion.

Install:
  Download files
  Create and activate python virtual environment
  Install requirements and dependancies - requirements.txt need to be updated/streamlined; also install Chrome, Pillow, Selenium, ffmpeg, Undetected chrome? as system package.
  Setup for use case: 
    Put needed files where they need to go - tiktok cookies.json, youtube oauth client secrets credentials, songs.txt, font, chromedriver, adblock extension for youtube crosspost...
    Change any filenames/directories as needed, any references in scripts, actual file contents in the case of songs.txt...

Run:50,000
  python3 main.py - will use Selenium and fetch the latest by default 20 pages of 100 UFO Reports (configurable; need to add rate limit waiting past ~300 pages?...) from https://nuforc.org/subndx/?id=all and download the reports - videos, images, and report details, generating a folder 'sightings' and on script completion will generate a log file for the sighting IDs captured on run.
  python3 render.py - will use FFMPEG and GTTS to generate 9:16 videos in the 'renders' folder for all sightings from the last log file generated, adding TTS to each video.
  python3 uploadTk.py - will use Selenium to post all the videos in the 'renders' folder that correspond with the last log file generated, and then cross post to Youtube using helper script uploadYt.py, before waiting to upload again.
OR
  use the run_all.sh, which should run each script before moving to the next, and can be setup as a cron job.

Currently also working on a script to implement creating slideshows not too dissimilar from the render.py script, to generate media from the sighting images.

If you thought any of this was useful, please consider donating (BTC): 3Q483nJRB2aZ8MjubYzxDXqFr3yQ1MvmNe
