import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from artist_manager_agent.agent import (
    ArtistManagerAgent, 
    ArtistProfile, 
    TeamMember, 
    Task,
    Contract,
    Event,
    FinancialRecord
)
from artist_manager_agent.integrations import (
    ServiceManager,
    TelegramIntegration
)

async def main():
    # Load environment variables
    load_dotenv()

    # Initialize artist profile
    artist = ArtistProfile(
        name="Alex Rivera",
        genre="Alternative R&B",
        career_stage="emerging",
        goals=[
            "Release a full-length album in 6 months",
            "Grow social media following to 100k",
            "Book 3 major festival appearances",
            "Collaborate with established artists"
        ],
        strengths=[
            "Unique vocal style",
            "Strong songwriting",
            "Engaging live performances"
        ],
        areas_for_improvement=[
            "Social media consistency",
            "Network building",
            "Time management"
        ],
        achievements=[
            "Released 2 successful EPs",
            "Featured on major playlist",
            "Opened for established act"
        ],
        social_media={
            "instagram": "@alexrivera",
            "twitter": "@alexriveramusic",
            "tiktok": "@alexrivera.music"
        },
        streaming_profiles={
            "spotify": "spotify:artist:xxxx",
            "apple_music": "artist/xxxx"
        },
        health_notes=[
            "2024-02-07: Feeling energized and creative",
            "2024-02-06: Slight vocal strain, taking it easy"
        ]
    )

    # Initialize the agent
    agent = ArtistManagerAgent(
        artist_profile=artist,
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", "")
    )

    # Add team members
    team_members = [
        TeamMember(
            name="Sarah Chen",
            role="Producer",
            skills=["Music Production", "Mixing", "Arrangement"],
            performance_metrics={"track_completion_rate": 0.9},
            contact_info={
                "email": "sarah@example.com",
                "phone": "+1234567890"
            },
            availability={
                "monday": ["09:00-17:00"],
                "wednesday": ["09:00-17:00"],
                "friday": ["09:00-17:00"]
            }
        ),
        TeamMember(
            name="Marcus Johnson",
            role="Manager",
            skills=["Booking", "Negotiation", "Marketing"],
            performance_metrics={"deal_success_rate": 0.85},
            contact_info={
                "email": "marcus@example.com",
                "phone": "+1234567891"
            },
            availability={"monday": ["10:00-18:00"], "tuesday": ["10:00-18:00"]}
        ),
        TeamMember(
            name="Lisa Wong",
            role="Designer",
            skills=["Graphic Design", "Art Direction", "Motion Graphics"],
            performance_metrics={"project_satisfaction": 0.95},
            contact_info={
                "email": "lisa@example.com",
                "phone": "+1234567892"
            },
            availability={"wednesday": ["11:00-19:00"], "thursday": ["11:00-19:00"]}
        )
    ]

    for member in team_members:
        agent.add_team_member(member)

    # Add some tasks
    tasks = [
        Task(
            title="Complete album production",
            description="Finish producing all tracks for the upcoming album",
            deadline=datetime.now() + timedelta(days=90),
            assigned_to="Sarah Chen",
            status="in_progress",
            priority=1,
            dependencies=["Track recording", "Mixing", "Mastering"],
            notes=["Focus on maintaining consistent sound across all tracks"]
        ),
        Task(
            title="Design album artwork",
            description="Create artwork for the album release",
            deadline=datetime.now() + timedelta(days=60),
            assigned_to="Lisa Wong",
            status="pending",
            priority=2,
            dependencies=[],
            notes=["Reference mood board has been shared"]
        ),
        Task(
            title="Book summer tour venues",
            description="Secure venues for the summer tour",
            deadline=datetime.now() + timedelta(days=120),
            assigned_to="Marcus Johnson",
            status="pending",
            priority=2,
            dependencies=[],
            notes=["Focus on venues with 500+ capacity"]
        )
    ]

    for task in tasks:
        agent.assign_task(task)

    # Initialize Telegram bot
    telegram = TelegramIntegration(
        token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        agent=agent
    )
    
    print("Starting Telegram bot...")
    print("Available commands:")
    print("- /start - Start interaction")
    print("- /help - Show available commands")
    print("- /goals - View and manage goals")
    print("- /tasks - View and manage tasks")
    print("- /team - View and manage team")
    print("- /schedule - View and manage schedule")
    print("- /master - AI master a track")
    print("- /release - Plan a release")
    print("- /health - Track wellbeing")
    print("- /guidance - Get career guidance")
    print("- /crisis - Get crisis management help")
    
    try:
        await telegram.initialize()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await telegram.close()

if __name__ == "__main__":
    asyncio.run(main()) 