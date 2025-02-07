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
        track_id="test_track_1",
        title="Test Track",
        artist_id="test_artist_1",
        duration=180,
        file_path="/test/track.wav",
        genre="Pop",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def mock_release():
    track = mock_track()
    return Release(
        release_id="test_release_1",
        title="Test Album",
        artist_id="test_artist_1",
        release_type=ReleaseType.ALBUM,
        tracks=[track],
        genre="Pop",
        release_date=datetime.now(),
        artwork_path="/test/artwork.jpg",
        created_at=datetime.now(),
        updated_at=datetime.now()
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
            "release_id": "test_release_id",
            "status": "created"
        }
        
        result = await music_services.create_release(mock_release)
        assert result["release_id"] == "test_release_id"
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
            release_id="test_release_1"
        )
        assert result["streams"] == 1000
        assert result["listeners"] == 500
        assert result["saves"] == 100 