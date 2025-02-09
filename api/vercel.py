from http.server import BaseHTTPRequestHandler
import os
import sys
import json
from artist_manager_agent.models import ArtistProfile
from artist_manager_agent.bot import ArtistManagerBot
from artist_manager_agent.log import logger, log_event

# Initialize bot as a global variable for reuse
bot = None

def init_bot():
    """Initialize the bot if not already initialized."""
    global bot
    if bot is None:
        try:
            # Check required environment variables
            required_vars = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
                return None

            # Initialize bot
            artist_profile = ArtistProfile(
                id="default",
                name="Artist",
                genre="",
                career_stage="emerging",
                goals=[],
                strengths=[],
                areas_for_improvement=[],
                achievements=[],
                social_media={},
                streaming_profiles={},
                brand_guidelines={}
            )
            
            bot = ArtistManagerBot(
                telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
                artist_profile=artist_profile,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                db_url=os.getenv("DATABASE_URL", "sqlite:///artist_manager.db")
            )
            
            # Log startup
            log_event("startup", {
                "config": {
                    "model": bot.agent.model,
                    "db_url": bot.agent.db_url,
                    "log_level": logger.level
                },
                "environment": "vercel"
            })
            
            return bot
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            return None
    return bot

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - health check."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "healthy",
            "bot_initialized": bot is not None
        }
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests - Telegram webhook."""
        try:
            # Initialize bot if needed
            if not init_bot():
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Bot initialization failed"}).encode())
                return
            
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data.decode())
            
            # Process update
            bot.process_update(update)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode()) 