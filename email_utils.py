import re
import html
from html.parser import HTMLParser

class EmailHTMLParser(HTMLParser):
    """Custom HTML parser for email content that preserves links and formatting"""
    
    def __init__(self):
        super().__init__()
        self.output = []
        self.current_tag = None
        self.current_attrs = {}
        self.in_link = False
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == 'a' and 'href' in attrs_dict:
            self.in_link = True
            href = attrs_dict['href']
            # Ensure the URL is valid and safe
            if href.startswith(('http://', 'https://', 'mailto:')):
                self.output.append(f'<div class="email-link-section my-3">')
                self.output.append(f'<a href="{html.escape(href)}" target="_blank" rel="noopener noreferrer" class="email-link-button">')
        elif tag in ['p', 'div']:
            if not self.in_link:
                self.output.append('<div class="email-paragraph mb-3">')
        elif tag == 'br':
            self.output.append('<br>')
        elif tag in ['strong', 'b']:
            self.output.append('<strong>')
        elif tag in ['em', 'i']:
            self.output.append('<em>')
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.output.append(f'<{tag} class="email-heading font-bold mb-2">')
        
        self.current_tag = tag
        self.current_attrs = attrs_dict
        
    def handle_endtag(self, tag):
        if tag == 'a' and self.in_link:
            self.output.append('</a></div>')
            self.in_link = False
        elif tag in ['p', 'div'] and not self.in_link:
            self.output.append('</div>')
        elif tag in ['strong', 'b']:
            self.output.append('</strong>')
        elif tag in ['em', 'i']:
            self.output.append('</em>')
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.output.append(f'</{tag}>')
            
        self.current_tag = None
        
    def handle_data(self, data):
        # Clean and format the text data
        clean_data = data.strip()
        if clean_data:
            if self.in_link:
                # For links, create smart button text
                link_text = self.get_smart_link_text(clean_data, self.current_attrs.get('href', ''))
                self.output.append(link_text)
            else:
                # For regular text, escape HTML and preserve formatting
                self.output.append(html.escape(clean_data))
    
    def get_smart_link_text(self, original_text, href):
        """Generate smart link button text based on URL and content"""
        href_lower = href.lower() if href else ""
        text_lower = original_text.lower()
        
        # Smart button text based on URL patterns
        if any(keyword in href_lower for keyword in ['verify', 'verification']):
            return 'Verify Email'
        elif any(keyword in href_lower for keyword in ['confirm', 'confirmation']):
            return 'Confirm Account'
        elif any(keyword in href_lower for keyword in ['activate', 'activation']):
            return 'Activate Account'
        elif any(keyword in href_lower for keyword in ['reset', 'password']):
            return 'Reset Password'
        elif any(keyword in href_lower for keyword in ['download']):
            return 'Download'
        elif any(keyword in href_lower for keyword in ['login', 'signin']):
            return 'Login'
        elif any(keyword in href_lower for keyword in ['signup', 'register']):
            return 'Sign Up'
        elif any(keyword in href_lower for keyword in ['unsubscribe']):
            return 'Unsubscribe'
        elif any(keyword in text_lower for keyword in ['verify', 'verification']):
            return 'Verify Email'
        elif any(keyword in text_lower for keyword in ['confirm']):
            return 'Confirm Account'
        elif len(original_text) > 50:  # Long URLs
            return 'Open Link'
        else:
            return original_text if len(original_text) < 30 else 'Open Link'
    
    def get_output(self):
        return ''.join(self.output)

def process_email_content(html_content, text_content, body_content):
    """
    Process email content to create properly formatted HTML with working links
    
    Args:
        html_content: HTML version of email
        text_content: Plain text version of email  
        body_content: Fallback body content
        
    Returns:
        Formatted HTML string with preserved links and styling
    """
    # Determine the best content to use
    content = ''
    if html_content and html_content.strip():
        content = html_content.strip()
        content_type = 'html'
    elif text_content and text_content.strip():
        content = text_content.strip()
        content_type = 'text'
    elif body_content and body_content.strip():
        content = body_content.strip()
        content_type = 'text'
    else:
        return '<div class="text-gray-500 italic text-center py-8"><p>No message content available</p></div>'
    
    # Clean up JSON artifacts and escape characters
    content = clean_json_artifacts(content)
    
    if content_type == 'html':
        # Process HTML content
        return process_html_content(content)
    else:
        # Process plain text content
        return process_text_content(content)

