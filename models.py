from datetime import datetime, timedelta
from app import db
import uuid

class TempEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_address = db.Column(db.String(255), unique=True, nullable=False)
    session_id = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Mail.tm integration fields
    mail_tm_password = db.Column(db.String(255), nullable=True)
    mail_tm_id = db.Column(db.String(255), nullable=True)
    
    def __init__(self, session_id, hours=24, use_real_email=True):
        self.session_id = session_id
        if not use_real_email:
            # Fallback to local domain
            domain = "tempmail.replit.app"
            self.email_address = f"{uuid.uuid4().hex[:12]}@{domain}"
            self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        # If use_real_email=True, this will be handled by mail_tm_service.create_real_temp_email()
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def deactivate(self):
        self.is_active = False
        db.session.commit()

class EmailMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temp_email_id = db.Column(db.Integer, db.ForeignKey('temp_email.id'), nullable=False)
    sender = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500), nullable=True)
    body = db.Column(db.Text, nullable=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_spam = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    
    # Mail.tm integration field
    mail_tm_id = db.Column(db.String(255), nullable=True)
    
    temp_email = db.relationship('TempEmail', backref=db.backref('messages', lazy=True))


