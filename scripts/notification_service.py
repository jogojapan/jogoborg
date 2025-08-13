#!/usr/bin/env python3
import os
import sys
import smtplib
import ssl
import json
import requests
import logging
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Add project root to Python path
sys.path.append('/app')

from scripts.init_gpg import decrypt_data

class NotificationService:
    def __init__(self):
        self.db_path = '/config/jogoborg.db'
        self.logger = logging.getLogger('NotificationService')

    def send_notification(self, subject, message, is_error=False):
        """Send notification via configured methods (SMTP and/or webhook)."""
        try:
            # Load notification settings
            settings = self._load_notification_settings()
            
            if not settings:
                self.logger.info("No notification settings configured, skipping notification")
                return
            
            # Send SMTP notification if configured
            if settings.get('smtp_config'):
                try:
                    self._send_smtp_notification(
                        settings['smtp_config'], 
                        subject, 
                        message, 
                        is_error
                    )
                except Exception as e:
                    self.logger.error(f"SMTP notification failed: {e}")
            
            # Send webhook notification if configured
            if settings.get('webhook_config'):
                try:
                    self._send_webhook_notification(
                        settings['webhook_config'], 
                        subject, 
                        message, 
                        is_error
                    )
                except Exception as e:
                    self.logger.error(f"Webhook notification failed: {e}")
                    
        except Exception as e:
            self.logger.error(f"Notification service error: {e}")

    def _load_notification_settings(self):
        """Load notification settings from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT smtp_config, webhook_config 
            FROM notification_settings 
            WHERE id = 1
            ''')
            
            row = cursor.fetchone()
            if not row:
                return None
            
            smtp_config_encrypted, webhook_config_encrypted = row
            
            # Decrypt configurations
            smtp_config = None
            webhook_config = None
            
            if smtp_config_encrypted:
                smtp_config_json = decrypt_data(smtp_config_encrypted)
                if smtp_config_json:
                    smtp_config = json.loads(smtp_config_json)
            
            if webhook_config_encrypted:
                webhook_config_json = decrypt_data(webhook_config_encrypted)
                if webhook_config_json:
                    webhook_config = json.loads(webhook_config_json)
            
            return {
                'smtp_config': smtp_config,
                'webhook_config': webhook_config,
            }
            
        finally:
            conn.close()

    def _send_smtp_notification(self, smtp_config, subject, message, is_error):
        """Send email notification via SMTP."""
        if not smtp_config or not all(k in smtp_config for k in ['host', 'username', 'password', 'sender_email']):
            self.logger.warning("Incomplete SMTP configuration, skipping email notification")
            return
        
        host = smtp_config['host']
        username = smtp_config['username']
        password = smtp_config['password']
        sender_email = smtp_config['sender_email']
        recipient_email = smtp_config.get('recipient_email', sender_email)  # Default to sender if no recipient specified
        security = smtp_config.get('security', 'STARTTLS').upper()
        
        # Set default port based on security type if not specified
        if 'port' in smtp_config:
            port = smtp_config['port']
        else:
            port = 465 if security == 'SSL' else 587
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"[Jogoborg] {subject}"
        
        # Add timestamp and hostname to message
        hostname = os.uname().nodename
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        full_message = f"""Jogoborg Backup Notification
        
Time: {timestamp}
Host: {hostname}
Status: {'ERROR' if is_error else 'SUCCESS'}

{message}

