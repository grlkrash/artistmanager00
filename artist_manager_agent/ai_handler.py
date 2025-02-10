"""AI handler for natural language processing and autonomous operations."""
from typing import Dict, Any, List, Optional, Tuple
import asyncio
from datetime import datetime, timedelta
import json
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from .log import log_event, log_error
from .utils import async_retry
from .models import ArtistProfile, Task, Event, Project

class GoalPlan(BaseModel):
    """Structured plan for achieving a goal."""
    goal: str = Field(description="The target goal")
    estimated_timeline: timedelta = Field(description="Estimated time to achieve goal")
    milestones: List[Dict[str, Any]] = Field(description="Key milestones to reach")
    required_resources: List[str] = Field(description="Resources needed")
    success_metrics: Dict[str, Any] = Field(description="Metrics to measure success")
    contingency_plans: List[str] = Field(description="Backup plans if primary approach fails")

class PlanStep(BaseModel):
    """Individual step in executing a plan."""
    action: str = Field(description="Specific action to take")
    command: str = Field(description="Bot command to execute")
    args: Dict[str, Any] = Field(description="Command arguments")
    priority: int = Field(description="Priority level (1-5)")
    dependencies: List[str] = Field(description="IDs of steps this depends on")
    estimated_duration: timedelta = Field(description="Expected time to complete")
    success_criteria: Dict[str, Any] = Field(description="How to measure step success")

class ExecutionResult(BaseModel):
    """Result of executing a plan step."""
    step_id: str = Field(description="ID of the executed step")
    success: bool = Field(description="Whether the step succeeded")
    output: Dict[str, Any] = Field(description="Output data from execution")
    metrics: Dict[str, float] = Field(description="Measured metrics")
    next_steps: List[str] = Field(description="IDs of next steps to execute")

