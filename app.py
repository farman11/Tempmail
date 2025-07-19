import os
import logging
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# In-memory storage for emails and messages with persistence using session
import pickle
import json

# In-memory storage for emails and messages
temp_emails = {}
email_messages = {}

# File-based persistence for critical data
EMAILS_CACHE_FILE = 'temp_emails.json'
MESSAGES_CACHE_FILE = 'temp_messages.json'

def save_emails_to_cache():
    """Save emails to cache file"""
    try:
        cache_data = {}
        for email_id, email in temp_emails.items():
            if hasattr(email, '__dict__'):
                cache_data[email_id] = {
                    'id': email.id,
                    'email_address': email.email_address,
                    'session_id': email.session_id,
                    'is_active': email.is_active,
                    'mail_tm_id': getattr(email, 'mail_tm_id', None),
                    'mail_tm_password': getattr(email, 'mail_tm_password', None),
                    'created_at': email.created_at.isoformat() if hasattr(email, 'created_at') else None
                }
        
        with open(EMAILS_CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
    except Exception as e:
        logging.error(f"Error saving emails cache: {e}")

def load_emails_from_cache():
    """Load emails from cache file"""
    try:
        if os.path.exists(EMAILS_CACHE_FILE):
            with open(EMAILS_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            
            from models import TempEmail
            from datetime import datetime
            
            for email_id, data in cache_data.items():
                if email_id not in temp_emails:
                    # Recreate TempEmail object
                    email = TempEmail(session_id=data['session_id'], use_real_email=True)
                    email.id = data['id']
                    email.email_address = data['email_address']
                    email.is_active = data['is_active']
                    email.mail_tm_id = data['mail_tm_id']
                    email.mail_tm_password = data['mail_tm_password']
                    if data['created_at']:
                        email.created_at = datetime.fromisoformat(data['created_at'])
                    
                    temp_emails[email_id] = email
                    
    except Exception as e:
        logging.error(f"Error loading emails cache: {e}")

mail = Mail()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Mail configuration (keeping for compatibility)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'localhost')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@tempmail.local')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Initialize extensions
mail.init_app(app)
limiter.init_app(app)

# Load emails from cache on startup
load_emails_from_cache()

# Add template filters for email processing
from email_utils import process_email_content
from markupsafe import Markup

@app.template_filter('process_email')
def process_email_filter(html_content, text_content='', body_content=''):
    """Template filter to process email content properly"""
    try:
        processed = process_email_content(html_content, text_content, body_content)
        return Markup(processed)  # Mark as safe HTML
    except Exception as e:
        logging.error(f"Error processing email content: {e}")
        return Markup('<div class="text-gray-500 italic">Error processing email content</div>')

# Import routes
import routes
