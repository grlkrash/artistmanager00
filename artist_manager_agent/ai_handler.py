"""AI handler for natural language processing and autonomous operations."""
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
import json
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from .log import log_event, log_error
from .utils import async_retry

class CommandIntent(BaseModel):
    """Parsed command intent."""
    command: str = Field(description="The base command to execute")
    args: Dict[str, Any] = Field(description="Command arguments")
    confidence: float = Field(description="Confidence score of the parsing")

class GoalAction(BaseModel):
    """Autonomous action to take towards a goal."""
    action: str = Field(description="Action to take")
    params: Dict[str, Any] = Field(description="Parameters for the action")
    priority: int = Field(description="Priority level (1-5)")
    reasoning: str = Field(description="Reasoning behind this action")

class AIHandler:
    """Handle AI-powered features."""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-3.5-turbo"):
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model=model,
            temperature=0.7
        )
        self.command_parser = PydanticOutputParser(pydantic_object=CommandIntent)
        self.action_parser = PydanticOutputParser(pydantic_object=GoalAction)
        
        # Load prompt templates
        self.command_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI assistant that helps parse natural language into structured commands. "
                      "Convert the user's input into the appropriate command and arguments."),
            ("human", "{input}")
        ])
        
        self.goal_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI assistant that helps manage an artist's career. "
                      "Based on the current state and goals, suggest the next best action to take."),
            ("human", "Current state: {state}\nGoals: {goals}\nPrevious actions: {previous_actions}")
        ])

    @async_retry(retries=3, delay=1)
    async def parse_command(self, user_input: str) -> CommandIntent:
        """Parse natural language input into a structured command."""
        try:
            # Format the prompt
            prompt = self.command_prompt.format_messages(input=user_input)
            
            # Get response from LLM
            response = await self.llm.agenerate([prompt])
            
            # Parse the response
            parsed_command = self.command_parser.parse(response.generations[0][0].text)
            
            log_event("command_parsed", {
                "input": user_input,
                "parsed": parsed_command.dict()
            })
            
            return parsed_command
        except Exception as e:
            log_error(e, {"user_input": user_input})
            raise

    @async_retry(retries=3, delay=1)
    async def suggest_action(
        self,
        current_state: Dict[str, Any],
        goals: List[str],
        previous_actions: List[str]
    ) -> GoalAction:
        """Suggest next action based on current state and goals."""
        try:
            # Format the prompt
            prompt = self.goal_prompt.format_messages(
                state=json.dumps(current_state),
                goals=json.dumps(goals),
                previous_actions=json.dumps(previous_actions)
            )
            
            # Get response from LLM
            response = await self.llm.agenerate([prompt])
            
            # Parse the response
            action = self.action_parser.parse(response.generations[0][0].text)
            
            log_event("action_suggested", {
                "goals": goals,
                "action": action.dict()
            })
            
            return action
        except Exception as e:
            log_error(e, {
                "current_state": current_state,
                "goals": goals
            })
            raise

    async def autonomous_mode(
        self,
        agent: Any,
        goals: List[str],
        max_actions: int = 5,
        delay: int = 60
    ):
        """Run in autonomous mode, taking actions towards goals."""
        actions_taken = []
        
        for _ in range(max_actions):
            try:
                # Get current state
                current_state = await agent.get_current_state()
                
                # Get next action
                action = await self.suggest_action(
                    current_state=current_state,
                    goals=goals,
                    previous_actions=actions_taken
                )
                
                # Execute action if confidence is high enough
                if action.priority >= 4:
                    result = await agent.execute_action(action.action, action.params)
                    actions_taken.append(action.dict())
                    
                    log_event("autonomous_action", {
                        "action": action.dict(),
                        "result": result
                    })
                
                # Wait before next action
                await asyncio.sleep(delay)
                
            except Exception as e:
                log_error(e, {"mode": "autonomous"})
                await asyncio.sleep(delay * 2)  # Longer delay on error
                
        return actions_taken 