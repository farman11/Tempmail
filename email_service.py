import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app import db
from models import TempEmail, EmailMessage
from utils import is_spam_email
import logging

class EmailService:
    def __init__(self):
        self.smtp_server = os.environ.get('MAIL_SERVER', 'localhost')
        self.smtp_port = int(os.environ.get('MAIL_PORT', 587))
        self.username = os.environ.get('MAIL_USERNAME')
        self.password = os.environ.get('MAIL_PASSWORD')
        self.imap_server = os.environ.get('IMAP_SERVER', self.smtp_server)
        self.imap_port = int(os.environ.get('IMAP_PORT', 993))
        
    def check_and_fetch_emails(self):
        """Check for new emails and store them in database"""
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.username, self.password)
            mail.select('inbox')
            
            # Search for unseen emails
            status, messages = mail.search(None, 'UNSEEN')
            
            if status == 'OK':
                for msg_id in messages[0].split():
                    # Fetch the email
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')
                    
                    if status == 'OK':
                        raw_email = msg_data[0][1]
                        email_message = email.message_from_bytes(raw_email)
                        
                        # Extract email details
                        to_email = email_message.get('To', '')
                        from_email = email_message.get('From', '')
                        subject = email_message.get('Subject', '')
                        
                        # Get body
                        body = ''
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    break
                        else:
                            body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                        
                        # Find corresponding temporary email
                        temp_email = TempEmail.query.filter_by(
                            email_address=to_email,
                            is_active=True
                        ).first()
                        
                        if temp_email and not temp_email.is_expired:
                            # Check for spam
                            spam_check = is_spam_email(from_email, subject, body)
                            
                            # Store the message
                            email_msg = EmailMessage(
                                temp_email_id=temp_email.id,
                                sender=from_email,
                                subject=subject,
                                body=body,
                                is_spam=spam_check
                            )
                            
                            db.session.add(email_msg)
                            db.session.commit()
                            
                            logging.info(f"Stored email for {to_email}")
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            logging.error(f"Error checking emails: {e}")

# Background task to check emails periodically
def setup_email_checking():
    """Setup periodic email checking (would be called by a scheduler)"""
    email_service = EmailService()
    email_service.check_and_fetch_emails()
