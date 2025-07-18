import uuid
from flask import render_template, request, session, redirect, url_for, flash, jsonify
from app import app, db, limiter
from models import TempEmail, EmailMessage
from utils import is_spam_email
from datetime import datetime
import logging

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
    
    return render_template('index.html', 
                         active_emails=active_emails)

@app.route('/generate-email', methods=['POST'])
@limiter.limit("10 per hour")
def generate_email():
    session_id = session.get('session_id')
    
    # Check if user already has 5 active emails (limit)
    active_count = TempEmail.query.filter_by(
        session_id=session_id, 
        is_active=True
    ).filter(TempEmail.expires_at > datetime.utcnow()).count()
    
    if active_count >= 5:
        flash('You can only have 5 active temporary emails at once.', 'warning')
        return redirect(url_for('index'))
    
    # Create new temporary email
    temp_email = TempEmail(session_id=session_id)
    db.session.add(temp_email)
    db.session.commit()
    
    flash(f'Temporary email created: {temp_email.email_address}', 'success')
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


