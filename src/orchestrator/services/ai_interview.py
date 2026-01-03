"""AI interview service for generating Spec Kit parameters through chat."""

import os
from typing import Dict, Any, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AIInterviewService:
    """Service for conducting AI-powered interviews to generate Spec Kit parameters."""
    
    PHASES = ['constitution', 'specify', 'clarify', 'plan', 'tasks', 'analyze']
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize AI interview service.
        
        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        
        # System prompt for the interview
        self.system_prompt = """You are a helpful assistant that interviews users about their software project or feature to generate Spec Kit command parameters.

Your goal is to ask thoughtful questions to understand:
1. What the project/feature is about
2. Key requirements and constraints
3. Technical context and dependencies
4. Success criteria and goals

After gathering sufficient information, you will help generate parameter documents for Spec Kit phases:
- Constitution: Project principles and governance
- Specify: Feature specification details
- Clarify: Clarification questions
- Plan: Implementation planning context
- Tasks: Task breakdown requirements
- Analyze: Analysis focus areas

Ask questions one at a time, be conversational, and gather comprehensive information before generating parameters."""
    
    def get_initial_question(self) -> str:
        """Get the first question to start the interview."""
        return "Hello! I'm here to help you generate Spec Kit command parameters for your project. Let's start with the basics: What project or feature are you planning to build? Please describe it in a few sentences."
    
    def conduct_interview_step(
        self,
        conversation_history: List[Dict[str, str]],
        user_response: str
    ) -> Dict[str, Any]:
        """
        Conduct one step of the interview.
        
        Args:
            conversation_history: List of previous messages in format [{"role": "user/assistant", "content": "..."}]
            user_response: User's response to the previous question
        
        Returns:
            Dictionary with:
                - "question": Next question to ask (or None if interview is complete)
                - "parameters": Generated parameters dict (or None if not ready)
                - "is_complete": Boolean indicating if interview is done
        """
        # Add user response to history
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + conversation_history + [
            {"role": "user", "content": user_response}
        ]
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            assistant_message = response.choices[0].message.content
            
            # Check if the assistant is ready to generate parameters
            # Look for indicators that the interview is complete
            if self._should_generate_parameters(assistant_message, conversation_history):
                # Generate parameters
                parameters = self._generate_parameters(messages + [{"role": "assistant", "content": assistant_message}])
                return {
                    "question": None,
                    "parameters": parameters,
                    "is_complete": True,
                    "final_message": assistant_message
                }
            else:
                return {
                    "question": assistant_message,
                    "parameters": None,
                    "is_complete": False
                }
        
        except Exception as e:
            raise RuntimeError(f"Error calling AI service: {str(e)}")
    
    def _should_generate_parameters(self, assistant_message: str, history: List[Dict[str, str]]) -> bool:
        """
        Determine if we have enough information to generate parameters.
        
        Args:
            assistant_message: Latest assistant message
            history: Conversation history
        
        Returns:
            True if ready to generate parameters
        """
        # Simple heuristic: if assistant mentions generating parameters or we have enough context
        lower_message = assistant_message.lower()
        if any(phrase in lower_message for phrase in [
            "generate parameters",
            "create the parameter",
            "i'll generate",
            "here are the parameters",
            "let me generate"
        ]):
            return True
        
        # Also check if we have substantial conversation (at least 4 exchanges)
        user_messages = [msg for msg in history if msg.get("role") == "user"]
        if len(user_messages) >= 4:
            # Check if assistant is wrapping up
            if any(phrase in lower_message for phrase in [
                "based on what",
                "now i'll",
                "let me create",
                "i'll now generate"
            ]):
                return True
        
        return False
    
    def _generate_parameters(self, full_conversation: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        """
        Generate Spec Kit parameters from the full conversation.
        
        Args:
            full_conversation: Complete conversation history including system prompt
        
        Returns:
            Dictionary mapping phase names to parameter dictionaries
        """
        # Create a prompt to extract parameters
        extraction_prompt = """Based on our conversation, generate Spec Kit command parameters for all phases.

For each phase, provide appropriate parameters that would help Spec Kit understand the project context:

1. **Constitution Phase**: Project principles, governance rules, coding standards, team guidelines
2. **Specify Phase**: Detailed feature specification, requirements, user stories, acceptance criteria
3. **Clarify Phase**: Areas that need clarification, open questions, ambiguous requirements
4. **Plan Phase**: Implementation approach, architecture decisions, technical constraints
5. **Tasks Phase**: Task breakdown structure, dependencies, priorities
6. **Analyze Phase**: Analysis focus areas, metrics to track, success criteria

Format your response as a structured description for each phase that can be used as command parameters. Be specific and comprehensive based on the conversation.

Respond in this format:
CONSTITUTION: [parameters for constitution phase]
SPECIFY: [parameters for specify phase]
CLARIFY: [parameters for clarify phase]
PLAN: [parameters for plan phase]
TASKS: [parameters for tasks phase]
ANALYZE: [parameters for analyze phase]"""
        
        messages = full_conversation + [{"role": "user", "content": extraction_prompt}]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent extraction
                max_tokens=2000
            )
            
            extracted_text = response.choices[0].message.content
            
            # Parse the extracted parameters
            parameters = self._parse_parameters(extracted_text, full_conversation)
            
            return parameters
        
        except Exception as e:
            raise RuntimeError(f"Error generating parameters: {str(e)}")
    
    def _parse_parameters(self, extracted_text: str, conversation: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        """
        Parse parameters from AI response.
        
        Args:
            extracted_text: AI response with parameters
            conversation: Full conversation for context
        
        Returns:
            Dictionary mapping phase names to parameter dictionaries
        """
        parameters = {}
        
        # Extract project description from conversation
        project_description = ""
        for msg in conversation:
            if msg.get("role") == "user" and len(msg.get("content", "")) > 50:
                project_description += msg.get("content", "") + " "
        
        # Parse each phase from the extracted text
        phase_mapping = {
            'constitution': ['CONSTITUTION', 'constitution'],
            'specify': ['SPECIFY', 'specify'],
            'clarify': ['CLARIFY', 'clarify'],
            'plan': ['PLAN', 'plan'],
            'tasks': ['TASKS', 'tasks'],
            'analyze': ['ANALYZE', 'analyze']
        }
        
        for phase_id, phase_keywords in phase_mapping.items():
            phase_params = {}
            
            # Find the section for this phase
            phase_content = None
            for keyword in phase_keywords:
                pattern = f"{keyword}:"
                if pattern in extracted_text:
                    # Extract content after the keyword
                    start_idx = extracted_text.find(pattern) + len(pattern)
                    # Find next phase or end of text
                    next_phase_idx = len(extracted_text)
                    for other_keyword in ['CONSTITUTION:', 'SPECIFY:', 'CLARIFY:', 'PLAN:', 'TASKS:', 'ANALYZE:']:
                        if other_keyword in extracted_text[start_idx:]:
                            idx = extracted_text.find(other_keyword, start_idx)
                            if idx < next_phase_idx:
                                next_phase_idx = idx
                    
                    phase_content = extracted_text[start_idx:next_phase_idx].strip()
                    break
            
            # If no specific content found, use a default based on project description
            if not phase_content or len(phase_content) < 20:
                if phase_id == 'constitution':
                    phase_content = f"Project principles and governance for: {project_description[:200]}"
                elif phase_id == 'specify':
                    phase_content = f"Feature specification: {project_description[:200]}"
                elif phase_id == 'clarify':
                    phase_content = "Clarification questions and open items to resolve"
                elif phase_id == 'plan':
                    phase_content = f"Implementation planning for: {project_description[:200]}"
                elif phase_id == 'tasks':
                    phase_content = "Task breakdown and implementation steps"
                elif phase_id == 'analyze':
                    phase_content = "Analysis of implementation and outcomes"
            
            # Store parameters
            parameters[phase_id] = {
                'command': f'speckit.{phase_id}',
                'parameters': {
                    'description': phase_content
                }
            }
        
        return parameters

