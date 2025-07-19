from datetime import datetime, timedelta
import uuid

class TempEmail:
    def __init__(self, session_id, hours=24, use_real_email=True):
        self.id = str(uuid.uuid4())
        self.session_id = session_id
        self.created_at = datetime.utcnow()
        self.is_active = True
        self.mail_tm_password = None
        self.mail_tm_id = None
        
        if not use_real_email:
            # Fallback to local domain
            domain = "tempmail.replit.app"
            self.email_address = f"{uuid.uuid4().hex[:12]}@{domain}"
            self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        # If use_real_email=True, email_address and other fields will be set manually
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def deactivate(self):
        self.is_active = False

class EmailMessage:
    def __init__(self, temp_email_id, sender_email, sender_name=None, subject=None, body=None, 
                 text_content=None, html_content=None, mail_tm_id=None):
        self.id = str(uuid.uuid4())
        self.temp_email_id = temp_email_id
        self.sender = sender_email  # Keeping for backward compatibility
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.subject = subject
        self.body = body
        self.text_content = text_content
        self.html_content = html_content
        self.received_at = datetime.utcnow()
        self.is_spam = False
        self.is_read = False
        self.mail_tm_id = mail_tm_id