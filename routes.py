import uuid
from flask import render_template, request, session, redirect, url_for, flash, jsonify, send_from_directory, make_response
from app import app, limiter, temp_emails, email_messages, save_emails_to_cache
from models import TempEmail, EmailMessage
from utils import is_spam_email
from datetime import datetime
import logging
import re
from mail_tm_service import mail_tm_service

@app.before_request
def ensure_session():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

@app.route('/')
def index():
    # Get user's active services
    session_id = session.get('session_id')
    active_emails = []
    
    # Get active emails from in-memory storage
    for email_id, email in temp_emails.items():
        if (email.session_id == session_id and 
            email.is_active and 
            not hasattr(email, 'is_expired') or not email.is_expired):
            active_emails.append(email)
    
    # AUTO-GENERATE EMAIL: If no active emails, create one automatically
    if not active_emails:
        logging.info(f"No active emails for session {session_id}, creating one automatically")
        
        # Delete any old emails for this session first
        to_delete = []
        for email_id, email in temp_emails.items():
            if email.session_id == session_id:
                to_delete.append(email_id)
        
        for email_id in to_delete:
            # Delete associated messages first
            messages_to_delete = []
            for msg_id, msg in email_messages.items():
                if msg.temp_email_id == email_id:
                    messages_to_delete.append(msg_id)
            
            for msg_id in messages_to_delete:
                del email_messages[msg_id]
            
            del temp_emails[email_id]
        
        # Create new temporary email automatically
        temp_email = mail_tm_service.create_real_temp_email(session_id, None, TempEmail)
        
        if temp_email:
            temp_emails[temp_email.id] = temp_email
            active_emails = [temp_email]
            logging.info(f"Auto-created email: {temp_email.email_address}")
            # Save to cache for persistence
            save_emails_to_cache()
        else:
            logging.error("Failed to auto-create email")
    
    # Fetch messages for active emails and attach them
    for email in active_emails:
        if hasattr(email, 'mail_tm_id') and email.mail_tm_id:
            # Refresh messages from mail.tm service
            mail_tm_service.fetch_emails_for_account(email, None, EmailMessage)
        
        # Get messages for this email from email_messages dictionary
        messages = []
        for msg_id, msg in email_messages.items():
            if msg.temp_email_id == email.id:
                messages.append(msg)
        
        # Sort messages by received date (newest first)
        messages.sort(key=lambda x: x.received_at, reverse=True)
        
        # Attach messages to the email object
        email.messages = messages
    
    return render_template('index.html', 
                         active_emails=active_emails)

@app.route('/generate-email', methods=['POST'])
@limiter.limit("10 per hour")
def generate_email():
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    # Delete all old emails for this session before creating new one
    to_delete = []
    for email_id, email in temp_emails.items():
        if email.session_id == session_id:
            to_delete.append(email_id)
    
    for email_id in to_delete:
        # Delete associated messages first
        messages_to_delete = []
        for msg_id, msg in email_messages.items():
            if msg.temp_email_id == email_id:
                messages_to_delete.append(msg_id)
        
        for msg_id in messages_to_delete:
            del email_messages[msg_id]
        
        del temp_emails[email_id]
    
    # Create new temporary email using mail.tm service
    temp_email = mail_tm_service.create_real_temp_email(session_id, None, TempEmail)
    
    if temp_email:
        temp_emails[temp_email.id] = temp_email
        save_emails_to_cache()  # Save to cache
        flash(f'New temporary email created: {temp_email.email_address}', 'success')
        return redirect(url_for('index'))
    else:
        # Fallback to local email if mail.tm fails
        temp_email = TempEmail(session_id=session_id, use_real_email=False)
        temp_emails[temp_email.id] = temp_email
        save_emails_to_cache()  # Save to cache
        flash(f'Temporary email created: {temp_email.email_address} (Demo mode)', 'warning')
        return redirect(url_for('index'))

@app.route('/email-inbox/<email_id>')
def email_inbox(email_id):
    session_id = session.get('session_id')
    
    # Verify ownership
    temp_email = temp_emails.get(email_id)
    if not temp_email or temp_email.session_id != session_id or not temp_email.is_active:
        flash('Email not found or expired.', 'error')
        return redirect(url_for('index'))
    
    # Get messages for this email
    messages = []
    for msg_id, msg in email_messages.items():
        if msg.temp_email_id == email_id:
            messages.append(msg)
    
    # Sort messages by received date (newest first)
    messages.sort(key=lambda x: x.received_at, reverse=True)
    
    return render_template('email_inbox.html', 
                         temp_email=temp_email, 
                         messages=messages)

