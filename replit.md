# Overview

This is a Telegram bot application for text-to-speech (TTS) services with voice cloning capabilities. The bot allows users to convert text to speech using various AI voices, create custom voice clones, purchase credits through multiple payment methods, and manage user accounts with a referral system. The application is built using Python with the pyTelegramBotAPI framework and includes multi-language support.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **Framework**: pyTelegramBotAPI (telebot) for Telegram bot interactions
- **Architecture Pattern**: Modular design with separate handlers for different features
- **Message Handling**: Event-driven callback and message handlers with state management

## Database Design
- **Database**: SQLite with direct SQL queries for simplicity
- **Schema**: User management, credit system, purchases, messages, voice clones, and key-value state storage
- **Tables**: 
  - `users` - User profiles with referral tracking
  - `kv_state` - User state management for conversation flows
  - `settings` - Bot configuration storage
  - `purchases` - Payment transaction records
  - `messages` - Message logging
  - `user_voices` - Custom voice clone storage

## Modular Structure
- **Admin Module**: User management, credit operations, broadcasting, statistics
- **TTS Module**: Text-to-speech conversion with multiple voice options
- **Clone Module**: Voice cloning functionality using ElevenLabs API
- **Credit Module**: Payment processing (Telegram Stars and manual verification)
- **Profile Module**: User account information display
- **Invite Module**: Referral system with bonus rewards
- **Language Module**: Multi-language support (8 languages)
- **Home Module**: Main navigation and welcome functionality

## State Management
- **User States**: Conversation flow tracking using database storage
- **Session Management**: Temporary data storage for multi-step operations
- **Force Subscription**: Optional channel membership verification

## Payment Architecture
- **Telegram Stars**: Native Telegram payment integration
- **Manual Verification**: Card-to-card transfers with receipt verification
- **Credit System**: Character-based pricing (1 character = 1 credit)

## Internationalization
- **Language Support**: 8 languages (Persian, English, Arabic, Turkish, Russian, Spanish, German, French)
- **Dynamic Text**: Centralized translation system with fallback to English

# External Dependencies

## AI Services
- **ElevenLabs API**: Primary TTS service and voice cloning provider
- **Voice Models**: eleven_v3 model for consistent audio quality

## Telegram Platform
- **Bot API**: Core messaging and callback functionality
- **Telegram Stars**: Native payment processing
- **File Handling**: Audio file upload/download for voice cloning

## Development Dependencies
- **pyTelegramBotAPI**: Telegram bot framework
- **requests**: HTTP client for external API calls
- **python-dotenv**: Environment variable management
- **sqlite3**: Built-in database functionality

## Configuration Management
- **Environment Variables**: BOT_TOKEN, ELEVEN_API_KEY, BOT_OWNER_ID, CARD_NUMBER
- **Settings Storage**: Database-backed configuration for runtime adjustments
- **Debug Mode**: Development logging and error reporting