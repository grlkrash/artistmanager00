import asyncio
import os
from datetime import datetime, timedelta
from artist_manager_agent.agent import ArtistManagerAgent, ArtistProfile, TeamMember, Task

async def main():
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
        ]
    )

    # Initialize the agent
    agent = ArtistManagerAgent(
        artist_profile=artist,
        openai_api_key=os.getenv("OPENAI_API_KEY", "")
    )

    # Add team members
    producer = TeamMember(
        name="Sarah Chen",
        role="Producer",
        skills=["Music Production", "Mixing", "Arrangement"],
        performance_metrics={"track_completion_rate": 0.9}
    )
    agent.add_team_member(producer)

    # Create and assign tasks
    album_task = Task(
        title="Complete album production",
        description="Finish producing all tracks for the upcoming album",
        deadline=datetime.now() + timedelta(days=90),
        assigned_to="Sarah Chen",
        status="in_progress",
        priority=1
    )
    agent.assign_task(album_task)

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
    task_status = agent.get_task_status()
    print("\nCurrent Task Status:")
    print(task_status)

if __name__ == "__main__":
    asyncio.run(main()) 