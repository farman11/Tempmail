import requests
import json
import logging
from datetime import datetime, timedelta
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
                data = response.json()
                logging.debug(f"Domains response: {data}")
                
                # Handle different response formats
                if isinstance(data, list):
                    return [domain['domain'] for domain in data if 'domain' in domain]
                elif isinstance(data, dict):
                    if 'hydra:member' in data:
                        return [domain['domain'] for domain in data['hydra:member']]
                    elif '@graph' in data:
                        return [domain['domain'] for domain in data['@graph']]
                    elif 'domains' in data:
                        return [domain['domain'] for domain in data['domains']]
                    elif 'data' in data:
                        return [domain['domain'] for domain in data['data']]
                
                logging.error(f"Unexpected response format: {data}")
                return []
            else:
                logging.error(f"Failed to get domains: {response.status_code} - {response.text}")
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
                data = response.json()
                logging.debug(f"Messages response: {data}")
                
                # Handle different response formats
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    if 'hydra:member' in data:
                        return data['hydra:member']
                    elif '@graph' in data:
                        return data['@graph']
                    elif 'messages' in data:
                        return data['messages']
                    elif 'data' in data:
                        return data['data']
                
                logging.error(f"Unexpected messages response format: {data}")
                return []
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
    
    def create_real_temp_email(self, session_id, db, TempEmail):
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
            
            # Create TempEmail record
            temp_email = TempEmail(
                session_id=session_id,
                use_real_email=True  # This prevents the __init__ from setting local email
            )
            temp_email.email_address = email_address
            temp_email.expires_at = datetime.utcnow() + timedelta(hours=24)
            temp_email.is_active = True
            temp_email.created_at = datetime.utcnow()
            
            # Store mail.tm credentials
            temp_email.mail_tm_password = password
            temp_email.mail_tm_id = account.get('id')
            
            return temp_email
            
        except Exception as e:
            logging.error(f"Error creating real temp email: {e}")
            return None
    
    def fetch_emails_for_account(self, temp_email, db, EmailMessage):
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
            
            # Import email_messages from app module
            from app import email_messages
            
            for msg in messages:
                # Check if message already exists in memory
                existing = False
                for msg_id, stored_msg in email_messages.items():
                    if (stored_msg.temp_email_id == temp_email.id and 
                        stored_msg.mail_tm_id == msg['id']):
                        existing = True
                        break
                
                if existing:
                    continue
                
                # Get message details
                details = self.get_message_details(msg['id'], token)
                if not details:
                    continue
                
                # Extract sender information
                from_info = details.get('from', {})
                sender_email = from_info.get('address', 'Unknown')
                sender_name = from_info.get('name', '')
                
                # Create EmailMessage object
                email_msg = EmailMessage(
                    temp_email_id=temp_email.id,
                    sender_email=sender_email,
                    sender_name=sender_name if sender_name else None,
                    subject=details.get('subject', ''),
                    body=details.get('text', details.get('html', '')),
                    text_content=details.get('text', ''),
                    html_content=details.get('html', ''),
                    mail_tm_id=msg['id']
                )
                
                # Set received_at
                try:
                    email_msg.received_at = datetime.fromisoformat(details['createdAt'].replace('Z', '+00:00'))
                except:
                    email_msg.received_at = datetime.utcnow()
                
                # Store in memory
                email_messages[email_msg.id] = email_msg
                new_messages += 1
            
            if new_messages > 0:
                logging.info(f"Fetched {new_messages} new messages for {temp_email.email_address}")
            
            return new_messages
            
        except Exception as e:
            logging.error(f"Error fetching emails: {e}")
            return 0
    
    def fetch_all_emails(self, db, TempEmail, EmailMessage):
        """Fetch emails for all active temp email accounts"""
        try:
            from app import temp_emails
            
            total_new = 0
            for email_id, temp_email in temp_emails.items():
                if (temp_email.is_active and 
                    not temp_email.is_expired and 
                    hasattr(temp_email, 'mail_tm_password')):
                    new_count = self.fetch_emails_for_account(temp_email, db, EmailMessage)
                    total_new += new_count
            
            return total_new
            
        except Exception as e:
            logging.error(f"Error in fetch_all_emails: {e}")
            return 0

# Global service instance
mail_tm_service = MailTMService()