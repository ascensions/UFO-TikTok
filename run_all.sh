#!/bin/bash
 
echo "Navigating to the ufo_project directory"
cd ~/Desktop/ufo_project
echo "Activating virtual environment"
source ufo_env/bin/activate

# Run your scripts
echo "Running main.py"
python3 main.py

echo "Running render.py"
python3 render.py

echo "Running uploadTk.py"
python3 uploadTk.py

# Deactivate the virtual environment
echo "Deactivating virtual environment"
deactivate
