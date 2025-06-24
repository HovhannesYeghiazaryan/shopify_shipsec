# FastAPI + ngrok Production Setup

This guide will help you run your FastAPI application with ngrok for remote access on macOS.

## Prerequisites

1. **Install ngrok**:
   ```bash
   brew install ngrok
   ```

2. **Install PostgreSQL** (if not already installed):
   ```bash
   brew install postgresql@15
   brew services start postgresql@15
   ```

3. **Set up database**:
   ```bash
   psql postgres
   CREATE USER shipsec_user WITH PASSWORD 'jk2qAGQq4w6e8rSGdf7234Akem26DFG4';
   CREATE DATABASE shipsec OWNER shipsec_user;
   GRANT ALL PRIVILEGES ON DATABASE shipsec TO shipsec_user;
   \q
   ```

4. **Set up Python environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

## Quick Start

### Option 1: Simple Setup (Recommended)
```bash
# Make scripts executable
chmod +x start_simple_ngrok.sh stop_services.sh

# Start the application with ngrok
./start_simple_ngrok.sh
```

### Option 2: Manual Setup
```bash
# Terminal 1: Start FastAPI
source venv/bin/activate
gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 2

# Terminal 2: Start ngrok
ngrok http 8000
```

## What You'll Get

After running the setup:

1. **FastAPI Application**: Running on `http://localhost:8000`
2. **ngrok Dashboard**: Available at `http://localhost:4040`
3. **Public URL**: Shown in the ngrok dashboard (e.g., `https://abc123.ngrok.io`)
4. **API Documentation**: Available at `{ngrok_url}/docs`
5. **Health Check**: Available at `{ngrok_url}/health`

## Testing Remote Access

1. **Health Check**:
   ```bash
   curl https://your-ngrok-url.ngrok.io/health
   ```

2. **API Documentation**:
   Open `https://your-ngrok-url.ngrok.io/docs` in your browser

3. **Test from another device**:
   Use the ngrok URL from any device with internet access

## Stopping Services

```bash
./stop_services.sh
```

Or manually:
```bash
pkill -f "gunicorn main:app"
pkill -f "ngrok http 8000"
```

## Logs

- **FastAPI logs**: `logs/access.log` and `logs/error.log`
- **ngrok logs**: `logs/ngrok.log`
- **Real-time ngrok logs**: Shown in the terminal when using `start_simple_ngrok.sh`

## Troubleshooting

### FastAPI won't start
1. Check if PostgreSQL is running: `brew services list | grep postgresql`
2. Verify database connection: `psql -U shipsec_user -d shipsec`
3. Check logs: `tail -f logs/error.log`

### ngrok won't start
1. Check if ngrok is installed: `which ngrok`
2. Verify port 8000 is free: `lsof -i :8000`
3. Check ngrok logs: `tail -f logs/ngrok.log`

### Can't access from remote
1. Check ngrok dashboard: `http://localhost:4040`
2. Verify the public URL is active
3. Test locally first: `curl http://localhost:8000/health`

## Security Notes

⚠️ **Important**: This setup is for development/testing. For production:

1. **Restrict CORS origins** in `main.py`
2. **Use environment variables** for sensitive data
3. **Enable ngrok authentication** for better security
4. **Consider using a custom domain** with ngrok

## Environment Variables

Create a `.env` file in your project root:
```env
DB_USER=shipsec_user
PASSWD=jk2qAGQq4w6e8rSGdf7234Akem26DFG4
DB_NAME=shipsec
HOST=localhost
PORT=5432
SHIPSEC_API_KEY=your_api_key
SHIPSEC_BASE_URL=your_base_url
VJD_BASE_URL=your_vjd_url
WEBHOOK_SECRET=your_webhook_secret
SHOPIFY_API_VERSION=2024-01
```

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

Your custom endpoints are available under their respective routers:
- `/customers/*` - Customer management
- `/shipsec/*` - ShipSec integration
- `/vjd/*` - VJD API integration
- `/webhook/*` - Webhook handlers 