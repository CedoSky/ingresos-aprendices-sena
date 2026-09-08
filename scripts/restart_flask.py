#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import os
import sys
import signal
import time
import platform

# Move to project root first
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # Go up from scripts/ to root
os.chdir(project_root)

# Kill Flask server cleanly
print("Restarting Flask server...")
if platform.system() == "Windows":
    # Use wmic which bypasses the policy restriction
    os.system('wmic process where "name=python.exe" delete /nointeractive 2>nul || echo "No Python process found"')
else:
    os.system('pkill -f "python.*app.py" || echo "No Flask process found"')

time.sleep(2)

# Clear Python cache
cache_dir = os.path.join('backend', '__pycache__')
if os.path.exists(cache_dir):
    try:
        import shutil
        shutil.rmtree(cache_dir)
        print("Cleared cache")
    except:
        pass

# Start server again
print("Starting Flask server...")
os.chdir('backend')
os.execvp('python', ['python', 'app.py'])
