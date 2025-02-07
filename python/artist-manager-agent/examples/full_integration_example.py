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
    SupabaseIntegration,
    TelegramIntegration,
    SpotifyIntegration,
    SocialMediaIntegration
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
        }
    )

    # Initialize the agent with integrations
    agent = ArtistManagerAgent(
        artist_profile=artist,
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        db_url=os.getenv("SUPABASE_URL"),
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN")
    )

    # Initialize service manager
    service_manager = ServiceManager()

    # Initialize Supabase integration
    supabase = SupabaseIntegration(
        url=os.getenv("SUPABASE_URL", ""),
        key=os.getenv("SUPABASE_KEY", "")
    )
    await service_manager.initialize_service("supabase", supabase)

    # Initialize Telegram integration
    telegram = TelegramIntegration(
        token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        agent=agent
    )
    await service_manager.initialize_service("telegram", telegram)

    # Initialize Spotify integration
    spotify = SpotifyIntegration(
        client_id=os.getenv("SPOTIFY_CLIENT_ID", ""),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET", "")
    )
    await service_manager.initialize_service("spotify", spotify)

    # Initialize social media integration
    social_media = SocialMediaIntegration({
        "twitter": {
            "api_key": os.getenv("TWITTER_API_KEY", ""),
            "api_secret": os.getenv("TWITTER_API_SECRET", "")
        },
        "instagram": {
            "username": os.getenv("INSTAGRAM_USERNAME", ""),
            "password": os.getenv("INSTAGRAM_PASSWORD", "")
        }
    })
    await service_manager.initialize_service("social_media", social_media)

    # Add team members
    producer = TeamMember(
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
    )
    agent.add_team_member(producer)

    # Create and assign tasks
    album_task = Task(
        title="Complete album production",
        description="Finish producing all tracks for the upcoming album",
        deadline=datetime.now() + timedelta(days=90),
        assigned_to="Sarah Chen",
        status="in_progress",
        priority=1,
        dependencies=["Track recording", "Mixing", "Mastering"],
        notes=["Focus on maintaining consistent sound across all tracks"]
    )
    agent.assign_task(album_task)

    # Create an event
    release_party = Event(
        title="Album Release Party",
        type="launch_event",
        date=datetime.now() + timedelta(days=120),
        venue="The Blue Room",
        capacity=300,
        budget=5000.0,
        status="planning"
    )

    # Record financial transaction
    studio_payment = FinancialRecord(
        date=datetime.now(),
        type="expense",
        amount=1000.0,
        category="studio_time",
        description="Studio session for album recording"
    )
    agent.record_financial_transaction(studio_payment)

    # Example contract
    brand_deal = Contract(
        title="Brand Ambassador Deal",
        parties=["Alex Rivera", "Cool Brand Inc."],
        terms={
            "duration": "6 months",
            "payment": 50000.0,
            "deliverables": ["3 social media posts", "2 live appearances"]
        },
        status="negotiating",
        value=50000.0,
        expiration=datetime.now() + timedelta(days=180)
    )

    # Demonstrate some agent capabilities
    print("\nGetting guidance on opportunity...")
    guidance = await agent.provide_guidance(
        "We have an opportunity to collaborate with a major artist, but it would delay our album release by two months."
    )
    print(guidance)

    print("\nCreating strategy...")
    strategy = await agent.create_strategy()
    print(strategy)

    print("\nEvaluating opportunity...")
    opportunity = """
    A major brand wants to license one of our unreleased tracks for their 
    upcoming campaign. They're offering $50,000 but want exclusive rights 
    for 6 months.
    """
    evaluation = await agent.evaluate_opportunity(opportunity)
    print(evaluation)

    print("\nManaging crisis...")
    crisis = await agent.manage_crisis(
        "A controversial statement about our artist has gone viral on social media."
    )
    print(crisis)

    # Sync data to database
    await agent.sync_to_database()

    # Clean up
    await service_manager.close_all()

if __name__ == "__main__":
    asyncio.run(main()) 