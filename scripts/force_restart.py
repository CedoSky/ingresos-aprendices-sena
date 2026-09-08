#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple script to kill and restart Flask by importing the app module fresh
"""
import os
import sys
import subprocess
import time

print("Attempting to restart Flask server...")

# Try to kill existing Python processes (method 1: os.system with wmic)
try:
    exit_code = os.system('wmic process where "name=python.exe" delete /nointeractive>nul 2>&1')
    print(f"WMIC kill attempt returned code: {exit_code}")
except:
    print("WMIC approach failed")

time.sleep(1)

# Method 2: Try with subprocess
try:
    subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                  capture_output=True, timeout=2)
    print("taskkill succeeded")
except:
    pass

time.sleep(2)

# Start fresh Flask instance
print("Starting new Flask server...")
sys.argv = ['app.py']
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

# Clear any cached modules
if 'routes' in sys.modules:
    del sys.modules['routes']
if 'app' in sys.modules:
    del sys.modules['app']

# Now start the app
import app
if __name__ == '__main__':
    app_inst, socketio = app.create_app()
    socketio.run(app_inst, host='0.0.0.0', port=8000, debug=False)
