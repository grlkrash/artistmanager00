from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel
import aiohttp
import os
from pathlib import Path
import asyncio

class Platform(str, Enum):
    """Supported social media platforms."""
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"

class ContentType(str, Enum):
    """Types of social media content."""
    IMAGE = "image"
    VIDEO = "video"
    STORY = "story"
    REEL = "reel"
    TWEET = "tweet"
    POST = "post"
    LIVE = "live"

class PostStatus(str, Enum):
    """Status of social media posts."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"

class Engagement(BaseModel):
    """Track engagement metrics."""
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    views: Optional[int] = None
    reach: Optional[int] = None
    clicks: Optional[int] = None
    timestamp: datetime = datetime.now()

class MediaAsset(BaseModel):
    """Media asset for social posts."""
    file_path: Path
    type: ContentType
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    thumbnail: Optional[Path] = None
    duration: Optional[float] = None  # for videos

class SocialPost(BaseModel):
    """Social media post information."""
    id: Optional[str] = None
    platform: Platform
    content_type: ContentType
    caption: str
    media: List[MediaAsset] = []
    hashtags: List[str] = []
    mentions: List[str] = []
    scheduled_time: Optional[datetime] = None
    status: PostStatus = PostStatus.DRAFT
    engagement: Optional[Engagement] = None
    url: Optional[str] = None
    created_at: datetime = datetime.now()
    published_at: Optional[datetime] = None

class Campaign(BaseModel):
    """Social media campaign information."""
    id: Optional[str] = None
    name: str
    description: str
    start_date: datetime
    end_date: datetime
    platforms: List[Platform]
    target_audience: Dict[str, Any] = {}
    budget: Optional[float] = None
    posts: List[SocialPost] = []
    goals: Dict[str, int] = {}
    results: Dict[str, int] = {}

class SocialMediaManager:
    """Manage social media content and campaigns."""
    
    def __init__(self):
        self.api_keys = {
            Platform.INSTAGRAM: os.getenv("INSTAGRAM_API_KEY"),
            Platform.TWITTER: os.getenv("TWITTER_API_KEY"),
            Platform.FACEBOOK: os.getenv("FACEBOOK_API_KEY"),
            Platform.TIKTOK: os.getenv("TIKTOK_API_KEY"),
            Platform.YOUTUBE: os.getenv("YOUTUBE_API_KEY"),
            Platform.LINKEDIN: os.getenv("LINKEDIN_API_KEY")
        }
        self.base_urls = {
            Platform.INSTAGRAM: "https://api.instagram.com/v1",
            Platform.TWITTER: "https://api.twitter.com/v2",
            Platform.FACEBOOK: "https://graph.facebook.com/v12.0",
            Platform.TIKTOK: "https://open-api.tiktok.com/v2",
            Platform.YOUTUBE: "https://www.googleapis.com/youtube/v3",
            Platform.LINKEDIN: "https://api.linkedin.com/v2"
        }
        self.posts: Dict[str, SocialPost] = {}
        self.campaigns: Dict[str, Campaign] = {}
        
    async def create_post(
        self,
        platform: Platform,
        content_type: ContentType,
        caption: str,
        media: List[MediaAsset],
        hashtags: List[str] = [],
        mentions: List[str] = [],
        scheduled_time: Optional[datetime] = None
    ) -> Dict:
        """Create a new social media post."""
        # Create post object
        post = SocialPost(
            platform=platform,
            content_type=content_type,
            caption=caption,
            media=media,
            hashtags=hashtags,
            mentions=mentions,
            scheduled_time=scheduled_time
        )
        
        async with aiohttp.ClientSession() as session:
            # Upload media assets
            media_urls = []
            for asset in media:
                url = await self._upload_media(
                    session,
                    platform,
                    asset
                )
                if url:
                    media_urls.append(url)
                else:
                    return {
                        "error": f"Failed to upload media: {asset.file_path}"
                    }
            
            # Prepare post data
            post_data = {
                "caption": self._format_caption(
                    caption,
                    hashtags,
                    mentions
                ),
                "media_urls": media_urls
            }
            
            if scheduled_time:
                post_data["scheduled_time"] = scheduled_time.isoformat()
                
            # Create post on platform
            async with session.post(
                f"{self.base_urls[platform]}/posts",
                json=post_data,
                headers=self._get_headers(platform)
            ) as response:
                result = await response.json()
                
            if response.status == 201:
                post.id = result["id"]
                post.status = (
                    PostStatus.SCHEDULED if scheduled_time
                    else PostStatus.PUBLISHED
                )
                post.url = result.get("url")
                self.posts[post.id] = post
                
            return result
            
    async def schedule_campaign(self, campaign: Campaign) -> Dict:
        """Schedule a social media campaign."""
        if not campaign.id:
            campaign.id = str(uuid.uuid4())
            
        results = []
        for post in campaign.posts:
            result = await self.create_post(
                platform=post.platform,
                content_type=post.content_type,
                caption=post.caption,
                media=post.media,
                hashtags=post.hashtags,
                mentions=post.mentions,
                scheduled_time=post.scheduled_time
            )
            results.append(result)
            
        self.campaigns[campaign.id] = campaign
        return {
            "campaign_id": campaign.id,
            "post_results": results
        }
        
    async def get_post_analytics(
        self,
        post_id: str,
        metrics: List[str] = ["likes", "comments", "shares"]
    ) -> Dict:
        """Get analytics for a specific post."""
        if post_id not in self.posts:
            return {"error": "Post not found"}
            
        post = self.posts[post_id]
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_urls[post.platform]}/posts/{post_id}/analytics",
                params={"metrics": ",".join(metrics)},
                headers=self._get_headers(post.platform)
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    post.engagement = Engagement(**result)
                    
                return result
                
    async def get_campaign_analytics(
        self,
        campaign_id: str
    ) -> Dict:
        """Get analytics for an entire campaign."""
        if campaign_id not in self.campaigns:
            return {"error": "Campaign not found"}
            
        campaign = self.campaigns[campaign_id]
        analytics = {
            "campaign_name": campaign.name,
            "duration": (campaign.end_date - campaign.start_date).days,
            "platforms": {},
            "total_engagement": {
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "views": 0
            }
        }
        
        for platform in campaign.platforms:
            analytics["platforms"][platform] = {
                "posts": 0,
                "total_reach": 0,
                "engagement_rate": 0
            }
            
        for post in campaign.posts:
            if post.engagement:
                platform_stats = analytics["platforms"][post.platform]
                platform_stats["posts"] += 1
                platform_stats["total_reach"] += (
                    post.engagement.reach or 0
                )
                
                # Update total engagement
                for metric in ["likes", "comments", "shares", "views"]:
                    value = getattr(post.engagement, metric, 0)
                    if value:
                        analytics["total_engagement"][metric] += value
                        
        # Calculate engagement rates
        for platform in campaign.platforms:
            stats = analytics["platforms"][platform]
            if stats["total_reach"] > 0:
                total_engagement = sum(
                    analytics["total_engagement"].values()
                )
                stats["engagement_rate"] = (
                    total_engagement / stats["total_reach"]
                ) * 100
                
        return analytics
        
    async def generate_content_ideas(
        self,
        platform: Platform,
        content_type: ContentType,
        theme: str,
        count: int = 5
    ) -> List[Dict]:
        """Generate content ideas based on theme and platform."""
        # This would integrate with an AI service for content ideation
        # For now, return template-based ideas
        templates = {
            Platform.INSTAGRAM: {
                ContentType.IMAGE: [
                    "Behind the scenes at {location}",
                    "New release sneak peek: {title}",
                    "Studio session with {collaborator}",
                    "Throwback to {event}",
                    "Fan art spotlight: {artist_name}"
                ],
                ContentType.REEL: [
                    "Day in the life of {artist_name}",
                    "Quick tutorial: {technique}",
                    "Song snippet: {title}",
                    "Gear showcase: {equipment}",
                    "Fan cover compilation"
                ]
            },
            Platform.TIKTOK: {
                ContentType.VIDEO: [
                    "How I made {song_title}",
                    "Responding to fan questions about {topic}",
                    "POV: Creating {song_element}",
                    "Duet chain: {challenge}",
                    "Music production hack: {technique}"
                ]
            }
        }
        
        platform_templates = templates.get(platform, {})
        type_templates = platform_templates.get(content_type, [])
        
        ideas = []
        for template in type_templates[:count]:
            ideas.append({
                "title": template.format(
                    artist_name="Artist",
                    location="Studio",
                    title="New Track",
                    collaborator="Producer",
                    event="Last Show",
                    technique="Mix Tips",
                    equipment="New Mic",
                    song_title="Hit Song",
                    topic="Music Production",
                    song_element="Beat",
                    challenge="Remix Challenge"
                ),
                "platform": platform,
                "content_type": content_type,
                "suggested_hashtags": self._generate_hashtags(
                    platform,
                    theme
                )
            })
            
        return ideas
        
    def _format_caption(
        self,
        caption: str,
        hashtags: List[str],
        mentions: List[str]
    ) -> str:
        """Format caption with hashtags and mentions."""
        formatted = caption
        
        if mentions:
            formatted += "\n\n" + " ".join(
                f"@{mention}" for mention in mentions
            )
            
        if hashtags:
            formatted += "\n\n" + " ".join(
                f"#{tag}" for tag in hashtags
            )
            
        return formatted
        
    async def _upload_media(
        self,
        session: aiohttp.ClientSession,
        platform: Platform,
        asset: MediaAsset
    ) -> Optional[str]:
        """Upload media to a platform."""
        if not asset.file_path.exists():
            return None
            
        # Get upload URL
        async with session.post(
            f"{self.base_urls[platform]}/media/upload",
            headers=self._get_headers(platform)
        ) as response:
            upload_data = await response.json()
            
        # Upload file
        with open(asset.file_path, "rb") as f:
            async with session.put(
                upload_data["upload_url"],
                data=f
            ) as response:
                if response.status == 200:
                    return upload_data["media_url"]
                    
        return None
        
    def _get_headers(self, platform: Platform) -> Dict[str, str]:
        """Get API headers for a platform."""
        return {
            "Authorization": f"Bearer {self.api_keys[platform]}",
            "Content-Type": "application/json"
        }
        
    def _generate_hashtags(
        self,
        platform: Platform,
        theme: str
    ) -> List[str]:
        """Generate relevant hashtags."""
        # This would integrate with a trending hashtag API
        # For now, return template hashtags
        base_tags = [
            "music",
            "musician",
            "newmusic",
            "producer",
            "studio",
            "recording"
        ]
        
        theme_tags = {
            "release": [
                "newsingle",
                "newrelease",
                "newsong",
                "spotifyartist"
            ],
            "studio": [
                "studiolife",
                "musicproduction",
                "musicproducer",
                "behindthescenes"
            ],
            "performance": [
                "livemusic",
                "musicperformance",
                "gig",
                "concert"
            ]
        }
        
        return base_tags + theme_tags.get(theme.lower(), []) 