---
This notification was sent by Jogoborg backup system.
"""
        
        msg.attach(MIMEText(full_message, 'plain'))
        
        try:
            # Create SMTP connection based on security type
            if security == 'SSL':
                # SSL/TLS connection (usually port 465)
                context = ssl.create_default_context()
                self.logger.debug(f"Connecting to {host}:{port} using SSL/TLS")
                server = smtplib.SMTP_SSL(host, port, context=context, timeout=30)
            else:
                # Plain connection or STARTTLS (usually port 587 or 25)
                self.logger.debug(f"Connecting to {host}:{port} using plain connection")
                server = smtplib.SMTP(host, port, timeout=30)
                
                if security == 'STARTTLS':
                    self.logger.debug("Starting STARTTLS encryption")
                    context = ssl.create_default_context()
                    server.starttls(context=context)
            
            # Authenticate and send
            self.logger.debug("Authenticating with SMTP server")
            server.login(username, password)
            
            self.logger.debug("Sending email message")
            server.send_message(msg)
            server.quit()
            
            self.logger.info("SMTP notification sent successfully")
            
        except Exception as e:
            self.logger.error(f"SMTP send failed: {e}")
            self.logger.error(f"SMTP config: host={host}, port={port}, security={security}")
            raise

    def _send_webhook_notification(self, webhook_config, subject, message, is_error):
        """Send webhook notification (Gotify format)."""
        if not webhook_config or not webhook_config.get('url'):
            self.logger.warning("Incomplete webhook configuration, skipping webhook notification")
            return
        
        url = webhook_config['url']
        token = webhook_config.get('token', '')
        success_priority = webhook_config.get('success_priority', 'normal')
        error_priority = webhook_config.get('error_priority', 'high')
        
        # Determine priority
        priority = error_priority if is_error else success_priority
        priority_map = {
            'low': 1,
            'normal': 5,
            'high': 10
        }
        priority_num = priority_map.get(priority, 5)
        
        # Create payload
        hostname = os.uname().nodename
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        payload = {
            'title': f"[Jogoborg] {subject}",
            'message': f"{message}\n\nHost: {hostname}\nTime: {timestamp}",
            'priority': priority_num,
            'extras': {
                'client::display': {
                    'contentType': 'text/markdown'
                }
            }
        }
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Add token to URL or headers depending on Gotify setup
        if token:
            if '?' in url:
                url += f"&token={token}"
            else:
                url += f"?token={token}"
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            response.raise_for_status()
            self.logger.info("Webhook notification sent successfully")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Webhook send failed: {e}")
            raise

    def test_smtp_configuration(self, smtp_config):
        """Test SMTP configuration by sending a test email."""
        try:
            self._send_smtp_notification(
                smtp_config,
                "SMTP Test",
                "This is a test message from Jogoborg backup system. If you receive this, your SMTP configuration is working correctly.",
                False
            )
            return True, "SMTP test successful"
            
        except Exception as e:
            return False, f"SMTP test failed: {str(e)}"

    def test_webhook_configuration(self, webhook_config):
        """Test webhook configuration by sending a test message."""
        try:
            self._send_webhook_notification(
                webhook_config,
                "Webhook Test",
                "This is a test message from Jogoborg backup system. If you receive this, your webhook configuration is working correctly.",
                False
            )
            return True, "Webhook test successful"
            
        except Exception as e:
            return False, f"Webhook test failed: {str(e)}"

    def save_notification_settings(self, smtp_config=None, webhook_config=None):
        """Save notification settings to database with encryption."""
        from scripts.init_gpg import encrypt_data
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Load existing settings to preserve unchanged passwords
            existing_settings = self._load_notification_settings()
            
            # Encrypt configurations
            smtp_config_encrypted = None
            webhook_config_encrypted = None
            
            if smtp_config:
                # Preserve existing password if not changed (indicated by ***)
                if (smtp_config.get('password') == '***' and 
                    existing_settings and existing_settings.get('smtp_config')):
                    smtp_config = smtp_config.copy()
                    smtp_config['password'] = existing_settings['smtp_config'].get('password', '')
                
                smtp_config_json = json.dumps(smtp_config)
                smtp_config_encrypted = encrypt_data(smtp_config_json)
                if smtp_config_encrypted is None:
                    raise Exception("Failed to encrypt SMTP configuration")
            
            if webhook_config:
                # Preserve existing token if not changed (indicated by ***)
                if (webhook_config.get('token') == '***' and 
                    existing_settings and existing_settings.get('webhook_config')):
                    webhook_config = webhook_config.copy()
                    webhook_config['token'] = existing_settings['webhook_config'].get('token', '')
                
                webhook_config_json = json.dumps(webhook_config)
                webhook_config_encrypted = encrypt_data(webhook_config_json)
                if webhook_config_encrypted is None:
                    raise Exception("Failed to encrypt webhook configuration")
            
            # Update database
            cursor.execute('''
            UPDATE notification_settings 
            SET smtp_config = ?, webhook_config = ?
            WHERE id = 1
            ''', (smtp_config_encrypted, webhook_config_encrypted))
            
            conn.commit()
            self.logger.info("Notification settings saved successfully")
            
        finally:
            conn.close()

    def get_notification_settings(self, mask_sensitive=True):
        """Get notification settings. If mask_sensitive=False, returns full settings for editing."""
        settings = self._load_notification_settings()
        
        if not settings:
            return {'smtp_config': None, 'webhook_config': None}
        
        if not mask_sensitive:
            # Return full settings for editing
            return settings
        
        # Remove sensitive information for display
        display_settings = {}
        
        if settings.get('smtp_config'):
            smtp_config = settings['smtp_config'].copy()
            if 'password' in smtp_config:
                smtp_config['password'] = '***' if smtp_config['password'] else ''
            display_settings['smtp_config'] = smtp_config
        else:
            display_settings['smtp_config'] = None
        
        if settings.get('webhook_config'):
            webhook_config = settings['webhook_config'].copy()
            if 'token' in webhook_config:
                webhook_config['token'] = '***' if webhook_config['token'] else ''
            display_settings['webhook_config'] = webhook_config
        else:
            display_settings['webhook_config'] = None
        
        return display_settings

if __name__ == '__main__':
    # This can be used for testing notification functionality
    notification_service = NotificationService()
    
    # Example test
    # notification_service.send_notification(
    #     "Test Notification",
    #     "This is a test notification from Jogoborg",
    #     False
    # )