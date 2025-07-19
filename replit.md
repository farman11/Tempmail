# TempMail - Temporary Email & Phone Service

## Overview

TempMail is a Flask-based web application that provides users with temporary, disposable email addresses for privacy protection. The service features a modern Tailwind CSS interface with Gmail-style email formatting, Google Ads placement areas, and smooth user interactions. The service allows anonymous access without registration, automatically manages service expiration, and includes spam filtering capabilities.

## Recent Changes

✓ **2025-07-19**: Enhanced Email Display & Interactive Refresh System
- Fixed database connection issues by creating PostgreSQL database
- Removed JSON formatting characters ({}, "", []) from email content display
- Added dynamic link-to-button conversion with intelligent button naming
- Enhanced verification code highlighting with professional styling
- Fixed JavaScript errors related to DOM manipulation
- Improved email content processing with better formatting
- Added professional CSS styling for email buttons and verification codes
- Replaced text-based "Check for New Emails" with animated refresh icons
- Implemented enhanced motion effects: hover animations, pulse effects, and smooth spinning
- Added automatic refresh every 30 seconds with subtle animations
- Removed all alerts for completely silent operation

✓ **2025-07-18**: Migrated from Bootstrap to Tailwind CSS framework
✓ **2025-07-18**: Implemented Gmail-style email formatting and display
✓ **2025-07-18**: Added Google Ads placement areas in left/right sidebars and footer
✓ **2025-07-18**: Removed "Need Help" and "Quick Tools" sections for simplified UI
✓ **2025-07-18**: Updated all button functionality with smooth transitions
✓ **2025-07-18**: Enhanced copy-to-clipboard functionality with visual feedback
✓ **2025-07-18**: Added comprehensive SEO meta tags, Open Graph, Twitter Cards, and Schema.org structured data
✓ **2025-07-18**: Removed "Temp Number", "Premium", "App Store", and "Google Play" sections from navigation
✓ **2025-07-18**: Implemented automatic link handling to open email links in new tabs with security attributes
✓ **2025-07-18**: Made application fully responsive for all devices (mobile, tablet, desktop)
✓ **2025-07-18**: Added mobile-specific CSS breakpoints and responsive layout adjustments
✓ **2025-07-18**: Optimized text overflow handling and touch-friendly button sizes for mobile

## User Preferences

Preferred communication style: Simple, everyday language.
UI Preferences: Tailwind CSS with simplified layout, Gmail-style email formatting, smooth transitions, Google Ads placement in sidebars and footer, fully responsive design for all devices.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with support for multiple databases
  - Default: SQLite for development
  - Production: Configurable via DATABASE_URL environment variable
- **Session Management**: Flask sessions with secure secret key configuration
- **Rate Limiting**: Flask-Limiter for API protection (200 requests/day, 50/hour default)
- **Proxy Support**: ProxyFix middleware for deployment behind reverse proxies

### Frontend Architecture
- **Template Engine**: Jinja2 (Flask's default)
- **Styling**: Tailwind CSS with custom utility classes and Gmail-inspired design
- **JavaScript**: Vanilla JS for clipboard functionality and UI interactions
- **Icons**: Font Awesome for consistent iconography
- **Layout**: Three-column layout with Google Ads placement in left/right sidebars and footer

### Email System
- **SMTP Integration**: Flask-Mail for outgoing email capabilities
- **IMAP Integration**: Native Python imaplib for incoming email monitoring
- **Email Processing**: Custom EmailService class for fetching and parsing emails
- **Spam Detection**: Keyword-based filtering with configurable patterns

### SMS System
- **Provider**: Twilio integration for SMS services
- **Features**: Send/receive SMS, number provisioning, OTP handling
- **Fallback**: Mock implementation when Twilio credentials unavailable

## Key Components

### Database Models
1. **TempEmail**: Manages temporary email addresses
   - Auto-generated UUID-based addresses
   - Session-based ownership
   - Configurable expiration (default 24 hours)
   - Active/inactive status tracking

2. **EmailMessage**: Stores received emails
   - Links to TempEmail via foreign key
   - Spam detection flags
   - Read/unread status
   - Full email content storage

3. **TempPhone**: Manages temporary phone numbers
   - Session-based ownership
   - Expiration management
   - Integration with SMS providers

### Core Services
1. **EmailService**: Handles email operations
   - IMAP connection management
   - Email fetching and parsing
   - Spam detection integration
   - Database storage of messages

2. **SMSService**: Manages SMS operations
   - Twilio client integration
   - Message sending/receiving
   - Number provisioning
   - Error handling and logging

### Utility Functions
- **Spam Detection**: Keyword and pattern-based filtering
- **Random Generation**: Secure string generation for addresses
- **Phone Number Generation**: Mock/Twilio integration for number creation

## Data Flow

### Email Generation Flow
1. User requests temporary email via POST to `/generate-email`
2. System checks user's active email limit (max 5 per session)
3. Creates new TempEmail record with UUID-based address
4. Returns email address to user interface
5. Background service monitors IMAP for incoming messages
6. New emails are processed, spam-filtered, and stored in database

### Phone Generation Flow
1. User requests temporary phone via POST to `/generate-phone`
2. System interfaces with Twilio to provision number
3. Creates TempPhone record linked to user session
4. Returns phone number for immediate use
5. SMS messages received via Twilio webhooks (when configured)

### Message Retrieval Flow
1. User accesses inbox via `/email-inbox/<id>` or `/sms-inbox/<id>`
2. System queries messages for specific temporary service
3. Messages displayed with spam filtering options
4. Real-time refresh capabilities via JavaScript

## External Dependencies

### Required Services
- **SMTP Server**: For sending emails (configurable via environment)
- **IMAP Server**: For receiving emails (typically same as SMTP)
- **Twilio**: For SMS/phone number services (optional but recommended)

### Environment Configuration
- Database connection (DATABASE_URL)
- Mail server settings (MAIL_SERVER, MAIL_PORT, etc.)
- Twilio credentials (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
- Session security (SESSION_SECRET)

### Frontend Dependencies
- Bootstrap 5 CSS framework (CDN)
- Font Awesome icons (CDN)
- Modern browser with clipboard API support

## Deployment Strategy

### Development Setup
- SQLite database for local development
- Debug mode enabled via main.py
- Environment variables with sensible defaults
- Mock services when external providers unavailable

### Production Considerations
- PostgreSQL or MySQL recommended for production database
- Secure session secret key mandatory
- Rate limiting configured for production traffic
- Proxy configuration for load balancer deployment
- SSL/TLS required for clipboard functionality
- Background email fetching service (cron job or worker process)
- Twilio webhook configuration for SMS delivery

### Security Features
- Rate limiting on all endpoints
- Session-based isolation between users
- No persistent user data storage
- Automatic service expiration
- Spam filtering for email content
- Environment-based configuration for sensitive data

### Scalability Notes
- Database connection pooling configured
- Stateless design enables horizontal scaling
- Background services can be distributed
- CDN integration for static assets
- Configurable service limits per user session