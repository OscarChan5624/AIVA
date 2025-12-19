from plyer import notification
from datetime import datetime, time
from notification_manager import NotificationManager


class NotificationService:
    """
    Service for sending system notifications based on user preferences.
    Supports Android, iOS, Windows, macOS, and Linux notifications.
    """
    
    def __init__(self, notification_manager):
        self.notification_manager = notification_manager
    
    def _is_quiet_hours(self):
        """Check if current time is in quiet hours."""
        try:
            prefs = self.notification_manager.get_preferences()
            if not prefs.get('quiet_hours_enabled'):
                return False
            
            now = datetime.now().time()
            start_str = prefs.get('quiet_hours_start', '22:00')
            end_str = prefs.get('quiet_hours_end', '08:00')
            
            start = datetime.strptime(start_str, '%H:%M').time()
            end = datetime.strptime(end_str, '%H:%M').time()
            
            # Handle overnight quiet hours (e.g., 22:00 to 08:00)
            if start > end:
                return now >= start or now <= end
            return start <= now <= end
        except Exception as e:
            print(f"Error checking quiet hours: {e}")
            return False
    
    def send_notification(self, title, message, notification_type):
        """
        Send a notification if enabled and not in quiet hours.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification (e.g., 'session_reminders')
        """
        try:
            prefs = self.notification_manager.get_preferences()
            
            # Check if this notification type is enabled
            if not prefs.get(notification_type, False):
                print(f"Notification disabled: {notification_type}")
                return
            
            # Check quiet hours
            if self._is_quiet_hours():
                print(f"Skipping notification (quiet hours): {title}")
                return
            
            # Send system notification
            notification.notify(
                title=title,
                message=message,
                app_name='Time Manager',
                timeout=10  # seconds
            )
            print(f"✓ Notification sent: {title}")
        except Exception as e:
            print(f"Error sending notification: {e}")
    
    # ===== Focus Session Notifications =====
    
    def notify_session_start(self, duration_minutes):
        """Notify when a focus session starts."""
        self.send_notification(
            title='Focus Session Started! 💪',
            message=f'Stay focused for {duration_minutes} minutes. You got this!',
            notification_type='session_reminders'
        )
    
    def notify_session_complete(self, duration_minutes):
        """Notify when a focus session completes."""
        self.send_notification(
            title='Focus Session Complete! 🎉',
            message=f'Great work! You focused for {duration_minutes} minutes.',
            notification_type='session_reminders'
        )
    
    def notify_session_cancelled(self):
        """Notify when a focus session is cancelled."""
        self.send_notification(
            title='Session Cancelled',
            message='No worries! Try again when you\'re ready.',
            notification_type='session_reminders'
        )
    
    # ===== Break Notifications =====
    
    def notify_break_time(self, break_minutes):
        """Notify when it's time for a break."""
        self.send_notification(
            title='Break Time! ☕',
            message=f'Relax for {break_minutes} minutes. You earned it!',
            notification_type='break_reminders'
        )
    
    def notify_break_complete(self):
        """Notify when break is over."""
        self.send_notification(
            title='Break Complete! 🔄',
            message='Ready to start another focus session?',
            notification_type='break_reminders'
        )
    
    # ===== Daily Goal Notifications =====
    
    def notify_daily_goal(self, goal_minutes=None):
        """Send daily goal reminder."""
        if goal_minutes:
            message = f'Your goal today: {goal_minutes} minutes of focused work!'
        else:
            message = 'Ready to crush your goals today?'
        
        self.send_notification(
            title='Daily Goal Reminder 🎯',
            message=message,
            notification_type='daily_goals'
        )
    
    def notify_daily_goal_achieved(self, minutes_completed):
        """Notify when daily goal is achieved."""
        self.send_notification(
            title='Daily Goal Achieved! 🎉',
            message=f'Amazing! You completed {minutes_completed} minutes today!',
            notification_type='daily_goals'
        )
    
    # ===== Streak Notifications =====
    
    def notify_streak_alert(self, current_streak):
        """Alert user to maintain their streak."""
        self.send_notification(
            title='Don\'t Break Your Streak! 🔥',
            message=f'You have a {current_streak} day streak. Start a session today!',
            notification_type='streak_alerts'
        )
    
    def notify_streak_milestone(self, streak_days):
        """Notify when user reaches a streak milestone."""
        milestones = {
            7: 'One Week',
            14: 'Two Weeks',
            30: 'One Month',
            60: 'Two Months',
            90: 'Three Months',
            180: 'Six Months',
            365: 'One Year'
        }
        
        milestone_name = milestones.get(streak_days, f'{streak_days} Days')
        
        self.send_notification(
            title=f'Streak Milestone: {milestone_name}! 🔥',
            message=f'Incredible! You\'ve maintained a {streak_days} day streak!',
            notification_type='streak_alerts'
        )
    
    # ===== Task Deadline Notifications =====
    
    def notify_task_deadline(self, task_name, hours_until_due):
        """Notify about upcoming task deadline."""
        if hours_until_due <= 1:
            time_text = 'less than 1 hour'
        elif hours_until_due < 24:
            time_text = f'{int(hours_until_due)} hours'
        else:
            days = int(hours_until_due / 24)
            time_text = f'{days} day{"s" if days > 1 else ""}'
        
        self.send_notification(
            title='Task Deadline Alert ⏰',
            message=f'"{task_name}" is due in {time_text}!',
            notification_type='task_deadlines'
        )
    
    def notify_task_overdue(self, task_name):
        """Notify about overdue task."""
        self.send_notification(
            title='Task Overdue! ⚠️',
            message=f'"{task_name}" is past its deadline.',
            notification_type='task_deadlines'
        )
    
    # ===== Weekly Summary Notifications =====
    
    def notify_weekly_summary(self, total_minutes, total_sessions, streak):
        """Send weekly progress summary."""
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        self.send_notification(
            title='Weekly Summary 📊',
            message=f'This week: {hours}h {minutes}m • {total_sessions} sessions • {streak} day streak',
            notification_type='weekly_summary'
        )
    
    # ===== Achievement Notifications =====
    
    def notify_achievement(self, achievement_name, achievement_description):
        """Notify when user unlocks an achievement."""
        self.send_notification(
            title=f'Achievement Unlocked! 🏆',
            message=f'{achievement_name}: {achievement_description}',
            notification_type='achievements'
        )
    
    def notify_pomodoro_milestone(self, total_pomodoros):
        """Notify when user reaches pomodoro milestones."""
        milestones = {
            10: 'First 10 Pomodoros',
            25: '25 Pomodoros',
            50: '50 Pomodoros',
            100: '100 Pomodoros',
            250: '250 Pomodoros',
            500: '500 Pomodoros',
            1000: '1000 Pomodoros'
        }
        
        if total_pomodoros in milestones:
            self.send_notification(
                title='Milestone Reached! 🎯',
                message=f'Congratulations! You\'ve completed {milestones[total_pomodoros]}!',
                notification_type='achievements'
            )


__all__ = ["NotificationService"]

