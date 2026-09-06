#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import signal
import time

# Move to project root first
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # Go up from scripts/ to root
os.chdir(project_root)

# Find and kill existing Python process running app.py
print("Finding and killing old Flask server...")
try:
    # Use Python's own process module
    import psutil
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower() and proc.info['cmdline']:
                if any('app.py' in str(arg) for arg in proc.info['cmdline']):
                    print(f"Killing PID {proc.info['pid']}")
                    proc.kill()
        except:
            pass
except ImportError:
    print("psutil not available, trying alternate method")
    pass

# Wait for port to be free
print("Waiting for port 8000 to be free...")
time.sleep(3)

# Start new server
print("Starting new Flask server...")
os.chdir('backend')
sys.argv = ['app.py']
exec(open('app.py').read())
