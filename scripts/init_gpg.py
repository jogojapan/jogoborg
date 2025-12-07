#!/usr/bin/env python3
import os
import subprocess
import sys
from cryptography.fernet import Fernet

def init_gpg_key():
    """Initialize GPG key for encrypting sensitive configuration data."""
    # Use environment variable for config directory, default to /config for Docker
    config_dir = os.environ.get('JOGOBORG_CONFIG_DIR', '/config')
    gpg_key_file = os.path.join(config_dir, 'jogoborg.gpg')
    
    # Ensure config directory exists
    os.makedirs(config_dir, exist_ok=True)
    
    # Check if GPG key already exists
    if os.path.exists(gpg_key_file):
        print("GPG key already exists.")
        return
    
    # Get passphrase from environment variable
    passphrase = os.environ.get('JOGOBORG_GPG_PASSPHRASE', os.environ.get('GPG_PASSPHRASE', 'changeme'))
    
    if passphrase == 'changeme':
        print("WARNING: Using default GPG passphrase. Set GPG_PASSPHRASE environment variable for security.")
    
    # Generate a symmetric key using Fernet (simpler than GPG for this use case)
    key = Fernet.generate_key()
    
    # Encrypt the key with the passphrase using a simple XOR method
    # In production, you'd want to use proper key derivation (like PBKDF2)
    passphrase_bytes = passphrase.encode('utf-8')
    encrypted_key = bytes(a ^ b for a, b in zip(key, passphrase_bytes * (len(key) // len(passphrase_bytes) + 1)))
    
    # Save the encrypted key to file
    with open(gpg_key_file, 'wb') as f:
        f.write(encrypted_key)
    
    # Set secure permissions
    os.chmod(gpg_key_file, 0o600)
    
    print("GPG key initialized successfully.")

def get_encryption_key():
    """Retrieve and decrypt the encryption key."""
    # Use environment variable for config directory, default to /config for Docker
    config_dir = os.environ.get('JOGOBORG_CONFIG_DIR', '/config')
    gpg_key_file = os.path.join(config_dir, 'jogoborg.gpg')
    
    if not os.path.exists(gpg_key_file):
        print("ERROR: GPG key file not found. Run init_gpg.py first.")
        return None
    
    passphrase = os.environ.get('JOGOBORG_GPG_PASSPHRASE', os.environ.get('GPG_PASSPHRASE', 'changeme'))
    passphrase_bytes = passphrase.encode('utf-8')
    
    try:
        with open(gpg_key_file, 'rb') as f:
            encrypted_key = f.read()
        
        # Decrypt the key
        key = bytes(a ^ b for a, b in zip(encrypted_key, passphrase_bytes * (len(encrypted_key) // len(passphrase_bytes) + 1)))
        
        return key
    except Exception as e:
        print(f"ERROR: Failed to decrypt GPG key: {e}")
        return None

def encrypt_data(data):
    """Encrypt data using the stored key."""
    key = get_encryption_key()
    if key is None:
        return None
    
    try:
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data.encode('utf-8'))
        return encrypted_data.decode('utf-8')
    except Exception as e:
        print(f"ERROR: Failed to encrypt data: {e}")
        return None

def decrypt_data(encrypted_data):
    """Decrypt data using the stored key."""
    key = get_encryption_key()
    if key is None:
        return None
    
    try:
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data.encode('utf-8'))
        return decrypted_data.decode('utf-8')
    except Exception as e:
        print(f"ERROR: Failed to decrypt data: {e}")
        return None

if __name__ == '__main__':
    init_gpg_key()