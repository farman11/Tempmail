import requests
import json
import logging
from datetime import datetime, timedelta
from app import db
from models import TempEmail, EmailMessage
import hashlib

class MailTMService:
    """Service to integrate with mail.tm API for real temporary emails"""
    
    def __init__(self):
        self.base_url = "https://api.mail.tm"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def get_available_domains(self):
        """Get list of available domains from mail.tm"""
        try:
            response = self.session.get(f"{self.base_url}/domains")
            if response.status_code == 200:
                domains = response.json()['hydra:member']
                return [domain['domain'] for domain in domains]
            return []
        except Exception as e:
            logging.error(f"Error getting domains: {e}")
            return []
    
    def create_account(self, email_address, password):
        """Create a new account on mail.tm"""
        try:
            data = {
                "address": email_address,
                "password": password
            }
            response = self.session.post(f"{self.base_url}/accounts", json=data)
            if response.status_code == 201:
                return response.json()
            else:
                logging.error(f"Failed to create account: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Error creating account: {e}")
            return None
    
    def get_auth_token(self, email_address, password):
        """Get authentication token for accessing emails"""
        try:
            data = {
                "address": email_address,
                "password": password
            }
            response = self.session.post(f"{self.base_url}/token", json=data)
            if response.status_code == 200:
                return response.json()['token']
            else:
                logging.error(f"Failed to get token: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Error getting token: {e}")
            return None
    
    def get_messages(self, token):
        """Get all messages for the authenticated account"""
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = self.session.get(f"{self.base_url}/messages", headers=headers)
            if response.status_code == 200:
                return response.json()['hydra:member']
            else:
                logging.error(f"Failed to get messages: {response.text}")
                return []
        except Exception as e:
            logging.error(f"Error getting messages: {e}")
            return []
    
    def get_message_details(self, message_id, token):
        """Get detailed content of a specific message"""
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = self.session.get(f"{self.base_url}/messages/{message_id}", headers=headers)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logging.error(f"Error getting message details: {e}")
            return None
    
    def create_real_temp_email(self, session_id):
        """Create a real temporary email using mail.tm"""
        try:
            domains = self.get_available_domains()
            if not domains:
                logging.error("No domains available")
                return None
            
            # Use the first available domain
            domain = domains[0]
            
            # Generate unique email address
            import uuid
            username = uuid.uuid4().hex[:12]
            email_address = f"{username}@{domain}"
            
            # Generate password
            password = uuid.uuid4().hex
            
            # Create account on mail.tm
            account = self.create_account(email_address, password)
            if not account:
                return None
            
            # Create TempEmail record in our database
            temp_email = TempEmail.__new__(TempEmail)
            temp_email.session_id = session_id
            temp_email.email_address = email_address
            temp_email.expires_at = datetime.utcnow() + timedelta(hours=24)
            temp_email.is_active = True
            temp_email.created_at = datetime.utcnow()
            
            # Store mail.tm credentials
            temp_email.mail_tm_password = password
            temp_email.mail_tm_id = account.get('id')
            
            db.session.add(temp_email)
            db.session.commit()
            
            return temp_email
            
        except Exception as e:
            logging.error(f"Error creating real temp email: {e}")
            return None
    
    def fetch_emails_for_account(self, temp_email):
        """Fetch new emails for a specific temp email account"""
        try:
            if not hasattr(temp_email, 'mail_tm_password'):
                return 0
            
            # Get auth token
            token = self.get_auth_token(temp_email.email_address, temp_email.mail_tm_password)
            if not token:
                return 0
            
            # Get messages
            messages = self.get_messages(token)
            new_messages = 0
            
            for msg in messages:
                # Check if message already exists
                existing = EmailMessage.query.filter_by(
                    temp_email_id=temp_email.id,
                    mail_tm_id=msg['id']
                ).first()
                
                if existing:
                    continue
                
                # Get message details
                details = self.get_message_details(msg['id'], token)
                if not details:
                    continue
                
                # Create EmailMessage record
                email_msg = EmailMessage(
                    temp_email_id=temp_email.id,
                    sender=details.get('from', {}).get('address', 'Unknown'),
                    subject=details.get('subject', ''),
                    body=details.get('text', details.get('html', '')),
                    received_at=datetime.fromisoformat(details['createdAt'].replace('Z', '+00:00')),
                    is_spam=False,  # mail.tm handles spam filtering
                    is_read=False
                )
                
                # Store mail.tm message ID for deduplication
                email_msg.mail_tm_id = msg['id']
                
                db.session.add(email_msg)
                new_messages += 1
            
            if new_messages > 0:
                db.session.commit()
                logging.info(f"Fetched {new_messages} new messages for {temp_email.email_address}")
            
            return new_messages
            
        except Exception as e:
            logging.error(f"Error fetching emails: {e}")
            return 0
    
    def fetch_all_emails(self):
        """Fetch emails for all active temp email accounts"""
        try:
            active_emails = TempEmail.query.filter_by(is_active=True).filter(
                TempEmail.expires_at > datetime.utcnow()
            ).all()
            
            total_new = 0
            for temp_email in active_emails:
                if hasattr(temp_email, 'mail_tm_password'):
                    new_count = self.fetch_emails_for_account(temp_email)
                    total_new += new_count
            
            return total_new
            
        except Exception as e:
            logging.error(f"Error in fetch_all_emails: {e}")
            return 0

# Global service instance
mail_tm_service = MailTMService()