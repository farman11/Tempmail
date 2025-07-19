# TempMail Deployment Guide for Hostinger

## Overview
This guide will help you deploy your TempMail Flask application to Hostinger hosting.

## Prerequisites
- Hostinger hosting account with Python support
- Domain name configured in Hostinger
- SSH access to your hosting account

## Step 1: Prepare Your Project

### 1.1 Create requirements.txt
Create a requirements.txt file with all dependencies:

```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Mail==0.9.1
Flask-Limiter==3.5.0
gunicorn==21.2.0
psycopg2-binary==2.9.7
requests==2.31.0
email-validator==2.0.0
Werkzeug==2.3.7
```

### 1.2 Environment Configuration
Create a `.env` file for production settings:

```
FLASK_ENV=production
DATABASE_URL=postgresql://username:password@localhost/tempmail_db
SESSION_SECRET=your-super-secret-key-here
MAIL_SERVER=smtp.hostinger.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@yourdomain.com
MAIL_PASSWORD=your-email-password
```

### 1.3 Update main.py for Production
```python
import os
from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
```

## Step 2: Hostinger Setup

### 2.1 Access Your Hosting Panel
1. Log into your Hostinger account
2. Go to your hosting panel
3. Navigate to "File Manager" or use SSH access

### 2.2 Upload Project Files
1. Create a new directory in your domain's public_html folder (e.g., `tempmail`)
2. Upload all your project files to this directory:
   - `app.py`
   - `main.py`
   - `routes.py`
   - `models.py`
   - `mail_tm_service.py`
   - `utils.py`
   - `templates/` folder
   - `static/` folder
   - `requirements.txt`
   - `.env` file

### 2.3 Set Up Python Environment
Via SSH or terminal in Hostinger:

```bash
# Navigate to your project directory
cd public_html/tempmail

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Database Setup

### 3.1 Create PostgreSQL Database
In Hostinger panel:
1. Go to "Databases" section
2. Create a new PostgreSQL database
3. Note down the database credentials
4. Update your `.env` file with correct DATABASE_URL

### 3.2 Initialize Database
```bash
# In your project directory with activated venv
python3
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

## Step 4: Web Server Configuration

### 4.1 Create WSGI File
Create `wsgi.py` in your project root:

```python
#!/usr/bin/python3
import sys
import os

# Add your project directory to sys.path
sys.path.insert(0, "/home/yourusername/public_html/tempmail/")

from main import app as application

if __name__ == "__main__":
    application.run()
```

### 4.2 Create .htaccess File
Create `.htaccess` in your project directory:

```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteRule ^(.*)$ wsgi.py [QSA,L]

# Security headers
<IfModule mod_headers.c>
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options DENY
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
    Header always set Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://api.mail.tm;"
</IfModule>
```

## Step 5: Domain Configuration

### 5.1 Update Hostinger DNS
1. Go to DNS settings in Hostinger
2. Add/update A record to point to your hosting server
3. Ensure subdomain (if using) points correctly

### 5.2 SSL Certificate
1. In Hostinger panel, go to SSL certificates
2. Enable free SSL certificate for your domain
3. Force HTTPS redirect

## Step 6: Environment Variables

### 6.1 Secure Environment Variables
Instead of .env file, use Hostinger's environment variable settings:
1. Go to hosting panel
2. Find "Environment Variables" or "Python App" settings
3. Add your production variables securely

## Step 7: Testing and Monitoring

### 7.1 Test Your Deployment
1. Visit your domain: `https://yourdomain.com/tempmail`
2. Test email generation functionality
3. Check that all routes work correctly
4. Verify database connections

### 7.2 Enable Logging
Create a logging configuration in your app:

```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/tempmail.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
```

## Step 8: Performance Optimization

### 8.1 Enable Caching
Add caching headers to your Flask app:

```python
@app.after_request
def after_request(response):
    if request.endpoint == 'static':
        response.headers['Cache-Control'] = 'public, max-age=31536000'
    return response
```

### 8.2 Database Connection Pooling
Update your database configuration:

```python
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 10,
    "max_overflow": 20
}
```

## Troubleshooting

### Common Issues:

1. **Permission Errors**: Ensure proper file permissions (755 for directories, 644 for files)
2. **Import Errors**: Check Python path and virtual environment activation
3. **Database Connection**: Verify database credentials and firewall settings
4. **Static Files**: Ensure static files are accessible and properly served

### Debugging:
```bash
# Check error logs
tail -f /path/to/error.log

# Test Python import
python3 -c "from main import app; print('Import successful')"
```

## Maintenance

### Regular Tasks:
1. Monitor error logs weekly
2. Update dependencies monthly
3. Backup database weekly
4. Check SSL certificate expiration
5. Monitor disk space usage

### Updates:
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart application (method varies by hosting)
touch wsgi.py  # Force reload
```

## Security Considerations

1. Keep all dependencies updated
2. Use environment variables for sensitive data
3. Enable HTTPS/SSL
4. Regular security headers in .htaccess
5. Monitor for suspicious activity
6. Regular database backups

## Contact Support

For Hostinger-specific issues:
- Contact Hostinger support
- Check Hostinger documentation for Python hosting
- Use Hostinger community forums

---

**Developed by Root Group Tech** - https://rootgroup.tech
Specializing in Digital Marketing, Web Development, Mobile Apps, and IT Solutions