import asyncio
import os
from datetime import datetime, timedelta
from artist_manager_agent.agent import ArtistManagerAgent, ArtistProfile, Contract, Task, Event, FinancialRecord

async def main():
    # Initialize artist profile
    artist = ArtistProfile(
        artist_id="alex_rivera_1",
        name="Alex Rivera",
        email="alex@rivera.com",
        phone="+1234567890",
        genre=["Alternative R&B"],
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
            "tiktok": "@alexrivera"
        },
        streaming_profiles={
            "spotify": "spotify:artist:alexrivera",
            "apple_music": "artist/alexrivera"
        },
        health_notes=[],
        brand_guidelines="Modern, authentic R&B artist with a focus on emotional storytelling and innovative sound design",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    # Initialize the agent
    agent = ArtistManagerAgent(
        artist_profile=artist,
        openai_api_key=os.getenv("OPENAI_API_KEY", "")
    )

    # Create a new contract
    collaboration_contract = Contract(
        contract_id="contract_1",
        title="Producer Collaboration Agreement",
        parties=["Alex Rivera", "Sarah Chen"],
        terms="Full production rights for upcoming album",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=180),
        value=50000.0,
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    agent.add_contract(collaboration_contract)

    # Create a new task
    album_task = Task(
        task_id="task_1",
        title="Complete album production",
        description="Finish producing all tracks for the upcoming album",
        assigned_to="Sarah Chen",
        due_date=datetime.now() + timedelta(days=90),
        priority="high",
        status="in_progress",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    agent.add_task(album_task)

    # Create a new event
    studio_session = Event(
        event_id="event_1",
        title="Album Recording Session",
        description="Full day studio session for album tracks",
        start_time=datetime.now() + timedelta(days=7),
        end_time=datetime.now() + timedelta(days=7, hours=8),
        location="Sunset Sound Studios",
        attendees=["Alex Rivera", "Sarah Chen"],
        status="scheduled",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    agent.add_event(studio_session)

    # Record a financial transaction
    payment = FinancialRecord(
        record_id="finance_1",
        type="income",
        amount=5000.0,
        description="Advance payment for studio time",
        date=datetime.now(),
        category="studio_expenses",
        status="completed",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    agent.add_financial_record(payment)

    # Get guidance on a situation
    situation = """
    We have an opportunity to collaborate with a major artist, but it would 
    delay our album release by two months. How should we proceed?
    """
    guidance = await agent.provide_guidance(situation)
    print("\nGuidance on collaboration opportunity:")
    print(guidance)

    # Generate strategy
    strategy = await agent.create_strategy()
    print("\nStrategic Plan:")
    print(strategy)

    # Evaluate a business opportunity
    opportunity = """
    A major brand wants to license one of our unreleased tracks for their 
    upcoming campaign. They're offering $50,000 but want exclusive rights 
    for 6 months.
    """
    evaluation = await agent.evaluate_opportunity(opportunity)
    print("\nOpportunity Evaluation:")
    print(evaluation)

    # Check task status
    tasks = agent.get_tasks()
    print("\nCurrent Tasks:")
    for task in tasks:
        print(f"- {task.title}: {task.status}")

if __name__ == "__main__":
    asyncio.run(main()) 