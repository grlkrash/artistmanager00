import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from artist_manager_agent.music_services import (
    MusicServices,
    Track,
    Release,
    MasteringJob,
    ReleaseType,
    MasteringPreset,
    DistributionPlatform
)

@pytest.fixture
def mock_track():
    return Track(
        title="Test Track",
        artist="Test Artist",
        genre="Pop",
        release_date=datetime.now(),
        file_path=Path("/test/track.wav"),
        artwork_path=Path("/test/artwork.jpg")
    )

@pytest.fixture
def mock_release():
    return Release(
        title="Test Album",
        artist="Test Artist",
        type=ReleaseType.ALBUM,
        genre="Pop",
        release_date=datetime.now(),
        tracks=[mock_track()],
        artwork_path=Path("/test/artwork.jpg")
    )

@pytest.fixture
def music_services():
    with patch("aiohttp.ClientSession") as mock_session:
        service = MusicServices()
        service.session = mock_session
        return service

@pytest.mark.asyncio
async def test_create_release(music_services, mock_release):
    """Test creating a new release."""
    with patch.object(music_services.session, "post") as mock_post:
        mock_post.return_value.__aenter__.return_value.json.return_value = {
            "id": "test_release_id",
            "status": "created"
        }
        
        result = await music_services.create_release(mock_release)
        assert result["id"] == "test_release_id"
        assert result["status"] == "created"

@pytest.mark.asyncio
async def test_submit_for_mastering(music_services, mock_track):
    """Test submitting a track for AI mastering."""
    with patch.object(music_services.session, "post") as mock_post:
        mock_post.return_value.__aenter__.return_value.json.return_value = {
            "job_id": "test_job_id",
            "status": "processing"
        }
        
        result = await music_services.submit_for_mastering(
            track=mock_track,
            preset=MasteringPreset.BALANCED
        )
        assert result["job_id"] == "test_job_id"
        assert result["status"] == "processing"

@pytest.mark.asyncio
async def test_get_platform_stats(music_services):
    """Test getting platform-specific statistics."""
    with patch.object(music_services.session, "get") as mock_get:
        mock_get.return_value.__aenter__.return_value.json.return_value = {
            "streams": 1000,
            "listeners": 500,
            "saves": 100
        }
        
        result = await music_services.get_platform_stats(
            platform=DistributionPlatform.SPOTIFY,
            release_id="test_release"
        )
        assert result["streams"] == 1000
        assert result["listeners"] == 500
        assert result["saves"] == 100 