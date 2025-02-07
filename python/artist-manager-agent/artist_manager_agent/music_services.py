from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
import aiohttp
import os
from pathlib import Path

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
    """Integration with music distribution and AI mastering services."""
    
    def __init__(self):
        self.distribution_api_key = os.getenv("DISTRIBUTION_API_KEY")
        self.mastering_api_key = os.getenv("MASTERING_API_KEY")
        self.base_url_distribution = "https://api.distribution.example.com/v1"
        self.base_url_mastering = "https://api.mastering.example.com/v1"
        self.mastering_jobs: Dict[str, MasteringJob] = {}
        self.releases: Dict[str, Release] = {}
        
    async def create_release(self, release: Release) -> Dict:
        """Create a new release for distribution."""
        async with aiohttp.ClientSession() as session:
            # Validate release data
            validation_errors = await self._validate_release(release)
            if validation_errors:
                return {"error": "Validation failed", "details": validation_errors}
                
            # Upload artwork
            artwork_url = await self._upload_artwork(session, release.artwork_path)
            
            # Upload tracks
            track_urls = []
            for track in release.tracks:
                track_url = await self._upload_track(session, track.file_path)
                track_urls.append(track_url)
                
            # Create release package
            release_data = {
                "title": release.title,
                "artist": release.artist,
                "type": release.type,
                "genre": release.genre,
                "subgenre": release.subgenre,
                "release_date": release.release_date.isoformat(),
                "upc": release.upc,
                "copyright": release.copyright_info,
                "artwork_url": artwork_url,
                "territories": release.territories,
                "tracks": [
                    {
                        "title": track.title,
                        "artist": track.artist,
                        "featuring": track.featuring,
                        "genre": track.genre,
                        "isrc": track.isrc,
                        "composer": track.composer,
                        "producer": track.producer,
                        "explicit": track.explicit,
                        "language": track.language,
                        "audio_url": url
                    }
                    for track, url in zip(release.tracks, track_urls)
                ]
            }
            
            async with session.post(
                f"{self.base_url_distribution}/releases",
                json=release_data,
                headers={"Authorization": f"Bearer {self.distribution_api_key}"}
            ) as response:
                result = await response.json()
                
            if response.status == 201:
                self.releases[result["id"]] = release
                
            return result
            
    async def get_release_status(self, release_id: str) -> Dict:
        """Get the status of a release."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url_distribution}/releases/{release_id}",
                headers={"Authorization": f"Bearer {self.distribution_api_key}"}
            ) as response:
                return await response.json()
                
    async def submit_for_mastering(
        self,
        track: Track,
        preset: MasteringPreset,
        reference_track: Optional[Path] = None,
        target_loudness: Optional[float] = None
    ) -> Dict:
        """Submit a track for AI mastering."""
        async with aiohttp.ClientSession() as session:
            # Create mastering job
            job = MasteringJob(
                track=track,
                preset=preset,
                reference_track=reference_track,
                target_loudness=target_loudness
            )
            
            # Upload track
            track_url = await self._upload_track(session, track.file_path)
            
            # Upload reference track if provided
            reference_url = None
            if reference_track:
                reference_url = await self._upload_track(session, reference_track)
                
            # Submit mastering job
            job_data = {
                "track_url": track_url,
                "preset": preset,
                "reference_track_url": reference_url,
                "target_loudness": target_loudness
            }
            
            async with session.post(
                f"{self.base_url_mastering}/jobs",
                json=job_data,
                headers={"Authorization": f"Bearer {self.mastering_api_key}"}
            ) as response:
                result = await response.json()
                
            if response.status == 201:
                job.status = "processing"
                self.mastering_jobs[result["id"]] = job
                
            return result
            
    async def get_mastering_status(self, job_id: str) -> Dict:
        """Get the status of a mastering job."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url_mastering}/jobs/{job_id}",
                headers={"Authorization": f"Bearer {self.mastering_api_key}"}
            ) as response:
                result = await response.json()
                
            if job_id in self.mastering_jobs:
                job = self.mastering_jobs[job_id]
                job.status = result["status"]
                if result["status"] == "completed":
                    job.completed_at = datetime.now()
                    job.result_path = Path(result["result_url"])
                    
            return result
            
    async def download_master(self, job_id: str, destination: Path) -> bool:
        """Download a completed master."""
        if job_id not in self.mastering_jobs:
            return False
            
        job = self.mastering_jobs[job_id]
        if job.status != "completed" or not job.result_path:
            return False
            
        async with aiohttp.ClientSession() as session:
            async with session.get(str(job.result_path)) as response:
                if response.status == 200:
                    with open(destination, "wb") as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                    return True
                    
        return False
        
    async def get_platform_stats(
        self,
        platform: DistributionPlatform,
        release_id: str
    ) -> Dict:
        """Get streaming and revenue stats for a release on a platform."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url_distribution}/stats/{platform}/{release_id}",
                headers={"Authorization": f"Bearer {self.distribution_api_key}"}
            ) as response:
                return await response.json()
                
    async def _validate_release(self, release: Release) -> List[str]:
        """Validate release data before submission."""
        errors = []
        
        # Check required fields
        if not release.artwork_path.exists():
            errors.append("Artwork file not found")
            
        for track in release.tracks:
            if not track.file_path.exists():
                errors.append(f"Audio file not found for track: {track.title}")
                
        # Validate artwork dimensions and format
        if release.artwork_path.exists():
            # Add image validation logic here
            pass
            
        # Validate audio files
        for track in release.tracks:
            if track.file_path.exists():
                # Add audio validation logic here
                pass
                
        return errors
        
    async def _upload_track(
        self,
        session: aiohttp.ClientSession,
        file_path: Path
    ) -> Optional[str]:
        """Upload a track and get its URL."""
        if not file_path.exists():
            return None
            
        # Get upload URL
        async with session.post(
            f"{self.base_url_distribution}/upload",
            headers={"Authorization": f"Bearer {self.distribution_api_key}"}
        ) as response:
            upload_data = await response.json()
            
        # Upload file
        with open(file_path, "rb") as f:
            async with session.put(
                upload_data["upload_url"],
                data=f
            ) as response:
                if response.status == 200:
                    return upload_data["file_url"]
                    
        return None
        
    async def _upload_artwork(
        self,
        session: aiohttp.ClientSession,
        file_path: Path
    ) -> Optional[str]:
        """Upload artwork and get its URL."""
        if not file_path.exists():
            return None
            
        # Get upload URL
        async with session.post(
            f"{self.base_url_distribution}/upload",
            headers={"Authorization": f"Bearer {self.distribution_api_key}"}
        ) as response:
            upload_data = await response.json()
            
        # Upload file
        with open(file_path, "rb") as f:
            async with session.put(
                upload_data["upload_url"],
                data=f
            ) as response:
                if response.status == 200:
                    return upload_data["file_url"]
                    
        return None 