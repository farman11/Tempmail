import uuid
from flask import render_template, request, session, redirect, url_for, flash, jsonify, send_from_directory, make_response
from app import app, db, limiter
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
    active_emails = TempEmail.query.filter_by(
        session_id=session_id, 
        is_active=True
    ).filter(TempEmail.expires_at > datetime.utcnow()).all()
    
    # Fetch messages for active emails
    for email in active_emails:
        if email.mail_tm_id:
            # Refresh messages from mail.tm service
            mail_tm_service.fetch_emails_for_account(email, db, EmailMessage)
    
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
    old_emails = TempEmail.query.filter_by(session_id=session_id).all()
    for old_email in old_emails:
        # Delete associated messages first
        EmailMessage.query.filter_by(temp_email_id=old_email.id).delete()
        db.session.delete(old_email)
    
    db.session.commit()
    
    # Create new temporary email using mail.tm service
    temp_email = mail_tm_service.create_real_temp_email(session_id, db, TempEmail)
    
    if temp_email:
        flash(f'New temporary email created: {temp_email.email_address}', 'success')
        return redirect(url_for('index'))
    else:
        # Fallback to local email if mail.tm fails
        temp_email = TempEmail(session_id=session_id, use_real_email=False)
        db.session.add(temp_email)
        db.session.commit()
        flash(f'Temporary email created: {temp_email.email_address} (Demo mode)', 'warning')
        return redirect(url_for('index'))



@app.route('/email-inbox/<int:email_id>')
def email_inbox(email_id):
    session_id = session.get('session_id')
    
    # Verify ownership
    temp_email = TempEmail.query.filter_by(
        id=email_id, 
        session_id=session_id, 
        is_active=True
    ).first_or_404()
    
    if temp_email.is_expired:
        flash('This email address has expired.', 'warning')
        return redirect(url_for('index'))
    
    # Fetch new emails from mail.tm before displaying
    if hasattr(temp_email, 'mail_tm_password') and temp_email.mail_tm_password:
        mail_tm_service.fetch_emails_for_account(temp_email, db, EmailMessage)
    
    # Get messages (filter out spam unless requested)
    show_spam = request.args.get('show_spam', False)
    if show_spam:
        messages = EmailMessage.query.filter_by(temp_email_id=email_id).order_by(EmailMessage.received_at.desc()).all()
    else:
        messages = EmailMessage.query.filter_by(temp_email_id=email_id, is_spam=False).order_by(EmailMessage.received_at.desc()).all()
    
    return render_template('email_inbox.html', 
                         temp_email=temp_email, 
                         messages=messages,
                         show_spam=show_spam)



@app.route('/delete-email/<int:email_id>', methods=['POST'])
def delete_email(email_id):
    session_id = session.get('session_id')
    
    temp_email = TempEmail.query.filter_by(
        id=email_id, 
        session_id=session_id, 
        is_active=True
    ).first_or_404()
    
    temp_email.deactivate()
    flash('Temporary email deleted.', 'success')
    return redirect(url_for('index'))



@app.route('/mark-read/<int:message_id>', methods=['POST'])
def mark_email_read(message_id):
    session_id = session.get('session_id')
    
    message = EmailMessage.query.join(TempEmail).filter(
        EmailMessage.id == message_id,
        TempEmail.session_id == session_id
    ).first_or_404()
    
    message.is_read = True
    db.session.commit()
    
    return jsonify({'status': 'success'})


