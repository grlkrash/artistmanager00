from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel
from ..models import (
    Track, Release, ReleaseType, MasteringPreset, DistributionPlatform,
    StreamingStats, PromotionCampaign
)
import uuid

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
        self.streaming_stats: Dict[str, List[StreamingStats]] = {}
        self.promotion_campaigns: Dict[str, PromotionCampaign] = {}

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

    async def get_streaming_stats(
        self,
        track_id: str,
        platform: Optional[DistributionPlatform] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[StreamingStats]:
        """Get streaming statistics for a track."""
        if track_id not in self.tracks:
            raise ValueError(f"Track with ID {track_id} not found")
            
        stats = self.streaming_stats.get(track_id, [])
        
        # Filter by platform
        if platform:
            stats = [s for s in stats if s.platform == platform]
            
        # Filter by date range
        if start_date:
            stats = [s for s in stats if s.period_end >= start_date]
        if end_date:
            stats = [s for s in stats if s.period_start <= end_date]
            
        return sorted(stats, key=lambda x: x.period_start, reverse=True)

    async def create_promotion_campaign(
        self,
        title: str,
        campaign_type: str,
        target_platforms: List[str],
        budget: float,
        start_date: datetime,
        end_date: datetime
    ) -> PromotionCampaign:
        """Create a new promotion campaign."""
        campaign = PromotionCampaign(
            id=str(uuid.uuid4()),
            title=title,
            type=campaign_type,
            target_platforms=target_platforms,
            budget=budget,
            start_date=start_date,
            end_date=end_date,
            status="pending",
            metrics={}
        )
        
        self.promotion_campaigns[campaign.id] = campaign
        return campaign

    async def update_campaign_metrics(
        self,
        campaign_id: str,
        metrics: Dict[str, Any]
    ) -> PromotionCampaign:
        """Update promotion campaign metrics."""
        if campaign_id not in self.promotion_campaigns:
            raise ValueError(f"Campaign with ID {campaign_id} not found")
            
        campaign = self.promotion_campaigns[campaign_id]
        campaign.metrics.update(metrics)
        return campaign

    async def get_revenue_report(
        self,
        start_date: datetime,
        end_date: datetime,
        platform: Optional[DistributionPlatform] = None
    ) -> Dict[str, float]:
        """Get revenue report for all tracks."""
        revenue = {}
        
        for track_id, stats_list in self.streaming_stats.items():
            track_revenue = 0
            for stats in stats_list:
                if stats.period_start >= start_date and stats.period_end <= end_date:
                    if not platform or stats.platform == platform:
                        track_revenue += stats.revenue
            if track_revenue > 0:
                revenue[track_id] = track_revenue
                
        return revenue

    async def get_playlist_analytics(
        self,
        track_id: str,
        platform: Optional[DistributionPlatform] = None
    ) -> Dict[str, int]:
        """Get playlist analytics for a track."""
        if track_id not in self.tracks:
            raise ValueError(f"Track with ID {track_id} not found")
            
        stats = self.streaming_stats.get(track_id, [])
        
        # Filter by platform
        if platform:
            stats = [s for s in stats if s.platform == platform]
            
        return {
            "total_playlists": sum(s.playlist_adds for s in stats),
            "total_streams_from_playlists": sum(s.streams for s in stats)
        }

    async def get_audience_demographics(
        self,
        track_id: str
    ) -> Dict[str, Dict[str, int]]:
        """Get audience demographics for a track."""
        # Mock implementation - would integrate with platform APIs
        return {
            "age_groups": {
                "13-17": 100,
                "18-24": 500,
                "25-34": 300,
                "35-44": 100,
                "45+": 50
            },
            "top_countries": {
                "US": 400,
                "UK": 200,
                "DE": 150,
                "FR": 100,
                "CA": 100
            },
            "gender": {
                "male": 600,
                "female": 400,
                "other": 50
            }
        } 