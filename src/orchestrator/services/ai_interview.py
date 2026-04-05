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

Ask ONE question at a time. Be conversational but thorough. Only suggest generating parameters when you have comprehensive, detailed information.

When the interview is complete, a separate step will turn this transcript into Spec Kit phase parameters: **specific names (controls, APIs, platforms), flows, and decisions stated here should survive into that output**—so prefer precise, concrete answers from the user rather than vague themes."""

    _REFERENCE_SYSTEM_ADDENDUM = """

## Uploaded reference documents (when provided)
A separate user-role message may contain text from files the user uploaded. That material is **not automatically confirmed** by the user. Use it to ask better questions and to suggest details they should validate. **The live chat remains authoritative**: if a document disagrees with the user, follow the user and clarify. Do not treat uploads as decisions until the user agrees in the conversation."""

    def get_initial_question(self) -> str:
        """Get the first question to start the interview."""
        return "Hello! I'm here to help you generate Spec Kit command parameters for your project. Let's start with the basics: What project or feature are you planning to build? Please describe it in a few sentences."
    
    def conduct_interview_step(
        self,
        conversation_history: List[Dict[str, str]],
        user_response: str,
        reference_bundle: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Conduct one step of the interview.
        
        Args:
            conversation_history: List of previous messages in format [{"role": "user/assistant", "content": "..."}]
            user_response: User's response to the previous question
            reference_bundle: Optional project-knowledge text (inline + RAG); injected after system prompt.
        
        Returns:
            Dictionary with:
                - "question": Next question to ask (or None if interview is complete)
                - "parameters": Generated parameters dict (or None if not ready)
                - "is_complete": Boolean indicating if interview is done
        """
        sys_content = self.system_prompt
        if reference_bundle:
            sys_content = sys_content + self._REFERENCE_SYSTEM_ADDENDUM
        messages: List[Dict[str, str]] = [{"role": "system", "content": sys_content}]
        if reference_bundle:
            messages.append({"role": "user", "content": reference_bundle})
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_response})
        
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
            if self._should_generate_parameters(
                assistant_message, conversation_history, user_response
            ):
                # Generate parameters
                parameters = self._generate_parameters(
                    messages + [{"role": "assistant", "content": assistant_message}]
                )
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
    
    def _should_generate_parameters(
        self,
        assistant_message: str,
        history: List[Dict[str, str]],
        user_response: str = "",
    ) -> bool:
        """
        Determine if we have enough information to generate parameters.
        
        Args:
            assistant_message: Latest assistant message
            history: Conversation history (messages before the current user turn)
            user_response: The user's latest message (not always present in history yet)
        
        Returns:
            True if ready to generate parameters
        """
        # Meaningful user turns: history may not yet include the message being processed
        user_messages = [msg for msg in history if msg.get("role") == "user" and len(msg.get("content", "")) > 20]
        current_user = (user_response or "").strip()
        meaningful_user_count = len(user_messages) + (1 if len(current_user) > 20 else 0)

        lower_message = assistant_message.lower()
        lower_user = current_user.lower()

        # Phrases models often use instead of the exact substring "generate parameters"
        explicit_indicators = [
            "generate parameters",
            "create the parameter",
            "i'll generate",
            "here are the parameters",
            "let me generate",
            "finalize these parameters",
            "ready to generate",
            "generate the command parameters",
            "generate detailed",
            "help generate",
            "i can help generate",
            "help you generate",
            "spec kit command parameters",
            "detailed spec kit",
            "comprehensive spec kit",
            "these detailed parameters",
            "spec kit phases",
            "into actionable elements",
            "### constitution",
            "### specify",
        ]

        # Require at least six substantive user turns before extracting
        has_enough_exchanges = meaningful_user_count >= 6

        has_explicit_intent = any(phrase in lower_message for phrase in explicit_indicators)

        # User intent: check the current message (previously only history[-1], which was often the assistant)
        user_finalize_phrases = [
            "generate the parameters",
            "generate parameters",
            "create parameters",
            "finalize",
            "extract parameters",
            "parameter documents",
            "spec-kit parameters",
            "spec kit parameters",
            "let's go",
            "lets go",
            "yes - let's",
            "proceed",
            "go ahead",
            "that's enough",
            "that is enough",
            "i'm satisfied",
            "im satisfied",
            "looks good",
            "ready to finalize",
        ]
        user_wants_generate = any(phrase in lower_user for phrase in user_finalize_phrases)

        return (has_explicit_intent and has_enough_exchanges) or (
            user_wants_generate and has_enough_exchanges
        )

    def extract_parameters_from_transcript(
        self,
        chat_messages: List[Dict[str, str]],
        reference_bundle: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Run structured parameter extraction over the full chat transcript.

        Use when the model produced parameters in prose but automatic completion
        detection did not run (so interview_state never got generated_parameters).
        """
        sys_content = self.system_prompt
        if reference_bundle:
            sys_content = sys_content + self._REFERENCE_SYSTEM_ADDENDUM
        messages: List[Dict[str, str]] = [{"role": "system", "content": sys_content}]
        if reference_bundle:
            messages.append({"role": "user", "content": reference_bundle})
        messages.extend(list(chat_messages))
        return self._generate_parameters(messages)
    
    def _generate_parameters(self, full_conversation: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        """
        Generate Spec Kit parameters from the full conversation.
        
        Args:
            full_conversation: Complete conversation history including system prompt
        
        Returns:
            Dictionary mapping phase names to parameter dictionaries
        """
        # Extraction: prioritize fidelity to the transcript over brevity or generic templates
        extraction_prompt = """You are producing inputs for Spec Kit slash commands (`/speckit.constitution`, `/speckit.specify`, etc.). The transcript above is the ONLY authoritative source.

**Critical rules (read carefully):**
1. **Transcript fidelity**: Carry over concrete details from the conversation—do not replace them with generic product-management boilerplate. If the user named buttons, panels, flows, platforms, libraries, milestones, data stores, or policies, those exact choices (or faithful paraphrases) must appear in the right phase sections.
2. **No thinning**: Do not summarize away lists the user gave (e.g. feature checklists, UI controls, acceptance nuances). Prefer longer, dense text over short high-level blurbs. It is better to be verbose than to lose agreed decisions.
3. **Attribution of decisions**: When the user chose among options (e.g. local-first vs cloud, framework, interaction model), state the decision and the rationale as discussed—not a new rationale.
4. **Place detail in the right phase**: UX and product rules → CONSTITUTION where appropriate; feature behavior, stories, criteria, edge cases → SPECIFY; still-open items only → CLARIFY; stack, architecture, milestones, integrations → PLAN; implementable work units → TASKS; metrics, feedback, success definition → ANALYZE.
5. **If something was not discussed**, you may mark it briefly as NEEDS CLARIFICATION in CLARIFY rather than inventing detail.
6. **Uploaded reference material**: If a reference block was included above the transcript, treat it as **supplementary**. If a fact appears only there and the user never confirmed it in chat, put it in CLARIFY as needing user confirmation (or omit)—do not record it as a decided requirement.

**Per-phase content expectations:**

**CONSTITUTION**: Purpose, users, principles, non-goals, constraints, governance (e.g. licensing, privacy posture if discussed), UX rules—each grounded in what was actually said.

**SPECIFY**: Full feature and behavior description: user-visible controls and flows, interaction modes (drag, click-to-move, etc.), data the app stores, error/edge cases mentioned, acceptance-style criteria tied to named behaviors.

**CLARIFY**: Only genuine open questions or ambiguities left in the transcript; avoid padding.

**PLAN**: Stack (languages, frameworks, libraries named), deployment shape, storage, major components, milestone ordering if the user defined it, integration points (APIs, AI, search, etc.).

**TASKS**: Ordered or grouped work that reflects the real scope discussed (not a generic agile skeleton). Dependencies called out when obvious from the chat.

**ANALYZE**: Success signals, metrics, testing/beta plans, feedback channels—only from the conversation.

Use markdown headings and bullet lists inside each phase block for clarity. Each phase should read like a dense handoff document, not an executive summary.

**Output format (required, exact labels):**
CONSTITUTION:
[content]

SPECIFY:
[content]

CLARIFY:
[content]

PLAN:
[content]

TASKS:
[content]

ANALYZE:
[content]"""
        
        messages = full_conversation + [{"role": "user", "content": extraction_prompt}]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=12000,
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

