#!/usr/bin/env python3
"""
Setup script for Gemini Flow Telegram Bot
"""

import os
import secrets
import base64

def generate_encryption_key():
    """Generate a secure encryption key for Fernet"""
    key = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(key).decode()

def setup_environment():
    """Setup environment file"""
    if os.path.exists('.env'):
        print("✅ .env file already exists")
        return
    
    print("🔧 Setting up environment...")
    
    # Generate encryption key
    encryption_key = generate_encryption_key()
    
    # Create .env file
    env_content = f"""# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/gemini_flow

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Security
ENCRYPTION_KEY={encryption_key}

# Admin Configuration (comma-separated Telegram IDs)
ADMIN_IDS=123456789
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Environment file created")
    print("📝 Please edit .env file and set your BOT_TOKEN and ADMIN_IDS")

def create_directories():
    """Create necessary directories"""
    directories = [
        'logs',
        'handlers',
        'services', 
        'utils',
        'database'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Created directory: {directory}")

def main():
    """Main setup function"""
    print("🚀 Setting up Gemini Flow Telegram Bot...")
    
    create_directories()
    setup_environment()
    
    print("\n✅ Setup completed!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your bot token and admin IDs")
    print("2. Run: docker-compose up -d")
    print("3. Your bot will be ready!")
    
    print("\n🔗 Get your bot token: https://t.me/BotFather")
    print("🔗 Get Gemini API key: https://aistudio.google.com/app/apikey")

if __name__ == "__main__":
    main()