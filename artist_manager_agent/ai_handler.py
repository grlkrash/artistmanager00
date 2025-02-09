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