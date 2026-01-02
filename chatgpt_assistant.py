"""
Complete AI Assistant for Time Manager App
Updated to use DeepSeek cloud API (official SDK)
Includes enhanced error handling, retry logic, and better action parsing
"""

from deepseek import DeepSeekClient
from typing import Dict, Any, Tuple, Optional, List
import json
import os
from datetime import datetime


class ChatGPTAssistant:
    """
    Handles AI integration for the voice assistant.
    Powered by DeepSeek's official cloud API.
    """
    
    def __init__(self, app, api_key: Optional[str] = None, model_name: str = "deepseek-chat"):
        """
        Initialize AI assistant with DeepSeek.
        
        Args:
            app: Reference to the main Kivy app instance
            api_key: DeepSeek API key (if None, loads from environment)
            model_name: DeepSeek model name (default: deepseek-chat)
        """
        if not api_key:
            api_key = os.getenv('DEEPSEEK_API_KEY')
        
        if not api_key:
            raise ValueError(
                "DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable "
                "or pass api_key parameter. Generate a key at https://platform.deepseek.com/"
            )
        
        self.app = app
        self.client = DeepSeekClient(api_key=api_key)
        self.model_name = model_name
        self.conversation_history = []
        self.max_history = 20  # Keep last 20 messages for context
        
        # Enhanced system prompt with comprehensive capabilities
        self.system_prompt = """You are an intelligent AI assistant for Time Manager, a productivity and focus app.

**CRITICAL: You MUST use ACTION blocks to access user data. You CANNOT answer questions about their stats, tasks, streak, or schedule without using the appropriate ACTION.**

**Your Capabilities:**

1. **Timer Management:**
   - Start focus timers (default 25 min, or custom durations)
   - Stop/pause timers
   - Complete focus sessions

2. **Task Management:**
   - Add tasks with priorities (high/medium/low)
   - View active tasks
   - Mark tasks as complete
   - Delete tasks

3. **Statistics & Analytics:**
   - Show daily/weekly/monthly/all-time focus stats
   - Display focus streaks (current and best)
   - Provide productivity insights

4. **Schedule Management:**
   - View today's schedule/events
   - Show upcoming appointments
   - Create calendar events (basic)

5. **Motivation & Coaching:**
   - Provide productivity tips
   - Offer encouragement
   - Suggest focus strategies

**Response Guidelines:**
- Be friendly, concise, and encouraging (1-2 sentences)
- Acknowledge actions you're taking
- Provide helpful context when relevant

**Action Format:**
When you need to execute an app action, include a JSON block at the END of your response:
ACTION: {"type": "action_name", "param1": value1, "param2": value2}

**Available Actions:**

TIMER:
- {"type": "start_timer", "duration": 25}  // duration in minutes
- {"type": "stop_timer"}  // pause the timer
- {"type": "resume_timer"}  // resume a paused timer
- {"type": "reset_timer"}  // reset timer to 00:00:00
- {"type": "complete_session"}

TASKS:
- {"type": "add_task", "title": "Task name", "priority": "medium"}  // priority: high, medium, low
- {"type": "add_multiple_tasks", "tasks": [{"title": "Task 1", "priority": "high"}, {"title": "Task 2"}]}
- {"type": "view_tasks"}
- {"type": "complete_task", "title": "Task name"}  // complete by task title
- {"type": "suggest_priorities"}  // AI analyzes tasks and suggests what to do first

**PRIORITY DETECTION:**
When adding tasks, ALWAYS infer priority from user's language:
- HIGH priority keywords: "urgent", "important", "asap", "critical", "deadline", "must do", "high priority", "priority"
- LOW priority keywords: "whenever", "eventually", "not urgent", "low priority", "optional", "can wait", "later"
- MEDIUM priority: Default if no priority keywords detected
- If user explicitly says "high/low/medium priority", use that exact priority

CALENDAR:
- {"type": "add_event", "title": "Event name", "time": "4pm", "date": "today"}  // add appointment/meeting to calendar
  // date examples: "today", "tomorrow", "next Monday", "December 5", "12/5", "next week"
- {"type": "add_multiple_events", "events": [{"title": "Event 1", "time": "2pm", "date": "today"}, {"title": "Event 2", "time": "4pm", "date": "tomorrow"}]}

STATS:
- {"type": "get_stats", "period": "today"}  // period: today/week/month/alltime
- {"type": "get_streak"}

SCHEDULE:
- {"type": "view_schedule", "date": "today"}  // date can be "today", "tomorrow", "next Monday", "December 5", etc.

**Examples:**

User: "Start a 25 minute timer"
You: "Starting a 25-minute focus session! ACTION: {"type": "start_timer", "duration": 25}

User: "Reset the timer" or "Clear the timer"
You: "Resetting timer to zero! ACTION: {"type": "reset_timer"}

User: "Resume the timer" or "Continue the timer"
You: "Resuming your timer! ACTION: {"type": "resume_timer"}

User: "How's my streak?" or "What's my streak?"
You: "Let me check your focus streak! ACTION: {"type": "get_streak"}

User: "Show my tasks" or "What are my tasks?"
You: "Here are your tasks! ACTION: {"type": "view_tasks"}

User: "What did I accomplish today?" or "Show my stats"
You: "Let me pull up your stats! ACTION: {"type": "get_stats", "period": "today"}

User: "How did I do this week?"
You: "Checking your weekly progress! ACTION: {"type": "get_stats", "period": "week"}

User: "What's on my schedule?" or "What's my schedule?"
You: "Let me check your schedule! ACTION: {"type": "view_schedule", "date": "today"}

User: "What's my schedule tomorrow?"
You: "Checking tomorrow's schedule! ACTION: {"type": "view_schedule", "date": "tomorrow"}

User: "Do I have anything on Friday?"
You: "Let me check Friday's schedule! ACTION: {"type": "view_schedule", "date": "Friday"}

User: "Appointment with Dr Lee at 4pm today"
You: "I'll add that appointment to your calendar! ACTION: {"type": "add_event", "title": "Appointment with Dr Lee", "time": "4pm"}

User: "Meeting with team at 2pm"
You: "Adding that meeting to your schedule! ACTION: {"type": "add_event", "title": "Meeting with team", "time": "2pm", "date": "today"}

User: "Meeting at 2pm tomorrow"
You: "I'll schedule that meeting for tomorrow! ACTION: {"type": "add_event", "title": "Meeting", "time": "2pm", "date": "tomorrow"}

User: "Dentist appointment on December 5th at 3pm"
You: "Scheduling your dentist appointment! ACTION: {"type": "add_event", "title": "Dentist appointment", "time": "3pm", "date": "December 5"}

User: "Team meeting next Friday at 10am"
You: "Adding team meeting to your calendar! ACTION: {"type": "add_event", "title": "Team meeting", "time": "10am", "date": "next Friday"}

User: "Remind me to call mom"
You: "I'll add that reminder! ACTION: {"type": "add_task", "title": "Call mom", "priority": "medium"}

User: "Add high priority task: finish homework"
You: "Adding that as high priority! ACTION: {"type": "add_task", "title": "Finish homework", "priority": "high"}

User: "I need to finish this report urgently"
You: "Adding that as high priority! ACTION: {"type": "add_task", "title": "Finish report", "priority": "high"}

User: "Add task: organize desk whenever I have time"
You: "Adding that as low priority! ACTION: {"type": "add_task", "title": "Organize desk", "priority": "low"}

User: "Add three tasks: buy milk, call dentist urgently, and finish report"
You: "I'll add all three tasks with appropriate priorities! ACTION: {"type": "add_multiple_tasks", "tasks": [{"title": "Buy milk", "priority": "medium"}, {"title": "Call dentist", "priority": "high"}, {"title": "Finish report", "priority": "medium"}]}

User: "Schedule meetings at 2pm today and 4pm tomorrow"
You: "Adding both meetings! ACTION: {"type": "add_multiple_events", "events": [{"title": "Meeting", "time": "2pm", "date": "today"}, {"title": "Meeting", "time": "4pm", "date": "tomorrow"}]}

User: "I have too many tasks, what should I do?"
You: "Let me help you prioritize! ACTION: {"type": "suggest_priorities"}

User: "Complete buy milk" or "Mark buy milk as done"
You: "I'll mark that as complete! ACTION: {"type": "complete_task", "title": "buy milk"}

User: "I'm feeling unmotivated"
You: "Remember why you started! Every small step counts. How about a quick 25-minute focus session to build momentum?

**MANDATORY RULES:**
1. ALWAYS use ACTION blocks when user asks about their data (stats, tasks, streak, schedule)
2. NEVER say "I don't have access" - use the appropriate ACTION instead
3. If user asks "what's my X", immediately use the corresponding ACTION
4. Be proactive - suggest actions when helpful
5. Keep responses short (1-2 sentences) before the ACTION block
"""
    
    def send_message(self, user_message: str, retry_count: int = 0) -> Tuple[str, Dict[str, Any]]:
        """
        Send message to DeepSeek and parse response for actions.
        Includes automatic retry logic for failed requests.
        """
        max_retries = 3
        
        try:
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                *self.conversation_history[-self.max_history:]
            ]
            
            # Call DeepSeek API
            response = self.client.chat_completion(
                messages=messages,
                model=self.model_name,
                temperature=0.7,
                max_tokens=300
            )
            
            # Extract the response text from ChatCompletion object
            # The deepseek-sdk returns a ChatCompletion object, not a dict
            try:
                ai_message = response.choices[0].message.content.strip()
            except (AttributeError, IndexError):
                ai_message = ""
            
            if not ai_message:
                ai_message = "Sorry, I didn't get a response from DeepSeek."
            
            # Add AI response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_message
            })
            
            # Parse for actions
            action = self._extract_action(ai_message)
            
            # Clean display text (remove ACTION: block)
            display_text = self._clean_display_text(ai_message)
            
            # Log success
            self._log_interaction(user_message, display_text, action)
            
            return display_text, action
            
        except Exception as e:
            error_str = str(e).lower()
            
            print(f"DeepSeek API error (attempt {retry_count + 1}/{max_retries}): {e}")
            
            # Don't retry quota/billing errors
            is_quota_error = (
                "quota" in error_str or 
                "billing" in error_str or
                "insufficient balance" in error_str or
                "limit" in error_str
            )
            
            if is_quota_error:
                error_msg = (
                    "I've reached my usage limit. Please check your DeepSeek plan at "
                    "https://platform.deepseek.com/"
                )
                return error_msg, {}
            
            # Retry logic for temporary errors
            if retry_count < max_retries - 1:
                import time
                wait_time = 2 ** retry_count  # Exponential backoff: 1s, 2s, 4s
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self.send_message(user_message, retry_count + 1)
            
            # All retries failed
            error_msg = self._get_friendly_error_message(e)
            return error_msg, {}
    
    def _extract_response_text(self, response) -> str:
        """
        Extract plain text from DeepSeek response object.
        Handles both object and dict representations.
        """
        try:
            if hasattr(response, "output_text"):
                text = response.output_text
                if text:
                    return text.strip()
            
            response_dict: Dict[str, Any] = {}
            if hasattr(response, "to_dict"):
                response_dict = response.to_dict()
            elif hasattr(response, "model_dump"):
                response_dict = response.model_dump()
            elif isinstance(response, dict):
                response_dict = response
            else:
                try:
                    response_dict = json.loads(str(response))
                except Exception:
                    response_dict = {}
            
            output = response_dict.get("output")
            if isinstance(output, list):
                pieces = []
                for block in output:
                    block_dict = block if isinstance(block, dict) else getattr(block, "__dict__", {}) or {}
                    content = block_dict.get("content")
                    if isinstance(content, list):
                        for item in content:
                            item_dict = item if isinstance(item, dict) else getattr(item, "__dict__", {}) or {}
                            text = item_dict.get("text") or item_dict.get("output_text")
                            if text:
                                pieces.append(text)
                    text = block_dict.get("text")
                    if text:
                        pieces.append(text)
                if pieces:
                    return "\n".join(pieces).strip()
            
            message = response_dict.get("message")
            if isinstance(message, dict):
                text = message.get("content")
                if isinstance(text, str):
                    return text.strip()
                if isinstance(text, list):
                    pieces = [t for t in text if isinstance(t, str)]
                    if pieces:
                        return "\n".join(pieces).strip()
            
        except Exception as e:
            print(f"Error extracting DeepSeek text: {e}")
        
        return str(response)
    
    def _extract_action(self, message: str) -> Dict[str, Any]:
        """
        Extract action JSON from AI response with robust parsing.
        
        Args:
            message: AI's response message
            
        Returns:
            Dictionary containing action details, or empty dict if no action
        """
        if "ACTION:" not in message:
            return {}
        
        try:
            # Extract everything after "ACTION:"
            action_str = message.split("ACTION:", 1)[1].strip()
            
            # Find the JSON object using bracket matching
            bracket_count = 0
            start_idx = -1
            end_idx = -1
            
            for i, char in enumerate(action_str):
                if char == '{':
                    if start_idx == -1:
                        start_idx = i
                    bracket_count += 1
                elif char == '}':
                    bracket_count -= 1
                    if bracket_count == 0 and start_idx != -1:
                        end_idx = i + 1
                        break
            
            if start_idx != -1 and end_idx != -1:
                json_str = action_str[start_idx:end_idx]
                action = json.loads(json_str)
                
                # Validate action structure
                if not isinstance(action, dict):
                    print("Warning: Action is not a dictionary")
                    return {}
                
                if 'type' not in action:
                    print("Warning: Action missing 'type' field")
                    return {}
                
                # Normalize action type to lowercase
                action['type'] = action['type'].lower().strip()
                
                return action
            
            print("Warning: Could not find valid JSON in ACTION block")
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Attempted to parse: {action_str[:100]}...")
        except Exception as e:
            print(f"Error extracting action: {e}")
        
        return {}
    
    def _clean_display_text(self, message: str) -> str:
        """
        Remove ACTION: block from message for clean display.
        
        Args:
            message: Raw AI message
            
        Returns:
            Cleaned message text
        """
        if "ACTION:" in message:
            cleaned = message.split("ACTION:", 1)[0].strip()
            # Remove trailing punctuation artifacts
            return cleaned.rstrip('.')  + '.' if cleaned else message.strip()
        return message.strip()
    
    def execute_action(self, action: Dict[str, Any]) -> str:
        """
        Execute app action based on AI's decision with comprehensive error handling.
        
        Args:
            action: Dictionary containing action type and parameters
            
        Returns:
            String result message from the action
        """
        if not action:
            return ""
        
        action_type = action.get("type", "").lower()
        
        try:
            # TIMER ACTIONS
            if action_type == "start_timer":
                duration = action.get("duration", 25)
                if not isinstance(duration, (int, float)) or duration <= 0 or duration > 240:
                    return "Timer duration must be between 1-240 minutes"
                return self.app.start_timer_voice(int(duration))
            
            elif action_type == "stop_timer" or action_type == "pause_timer":
                return self.app.stop_timer_voice()
            
            elif action_type == "resume_timer":
                return self.app.resume_timer_voice()
            
            elif action_type == "reset_timer":
                return self.app.reset_timer_voice()
            
            elif action_type == "complete_session":
                self.app.complete_session()
                return "Session completed and stats saved!"
            
            # TASK ACTIONS
            elif action_type == "add_task":
                title = action.get("title", "").strip()
                if not title:
                    return "Task title cannot be empty"
                if len(title) > 200:
                    return "Task title is too long (max 200 characters)"
                
                priority = action.get("priority", "medium").lower()
                if priority not in ["high", "medium", "low"]:
                    priority = "medium"
                
                return self.app.add_task_voice(title, priority)
            
            elif action_type == "view_tasks":
                tasks = self.app.tasks_list
                if not tasks:
                    return "You have no active tasks. Ready for a fresh start!"
                
                task_list = []
                for i, task in enumerate(tasks[:7], 1):  # Show max 7 tasks
                    priority = task.get('priority', 'medium')
                    priority_label = "[HIGH]" if priority == 'high' else "[LOW]" if priority == 'low' else ""
                    task_list.append(f"- {task['title']} {priority_label}")
                
                result = "Your active tasks:\n" + "\n".join(task_list)
                if len(tasks) > 7:
                    result += f"\n\n... and {len(tasks) - 7} more"
                return result
            
            elif action_type == "complete_task":
                title = action.get("title", "").strip()
                if not title:
                    return "Task title required"
                
                # Complete task by title
                return self.app.complete_task_by_title(title)
            
            elif action_type == "add_multiple_tasks":
                tasks = action.get("tasks", [])
                if not tasks:
                    return "No tasks provided"
                return self.app.add_multiple_tasks_voice(tasks)
            
            elif action_type == "suggest_priorities":
                return self.app.suggest_task_priorities_voice()
            
            # CALENDAR ACTIONS
            elif action_type == "add_event":
                title = action.get("title", "").strip()
                time_str = action.get("time", "").strip()
                date_hint = action.get("date", "today").strip()  # "today", "tomorrow", etc.
                if not title:
                    return "Event title cannot be empty"
                return self.app.add_event_voice(title, time_str, date_hint)
            
            elif action_type == "add_multiple_events":
                events = action.get("events", [])
                if not events:
                    return "No events provided"
                return self.app.add_multiple_events_voice(events)
            
            # STATS ACTIONS
            elif action_type == "get_stats":
                period = action.get("period", "today").lower()
                if period not in ["today", "week", "month", "alltime"]:
                    period = "today"
                return self.app.get_stats_voice(period)
            
            elif action_type == "get_streak":
                return self.app.get_streak_voice()
            
            # SCHEDULE ACTIONS
            elif action_type == "view_schedule":
                date_hint = action.get("date", "today").strip()
                return self.app.get_schedule_voice(date_hint)
            
            # UNKNOWN ACTION
            else:
                print(f"Unknown action type: {action_type}")
                return ""
                
        except AttributeError as e:
            print(f"❌ App method not found: {e}")
            return "Sorry, that feature isn't available right now"
        except Exception as e:
            print(f"❌ Error executing action '{action_type}': {e}")
            import traceback
            traceback.print_exc()
            return "Oops! Something went wrong. Please try again."
    
    def _get_friendly_error_message(self, error: Exception) -> str:
        """
        Convert technical errors to friendly user messages.
        
        Args:
            error: Exception that occurred
            
        Returns:
            User-friendly error message
        """
        error_str = str(error).lower()
        
        # Check for quota errors first
        if "quota" in error_str or "rate limit" in error_str or "insufficient balance" in error_str:
            return "I've reached my DeepSeek usage limit. Please check your plan at https://platform.deepseek.com/"
        
        if "401" in error_str or "api key" in error_str or "authentication" in error_str:
            return "There's an issue with my DeepSeek API key. Please double-check it!"
        if "timeout" in error_str:
            return "The DeepSeek API is taking too long to respond. Please try again!"
        if "connection" in error_str or "network" in error_str:
            return "I'm having trouble connecting to DeepSeek. Please check your internet connection!"
        if "429" in error_str:
            return "DeepSeek is receiving too many requests. Please wait a moment and try again!"
        return "Sorry, I'm having trouble with DeepSeek right now. Please try again in a moment!"
    
    def _log_interaction(self, user_input: str, ai_response: str, action: Dict[str, Any]):
        """
        Log interactions for debugging and analytics.
        
        Args:
            user_input: User's message
            ai_response: AI's response
            action: Action dictionary
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] User: {user_input[:50]}... | AI: {ai_response[:50]}..."
        if action:
            log_entry += f" | Action: {action.get('type', 'unknown')}"
        print(log_entry)
    
    def reset_conversation(self):
        """Clear conversation history for a fresh start."""
        self.conversation_history = []
        print("✓ Conversation history cleared")
    
    def get_conversation_length(self) -> int:
        """
        Get number of messages in conversation history.
        
        Returns:
            Number of messages
        """
        return len(self.conversation_history)
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the current conversation.
        
        Returns:
            Formatted summary string
        """
        if not self.conversation_history:
            return "No conversation yet"
        
        user_messages = sum(1 for msg in self.conversation_history if msg['role'] == 'user')
        ai_messages = sum(1 for msg in self.conversation_history if msg['role'] == 'assistant')
        
        return f"Conversation: {user_messages} user messages, {ai_messages} AI responses"
    
    def get_token_estimate(self) -> int:
        """
        Rough estimate of tokens used in current conversation.
        (1 token ≈ 4 characters for English text)
        
        Returns:
            Estimated token count
        """
        total_chars = sum(
            len(msg['content']) 
            for msg in self.conversation_history
        )
        system_prompt_chars = len(self.system_prompt)
        
        return (total_chars + system_prompt_chars) // 4
    
    def set_max_history(self, max_messages: int):
        """
        Set maximum conversation history length.
        
        Args:
            max_messages: Maximum number of messages to keep
        """
        if max_messages > 0:
            self.max_history = max_messages
            print(f"✓ Max history set to {max_messages} messages")
    
    def export_conversation(self) -> List[Dict[str, str]]:
        """
        Export conversation history for logging or debugging.
        
        Returns:
            List of message dictionaries
        """
        return self.conversation_history.copy()
    
    def get_model_info(self) -> Dict[str, str]:
        """
        Get information about the current model.
        
        Returns:
            Dictionary with model details
        """
        return {
            "model": self.model_name,
            "provider": "DeepSeek",
            "description": "DeepSeek Chat - versatile assistant optimized for productivity flows",
            "notes": "Uses official DeepSeek cloud API"
        }
    
    def test_connection(self) -> bool:
        """
        Test if the DeepSeek connection is working.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            print("Testing DeepSeek connection...")
            response = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'OK' if you can read this."}
                ],
                model=self.model_name,
                max_tokens=10
            )
            
            # Extract response from ChatCompletion object
            try:
                result = response.choices[0].message.content.strip()
            except (AttributeError, IndexError):
                result = "No response"
            
            print(f"✓ Connection test successful! Response: {result}")
            return True
            
        except Exception as e:
            print(f"✗ Connection test failed: {e}")
            return False