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
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize AI interview service.
        
        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            model: OpenAI model to use (default: gpt-4o for quality. Use gpt-4o-mini for lower cost)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        
        # System prompt for the interview
        self.system_prompt = """You are an expert product analyst conducting a deep-dive interview to generate comprehensive Spec Kit command parameters.

Your goal is to ask probing, thoughtful questions to deeply understand:
1. **Project Purpose**: What problem does this solve? Who is the target user? What are the pain points?
2. **Requirements & Features**: What are the core features? What are nice-to-haves? What are non-goals?
3. **User Experience**: What is the user journey? How should users feel when using this? What UX principles matter?
4. **Technical Context**: What technologies, frameworks, constraints? What integrations are needed? What's the architecture?
5. **Constraints & Limitations**: What are the technical, business, or resource constraints? What's out of scope?
6. **Success Criteria**: How will success be measured? What metrics matter? What does "done" look like?

IMPORTANT: Ask DEEP, PROBING questions. Don't accept surface-level answers. Follow up with "why?", "how?", "what if?" questions. 
Dig into details, edge cases, and implications. Aim for 8-12 meaningful exchanges before generating parameters.

The Spec Kit phases need:
- **Constitution**: Detailed principles, governance, constraints, non-goals, UX guidelines
- **Specify**: Comprehensive feature specs, user stories, acceptance criteria, edge cases
- **Clarify**: Specific open questions, ambiguous areas, decisions needed
- **Plan**: Detailed implementation approach, architecture, technical decisions, migration paths
- **Tasks**: Structured task breakdown with dependencies and priorities
- **Analyze**: Specific metrics, success criteria, evaluation methods

Ask ONE question at a time. Be conversational but thorough. Only suggest generating parameters when you have comprehensive, detailed information."""
    
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
                max_tokens=1500  # Increased for more detailed questions
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
        # Count meaningful user responses (exclude very short ones)
        user_messages = [msg for msg in history if msg.get("role") == "user" and len(msg.get("content", "")) > 20]
        
        lower_message = assistant_message.lower()
        
        # Only generate if assistant explicitly says so AND we have substantial conversation
        explicit_indicators = [
            "generate parameters",
            "create the parameter",
            "i'll generate",
            "here are the parameters",
            "let me generate",
            "finalize these parameters",
            "ready to generate",
            "generate the command parameters"
        ]
        
        # Require at least 6-8 meaningful exchanges before considering completion
        has_enough_exchanges = len(user_messages) >= 6
        
        # Check for explicit generation intent
        has_explicit_intent = any(phrase in lower_message for phrase in explicit_indicators)
        
        # Also check for user explicitly asking to generate
        if history:
            last_user_msg = history[-1].get("content", "").lower() if history[-1].get("role") == "user" else ""
            user_wants_generate = any(phrase in last_user_msg for phrase in [
                "generate",
                "create parameters",
                "let's go",
                "yes - let's",
                "proceed",
                "go ahead"
            ])
        else:
            user_wants_generate = False
        
        # Generate if: (explicit intent AND enough exchanges) OR (user explicitly requests AND enough exchanges)
        return (has_explicit_intent and has_enough_exchanges) or (user_wants_generate and has_enough_exchanges)
    
    def _generate_parameters(self, full_conversation: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        """
        Generate Spec Kit parameters from the full conversation.
        
        Args:
            full_conversation: Complete conversation history including system prompt
        
        Returns:
            Dictionary mapping phase names to parameter dictionaries
        """
        # Create a prompt to extract parameters
        extraction_prompt = """Based on our comprehensive conversation, generate detailed, structured Spec Kit command parameters for all phases.

Generate RICH, SPECIFIC parameters that capture the full depth of our discussion. Each phase should be comprehensive and actionable.

**CONSTITUTION Phase**: Create a detailed constitution that includes:
- Clear project purpose and problem statement
- Target users and their needs
- Core principles and values (UX, technical, business)
- Non-goals (what this is NOT)
- Constraints (technical, resource, scope)
- Governance rules and standards
- UX principles and guidelines
Format as a readable document that both humans and AI can understand.

**SPECIFY Phase**: Provide comprehensive specifications including:
- Detailed feature descriptions
- User stories and scenarios
- Acceptance criteria
- Edge cases and error handling
- User flows and interactions
- Data requirements

**CLARIFY Phase**: List specific areas needing clarification:
- Open questions that need answers
- Ambiguous requirements
- Decisions that need to be made
- Trade-offs to consider
- Risks and unknowns

**PLAN Phase**: Detail the implementation approach:
- Architecture and technical decisions
- Technology choices and rationale
- Development phases or milestones
- Migration paths (if applicable)
- Integration points
- Performance and scalability considerations

**TASKS Phase**: Provide structured task breakdown:
- Major work areas
- Task dependencies
- Priorities and sequencing
- Deliverables for each task

**Analyze Phase**: Define analysis and evaluation:
- Success metrics and KPIs
- How to measure effectiveness
- User feedback mechanisms
- Quality criteria
- Evaluation methods

For each phase, write comprehensive, detailed content (not just bullet points). The Constitution especially should be a well-structured document similar to a project charter.

Respond in this format:
CONSTITUTION: [comprehensive constitution document]
SPECIFY: [detailed specifications]
CLARIFY: [specific clarification needs]
PLAN: [detailed implementation plan]
TASKS: [structured task breakdown]
ANALYZE: [analysis and evaluation criteria]"""
        
        messages = full_conversation + [{"role": "user", "content": extraction_prompt}]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent extraction
                max_tokens=4000  # Increased for more detailed output
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
                # Try both uppercase and title case
                patterns = [f"{keyword.upper()}:", f"{keyword.title()}:", f"{keyword}:"]
                for pattern in patterns:
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
                        # Clean up: remove leading dashes or numbers if present
                        lines = phase_content.split('\n')
                        cleaned_lines = []
                        for line in lines:
                            # Remove common markdown list prefixes
                            line = line.lstrip('- ').lstrip('* ').lstrip('• ').lstrip()
                            # Remove numbered list prefixes
                            if line and line[0].isdigit() and ('.' in line[:3] or ')' in line[:3]):
                                line = line.split('.', 1)[-1].split(')', 1)[-1].lstrip()
                            cleaned_lines.append(line)
                        phase_content = '\n'.join(cleaned_lines).strip()
                        break
                if phase_content:
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

