"""Production deployment script with enhanced monitoring and error handling."""
import os
import sys
import asyncio
import logging
from datetime import datetime
import signal
import json
import psutil
from dotenv import load_dotenv
import structlog
from prometheus_client import start_http_server, Counter, Gauge

from artist_manager_agent.agent import ArtistManagerAgent
from artist_manager_agent.models import ArtistProfile
from artist_manager_agent.bot import ArtistManagerBot
from artist_manager_agent.log import logger, log_event, log_error

# Load environment variables
load_dotenv()

# Prometheus metrics
REQUEST_COUNT = Counter('bot_requests_total', 'Total bot requests')
ERROR_COUNT = Counter('bot_errors_total', 'Total errors')
ACTIVE_USERS = Gauge('bot_active_users', 'Number of active users')
CPU_USAGE = Gauge('bot_cpu_usage', 'CPU usage percentage')
MEMORY_USAGE = Gauge('bot_memory_usage', 'Memory usage in bytes')

class ProcessMonitor:
    """Enhanced process monitor with Prometheus metrics."""
    
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
                
                # Update Prometheus metrics
                CPU_USAGE.set(cpu_percent)
                MEMORY_USAGE.set(memory_info.rss)
                
                # Log metrics
                log_event("process_metrics", {
                    "cpu_percent": cpu_percent,
                    "memory_rss": memory_info.rss,
                    "memory_vms": memory_info.vms,
                    "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
                })
                
                # Check thresholds and alert if necessary
                if cpu_percent > 80:
                    log_error(Exception("High CPU usage"), {"cpu_percent": cpu_percent})
                if memory_info.rss > 1024 * 1024 * 1024:  # 1GB
                    log_error(Exception("High memory usage"), {"memory_rss": memory_info.rss})
                    
            except Exception as e:
                ERROR_COUNT.inc()
                log_error(e, {"monitor": "process_metrics"})
                
            await asyncio.sleep(self.check_interval)

async def shutdown(signal, loop, bot: ArtistManagerBot = None):
    """Enhanced graceful shutdown."""
    logger.info(f"Received exit signal {signal.name}...")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    if bot:
        try:
            # Stop the bot gracefully
            await bot.stop()
            logger.info("Bot stopped successfully")
        except Exception as e:
            log_error(e, {"shutdown": "bot_stop"})
    
    [task.cancel() for task in tasks]
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        log_error(e, {"shutdown": "task_cancellation"})
    
    loop.stop()
    logger.info("Shutdown complete")

def main():
    """Enhanced main deployment function."""
    # Check required environment variables
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY",
        "LOG_LEVEL",
        "DATABASE_URL"
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
        "db_url": os.getenv("DATABASE_URL"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "metrics_port": int(os.getenv("METRICS_PORT", "9090"))
    }
    
    # Configure logging
    logger.setLevel(config["log_level"])
    
    # Start Prometheus metrics server
    try:
        start_http_server(config["metrics_port"])
        logger.info(f"Metrics server started on port {config['metrics_port']}")
    except Exception as e:
        log_error(e, {"startup": "metrics_server"})
        sys.exit(1)
    
    # Create event loop
    loop = asyncio.get_event_loop()
    
    try:
        # Initialize bot with error handling
        try:
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
            logger.info("Bot initialized successfully")
            
        except Exception as e:
            log_error(e, {"startup": "bot_initialization"})
            sys.exit(1)
        
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
        log_error(e, {"main": "event_loop"})
        sys.exit(1)
    finally:
        loop.close()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    main() 