def clean_json_artifacts(content):
    """Remove JSON formatting artifacts from content"""
    # Remove JSON array brackets and quotes
    content = re.sub(r'^\["?|"?\]$', '', content)
    content = re.sub(r'^"?|"?$', '', content)
    
    # Fix escaped characters
    content = content.replace('\\r\\n', '\n')
    content = content.replace('\\n', '\n')
    content = content.replace('\r\n', '\n')
    content = content.replace('\\t', '\t')
    content = content.replace('\\"', '"')
    content = content.replace("\\'", "'")
    
    return content.strip()

def process_html_content(html_content):
    """Process HTML email content preserving links and formatting"""
    try:
        parser = EmailHTMLParser()
        parser.feed(html_content)
        processed_content = parser.get_output()
        
        # If parsing resulted in empty content, fall back to text processing
        if not processed_content.strip():
            return process_text_content(html_content)
            
        return f'<div class="gmail-email-content">{processed_content}</div>'
        
    except Exception as e:
        # If HTML parsing fails, process as text
        return process_text_content(html_content)

def process_text_content(text_content):
    """Process plain text email content, converting URLs to clickable links"""
    lines = text_content.split('\n')
    processed_lines = []
    
    # URL regex pattern
    url_pattern = re.compile(
        r'https?://[^\s<>"\']{2,}|www\.[^\s<>"\']{2,}',
        re.IGNORECASE
    )
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if line contains URLs
        urls = url_pattern.findall(line)
        
        if urls:
            # Process each URL in the line
            processed_line = line
            for url in urls:
                # Ensure URL has protocol
                clean_url = url if url.startswith(('http://', 'https://')) else f'http://{url}'
                
                # Create button for the URL
                button_text = get_url_button_text(clean_url)
                link_html = f'<div class="email-link-section my-3"><a href="{html.escape(clean_url)}" target="_blank" rel="noopener noreferrer" class="email-link-button">{button_text}</a></div>'
                
                # Replace URL in text with the button
                processed_line = processed_line.replace(url, link_html)
            
            processed_lines.append(processed_line)
        else:
            # Regular text line
            if line:
                processed_lines.append(f'<div class="email-paragraph mb-3">{html.escape(line)}</div>')
    
    return f'<div class="gmail-email-content">{"".join(processed_lines)}</div>'

def get_url_button_text(url):
    """Generate appropriate button text for a URL"""
    url_lower = url.lower()
    
    if any(keyword in url_lower for keyword in ['verify', 'verification']):
        return 'Verify Email'
    elif any(keyword in url_lower for keyword in ['confirm', 'confirmation']):
        return 'Confirm Account'
    elif any(keyword in url_lower for keyword in ['activate', 'activation']):
        return 'Activate Account'
    elif any(keyword in url_lower for keyword in ['reset', 'password']):
        return 'Reset Password'
    elif any(keyword in url_lower for keyword in ['download']):
        return 'Download'
    elif any(keyword in url_lower for keyword in ['login', 'signin']):
        return 'Login'
    elif any(keyword in url_lower for keyword in ['signup', 'register']):
        return 'Sign Up'
    elif any(keyword in url_lower for keyword in ['unsubscribe']):
        return 'Unsubscribe'
    else:
        return 'Open Link'

def extract_verification_codes(content):
    """Extract and highlight verification codes from email content"""
    # Common patterns for verification codes
    patterns = [
        r'\b[A-Z0-9]{4,8}\b',  # Alphanumeric codes
        r'\b\d{4,8}\b',        # Numeric codes
        r'\b[A-Z]{4,8}\b',     # Letter codes
    ]
    
    highlighted_content = content
    for pattern in patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            code = match.group()
            # Only highlight if it looks like a verification code (not too common words)
            if not code.lower() in ['your', 'email', 'code', 'here', 'link', 'click', 'this', 'that']:
                highlighted_code = f'<span class="verification-code">{code}</span>'
                highlighted_content = highlighted_content.replace(code, highlighted_code, 1)
    
    return highlighted_content