class AIHandler:
    """Handle AI-powered features."""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-3.5-turbo"):
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model=model,
            temperature=0.7
        )
        self.command_parser = PydanticOutputParser(pydantic_object=PlanStep)
        self.plan_parser = PydanticOutputParser(pydantic_object=GoalPlan)
        
        # Load enhanced prompt templates
        self.goal_analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an experienced artist manager AI that excels at breaking down goals into actionable plans. "
                      "Analyze the artist's profile, current state, and goals to create detailed execution plans."),
            ("human", "Artist Profile: {profile}\nCurrent State: {state}\nGoal: {goal}")
        ])
        
        self.step_planning_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI artist manager that converts high-level plans into specific, executable steps. "
                      "Generate the next best action to take based on the current plan and progress."),
            ("human", "Plan: {plan}\nProgress: {progress}\nCurrent State: {state}")
        ])
        
        self.execution_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI artist manager that executes plans through bot commands. "
                      "Convert the planned action into the appropriate command with arguments."),
            ("human", "Action: {action}\nContext: {context}")
        ])

        # Initialize plan storage
        self.active_plans: Dict[str, GoalPlan] = {}
        self.step_history: Dict[str, List[ExecutionResult]] = {}

    async def create_goal_plan(
        self,
        profile: ArtistProfile,
        goal: str,
        current_state: Dict[str, Any]
    ) -> GoalPlan:
        """Create a detailed plan for achieving a specific goal."""
        try:
            # Format the prompt
            prompt = self.goal_analysis_prompt.format_messages(
                profile=profile.json(),
                state=json.dumps(current_state),
                goal=goal
            )
            
            # Get response from LLM
            response = await self.llm.agenerate([prompt])
            
            # Parse the response into a structured plan
            plan = self.plan_parser.parse(response.generations[0][0].text)
            
            # Store the plan
            plan_id = f"plan_{len(self.active_plans)}"
            self.active_plans[plan_id] = plan
            self.step_history[plan_id] = []
            
            log_event("plan_created", {
                "goal": goal,
                "plan": plan.dict()
            })
            
            return plan
        except Exception as e:
            log_error(e, {
                "goal": goal,
                "profile": profile.dict()
            })
            raise

    async def get_next_step(
        self,
        plan_id: str,
        current_state: Dict[str, Any]
    ) -> Optional[PlanStep]:
        """Get the next step to execute in a plan."""
        try:
            plan = self.active_plans.get(plan_id)
            if not plan:
                return None
                
            progress = {
                "completed_steps": [r.step_id for r in self.step_history[plan_id] if r.success],
                "failed_steps": [r.step_id for r in self.step_history[plan_id] if not r.success],
                "metrics": {}  # Aggregate metrics from results
            }
            
            # Format the prompt
            prompt = self.step_planning_prompt.format_messages(
                plan=plan.json(),
                progress=json.dumps(progress),
                state=json.dumps(current_state)
            )
            
            # Get response from LLM
            response = await self.llm.agenerate([prompt])
            
            # Parse the response into a step
            step = self.command_parser.parse(response.generations[0][0].text)
            
            log_event("step_planned", {
                "plan_id": plan_id,
                "step": step.dict()
            })
            
            return step
        except Exception as e:
            log_error(e, {
                "plan_id": plan_id,
                "state": current_state
            })
            raise

    async def execute_step(
        self,
        step: PlanStep,
        agent: Any,
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute a plan step through bot commands."""
        try:
            # Format the execution prompt
            prompt = self.execution_prompt.format_messages(
                action=step.json(),
                context=json.dumps(context)
            )
            
            # Get command details
            response = await self.llm.agenerate([prompt])
            command_details = self.command_parser.parse(response.generations[0][0].text)
            
            # Execute the command
            result = await agent.execute_command(
                command_details.command,
                command_details.args
            )
            
            # Create execution result
            execution_result = ExecutionResult(
                step_id=str(step.action),
                success=result.get("success", False),
                output=result,
                metrics={},  # Add relevant metrics
                next_steps=[]  # Will be filled by get_next_step
            )
            
            log_event("step_executed", {
                "step": step.dict(),
                "result": execution_result.dict()
            })
            
            return execution_result
        except Exception as e:
            log_error(e, {
                "step": step.dict(),
                "context": context
            })
            raise

    async def autonomous_mode(
        self,
        agent: Any,
        profile: ArtistProfile,
        goals: List[str],
        max_actions: int = 5,
        delay: int = 60
    ):
        """Run in autonomous mode, executing plans for each goal."""
        try:
            # Create plans for each goal
            for goal in goals:
                current_state = await agent.get_current_state()
                plan = await self.create_goal_plan(profile, goal, current_state)
                
                # Execute steps until max_actions reached or goal achieved
                actions_taken = 0
                while actions_taken < max_actions:
                    # Get next step
                    step = await self.get_next_step(plan.id, current_state)
                    if not step:
                        break
                        
                    # Execute step
                    result = await self.execute_step(step, agent, {
                        "profile": profile.dict(),
                        "goal": goal,
                        "plan": plan.dict()
                    })
                    
                    # Update history
                    self.step_history[plan.id].append(result)
                    
                    # Check if goal is achieved
                    if await self._check_goal_achieved(goal, current_state):
                        break
                        
                    actions_taken += 1
                    await asyncio.sleep(delay)
                    
            return self.step_history
        except Exception as e:
            log_error(e, {
                "mode": "autonomous",
                "goals": goals
            })
            raise

    async def _check_goal_achieved(
        self,
        goal: str,
        current_state: Dict[str, Any]
    ) -> bool:
        """Check if a goal has been achieved based on current state."""
        try:
            # Format a prompt to evaluate goal completion
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an AI that evaluates whether goals have been achieved based on current state."),
                ("human", f"Goal: {goal}\nCurrent State: {json.dumps(current_state)}")
            ])
            
            # Get evaluation
            response = await self.llm.agenerate([prompt.format_messages()])
            
            # Parse response (expecting "true" or "false")
            return response.generations[0][0].text.strip().lower() == "true"
        except Exception as e:
            log_error(e, {
                "goal": goal,
                "state": current_state
            })
            return False

    async def analyze_goal_progress(self, goal: str, profile: ArtistProfile) -> float:
        """Analyze progress towards a specific goal."""
        try:
            # Format the prompt for goal analysis
            prompt = {
                "role": "system",
                "content": f"Analyze progress towards the goal: {goal}\nProfile: {profile.json()}"
            }
            
            # Get response from LLM
            response = await self.llm.agenerate([prompt])
            progress = float(response.generations[0][0].text.strip())
            
            return min(max(progress, 0), 100)  # Ensure between 0-100
        except Exception as e:
            log_error(e, {
                "goal": goal,
                "profile": profile.dict()
            })
            return 0.0

    async def suggest_tasks_for_goal(self, goal: str, profile: ArtistProfile) -> List[Task]:
        """Generate task suggestions for a goal."""
        try:
            # Format the prompt for task suggestions
            prompt = {
                "role": "system",
                "content": f"Suggest tasks to achieve the goal: {goal}\nProfile: {profile.json()}"
            }
            
            # Get response from LLM
            response = await self.llm.agenerate([prompt])
            tasks_data = json.loads(response.generations[0][0].text)
            
            # Convert to Task objects
            tasks = []
            for task_data in tasks_data:
                task = Task(
                    title=task_data["title"],
                    description=task_data["description"],
                    priority=task_data["priority"],
                    due_date=datetime.fromisoformat(task_data["due_date"])
                )
                tasks.append(task)
            
            return tasks
        except Exception as e:
            log_error(e, {
                "goal": goal,
                "profile": profile.dict()
            })
            return []

    async def analyze_metrics(self, profile: ArtistProfile) -> Dict[str, Any]:
        """Analyze performance metrics across platforms."""
        try:
            metrics = {
                "social_growth": 0.0,
                "streaming_growth": 0.0,
                "project_completion": 0.0,
                "goal_progress": 0.0,
                "insights": [],
                "suggested_actions": []
            }
            
            # Analyze social media growth
            if profile.social_media:
                for platform, handle in profile.social_media.items():
                    growth = await self._analyze_social_platform(platform, handle)
                    metrics["social_growth"] += growth
                metrics["social_growth"] /= len(profile.social_media)
            
            # Analyze streaming performance
            if profile.streaming_profiles:
                for platform, url in profile.streaming_profiles.items():
                    growth = await self._analyze_streaming_platform(platform, url)
                    metrics["streaming_growth"] += growth
                metrics["streaming_growth"] /= len(profile.streaming_profiles)
            
            # Generate insights
            insights = await self._generate_metric_insights(metrics, profile)
            metrics["insights"] = insights
            
            # Generate action suggestions
            actions = await self._generate_action_suggestions(metrics, profile)
            metrics["suggested_actions"] = actions
            
            return metrics
        except Exception as e:
            log_error(e, {
                "profile": profile.dict()
            })
            return None

    async def generate_insights(self, profile: ArtistProfile) -> Dict[str, List[str]]:
        """Generate AI-powered insights and suggestions."""
        try:
            # Format the prompt for insights
            prompt = {
                "role": "system",
                "content": f"Generate insights and suggestions for artist profile: {profile.json()}"
            }
            
            # Get response from LLM
            response = await self.llm.agenerate([prompt])
            insights_data = json.loads(response.generations[0][0].text)
            
            return {
                "career": insights_data.get("career_insights", []),
                "marketing": insights_data.get("marketing_insights", []),
                "performance": insights_data.get("performance_insights", []),
                "suggestions": insights_data.get("suggested_actions", [])
            }
        except Exception as e:
            log_error(e, {
                "profile": profile.dict()
            })
            return {}

    async def _analyze_social_platform(self, platform: str, handle: str) -> float:
        """Analyze growth on a social media platform."""
        try:
            # Get historical data
            history = await self._get_social_history(platform, handle)
            if not history:
                return 0.0
            
            # Calculate growth rate
            current = history[-1]["followers"]
            previous = history[-2]["followers"] if len(history) > 1 else current
            growth = ((current - previous) / previous) * 100 if previous > 0 else 0
            
            return growth
        except Exception as e:
            log_error(e, {
                "platform": platform,
                "handle": handle
            })
            return 0.0

    async def _analyze_streaming_platform(self, platform: str, url: str) -> float:
        """Analyze growth on a streaming platform."""
        try:
            # Get historical data
            history = await self._get_streaming_history(platform, url)
            if not history:
                return 0.0
            
            # Calculate growth rate
            current = history[-1]["streams"]
            previous = history[-2]["streams"] if len(history) > 1 else current
            growth = ((current - previous) / previous) * 100 if previous > 0 else 0
            
            return growth
        except Exception as e:
            log_error(e, {
                "platform": platform,
                "url": url
            })
            return 0.0

    async def _generate_metric_insights(self, metrics: Dict[str, Any], profile: ArtistProfile) -> List[str]:
        """Generate insights based on metrics."""
        try:
            # Format the prompt for insights
            prompt = {
                "role": "system",
                "content": f"Generate insights based on metrics: {json.dumps(metrics)}\nProfile: {profile.json()}"
            }
            
            # Get response from LLM
            response = await self.llm.agenerate([prompt])
            insights = json.loads(response.generations[0][0].text)
            
            return insights
        except Exception as e:
            log_error(e, {
                "metrics": metrics,
                "profile": profile.dict()
            })
            return []

    async def _generate_action_suggestions(self, metrics: Dict[str, Any], profile: ArtistProfile) -> List[Dict[str, Any]]:
        """Generate action suggestions based on metrics."""
        try:
            # Format the prompt for suggestions
            prompt = {
                "role": "system",
                "content": f"Suggest actions based on metrics: {json.dumps(metrics)}\nProfile: {profile.json()}"
            }
            
            # Get response from LLM
            response = await self.llm.agenerate([prompt])
            suggestions = json.loads(response.generations[0][0].text)
            
            return suggestions
        except Exception as e:
            log_error(e, {
                "metrics": metrics,
                "profile": profile.dict()
            })
            return []

    async def _get_social_history(self, platform: str, handle: str) -> List[Dict[str, Any]]:
        """Get historical data for a social media platform."""
        # This would integrate with social media APIs
        # For now, return mock data
        return [
            {"date": "2024-01-01", "followers": 1000},
            {"date": "2024-02-01", "followers": 1200}
        ]

    async def _get_streaming_history(self, platform: str, url: str) -> List[Dict[str, Any]]:
        """Get historical data for a streaming platform."""
        # This would integrate with streaming platform APIs
        # For now, return mock data
        return [
            {"date": "2024-01-01", "streams": 5000},
            {"date": "2024-02-01", "streams": 6000}
        ] 