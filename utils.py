import re
import random
import string
from typing import List
import os

# Simple spam detection keywords
SPAM_KEYWORDS = [
    'viagra', 'casino', 'lottery', 'winner', 'congratulations',
    'click here', 'free money', 'make money fast', 'work from home',
    'weight loss', 'bitcoin', 'crypto', 'investment opportunity',
    'nigerian prince', 'inheritance', 'tax refund', 'irs'
]

# Suspicious sender patterns
SPAM_SENDER_PATTERNS = [
    r'noreply@.*\.tk$',
    r'.*@.*\.ga$',
    r'.*@.*\.ml$',
    r'.*\.temp@.*',
    r'.*\d{8,}@.*'
]

def is_spam_email(sender: str, subject: str, body: str) -> bool:
    """Simple spam detection based on keywords and patterns"""
    
    # Check sender patterns
    for pattern in SPAM_SENDER_PATTERNS:
        if re.search(pattern, sender.lower()):
            return True
    
    # Check content for spam keywords
    content = f"{subject} {body}".lower()
    spam_count = 0
    
    for keyword in SPAM_KEYWORDS:
        if keyword in content:
            spam_count += 1
    
    # If more than 2 spam keywords found, mark as spam
    return spam_count >= 2

def generate_random_string(length: int = 8) -> str:
    """Generate a random string for email addresses"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))



def time_until_expiry(expires_at) -> str:
    """Return human-readable time until expiry"""
    from datetime import datetime
    
    now = datetime.utcnow()
    if expires_at <= now:
        return "Expired"
    
    diff = expires_at - now
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return "Less than a minute"

def clean_expired_data():
    """Clean up expired emails (would be run periodically)"""
    from datetime import datetime
    from app import db
    from models import TempEmail
    
    # Deactivate expired emails
    expired_emails = TempEmail.query.filter(
        TempEmail.expires_at <= datetime.utcnow(),
        TempEmail.is_active == True
    ).all()
    
    for email in expired_emails:
        email.deactivate()
    
    db.session.commit()
    return len(expired_emails)