@app.route('/fetch-emails', methods=['POST'])
def fetch_emails():
    """Manually fetch emails from mail.tm for active accounts"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'status': 'error', 'message': 'No active session'}), 400
        
        # Get user's active emails
        active_emails = TempEmail.query.filter_by(
            session_id=session_id,
            is_active=True
        ).filter(TempEmail.expires_at > datetime.utcnow()).all()
        
        if not active_emails:
            return jsonify({'status': 'error', 'message': 'No active temporary emails found'}), 404
        
        total_new_messages = 0
        
        # Fetch emails for each active temp email
        for temp_email in active_emails:
            if hasattr(temp_email, 'mail_tm_password') and temp_email.mail_tm_password:
                new_count = mail_tm_service.fetch_emails_for_account(temp_email, db, EmailMessage)
                total_new_messages += new_count
        
        if total_new_messages > 0:
            return jsonify({
                'status': 'success', 
                'message': f'Found {total_new_messages} new message(s)',
                'new_messages': total_new_messages
            })
        else:
            return jsonify({
                'status': 'success', 
                'message': 'No new messages found',
                'new_messages': 0
            })
            
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to check for new messages'}), 500



# Development route to add test emails
@app.route('/add-test-email/<int:email_id>')
def add_test_email(email_id):
    """Add test emails for development purposes"""
    session_id = session.get('session_id')
    
    temp_email = TempEmail.query.filter_by(
        id=email_id, 
        session_id=session_id, 
        is_active=True
    ).first_or_404()
    
    # Add some test emails
    test_emails = [
        {
            'sender': 'welcome@service.com',
            'subject': 'Welcome to our service!',
            'body': 'Thank you for signing up! Your account is now active.'
        },
        {
            'sender': 'noreply@bank.com',
            'subject': 'Your account statement is ready',
            'body': 'Your monthly account statement is now available for download.'
        },
        {
            'sender': 'spam@marketing.com',
            'subject': 'URGENT: You won 1 million dollars!',
            'body': 'Congratulations! You have won our lottery. Send us your bank details immediately!'
        },
        {
            'sender': 'support@github.com',
            'subject': 'Security alert: New login',
            'body': 'We noticed a new login to your account from a new device.'
        },
        {
            'sender': 'no-reply@amazon.com',
            'subject': 'Your order has been shipped',
            'body': 'Good news! Your order #123456 has been shipped and is on its way.'
        }
    ]
    
    for test_email in test_emails:
        # Check for spam
        spam_check = is_spam_email(test_email['sender'], test_email['subject'], test_email['body'])
        
        message = EmailMessage(
            temp_email_id=temp_email.id,
            sender=test_email['sender'],
            sender_email=test_email['sender'],
            sender_name=None,
            subject=test_email['subject'],
            body=test_email['body'],
            text_content=test_email['body'],
            html_content=None,
            is_spam=spam_check
        )
        
        db.session.add(message)
    
    db.session.commit()
    flash('Test emails added successfully!', 'success')
    return redirect(url_for('email_inbox', email_id=email_id))


# Route to manually add received email (for testing real services)
@app.route('/receive-email', methods=['POST'])
def receive_email():
    """Manually receive an email for testing purposes"""
    try:
        # Get form data
        to_email = request.form.get('to_email', '').strip()
        from_email = request.form.get('from_email', '').strip()
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()
        
        if not to_email or not from_email:
            flash('To and From email addresses are required', 'error')
            return redirect(url_for('index'))
        
        # Find the temporary email
        temp_email = TempEmail.query.filter_by(
            email_address=to_email, 
            is_active=True
        ).filter(TempEmail.expires_at > datetime.utcnow()).first()
        
        if not temp_email:
            flash(f'Temporary email {to_email} not found or expired', 'error')
            return redirect(url_for('index'))
        
        # Check for spam
        spam_check = is_spam_email(from_email, subject, body)
        
        # Create message
        message = EmailMessage(
            temp_email_id=temp_email.id,
            sender=from_email,
            subject=subject,
            body=body,
            is_spam=spam_check
        )
        
        db.session.add(message)
        db.session.commit()
        
        flash(f'Email received successfully! {"(Marked as spam)" if spam_check else ""}', 'success')
        return redirect(url_for('email_inbox', email_id=temp_email.id))
        
    except Exception as e:
        logging.error(f"Manual email receive error: {e}")
        flash('Error receiving email', 'error')
        return redirect(url_for('index'))


# API endpoint to simulate receiving verification codes
@app.route('/api/simulate-verification', methods=['POST'])
def simulate_verification():
    """API endpoint to simulate receiving verification codes from services"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        to_email = data.get('email')
        service_name = data.get('service', 'Unknown Service')
        code = data.get('code')
        
        if not to_email or not code:
            return jsonify({'error': 'Email and code are required'}), 400
        
        # Find the temporary email
        temp_email = TempEmail.query.filter_by(
            email_address=to_email, 
            is_active=True
        ).filter(TempEmail.expires_at > datetime.utcnow()).first()
        
        if not temp_email:
            return jsonify({'error': 'Email not found or expired'}), 404
        
        # Create verification email message
        subject = f"Verification Code from {service_name}"
        body = f"Your verification code is: {code}\n\nThis code will expire in 10 minutes.\n\nIf you didn't request this code, please ignore this email."
        
        message = EmailMessage(
            temp_email_id=temp_email.id,
            sender=f"noreply@{service_name.lower().replace(' ', '')}.com",
            subject=subject,
            body=body,
            is_spam=False
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Verification code sent',
            'email_id': temp_email.id
        })
        
    except Exception as e:
        logging.error(f"Verification simulation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Webhook endpoints for receiving messages
@app.route('/webhook/email', methods=['POST'])
def email_webhook():
    """Webhook to receive incoming emails"""
    try:
        data = request.get_json()
        to_email = data.get('to')
        from_email = data.get('from')
        subject = data.get('subject', '')
        body = data.get('body', '')
        
        # Find the temporary email
        temp_email = TempEmail.query.filter_by(
            email_address=to_email, 
            is_active=True
        ).filter(TempEmail.expires_at > datetime.utcnow()).first()
        
        if not temp_email:
            return jsonify({'status': 'email_not_found'}), 404
        
        # Check for spam
        spam_check = is_spam_email(from_email, subject, body)
        
        # Create message
        message = EmailMessage(
            temp_email_id=temp_email.id,
            sender=from_email,
            subject=subject,
            body=body,
            is_spam=spam_check
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({'status': 'received'})
        
    except Exception as e:
        logging.error(f"Email webhook error: {e}")
        return jsonify({'status': 'error'}), 500

# SEO and Performance Routes
@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt file for search engine crawlers"""
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    """Serve sitemap.xml file for search engines"""
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')

@app.route('/privacy')
def privacy_policy():
    """Privacy policy page for SEO and user trust"""
    return render_template('privacy.html')

@app.route('/terms')
def terms_of_service():
    """Terms of service page for SEO and legal compliance"""
    return render_template('terms.html')





