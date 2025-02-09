"""Deployment script with monitoring."""
import os
import sys
import asyncio
import logging
from datetime import datetime
import signal
from typing import Optional
import json
import psutil
from dotenv import load_dotenv

from artist_manager_agent.agent import ArtistManagerAgent
from artist_manager_agent.models import ArtistProfile
from artist_manager_agent.bot import ArtistManagerBot
from artist_manager_agent.log import logger, log_event

# Load environment variables
load_dotenv()

class ProcessMonitor:
    """Monitor process health and resources."""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.process = psutil.Process()
        self.start_time = datetime.now()
        
    async def monitor(self):
        """Monitor process metrics."""
        while True:
            try:
                # Collect metrics
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                
                # Log metrics
                log_event("process_metrics", {
                    "cpu_percent": cpu_percent,
                    "memory_rss": memory_info.rss,
                    "memory_vms": memory_info.vms,
                    "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
                })
                
                # Check thresholds
                if cpu_percent > 80:
                    logger.warning(f"High CPU usage: {cpu_percent}%")
                if memory_info.rss > 1024 * 1024 * 1024:  # 1GB
                    logger.warning("High memory usage")
                    
            except Exception as e:
                logger.error(f"Error in process monitoring: {str(e)}")
                
            await asyncio.sleep(self.check_interval)

async def shutdown(signal, loop, bot: Optional[ArtistManagerBot] = None):
    """Graceful shutdown."""
    logger.info(f"Received exit signal {signal.name}...")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    if bot:
        # Stop the bot gracefully
        await bot.stop()
    
    [task.cancel() for task in tasks]
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

def main():
    """Main deployment function."""
    # Check required environment variables
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Load configuration
    config = {
        "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        "db_url": os.getenv("DATABASE_URL", "sqlite:///artist_manager.db"),
        "log_level": os.getenv("LOG_LEVEL", "INFO")
    }
    
    # Configure logging level
    logger.setLevel(config["log_level"])
    
    # Create event loop
    loop = asyncio.get_event_loop()
    
    try:
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
            token=config["telegram_token"],
            artist_profile=artist_profile,
            openai_api_key=config["openai_api_key"],
            model=config["model"],
            db_url=config["db_url"]
        )
        
        # Setup process monitoring
        monitor = ProcessMonitor()
        
        # Register signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(shutdown(s, loop, bot))
            )
        
        # Start bot and monitoring
        loop.create_task(monitor.monitor())
        loop.create_task(bot.run())
        
        # Log startup
        log_event("startup", {
            "config": {k: v for k, v in config.items() if k != "openai_api_key"},
            "pid": os.getpid(),
            "python_version": sys.version
        })
        
        # Run forever
        loop.run_forever()
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
        sys.exit(1)
    finally:
        loop.close()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    main() 