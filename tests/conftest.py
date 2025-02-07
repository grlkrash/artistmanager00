import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

# Load test environment variables
load_dotenv(".env.test")

@pytest.fixture(autouse=True)
def test_env():
    """Set up test environment variables."""
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
    os.environ["OPENAI_API_KEY"] = "test_key"
    os.environ["SUPABASE_URL"] = "test_url"
    os.environ["SUPABASE_KEY"] = "test_key"
    os.environ["AI_MASTERING_KEY"] = "test_key"

@pytest.fixture
def test_data_dir():
    """Get the test data directory."""
    return Path(__file__).parent / "data"

@pytest.fixture(autouse=True)
def mock_aiohttp_session(monkeypatch):
    """Mock aiohttp ClientSession to prevent actual HTTP requests."""
    import aiohttp
    
    class MockClientSession:
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
        async def close(self):
            pass
    
    monkeypatch.setattr(aiohttp, "ClientSession", MockClientSession) 