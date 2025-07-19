#!/usr/bin/python3
import sys
import os

# Add your project directory to sys.path
# Update this path to match your actual hosting path
sys.path.insert(0, "/home/yourusername/public_html/tempmail/")

# Import your Flask application
from main import app as application

if __name__ == "__main__":
    application.run()