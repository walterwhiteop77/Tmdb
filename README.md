# Deployment Guide

This guide will help you deploy the IMDb-TMDB Telegram Bot to Render.com (or other platforms).

## Prerequisites

1. **Telegram Bot Token**
   - Create a bot with [@BotFather](https://t.me/botfather)
   - Get your bot token
   - Get your Telegram User ID (use [@userinfobot](https://t.me/userinfobot))

2. **TMDB API Key**
   - Sign up at [TMDB](https://www.themoviedb.org/)
   - Go to Settings > API
   - Create an API key (v3)

3. **MongoDB Database**
   - Sign up for [MongoDB Atlas](https://www.mongodb.com/atlas) (free tier available)
   - Create a cluster and get connection string
   - Or use any MongoDB hosting service

## Deployment Steps

### Option 1: Deploy to Render (Recommended)

1. **Fork/Clone Repository**
   ```bash
   git clone https://github.com/yourusername/imdb-tmdb-bot.git
   cd imdb-tmdb-bot
   ```

2. **Connect to Render**
   - Go to [Render.com](https://render.com)
   - Connect your GitHub account
   - Create a new Web Service
   - Connect your repository

3. **Configure Environment Variables**
   In Render dashboard, set these environment variables:
   ```
   BOT_TOKEN=your_bot_token_here
   TMDB_API_KEY=your_tmdb_api_key_here
   MONGODB_URL=your_mongodb_connection_string
   ADMIN_USER_ID=your_telegram_user_id
   WEBHOOK_URL=https://your-app-name.onrender.com
   PORT=10000
   ```

4. **Deploy**
   - Render will automatically build and deploy
   - Check logs for any errors

### Option 2: Deploy to Heroku

1. **Install Heroku CLI**
2. **Login and Create App**
   ```bash
   heroku login
   heroku create your-bot-
