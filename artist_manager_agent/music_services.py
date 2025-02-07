from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel

class DistributionPlatform(str, Enum):
    """Supported music distribution platforms."""
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    AMAZON_MUSIC = "amazon_music"
    YOUTUBE_MUSIC = "youtube_music"
    DEEZER = "deezer"
    TIDAL = "tidal"
    PANDORA = "pandora"
    SOUNDCLOUD = "soundcloud"

class ReleaseType(str, Enum):
    """Types of music releases."""
    SINGLE = "single"
    EP = "ep"
    ALBUM = "album"
    REMIX = "remix"

class MasteringPreset(str, Enum):
    """AI mastering presets."""
    BALANCED = "balanced"
    WARM = "warm"
    BRIGHT = "bright"
    AGGRESSIVE = "aggressive"
    BASS_HEAVY = "bass_heavy"
    VOCAL_FOCUS = "vocal_focus"

class Track(BaseModel):
    """Track metadata and file information."""
    title: str
    artist: str
    featuring: Optional[str] = None
    genre: str
    subgenre: Optional[str] = None
    isrc: Optional[str] = None
    composer: Optional[str] = None
    producer: Optional[str] = None
    lyrics: Optional[str] = None
    explicit: bool = False
    language: str = "en"
    release_date: datetime
    file_path: Path
    duration: Optional[float] = None
    artwork_path: Optional[Path] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class Release(BaseModel):
    """Release package information."""
    title: str
    artist: str
    type: ReleaseType
    genre: str
    subgenre: Optional[str] = None
    release_date: datetime
    upc: Optional[str] = None
    copyright_info: Optional[str] = None
    tracks: List[Track]
    artwork_path: Path
    description: Optional[str] = None
    territories: List[str] = ["worldwide"]
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class MasteringJob(BaseModel):
    """AI mastering job information."""
    track: Track
    preset: MasteringPreset
    reference_track: Optional[Path] = None
    target_loudness: Optional[float] = None  # in LUFS
    status: str = "pending"
    result_path: Optional[Path] = None
    created_at: datetime = datetime.now()
    completed_at: Optional[datetime] = None

class MusicServices:
    """Music services integration."""
    
    def __init__(self):
        self.tracks: Dict[str, Track] = {}
        self.releases: Dict[str, Release] = {}
        self.mastering_jobs: Dict[str, MasteringJob] = {}

    async def create_release(self, release_id: str, title: str, artist_id: str, tracks: List[Track]) -> Release:
        if release_id in self.releases:
            raise ValueError(f"Release with ID {release_id} already exists")
        
        release = Release(
            release_id=release_id,
            title=title,
            artist_id=artist_id,
            tracks=tracks
        )
        self.releases[release_id] = release
        return release

    async def submit_for_mastering(self, track_id: str) -> Dict[str, str]:
        if track_id not in self.tracks:
            raise ValueError(f"Track with ID {track_id} not found")
        
        # Simulate submitting track for AI mastering
        return {
            "job_id": f"mastering_{track_id}",
            "status": "processing"
        }

    async def get_platform_stats(self, release_id: str) -> Dict[str, int]:
        if release_id not in self.releases:
            raise ValueError(f"Release with ID {release_id} not found")
        
        # Simulate getting streaming stats
        return {
            "streams": 0,
            "unique_listeners": 0,
            "saves": 0
        } 