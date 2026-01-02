"""
AI Insights Manager for Time Manager App
Generates personalized productivity insights using DeepSeek AI
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import random


class AIInsightsManager:
    """Manages AI-powered productivity insights generation."""
    
    def __init__(self, app):
        """Initialize with reference to main app."""
        self.app = app
        self.stats_manager = app.stats_manager
        self.db = app.db
        self.chatgpt_assistant = app.chatgpt_assistant
        self.last_insight_type = None
        self.insight_cache = {}
    
    def generate_insight(self, insight_type: str = "auto", data: Dict[str, Any] = None) -> str:
        """
        Generate AI-powered insight.
        
        Args:
            insight_type: Type of insight to generate
                - "auto": Automatically select best insight type
                - "daily": Daily productivity insight
                - "peak": Optimal focus time detection
                - "weekly": Weekly pattern recognition
                - "trends": Productivity trends & comparisons
                - "tasks": Task completion analysis
                - "streak": Streak motivation & predictions
                - "burnout": Burnout prevention
                - "goals": Personalized goal recommendations
                - "schedule": Schedule optimization
                - "time": Morning/evening insights
            data: Pre-gathered data (if None, will gather from database - must be called from main thread)
        
        Returns:
            Generated insight text
        """
        if insight_type == "auto":
            # For auto selection, we need data to check milestones
            if data is None:
                data = self._gather_data(insight_type)
            insight_type = self._select_best_insight_type_from_data(data)
        
        self.last_insight_type = insight_type
        
        # Gather relevant data if not provided (must be called from main thread)
        if data is None:
            data = self._gather_data(insight_type)
        
        # Create AI prompt
        prompt = self._create_prompt(data, insight_type)
        
        # Get AI response
        try:
            ai_response, action = self.chatgpt_assistant.send_message(prompt)
            # Ignore any actions - insights should only provide suggestions, not execute actions
            # Clean the response to remove any ACTION blocks
            cleaned_response = self._clean_insight_response(ai_response)
            return cleaned_response.strip()
        except Exception as e:
            print(f"Error generating AI insight: {e}")
            return self._get_fallback_insight(insight_type, data)
    
    def _clean_insight_response(self, response: str) -> str:
        """Remove any ACTION blocks from insight responses."""
        import re
        # Remove ACTION: blocks (various formats)
        response = re.sub(r'ACTION:\s*\{[^}]*\}', '', response, flags=re.IGNORECASE | re.DOTALL)
        response = re.sub(r'ACTION\s*\{[^}]*\}', '', response, flags=re.IGNORECASE | re.DOTALL)
        # Remove any remaining action-related text
        response = re.sub(r'\bACTION\b\s*:', '', response, flags=re.IGNORECASE)
        return response.strip()
    
    def _select_best_insight_type_from_data(self, data: Dict[str, Any]) -> str:
        """Automatically select the most relevant insight type based on data."""
        now = datetime.now()
        hour = now.hour
        
        # Morning insights
        if 6 <= hour < 12:
            return "time"
        # Evening insights
        elif 18 <= hour < 22:
            return "time"
        # Check for streak milestones
        elif self._check_streak_milestone_from_data(data):
            return "streak"
        # Check for burnout risk
        elif self._check_burnout_risk_from_data(data):
            return "burnout"
        # Default to daily
        else:
            return "daily"
    
    def _gather_data(self, insight_type: str) -> Dict[str, Any]:
        """Gather relevant data for insight generation."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        data = {
            'today_stats': self.stats_manager.get_daily_stats(today),
            'yesterday_stats': self.stats_manager.get_daily_stats(yesterday),
            'weekly_stats': self.stats_manager.get_history_range(7),
            'monthly_stats': self.stats_manager.get_history_range(30),
            'hourly_patterns': self.stats_manager.get_hourly_stats(30),
            'day_patterns': self.stats_manager.get_day_of_week_stats(4),
            'streak': self.stats_manager.get_focus_streak(),
            'all_time': self.stats_manager.get_all_time_stats(),
        }
        
        # Get tasks
        tasks = self.db.get_tasks_by_status(completed=False)
        data['tasks'] = {
            'total': len(tasks),
            'high_priority': sum(1 for t in tasks if (t[8] if len(t) > 8 else None) == 'high'),
            'medium_priority': sum(1 for t in tasks if (t[8] if len(t) > 8 else None) == 'medium'),
            'low_priority': sum(1 for t in tasks if (t[8] if len(t) > 8 else None) == 'low'),
        }
        
        # Get today's schedule
        schedule = self.db.get_today_schedule(limit=10)
        data['schedule'] = len(schedule)
        
        # Current time
        now = datetime.now()
        data['current_time'] = {
            'hour': now.hour,
            'day_of_week': now.strftime('%A'),
            'is_morning': 6 <= now.hour < 12,
            'is_evening': 18 <= now.hour < 22,
        }
        
        return data
    
    def _create_prompt(self, data: Dict[str, Any], insight_type: str) -> str:
        """Create AI prompt based on insight type."""
        
        if insight_type == "daily":
            return self._create_daily_prompt(data)
        elif insight_type == "peak":
            return self._create_peak_prompt(data)
        elif insight_type == "weekly":
            return self._create_weekly_prompt(data)
        elif insight_type == "trends":
            return self._create_trends_prompt(data)
        elif insight_type == "tasks":
            return self._create_tasks_prompt(data)
        elif insight_type == "streak":
            return self._create_streak_prompt(data)
        elif insight_type == "burnout":
            return self._create_burnout_prompt(data)
        elif insight_type == "goals":
            return self._create_goals_prompt(data)
        elif insight_type == "schedule":
            return self._create_schedule_prompt(data)
        elif insight_type == "time":
            return self._create_time_prompt(data)
        else:
            return self._create_daily_prompt(data)
    
    def _create_daily_prompt(self, data: Dict) -> str:
        """Create prompt for daily productivity insight."""
        today = data['today_stats']
        yesterday = data['yesterday_stats']
        streak = data['streak']
        
        # Calculate change
        if yesterday['focus_minutes'] > 0:
            change_pct = ((today['focus_minutes'] - yesterday['focus_minutes']) / yesterday['focus_minutes']) * 100
        else:
            change_pct = 100 if today['focus_minutes'] > 0 else 0
        
        prompt = f"""**CRITICAL: This is an AI Insights request. DO NOT use ACTION blocks. Only provide text suggestions and insights. DO NOT execute any actions like starting timers, adding tasks, or creating events.**

Analyze this user's daily productivity and provide a personalized, encouraging insight (1-2 sentences max):

Today's Performance:
- Focus sessions: {today['pomodoros']}
- Focus time: {today['focus_minutes']} minutes
- Change from yesterday: {change_pct:+.0f}%
- Current streak: {streak['current']} days (best: {streak['best']} days)
- Active tasks: {data['tasks']['total']} ({data['tasks']['high_priority']} high priority)

Provide a concise, motivating insight highlighting their achievement or suggesting improvement. Be friendly and encouraging. Remember: Only provide text suggestions. Do not include any ACTION blocks in your response."""
        
        return prompt
    
    def _create_peak_prompt(self, data: Dict) -> str:
        """Create prompt for peak productivity hours."""
        hourly = data['hourly_patterns']
        
        if not any(hourly.values()):
            return "You haven't tracked enough focus sessions yet. Start a timer to begin building your productivity patterns!"
        
        # Find peak hour
        peak_hour = max(hourly.items(), key=lambda x: x[1])[0]
        peak_minutes = hourly[peak_hour]
        total_minutes = sum(hourly.values())
        peak_percentage = (peak_minutes / total_minutes * 100) if total_minutes > 0 else 0
        
        prompt = f"""**CRITICAL: This is an AI Insights request. DO NOT use ACTION blocks. Only provide text suggestions and insights. DO NOT execute any actions like starting timers, adding tasks, or creating events.**

Analyze this user's productivity patterns and provide insight about their optimal focus time (1-2 sentences max):

Hourly Focus Patterns (last 30 days):
- Peak hour: {peak_hour}:00 ({peak_minutes} minutes, {peak_percentage:.0f}% of total)
- Total focus time: {total_minutes} minutes
- Current time: {data['current_time']['hour']}:00

Provide actionable advice about when they should schedule important work. Be specific and helpful. Remember: Only provide text suggestions. Do not include any ACTION blocks in your response."""
        
        return prompt
    
    def _create_weekly_prompt(self, data: Dict) -> str:
        """Create prompt for weekly patterns."""
        day_patterns = data['day_patterns']
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        if not any(day_patterns.values()):
            return "Start tracking your focus sessions to discover your weekly productivity patterns!"
        
        best_day_idx = max(day_patterns.items(), key=lambda x: x[1])[0]
        best_day_name = day_names[best_day_idx]
        best_day_minutes = day_patterns[best_day_idx]
        
        # Find worst day
        active_days = [i for i, v in day_patterns.items() if v > 0]
        if active_days:
            worst_day_idx = min(active_days, key=lambda i: day_patterns[i])
            worst_day_name = day_names[worst_day_idx]
            worst_day_minutes = day_patterns[worst_day_idx]
        else:
            worst_day_name = "N/A"
            worst_day_minutes = 0
        
        prompt = f"""**CRITICAL: This is an AI Insights request. DO NOT use ACTION blocks. Only provide text suggestions and insights. DO NOT execute any actions like starting timers, adding tasks, or creating events.**

Analyze this user's weekly productivity patterns and provide insight (1-2 sentences max):

Day-of-Week Patterns (last 4 weeks):
- Best day: {best_day_name} ({best_day_minutes} minutes)
- Weakest day: {worst_day_name} ({worst_day_minutes} minutes)
- Current day: {data['current_time']['day_of_week']}

Provide specific advice about their weekly patterns and how to optimize productivity. Be encouraging. Remember: Only provide text suggestions. Do not include any ACTION blocks in your response."""
        
        return prompt
    
    def _create_trends_prompt(self, data: Dict) -> str:
        """Create prompt for productivity trends."""
        weekly = data['weekly_stats']
        monthly = data['monthly_stats']
        
        # Calculate week-over-week change
        if len(weekly) >= 7:
            this_week = sum(d.get('focus_minutes', 0) if isinstance(d, dict) else 0 for d in weekly.values())
            last_week_days = list(weekly.keys())[:7]
            last_week = sum(weekly.get(d, {}).get('focus_minutes', 0) if isinstance(weekly.get(d), dict) else 0 for d in last_week_days)
            
            if last_week > 0:
                week_change = ((this_week - last_week) / last_week) * 100
            else:
                week_change = 100 if this_week > 0 else 0
        else:
            week_change = 0
            this_week = sum(d.get('focus_minutes', 0) if isinstance(d, dict) else 0 for d in weekly.values())
        
        prompt = f"""**CRITICAL: This is an AI Insights request. DO NOT use ACTION blocks. Only provide text suggestions and insights. DO NOT execute any actions like starting timers, adding tasks, or creating events.**

Analyze this user's productivity trends and provide a motivating insight (1-2 sentences max):

Trend Analysis:
- This week: {this_week} minutes focused
- Week-over-week change: {week_change:+.0f}%
- All-time total: {data['all_time']['focus_minutes']} minutes ({data['all_time']['pomodoros']} sessions)
- Current streak: {data['streak']['current']} days

Highlight their progress and provide encouragement. Be specific about improvements. Remember: Only provide text suggestions. Do not include any ACTION blocks in your response."""
        
        return prompt
    
    def _create_tasks_prompt(self, data: Dict) -> str:
        """Create prompt for task analysis."""
        tasks = data['tasks']
        
        prompt = f"""**CRITICAL: This is an AI Insights request. DO NOT use ACTION blocks. Only provide text suggestions and insights. DO NOT execute any actions like starting timers, adding tasks, or creating events.**

Analyze this user's task patterns and provide actionable insight (1-2 sentences max):

Task Overview:
- Total active tasks: {tasks['total']}
- High priority: {tasks['high_priority']}
- Medium priority: {tasks['medium_priority']}
- Low priority: {tasks['low_priority']}
- Today's focus: {data['today_stats']['pomodoros']} sessions, {data['today_stats']['focus_minutes']} minutes

Provide advice on task prioritization or focus strategy. Be practical and helpful. Remember: Only provide text suggestions. Do not include any ACTION blocks in your response."""
        
        return prompt
    
    def _create_streak_prompt(self, data: Dict) -> str:
        """Create prompt for streak insights."""
        streak = data['streak']
        today_stats = data['today_stats']
        
        progress_to_best = (streak['current'] / streak['best'] * 100) if streak['best'] > 0 else 0
        days_to_beat = streak['best'] - streak['current'] if streak['current'] < streak['best'] else 0
        
        prompt = f"""**CRITICAL: This is an AI Insights request. DO NOT use ACTION blocks. Only provide text suggestions and insights. DO NOT execute any actions like starting timers, adding tasks, or creating events.**

Analyze this user's focus streak and provide motivating insight (1-2 sentences max):

Streak Status:
- Current streak: {streak['current']} days
- Best streak: {streak['best']} days
- Progress to best: {progress_to_best:.0f}%
- Today's sessions: {today_stats['pomodoros']} ({today_stats['focus_minutes']} minutes)
- Days to beat record: {days_to_beat}

Provide encouragement and motivation. Celebrate achievements or inspire them to continue. Remember: Only provide text suggestions. Do not include any ACTION blocks in your response."""
        
        return prompt
    
    def _create_burnout_prompt(self, data: Dict) -> str:
        """Create prompt for burnout prevention."""
        weekly = data['weekly_stats']
        recent_days = list(weekly.keys())[-5:] if len(weekly) >= 5 else list(weekly.keys())
        recent_sessions = sum(weekly.get(d, {}).get('pomodoros', 0) if isinstance(weekly.get(d), dict) else 0 for d in recent_days)
        
        prompt = f"""**CRITICAL: This is an AI Insights request. DO NOT use ACTION blocks. Only provide text suggestions and insights. DO NOT execute any actions like starting timers, adding tasks, or creating events.**

Analyze this user's activity level and provide burnout prevention insight (1-2 sentences max):

Recent Activity:
- Last 5 days: {recent_sessions} focus sessions
- Today: {data['today_stats']['pomodoros']} sessions, {data['today_stats']['focus_minutes']} minutes
- Current streak: {data['streak']['current']} days

Assess if they need rest or if they're maintaining healthy balance. Be caring and supportive. Remember: Only provide text suggestions. Do not include any ACTION blocks in your response."""
        
        return prompt
    
    def _create_goals_prompt(self, data: Dict) -> str:
        """Create prompt for goal recommendations."""
        weekly = data['weekly_stats']
        today = data['today_stats']
        
        # Calculate average
        avg_daily = sum(d.get('pomodoros', 0) if isinstance(d, dict) else 0 for d in weekly.values()) / max(len(weekly), 1)
        
        suggested_goal = int(avg_daily * 1.2)  # 20% above average
        
        prompt = f"""**CRITICAL: This is an AI Insights request. DO NOT use ACTION blocks. Only provide text suggestions and insights. DO NOT execute any actions like starting timers, adding tasks, or creating events.**

Suggest a personalized daily goal for this user (1-2 sentences max):

Current Performance:
- Today: {today['pomodoros']} sessions, {today['focus_minutes']} minutes
- Weekly average: {avg_daily:.1f} sessions per day
- Suggested goal: {suggested_goal} sessions today
- All-time best day: Check patterns

Provide a realistic, motivating goal recommendation. Be encouraging but not overwhelming. Remember: Only provide text suggestions. Do not include any ACTION blocks in your response."""
        
        return prompt
    
    def _create_schedule_prompt(self, data: Dict) -> str:
        """Create prompt for schedule optimization."""
        hourly = data['hourly_patterns']
        schedule_count = data['schedule']
        peak_hour = max(hourly.items(), key=lambda x: x[1])[0] if any(hourly.values()) else None
        
        prompt = f"""**CRITICAL: This is an AI Insights request. DO NOT use ACTION blocks. Only provide text suggestions and insights. DO NOT execute any actions like starting timers, adding tasks, or creating events.**

Analyze this user's schedule and productivity patterns (1-2 sentences max):

Schedule & Productivity:
- Today's events: {schedule_count}
- Peak focus hour: {peak_hour}:00 (if available)
- Current hour: {data['current_time']['hour']}:00
- Today's focus: {data['today_stats']['pomodoros']} sessions

Provide advice on schedule optimization or time management. Be practical. Remember: Only provide text suggestions. Do not include any ACTION blocks in your response."""
        
        return prompt
    
    def _create_time_prompt(self, data: Dict) -> str:
        """Create prompt for time-of-day insights."""
        current = data['current_time']
        hourly = data['hourly_patterns']
        today = data['today_stats']
        
        time_context = "morning" if current['is_morning'] else "evening" if current['is_evening'] else "day"
        
        if any(hourly.values()):
            peak_hour = max(hourly.items(), key=lambda x: x[1])[0]
        else:
            peak_hour = None
        
        prompt = f"""**CRITICAL: This is an AI Insights request. DO NOT use ACTION blocks. Only provide text suggestions and insights. DO NOT execute any actions like starting timers, adding tasks, or creating events.**

Provide a time-aware productivity insight for this {time_context} (1-2 sentences max):

Current Context:
- Time: {current['hour']}:00 ({time_context})
- Day: {current['day_of_week']}
- Today's progress: {today['pomodoros']} sessions, {today['focus_minutes']} minutes
- Peak hour: {peak_hour}:00 (if available)

Provide contextually relevant advice for this time of day. Be motivating and actionable. Remember: Only provide text suggestions. Do not include any ACTION blocks in your response."""
        
        return prompt
    
    def _check_streak_milestone_from_data(self, data: Dict[str, Any]) -> bool:
        """Check if user is near a streak milestone."""
        streak = data.get('streak', {'current': 0})
        milestones = [7, 14, 21, 30, 50, 100]
        return any(abs(streak['current'] - m) <= 2 for m in milestones)
    
    def _check_burnout_risk_from_data(self, data: Dict[str, Any]) -> bool:
        """Check if user might be at risk of burnout."""
        weekly = data.get('weekly_stats', {})
        recent_days = list(weekly.keys())[-3:] if len(weekly) >= 3 else list(weekly.keys())
        recent_sessions = sum(weekly.get(d, {}).get('pomodoros', 0) if isinstance(weekly.get(d), dict) else 0 for d in recent_days)
        return recent_sessions > 15  # More than 5 sessions per day average
    
    def _get_fallback_insight(self, insight_type: str, data: Dict) -> str:
        """Get fallback insight if AI fails."""
        fallbacks = {
            "daily": f"You've completed {data['today_stats']['pomodoros']} focus sessions today. Keep up the great work!",
            "peak": "Track your focus sessions to discover your most productive hours.",
            "weekly": "Consistency is key! Track your sessions to see your weekly patterns.",
            "trends": "Every session counts toward building better productivity habits.",
            "tasks": f"You have {data['tasks']['total']} active tasks. Focus on one at a time!",
            "streak": f"Your current streak is {data['streak']['current']} days. Keep it going!",
            "burnout": "Remember to take breaks between focus sessions for optimal performance.",
            "goals": "Set small, achievable goals and build momentum from there.",
            "schedule": "Plan your day around your peak productivity hours.",
            "time": "Make the most of this time! Start a focus session to build momentum.",
        }
        return fallbacks.get(insight_type, "Keep tracking your productivity to unlock personalized insights!")