@app.route('/fetch-emails/<email_id>')
def fetch_emails(email_id):
    session_id = session.get('session_id')
    
    logging.info(f"Fetch emails called - Email ID: {email_id}, Session ID: {session_id}")
    logging.info(f"Available temp_emails: {list(temp_emails.keys())}")
    
    # Verify ownership
    temp_email = temp_emails.get(email_id)
    if not temp_email:
        logging.error(f"Email not found: {email_id}, redirecting to create new email")
        return jsonify({'status': 'error', 'message': 'Email not found', 'redirect': '/'}), 404
    
    if temp_email.session_id != session_id:
        logging.error(f"Session mismatch: {temp_email.session_id} != {session_id}")
        return jsonify({'status': 'error', 'message': 'Session mismatch'}), 403
    
    if not temp_email.is_active:
        logging.error(f"Email inactive: {email_id}")
        return jsonify({'status': 'error', 'message': 'Email inactive'}), 404
    
    try:
        # Fetch emails from mail.tm service if available
        if hasattr(temp_email, 'mail_tm_id') and temp_email.mail_tm_id:
            logging.info(f"Fetching emails for account: {temp_email.email_address}")
            new_count = mail_tm_service.fetch_emails_for_account(temp_email, None, EmailMessage)
            logging.info(f"Fetched {new_count} new messages")
        
        # Get updated messages
        messages = []
        for msg_id, msg in email_messages.items():
            if msg.temp_email_id == email_id:
                messages.append({
                    'id': msg.id,
                    'sender': msg.sender,
                    'sender_name': msg.sender_name,
                    'subject': msg.subject,
                    'body': msg.body,
                    'text_content': msg.text_content,
                    'html_content': msg.html_content,
                    'received_at': msg.received_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_spam': msg.is_spam,
                    'is_read': msg.is_read
                })
        
        # Sort messages by received date (newest first)
        messages.sort(key=lambda x: x['received_at'], reverse=True)
        
        logging.info(f"Returning {len(messages)} messages for email {email_id}")
        return jsonify({'status': 'success', 'messages': messages, 'count': len(messages)})
    except Exception as e:
        logging.error(f"Error fetching emails: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Failed to check for new messages'}), 500

@app.route('/delete-email/<email_id>', methods=['POST'])
def delete_email(email_id):
    session_id = session.get('session_id')
    
    # Verify ownership
    temp_email = temp_emails.get(email_id)
    if not temp_email or temp_email.session_id != session_id:
        flash('Email not found.', 'error')
        return redirect(url_for('index'))
    
    # Delete associated messages
    messages_to_delete = []
    for msg_id, msg in email_messages.items():
        if msg.temp_email_id == email_id:
            messages_to_delete.append(msg_id)
    
    for msg_id in messages_to_delete:
        del email_messages[msg_id]
    
    # Delete the email
    del temp_emails[email_id]
    
    flash('Email deleted successfully.', 'success')
    return redirect(url_for('index'))

# SEO and Static Routes
@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/robots.txt')
def robots_txt():
    response = make_response("""User-agent: *
Allow: /
Sitemap: https://tempmail.replit.app/sitemap.xml""")
    response.headers['Content-Type'] = 'text/plain'
    return response

@app.route('/sitemap.xml')
def sitemap_xml():
    response = make_response("""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://tempmail.replit.app/</loc>
    <lastmod>2025-07-19</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://tempmail.replit.app/privacy</loc>
    <lastmod>2025-07-19</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://tempmail.replit.app/terms</loc>
    <lastmod>2025-07-19</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>""")
    response.headers['Content-Type'] = 'application/xml'
    return response

# Test route to add sample emails for testing
@app.route('/add-test-email/<email_id>')
def add_test_email(email_id):
    session_id = session.get('session_id')
    
    # Verify email exists and ownership
    temp_email = temp_emails.get(email_id)
    if not temp_email or temp_email.session_id != session_id:
        flash('Email not found.', 'error')
        return redirect(url_for('index'))
    
    # Add a test email message
    test_message = EmailMessage(
        temp_email_id=email_id,
        sender_email="test@example.com",
        sender_name="Test Sender",
        subject="Test Email Message",
        body="This is a test email message to verify the email display functionality.",
        text_content="This is a test email message to verify the email display functionality.",
        html_content="<p>This is a test email message to verify the email display functionality.</p>"
    )
    
    email_messages[test_message.id] = test_message
    flash('Test email added successfully!', 'success')
    return redirect(url_for('index'))

# Helper function to clean expired emails
def cleanup_expired_emails():
    """Remove expired emails from memory"""
    expired_emails = []
    for email_id, email in temp_emails.items():
        if hasattr(email, 'is_expired') and email.is_expired:
            expired_emails.append(email_id)
    
    for email_id in expired_emails:
        # Delete associated messages
        messages_to_delete = []
        for msg_id, msg in email_messages.items():
            if msg.temp_email_id == email_id:
                messages_to_delete.append(msg_id)
        
        for msg_id in messages_to_delete:
            del email_messages[msg_id]
        
        del temp_emails[email_id]

# Run cleanup before each request
@app.before_request
def cleanup_before_request():
    cleanup_expired_emails()