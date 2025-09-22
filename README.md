# Matka Betting Backend

Real-time Matka betting application backend built with Flask.

## Features

- 🔐 JWT Authentication (Login/Register)
- 🎲 8 Real-time Matka Markets
- 📊 Live Player Statistics
- ⏰ Real-time Market Status
- 🎯 Live Results & Data
- 🌐 CORS Enabled for Web
- 🚀 Vercel Serverless Ready

## API Endpoints

- `POST /api/login` - User login
- `POST /api/register` - User registration
- `GET /api/matka/markets` - Real-time market data
- `GET /api/matka/results` - Today's results
- `GET /api/matka/live-data` - Live statistics
- `GET /api/dashboard` - User dashboard

## Default Users

- Username: `test`, Password: `test123`
- Username: `admin`, Password: `admin123`

## Deploy to Vercel

1. Connect this repository to Vercel
2. Set environment variables if needed
3. Deploy automatically

## Local Development

```bash
python api/app.py
```

Server runs on `http://127.0.0.1:5000`