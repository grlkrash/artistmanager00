"""Entry point for running the bot as a module."""
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artist_manager_agent.main import main

if __name__ == "__main__":
    main() 