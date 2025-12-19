import os
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, StringProperty, ListProperty, NumericProperty, BooleanProperty, DictProperty
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from timer import PomodoroTimer
from stats_manager import FocusStatsManager
from graph_generator import FocusGraphGenerator
from database_manager import DatabaseManager
from profile_manager import ProfileManager
from notification_manager import NotificationManager
from notification_service import NotificationService
from chatgpt_assistant import ChatGPTAssistant
from voice_handler import VoiceHandler
from task import Task
from calendar_manager import CalendarManager
from event_manager import EventManager
from ai_insights_manager import AIInsightsManager
from datetime import datetime, date, timedelta
# Note: calendar module is now only used in calendar_manager.py

# Load the KV files that define the UI
Builder.load_file('design.kv')
Builder.load_file('login.kv')
Builder.load_file('notifications.kv')
Builder.load_file('subscription.kv')
Builder.load_file('security_password.kv')
Builder.load_file('terms_conditions.kv')
Builder.load_file('voice_chat.kv')
# Note: ai_insights.kv is included via design.kv, no need to load separately


class HomeScreen(BoxLayout):
    pass


class CalendarScreen(Screen):
    pass


class TaskCard(BoxLayout):
    """Task card widget with priority color support."""
    task_id = NumericProperty(0)
    task_title = StringProperty("Task")
    task_priority = StringProperty("medium")
    priority_color = ListProperty([1, 0.8, 0.2, 1])  # Default yellow
    _dot_color_instruction = None
    _dot_ellipse_instruction = None
    
    def get_priority_color(self):
        """Get color based on priority."""
        if self.task_priority == 'high':
            return [0.98, 0.3, 0.3, 1]  # Red
        elif self.task_priority == 'low':
            return [0.3, 0.98, 0.6, 1]  # Green
        else:
            return [1, 0.8, 0.2, 1]  # Yellow/Orange
    
    def on_task_priority(self, instance, value):
        """Update priority color when priority changes."""
        new_color = self.get_priority_color()
        self.priority_color = new_color
        # Update the color instruction if it exists
        if self._dot_color_instruction:
            self._dot_color_instruction.rgba = new_color
        # Also redraw the dot to ensure it's updated
        Clock.schedule_once(lambda dt: self._draw_dot(), 0.1)
    
    def on_priority_color(self, instance, value):
        """Update dot when priority_color changes."""
        Clock.schedule_once(lambda dt: self._draw_dot(), 0.05)
    
    def on_kv_post(self, base_widget):
        """Called after KV rules are applied."""
        super().on_kv_post(base_widget)
        # Initialize priority color after KV is loaded (use current task_priority value)
        self.priority_color = self.get_priority_color()
        # Draw dot after widget is fully built
        Clock.schedule_once(lambda dt: self._draw_dot(), 0.2)
    
    def _draw_dot(self):
        """Draw or update the priority dot."""
        # Check if widget is ready
        if not hasattr(self, 'ids'):
            Clock.schedule_once(lambda dt: self._draw_dot(), 0.1)
            return
        
        if 'priority_dot' not in self.ids:
            Clock.schedule_once(lambda dt: self._draw_dot(), 0.1)
            return
        
        dot = self.ids.priority_dot
        color = self.get_priority_color()
        
        # Clear existing canvas
        dot.canvas.clear()
        
        # Draw the colored circle
        from kivy.graphics import Color, Ellipse
        with dot.canvas:
            self._dot_color_instruction = Color(*color)
            self._dot_ellipse_instruction = Ellipse(pos=dot.pos, size=dot.size)
        
        # Bind to position/size changes (only once)
        if not hasattr(dot, '_dot_bound'):
            dot.bind(pos=self._update_dot_pos, size=self._update_dot_size)
            dot._dot_bound = True
    
    def _update_dot_pos(self, instance, pos):
        """Update dot position when widget moves."""
        if self._dot_ellipse_instruction:
            self._dot_ellipse_instruction.pos = pos
    
    def _update_dot_size(self, instance, size):
        """Update dot size when widget resizes."""
        if self._dot_ellipse_instruction:
            self._dot_ellipse_instruction.size = size

# Register TaskCard with Factory
Factory.register('TaskCard', cls=TaskCard)


class Home(App):
    # Kivy properties for dynamic stats display (default: daily only)
    stats_text = StringProperty("Pomodoros: 0  •  Focus time: 0m")
    schedule_text = StringProperty("• No schedule for today")
    tasks_list = ListProperty([])
    tasks_summary_text = StringProperty("No tasks yet")
    
    # Calendar properties
    current_year = NumericProperty(0)
    current_month = NumericProperty(0)
    selected_year = NumericProperty(0)
    selected_month = NumericProperty(0)
    calendar_events = ListProperty([])
    month_year_text = StringProperty("")
    today_text = StringProperty("")
    
    # Day events popup reference
    current_day_events_popup = ObjectProperty(None, allownone=True)
    current_day_events_date = StringProperty("")
    
    # Event management properties
    selected_event_date = StringProperty(None, allownone=True)
    selected_event_time = StringProperty(None, allownone=True)
    selected_hour = NumericProperty(None, allownone=True)
    selected_minute = NumericProperty(None, allownone=True)
    selected_ampm = StringProperty(None, allownone=True)
    is_recurring = BooleanProperty(False)
    selected_repeat_days = ListProperty([])
    date_picker_year = NumericProperty(0)
    date_picker_month = NumericProperty(0)
    current_event_popup = ObjectProperty(None, allownone=True)
    date_picker_popup = ObjectProperty(None, allownone=True)
    time_picker_popup = ObjectProperty(None, allownone=True)
    
    # Analytics cache properties
    analytics_cache_date = StringProperty("")  # Last date analytics were generated
    analytics_cached_hourly_path = StringProperty("")
    analytics_cached_day_pattern_path = StringProperty("")
    analytics_cached_insights = DictProperty({})  # Store insights text
    
    # AI Insights property
    ai_insight_text = StringProperty("Analyzing your productivity patterns...")
    
    def build(self):
        # Constrain window to iPhone 14 Pro size on desktop
        Window.size = (393, 830)
        Window.minimum_width = 393
        Window.minimum_height = 830
        Window.maximum_width = 430
        Window.maximum_height = 900
        Window.clearcolor = (1, 1, 1, 1)
        
        # Create screen manager
        sm = ScreenManager()
        sm.transition = NoTransition()  # Disable animation for instant screen switching
        
        # Handle window close to run cleanup promptly and avoid hangs
        Window.bind(on_request_close=self._on_request_close)
        
        # Create login screen (first screen)
        login_screen = Factory.LoginScreen()
        login_screen.name = 'login'
        sm.add_widget(login_screen)
        
        # Create home screen (wrap MyHome in Screen)
        home_content = Factory.MyHome()
        self.home_content = home_content  # Store reference for profile updates
        home_screen = Screen(name='home')
        home_screen.add_widget(home_content)
        sm.add_widget(home_screen)
        
        # Create calendar screen
        calendar_screen = Factory.CalendarScreen()
        calendar_screen.name = 'calendar'
        sm.add_widget(calendar_screen)
        
        # Create analytics screen
        analytics_screen = Factory.AnalyticsScreen()
        analytics_screen.name = 'analytics'
        sm.add_widget(analytics_screen)
        
        # Create profile screen
        profile_screen = Factory.ProfileScreen()
        profile_screen.name = 'profile'
        sm.add_widget(profile_screen)
        
        # Create edit profile screen
        edit_profile_screen = Factory.EditProfileScreen()
        edit_profile_screen.name = 'edit_profile'
        sm.add_widget(edit_profile_screen)
        
        # Create notification settings screen
        notification_settings_screen = Factory.NotificationSettingsScreen()
        notification_settings_screen.name = 'notification_settings'
        sm.add_widget(notification_settings_screen)
        
        # Create subscription screen
        subscription_screen = Factory.SubscriptionScreen()
        subscription_screen.name = 'subscription'
        sm.add_widget(subscription_screen)
        
        # Create security & password screen
        security_password_screen = Factory.SecurityPasswordScreen()
        security_password_screen.name = 'security_password'
        sm.add_widget(security_password_screen)
        
        # Create terms & conditions screen
        terms_conditions_screen = Factory.TermsConditionsScreen()
        terms_conditions_screen.name = 'terms_conditions'
        sm.add_widget(terms_conditions_screen)
        
        # Initialize app components
        self.timer = PomodoroTimer(self, minutes=0)
        self.stats_manager = FocusStatsManager()
        self.graph_generator = FocusGraphGenerator()
        self.db = DatabaseManager()
        self.profile_manager = ProfileManager()
        self.notification_manager = NotificationManager()
        self.notification_service = NotificationService(self.notification_manager)
        self.calendar_manager = CalendarManager(self)
        self.event_manager = EventManager(self)
        
        # Initialize AI voice assistant (DeepSeek cloud API)
        # Get your DeepSeek API key at: https://platform.deepseek.com/
        # TODO: Replace with your DeepSeek API key or set DEEPSEEK_API_KEY environment variable
        DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-b66cf4edabb946d0af371dea42ee531b")  # Replace with your real key!
        self.chatgpt_assistant = ChatGPTAssistant(self, api_key=DEEPSEEK_API_KEY)
        self.voice_handler = VoiceHandler()
        self.voice_popup = None  # Will store reference to voice chat popup
        
        # Initialize AI Insights Manager
        self.ai_insights_manager = AIInsightsManager(self)
        
        self.root = sm
        
        # Initialize home screen
        self.timer.reset()
        self.update_stats_display()  # Initialize stats display
        self.update_schedule_display()  # Initialize schedule
        self.load_tasks()  # Load tasks from database
        self.load_profile_data()  # Load profile data (username/email)
        
        # Initialize calendar screen
        self.calendar_manager.initialize_calendar()
        self.load_calendar_events()  # Load calendar events into memory
        
        # Generate initial AI insight
        Clock.schedule_once(lambda dt: self.refresh_ai_insights(), 1.0)
        
        # Schedule daily notifications check (every hour)
        Clock.schedule_interval(self.check_daily_notifications, 3600)  # Check every hour
        
        # Initialize shutdown flag
        self._is_shutting_down = False
        
        # Start at login screen
        sm.current = 'login'
        
        return sm

    # Open the time picker popup
    def open_time_picker(self):
        popup = Factory.TimePickerPopup()
        popup.open()

    # Apply hours/minutes from the popup
    def apply_time_from_picker(self, popup):
        try:
            hours = int(popup.ids.hours.value)
            minutes = int(popup.ids.minutes.value)
        except Exception:
            popup.dismiss()
            return
        self.timer.set_hm(hours, minutes)
        popup.dismiss()
    
    def complete_session(self):
        """Mark current timer session as completed and track stats."""
        # Schedule on main thread to avoid graphics instruction errors
        def _complete_on_main_thread(dt):
            # Get elapsed focus time BEFORE resetting the timer
            focus_minutes = self.timer.get_elapsed_focus_minutes()
            
            # Save session if there's focus time
            if focus_minutes > 0:
                try:
                    self.stats_manager.add_completed_session(focus_minutes)
                    
                    # Check for achievements
                    alltime_stats = self.stats_manager.get_all_time_stats()
                    total_pomodoros = alltime_stats['pomodoros']
                    
                    # Notify pomodoro milestones
                    self.notification_service.notify_pomodoro_milestone(total_pomodoros)
                    
                    # Check for streak milestones
                    streak = self.stats_manager.get_focus_streak()
                    current_streak = streak['current']
                    if current_streak in [7, 14, 30, 60, 90, 180, 365]:
                        self.notification_service.notify_streak_milestone(current_streak)
                    
                    # Force immediate update of stats display
                    self.update_stats_display()
                    # Show confirmation popup
                    popup = Factory.SessionCompletePopup()
                    popup.message = f'Great job! You focused for {focus_minutes} minutes.'
                    popup.open()
                except Exception as e:
                    # Show error if saving fails
                    print(f"Error saving session: {e}")
                    popup = Factory.SessionCompletePopup()
                    popup.message = f'Error saving session: {str(e)}'
                    popup.open()
            else:
                # Show message if no focus time
                popup = Factory.SessionCompletePopup()
                popup.message = 'Please start the timer and focus for at least a minute to record stats.'
                popup.open()
            
            # Reset timer for next session (clears session tracking)
            self.timer.reset()
        
        Clock.schedule_once(_complete_on_main_thread, 0)
    
    def open_stats_popup(self):
        """Open detailed statistics popup with daily and all-time stats."""
        daily_stats = self.stats_manager.get_daily_stats()
        alltime_stats = self.stats_manager.get_all_time_stats()
        
        # Create popup using KV template
        popup = Factory.StatsPopup()
        
        # Update the stats labels with actual data
        popup.ids.daily_stats.text = f"Pomodoros: {daily_stats['pomodoros']}\nFocus Time: {daily_stats['focus_minutes']} minutes"
        popup.ids.alltime_stats.text = f"Pomodoros: {alltime_stats['pomodoros']}\nFocus Time: {alltime_stats['focus_minutes']} minutes"
        
        popup.open()
    
    def update_stats_display(self):
        """Update the stats text (daily only by default)."""
        stats = self.stats_manager.get_daily_stats()
        pomodoros = stats['pomodoros']
        focus_minutes = stats['focus_minutes']
        # Add extra spacing between lines for better readability
        self.stats_text = f"Pomodoros: {pomodoros}\n\nFocus time: {focus_minutes}m"
        
        # Cache stats for voice assistant (avoid database queries)
        self._cached_today_stats = {'pomodoros': pomodoros, 'focus_minutes': focus_minutes}
        
        # Also cache weekly stats
        try:
            week_stats = self.stats_manager.get_weekly_stats()
            self._cached_week_stats = week_stats
        except:
            self._cached_week_stats = {'pomodoros': 0, 'focus_minutes': 0}
        
        # Cache streak
        try:
            self._cached_streak = self.stats_manager.get_focus_streak()
        except:
            self._cached_streak = {'current': 0, 'best': 0}
    
    def _switch_tab(self, popup, active_tab):
        """Update tab button active states."""
        popup.ids.tab_stats.active = (active_tab == 'stats')
        popup.ids.tab_weekly.active = (active_tab == 'weekly')
        popup.ids.tab_monthly.active = (active_tab == 'monthly')
    
    def show_stats_tab(self, popup):
        """Show the stats view and hide graph view."""
        self._switch_tab(popup, 'stats')
        popup.ids.stats_view.opacity = 1
        popup.ids.stats_view.disabled = False
        popup.ids.graph_view.opacity = 0
        popup.ids.graph_view.disabled = True
    
    def show_weekly_tab(self, popup):
        """Generate and show weekly graph."""
        self._switch_tab(popup, 'weekly')
        popup.ids.stats_view.opacity = 0
        popup.ids.stats_view.disabled = True
        popup.ids.graph_view.opacity = 1
        popup.ids.graph_view.disabled = False
        
        # Generate weekly graph
        history = self.stats_manager.get_history_range(7)
        graph_path = self.graph_generator.generate_weekly_graph(history)
        popup.ids.graph_image.source = graph_path
        popup.ids.graph_image.reload()
    
    def show_monthly_tab(self, popup):
        """Generate and show monthly graph."""
        self._switch_tab(popup, 'monthly')
        popup.ids.stats_view.opacity = 0
        popup.ids.stats_view.disabled = True
        popup.ids.graph_view.opacity = 1
        popup.ids.graph_view.disabled = False
        
        # Generate monthly graph (get 180 days to cover ~6 months)
        history = self.stats_manager.get_history_range(180)
        graph_path = self.graph_generator.generate_monthly_graph(history)
        popup.ids.graph_image.source = graph_path
        popup.ids.graph_image.reload()
    
    # === Task Management Functions ===
    
    def load_calendar_events(self):
        """Load all calendar events from database into memory for quick access."""
        try:
            # Get all events from database
            from datetime import date, timedelta
            today = date.today()
            # Load events for next 90 days (3 months)
            end_date = today + timedelta(days=90)
            
            events = self.db.get_schedule_by_date_range(today - timedelta(days=30), end_date)
            
            # Convert to list of dicts for easy access
            self.calendar_events = []
            for event in events:
                # event is a tuple: (id, title, start_time, source, description, location, is_recurring, repeat_days)
                self.calendar_events.append({
                    'id': event[0],
                    'title': event[1],
                    'start_time': event[2],
                    'source': event[3] if len(event) > 3 else 'local',
                    'description': event[4] if len(event) > 4 else '',
                    'location': event[5] if len(event) > 5 else '',
                    'is_recurring': event[6] if len(event) > 6 else False,
                    'repeat_days': event[7] if len(event) > 7 else None
                })
            
            print(f"Loaded {len(self.calendar_events)} calendar events")
        except Exception as e:
            print(f"Error loading calendar events: {e}")
            import traceback
            traceback.print_exc()
            self.calendar_events = []
    
    def update_schedule_display(self):
        """Update Today's Schedule from database with calendar events."""
        schedule = self.db.get_today_schedule(limit=3)
        
        if schedule:
            lines = []
            for title, start_time in schedule:
                if start_time:
                    try:
                        dt = datetime.fromisoformat(start_time)
                        # Format time in 12-hour format with AM/PM
                        hour = dt.hour
                        minute = dt.minute
                        am_pm = "AM" if hour < 12 else "PM"
                        hour_12 = hour if hour <= 12 else hour - 12
                        if hour_12 == 0:
                            hour_12 = 12
                        time_str = f"{hour_12}:{minute:02d} {am_pm}"
                    except:
                        time_str = "00:00 AM"
                else:
                    time_str = "00:00 AM"
                lines.append(f"• {time_str} {title}")
            # Add extra spacing between lines for better readability
            self.schedule_text = "\n\n".join(lines)
        else:
            self.schedule_text = "• No schedule for today"
    
    def load_tasks(self):
        """Load incomplete tasks from database."""
        tasks = self.db.get_tasks_by_status(completed=False)
        self.tasks_list = [
            {
                'id': task[0],
                'title': task[1],
                'start_time': task[2] or '',
                'source': task[3],
                'priority': (task[8] if len(task) > 8 and task[8] else 'medium') or 'medium'  # priority column, default to medium if None
            }
            for task in tasks
        ]
        self.update_tasks_summary()
    
    def toggle_task(self, task_id):
        """Toggle task completion status."""
        success = self.db.toggle_task_completion(task_id)
        if success:
            # Small delay to ensure database commit completes
            Clock.schedule_once(lambda dt: self._refresh_after_task_change(), 0.05)
    
    def complete_task_by_title(self, title: str) -> str:
        """Complete a task by its title (for voice commands with fuzzy matching)."""
        try:
            # Find task by title (bidirectional fuzzy matching)
            title_lower = title.lower()
            matching_task = None
            best_match_score = 0
            
            for task in self.tasks_list:
                task_title_lower = task['title'].lower()
                
                # Calculate match score (higher is better)
                score = 0
                
                # Check if search term is in task title
                if title_lower in task_title_lower:
                    score = len(title_lower) / len(task_title_lower)
                
                # Check if task title is in search term (e.g., "mom" in "calling mother")
                elif task_title_lower in title_lower:
                    score = len(task_title_lower) / len(title_lower)
                
                # Check for word-level matches (e.g., "call" matches in both)
                else:
                    search_words = set(title_lower.split())
                    task_words = set(task_title_lower.split())
                    common_words = search_words & task_words
                    if common_words:
                        score = len(common_words) / max(len(search_words), len(task_words))
                
                # Keep track of best match
                if score > best_match_score:
                    best_match_score = score
                    matching_task = task
            
            # Require at least 30% match confidence
            if not matching_task or best_match_score < 0.3:
                return f"Could not find task matching '{title}'"
            
            # Complete the task
            def _complete_on_main_thread(dt):
                self.db.toggle_task_completion(matching_task['id'])
                self._refresh_after_task_change()
            
            Clock.schedule_once(_complete_on_main_thread, 0)
            
            return f"Marked '{matching_task['title']}' as complete!"
        except Exception as e:
            print(f"Error completing task: {e}")
            return "Could not complete task"
    
    def _refresh_after_task_change(self):
        """Refresh UI after task change (delete/complete)."""
        self.load_tasks()  # Refresh task list and summary
        self.update_schedule_display()  # Update schedule
        
        # Refresh the tasks popup if it's open
        if hasattr(self, 'current_tasks_popup') and self.current_tasks_popup:
            try:
                # Update task count
                task_count = len(self.tasks_list)
                if task_count == 0:
                    self.current_tasks_popup.ids.task_count_label.text = "No tasks"
                elif task_count == 1:
                    self.current_tasks_popup.ids.task_count_label.text = "1 task"
                else:
                    self.current_tasks_popup.ids.task_count_label.text = f"{task_count} tasks"
                
                # Re-render the task list
                self.render_tasks_in_popup(self.current_tasks_popup)
            except Exception as e:
                print(f"Error refreshing popup: {e}")
                import traceback
                traceback.print_exc()
    
    def delete_task_by_id(self, task_id):
        """Delete a task."""
        success = self.db.delete_task(task_id)
        if success:
            # Small delay to ensure database commit completes
            Clock.schedule_once(lambda dt: self._refresh_after_task_change(), 0.05)
    
    def update_tasks_summary(self):
        """Update the tasks summary text on main screen."""
        task_count = len(self.tasks_list)
        if task_count == 0:
            self.tasks_summary_text = "No active tasks\nTap the icon to add tasks"
        elif task_count == 1:
            self.tasks_summary_text = "1 active task\nTap to view and manage"
        else:
            self.tasks_summary_text = f"{task_count} active tasks\nTap to view and manage"
    
    def open_tasks_popup(self):
        """Open the tasks management popup."""
        popup = Factory.TasksPopup()
        
        # Store reference to popup for refreshing after delete
        self.current_tasks_popup = popup
        
        # Bind cleanup on dismiss
        popup.bind(on_dismiss=lambda *args: setattr(self, 'current_tasks_popup', None))
        
        # Update task count in header
        task_count = len(self.tasks_list)
        if task_count == 0:
            popup.ids.task_count_label.text = "No tasks"
        elif task_count == 1:
            popup.ids.task_count_label.text = "1 task"
        else:
            popup.ids.task_count_label.text = f"{task_count} tasks"
        
        # Populate task list in popup
        self.render_tasks_in_popup(popup)
        
        popup.open()
    
    def render_tasks_in_popup(self, popup):
        """Render task cards in the popup."""
        tasks_container = popup.ids.popup_tasks_container
        tasks_container.clear_widgets()
        
        if not self.tasks_list:
            # Show "no tasks" message
            no_tasks_label = Factory.Label(
                text="No tasks yet.\nAdd your first task below!",
                color=(0.8, 0.8, 1, 1),
                font_size="15sp",
                size_hint_y=None,
                height=80,
                halign="center",
                valign="middle"
            )
            tasks_container.add_widget(no_tasks_label)
        else:
            for task in self.tasks_list:
                task_card = Factory.TaskCard()
                task_card.task_id = task['id']
                task_card.task_title = task['title']
                # Set priority BEFORE adding widget so on_kv_post uses correct value
                priority = task.get('priority', 'medium')
                task_card.task_priority = priority
                tasks_container.add_widget(task_card)
                # Force update after widget is fully built
                Clock.schedule_once(lambda dt, tc=task_card: tc._draw_dot(), 0.3)
    
    def add_task_from_popup(self, title, popup):
        """Add task from popup and refresh the popup."""
        if not title or not title.strip():
            return
        
        # Get selected priority from buttons
        priority = 'medium'  # default
        if popup.ids.priority_high.state == 'down':
            priority = 'high'
        elif popup.ids.priority_low.state == 'down':
            priority = 'low'
        elif popup.ids.priority_medium.state == 'down':
            priority = 'medium'
        
        task = Task(title=title.strip(), start_time=None, completed=False, source="local", priority=priority)
        self.db.add_task(task)
        self.load_tasks()  # Refresh task list and summary
        self.update_schedule_display()
        
        # Update popup
        task_count = len(self.tasks_list)
        if task_count == 1:
            popup.ids.task_count_label.text = "1 task"
        else:
            popup.ids.task_count_label.text = f"{task_count} tasks"
        
        self.render_tasks_in_popup(popup)
    
    def open_ai_insights_popup(self):
        """Open the AI insights popup with all insight types."""
        try:
            popup = Factory.AIInsightsPopup()
            # Store current insight type for refresh functionality
            popup.current_insight_type = "daily"
            
            # Insight type buttons
            insight_types = [
                ("Daily", "daily"),
                ("Peak Hours", "peak"),
                ("Weekly", "weekly"),
                ("Trends", "trends"),
                ("Tasks", "tasks"),
                ("Streak", "streak"),
                ("Burnout", "burnout"),
                ("Goals", "goals"),
                ("Schedule", "schedule"),
                ("Time", "time"),
            ]
            
            # Create type buttons
            container = popup.ids.insight_types_container
            for label, insight_type in insight_types:
                btn = Button(
                    text=label,
                    size_hint_x=None,
                    width=dp(100),
                    background_normal='',
                    background_color=(0.2, 0.2, 0.35, 1),
                    color=(1, 1, 1, 1),
                    font_size='13sp'
                )
                btn.bind(on_release=lambda instance, it=insight_type: self._show_insight_type(popup, it))
                container.add_widget(btn)
            
            # Show daily insight by default (only one insight at a time)
            self._show_insight_type(popup, "daily")
            
            popup.open()
        except Exception as e:
            print(f"Error opening AI insights popup: {e}")
            import traceback
            traceback.print_exc()
    
    def refresh_ai_insights(self):
        """Refresh AI insights on the home screen card."""
        try:
            # Update status
            home_screen = self.root.get_screen('home')
            if hasattr(home_screen, 'ids') and 'ai_insights_card' in home_screen.ids:
                insight_label = home_screen.ids.ai_insights_card.ids.primary_insight
                insight_label.text = "Generating insights..."
            
            # Gather data in main thread (SQLite must be accessed from main thread)
            data = self.ai_insights_manager._gather_data("auto")
            
            # Generate insight in background
            def generate(data):
                try:
                    insight = self.ai_insights_manager.generate_insight("auto", data=data)
                    Clock.schedule_once(lambda dt: self._update_insight_display(insight), 0)
                except Exception as e:
                    print(f"Error generating insight: {e}")
                    Clock.schedule_once(lambda dt: self._update_insight_display("Unable to generate insights. Please try again."), 0)
            
            from threading import Thread
            Thread(target=generate, args=(data,), daemon=True).start()
        except Exception as e:
            print(f"Error refreshing insights: {e}")
    
    def _update_insight_display(self, insight_text):
        """Update the insight display on main thread."""
        try:
            self.ai_insight_text = insight_text
            home_screen = self.root.get_screen('home')
            if hasattr(home_screen, 'ids') and 'ai_insights_card' in home_screen.ids:
                insight_label = home_screen.ids.ai_insights_card.ids.primary_insight
                insight_label.text = insight_text
                # Ensure text wraps properly
                if insight_label.width > 0:
                    insight_label.text_size = (insight_label.width - dp(4), None)
        except Exception as e:
            print(f"Error updating insight display: {e}")
    
    def _show_insight_type(self, popup, insight_type):
        """Show specific insight type in popup."""
        try:
            # Store current insight type for refresh
            popup.current_insight_type = insight_type
            insights_container = popup.ids.insights_container
            insights_container.clear_widgets()
            
            # Show loading
            loading = Label(
                text="Generating insight...",
                color=(0.81, 0.82, 1, 1),
                font_size='14sp',
                size_hint_y=None,
                height=dp(50)
            )
            insights_container.add_widget(loading)
            
            # Gather data in main thread (SQLite must be accessed from main thread)
            data = self.ai_insights_manager._gather_data(insight_type)
            
            # Generate insight in background
            def generate(insight_type, data):
                try:
                    insight = self.ai_insights_manager.generate_insight(insight_type, data=data)
                    Clock.schedule_once(lambda dt: self._display_insight(popup, insight_type, insight), 0)
                except Exception as e:
                    print(f"Error generating insight: {e}")
                    Clock.schedule_once(lambda dt: self._display_insight(popup, insight_type, "Unable to generate insight. Please try again."), 0)
            
            from threading import Thread
            Thread(target=generate, args=(insight_type, data), daemon=True).start()
        except Exception as e:
            print(f"Error showing insight type: {e}")
    
    def _load_all_insights(self, popup):
        """Load all insight types into popup."""
        try:
            insights_container = popup.ids.insights_container
            insights_container.clear_widgets()
            
            insight_types = [
                ("Daily Productivity", "daily"),
                ("Peak Focus Hours", "peak"),
                ("Weekly Patterns", "weekly"),
                ("Productivity Trends", "trends"),
                ("Task Analysis", "tasks"),
                ("Streak Status", "streak"),
                ("Burnout Prevention", "burnout"),
                ("Goal Recommendations", "goals"),
                ("Schedule Optimization", "schedule"),
                ("Time-Based Insights", "time"),
            ]
            
            for title, insight_type in insight_types:
                # Create insight card using ClickableCard style
                card = Factory.ClickableCard(
                    orientation='vertical',
                    size_hint_y=None,
                    height=dp(120),
                    padding=dp(12),
                    spacing=dp(10)
                )
                
                # Header section - Title (single line, no overflow)
                title_label = Label(
                    text=title,
                    color=(1, 1, 1, 1),
                    font_size='16sp',
                    bold=True,
                    halign='left',
                    valign='middle',
                    size_hint_y=None,
                    height=dp(28),
                    text_size=(card.width - dp(24), dp(28)),  # Constrain to card width, single line height (12dp padding each side)
                    shorten=True,
                    markup=False
                )
                
                # Update title text_size when card width changes (including after AI generates content)
                def update_title_size(card_widget, title_widget, *args):
                    if card_widget.width > 0:
                        title_widget.text_size = (card_widget.width - dp(24), dp(28))
                
                card.bind(width=lambda instance, value: update_title_size(instance, title_label, value))
                # Also update when card is laid out (after AI content is added)
                def ensure_title_size(*args):
                    if card.width > 0:
                        title_label.text_size = (card.width - dp(24), dp(28))
                Clock.schedule_once(ensure_title_size, 0.1)
                card.add_widget(title_label)
                
                # Insight text (will be updated)
                insight_label = Label(
                    text="Loading...",
                    color=(0.81, 0.82, 1, 1),
                    font_size='14sp',
                    halign='left',
                    valign='top',
                    text_size=(card.width - dp(24), None),  # Account for padding (12dp each side)
                    size_hint_y=None,
                    height=dp(60),
                    shorten=False,
                    markup=False
                )
                
                def update_card_height(label, card_widget, title_widget, container, *args):
                    if label.texture_size and label.texture_size[1] > 0:
                        # Calculate text height with some padding
                        text_height = max(label.texture_size[1] + dp(4), dp(60))
                        label.height = text_height
                        # Ensure title stays single line and constrained
                        if card_widget.width > 0:
                            title_widget.text_size = (card_widget.width - dp(24), dp(28))
                        # Update card height: padding top (12) + header (28 fixed) + spacing (10) + text height + padding bottom (12)
                        card_widget.height = dp(12) + dp(28) + dp(10) + text_height + dp(12)
                        # Update container height to prevent overlapping
                        def update_container():
                            total_height = sum(child.height for child in container.children if hasattr(child, 'height'))
                            spacing_total = (len(container.children) - 1) * dp(12) if len(container.children) > 1 else 0
                            container.height = total_height + spacing_total + dp(8)  # 4dp padding top + 4dp padding bottom
                        Clock.schedule_once(lambda dt: update_container(), 0.05)
                
                insight_label.bind(texture_size=lambda instance, *args: update_card_height(instance, card, title_label, insights_container, *args))
                insight_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (value - dp(24), None)) if value > 0 else None)
                card.add_widget(insight_label)
                
                insights_container.add_widget(card)
                
                # Update container height after adding card
                def update_container_height():
                    total_height = sum(child.height for child in insights_container.children if hasattr(child, 'height'))
                    spacing_total = (len(insights_container.children) - 1) * dp(12) if len(insights_container.children) > 1 else 0
                    insights_container.height = total_height + spacing_total + dp(8)  # 4dp padding top + 4dp padding bottom
                
                Clock.schedule_once(lambda dt: update_container_height(), 0.1)
                
                # Gather data in main thread (SQLite must be accessed from main thread)
                data = self.ai_insights_manager._gather_data(insight_type)
                
                # Generate insight in background
                def generate_insight(insight_type, label, data, card_widget, title_widget):
                    try:
                        insight = self.ai_insights_manager.generate_insight(insight_type, data=data)
                        def update_text():
                            label.text = insight
                            # Update text_size to match card width and trigger recalculation
                            if card_widget.width > 0:
                                label.text_size = (card_widget.width - dp(24), None)
                                # Also ensure title stays constrained
                                title_widget.text_size = (card_widget.width - dp(24), dp(28))
                            # Force texture update
                            Clock.schedule_once(lambda dt: label.texture_update(), 0.1)
                        Clock.schedule_once(lambda dt: update_text(), 0)
                    except Exception as e:
                        print(f"Error generating insight: {e}")
                        def update_error():
                            label.text = "Unable to generate insight."
                            if card_widget.width > 0:
                                label.text_size = (card_widget.width - dp(24), None)
                            Clock.schedule_once(lambda dt: label.texture_update(), 0.1)
                        Clock.schedule_once(lambda dt: update_error(), 0)
                
                from threading import Thread
                Thread(target=generate_insight, args=(insight_type, insight_label, data, card, title_label), daemon=True).start()
        except Exception as e:
            print(f"Error loading all insights: {e}")
            import traceback
            traceback.print_exc()
    
    def _display_insight(self, popup, insight_type, insight_text):
        """Display a single insight in the popup."""
        try:
            insights_container = popup.ids.insights_container
            insights_container.clear_widgets()
            
            # Get insight type title
            insight_titles = {
                "daily": "Daily Productivity",
                "peak": "Peak Focus Hours",
                "weekly": "Weekly Patterns",
                "trends": "Productivity Trends",
                "tasks": "Task Analysis",
                "streak": "Streak Status",
                "burnout": "Burnout Prevention",
                "goals": "Goal Recommendations",
                "schedule": "Schedule Optimization",
                "time": "Time-Based Insights",
            }
            title = insight_titles.get(insight_type, "AI Insight")
            
            # Create insight card using ClickableCard style
            card = Factory.ClickableCard(
                orientation='vertical',
                size_hint_y=None,
                height=dp(200),
                padding=dp(12),
                spacing=dp(10)
            )
            
            # Header section - Title (single line, no overflow)
            title_label = Label(
                text=title,
                color=(1, 1, 1, 1),
                font_size='16sp',
                bold=True,
                halign='left',
                valign='middle',
                size_hint_y=None,
                height=dp(28),
                text_size=(card.width - dp(24), dp(28)),  # Constrain to card width, single line height (12dp padding each side)
                shorten=True,
                markup=False
            )
            
            # Update title text_size when card width changes
            def update_title_size(card_widget, title_widget, *args):
                if card_widget.width > 0:
                    title_widget.text_size = (card_widget.width - dp(24), dp(28))
            
            card.bind(width=lambda instance, value: update_title_size(instance, title_label, value))
            # Also update when card is laid out
            def ensure_title_size(*args):
                if card.width > 0:
                    title_label.text_size = (card.width - dp(24), dp(28))
            Clock.schedule_once(ensure_title_size, 0.1)
            card.add_widget(title_label)
            
            # Insight text
            insight_label = Label(
                text=insight_text,
                color=(0.81, 0.82, 1, 1),
                font_size='14sp',
                halign='left',
                valign='top',
                text_size=(card.width - dp(24), None),  # Account for padding (12dp each side)
                size_hint_y=None,
                height=dp(100),
                shorten=False,
                markup=False
            )
            
            def update_card_height(label, card_widget, title_widget, container, *args):
                if label.texture_size and label.texture_size[1] > 0:
                    # Calculate text height with some padding
                    text_height = max(label.texture_size[1] + dp(4), dp(100))
                    label.height = text_height
                    # Ensure title stays single line and constrained
                    if card_widget.width > 0:
                        title_widget.text_size = (card_widget.width - dp(24), dp(28))
                    # Update card height: padding top (12) + header (28 fixed) + spacing (10) + text height + padding bottom (12)
                    card_widget.height = dp(12) + dp(28) + dp(10) + text_height + dp(12)
                    # Update container height properly
                    total_height = sum(child.height for child in container.children if hasattr(child, 'height'))
                    spacing_total = (len(container.children) - 1) * dp(12) if len(container.children) > 1 else 0
                    container.height = total_height + spacing_total + dp(8)
            
            insight_label.bind(texture_size=lambda instance, *args: update_card_height(instance, card, title_label, insights_container, *args))
            insight_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (value - dp(24), None)) if value > 0 else None)
            card.add_widget(insight_label)
            
            insights_container.add_widget(card)
            
            # Set initial height after texture is ready
            def set_initial_height():
                # Ensure title stays constrained
                if card.width > 0:
                    title_label.text_size = (card.width - dp(24), dp(28))
                if insight_label.texture_size and insight_label.texture_size[1] > 0:
                    text_height = max(insight_label.texture_size[1] + dp(4), dp(100))
                    insight_label.height = text_height
                    card.height = dp(12) + dp(28) + dp(10) + text_height + dp(12)
                else:
                    card.height = dp(12) + dp(28) + dp(10) + dp(100) + dp(12)
                # Update container height properly
                total_height = sum(child.height for child in insights_container.children if hasattr(child, 'height'))
                spacing_total = (len(insights_container.children) - 1) * dp(12) if len(insights_container.children) > 1 else 0
                insights_container.height = total_height + spacing_total + dp(8)
            
            Clock.schedule_once(lambda dt: set_initial_height(), 0.1)
        except Exception as e:
            print(f"Error displaying insight: {e}")
    
    def refresh_all_insights(self):
        """Refresh the current insight in the popup."""
        try:
            # Find the open popup by checking if it exists
            from kivy.uix.popup import Popup
            for widget in self.root.walk():
                if isinstance(widget, Popup) and hasattr(widget, 'ids') and 'insights_container' in widget.ids:
                    # Refresh the current insight type
                    current_type = getattr(widget, 'current_insight_type', 'daily')
                    self._show_insight_type(widget, current_type)
                    break
        except Exception as e:
            print(f"Error refreshing insight: {e}")
    
    def open_schedule_popup(self):
        """Open the schedule popup showing today's appointments/meetings."""
        popup = Factory.SchedulePopup()
        
        # Get today's schedule items
        schedule = self.db.get_today_schedule(limit=20)  # Get more items for popup
        
        # Update count in header
        if len(schedule) == 0:
            popup.ids.schedule_count_label.text = "No items"
        elif len(schedule) == 1:
            popup.ids.schedule_count_label.text = "1 item"
        else:
            popup.ids.schedule_count_label.text = f"{len(schedule)} items"
        
        # Populate schedule list
        schedule_container = popup.ids.schedule_container
        schedule_container.clear_widgets()
        
        if not schedule:
            # Show "no schedule" message
            no_schedule_label = Factory.Label(
                text="No schedule items for today.\nAll clear!",
                color=(0.8, 0.8, 1, 1),
                font_size="15sp",
                size_hint_y=None,
                height=80,
                halign="center",
                valign="middle"
            )
            schedule_container.add_widget(no_schedule_label)
        else:
            for title, start_time in schedule:
                if start_time:
                    try:
                        dt = datetime.fromisoformat(start_time)
                        # Format: "9:00 AM • 10/11/2025"
                        hour = dt.hour
                        minute = dt.minute
                        am_pm = "AM" if hour < 12 else "PM"
                        hour_12 = hour if hour <= 12 else hour - 12
                        if hour_12 == 0:
                            hour_12 = 12
                        time_str = f"{hour_12}:{minute:02d} {am_pm}"  # "9:00 AM"
                        date_str = dt.strftime("%m/%d/%Y")  # "10/11/2025"
                    except:
                        time_str = "00:00 AM"
                        date_str = datetime.now().strftime("%m/%d/%Y")
                else:
                    time_str = "00:00 AM"
                    date_str = datetime.now().strftime("%m/%d/%Y")
                
                # Create schedule item card
                item_card = Factory.ScheduleItemCard()
                item_card.item_title = title
                item_card.item_time = time_str
                item_card.item_date = date_str
                schedule_container.add_widget(item_card)
        
        popup.open()
    
    def navigate_to_home(self):
        """Navigate to home screen and scroll to top."""
        try:
            # Switch to home screen
            self.root.current = 'home'
            # Scroll to top of the main scroll view
            home_screen = self.root.get_screen('home')
            scroll_view = home_screen.ids.main_scroll
            scroll_view.scroll_y = 1.0  # Scroll to top (1.0 = top, 0.0 = bottom)
            # Refresh schedule display to show latest calendar events
            self.update_schedule_display()
            # Refresh stats display to show latest focus stats
            self.update_stats_display()
        except:
            pass  # Silently fail if scroll view not found
    
    def navigate_to_calendar(self):
        """Navigate to calendar screen."""
        self.calendar_manager.navigate_to_calendar()
    
    def navigate_to_analytics(self):
        """Navigate to analytics screen and load data."""
        self.root.current = 'analytics'
        self.load_analytics_data()
    
    def load_analytics_data(self, force_refresh=False):
        """Load and display all analytics data with daily caching."""
        today_str = str(date.today())
        
        # Check if we need to regenerate (new day or forced refresh)
        needs_refresh = force_refresh or (self.analytics_cache_date != today_str)
        
        try:
            analytics_screen = self.root.get_screen('analytics')
            
            if needs_refresh:
                # Generate new graphs and data
                # Get hourly stats
                hourly_data = self.stats_manager.get_hourly_stats(30)
                hourly_graph_path = self.graph_generator.generate_hourly_graph(hourly_data)
                
                # Get day patterns
                day_data = self.stats_manager.get_day_of_week_stats(4)
                day_graph_path = self.graph_generator.generate_day_pattern_graph(day_data)
                
                # Calculate insights
                if any(hourly_data.values()):
                    max_hour = max(hourly_data.items(), key=lambda x: x[1])[0]
                    peak_text = f"Most productive: {max_hour:02d}:00"
                else:
                    peak_text = "No data yet"
                
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                if any(day_data.values()):
                    best_day_idx = max(day_data.items(), key=lambda x: x[1])[0]
                    day_pattern_text = f"Best day: {days[best_day_idx]}"
                else:
                    day_pattern_text = "No data yet"
                
                # Session stats
                session_stats = self.stats_manager.get_session_duration_stats()
                if session_stats['total'] > 0:
                    session_text = (
                        f"Avg: {session_stats['avg']} min\n"
                        f"Longest: {session_stats['max']} min\n"
                        f"Shortest: {session_stats['min']} min"
                    )
                else:
                    session_text = "No sessions yet"
                
                # Streak
                streak = self.stats_manager.get_focus_streak()
                streak_text = (
                    f"Current: {streak['current']} days\n"
                    f"Best: {streak['best']} days"
                )
                
                # Update cache
                self.analytics_cache_date = today_str
                self.analytics_cached_hourly_path = hourly_graph_path
                self.analytics_cached_day_pattern_path = day_graph_path
                self.analytics_cached_insights = {
                    'peak_hours': peak_text,
                    'day_pattern': day_pattern_text,
                    'session_stats': session_text,
                    'streak': streak_text
                }
            else:
                # Use cached data
                hourly_graph_path = self.analytics_cached_hourly_path
                day_graph_path = self.analytics_cached_day_pattern_path
                peak_text = self.analytics_cached_insights.get('peak_hours', 'No data yet')
                day_pattern_text = self.analytics_cached_insights.get('day_pattern', 'No data yet')
                session_text = self.analytics_cached_insights.get('session_stats', 'No sessions yet')
                streak_text = self.analytics_cached_insights.get('streak', 'Current: 0 days\nBest: 0 days')
            
            # Update UI with data (cached or fresh)
            analytics_screen.ids.hourly_graph.source = hourly_graph_path
            analytics_screen.ids.hourly_graph.reload()
            analytics_screen.ids.peak_hours_insight.text = peak_text
            
            analytics_screen.ids.day_pattern_graph.source = day_graph_path
            analytics_screen.ids.day_pattern_graph.reload()
            analytics_screen.ids.day_pattern_insight.text = day_pattern_text
            
            analytics_screen.ids.session_stats_text.text = session_text
            analytics_screen.ids.streak_text.text = streak_text
            
        except Exception as e:
            print(f"Error loading analytics data: {e}")
    
    def refresh_analytics(self):
        """Force refresh of analytics data."""
        self.load_analytics_data(force_refresh=True)
    
    def navigate_to_profile(self):
        """Navigate to profile screen and load data."""
        self.root.current = 'profile'
        self.load_profile_data()
    
    def load_profile_data(self):
        """Load and display profile data."""
        try:
            profile_screen = self.root.get_screen('profile')
            
            # Get profile data from ProfileManager
            profile = self.profile_manager.get_profile()
            
            # Update profile screen username and email
            if profile.get('username'):
                profile_screen.ids.profile_name.text = profile['username']
            if profile.get('email'):
                profile_screen.ids.profile_email.text = profile['email']
            
            # Update home screen username (if home_content exists)
            home_content = getattr(self, 'home_content', None)
            if home_content and hasattr(home_content, 'ids'):
                home_label = home_content.ids.get('home_profile_name')
                if home_label and profile.get('username'):
                    home_label.text = profile['username']
            
            # Get all-time stats
            alltime_stats = self.stats_manager.get_all_time_stats()
            
            # Format focus time (convert minutes to hours and minutes)
            total_minutes = alltime_stats['focus_minutes']
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if hours > 0:
                focus_time_text = f"{hours} hours {minutes} min"
            else:
                focus_time_text = f"{minutes} min"
            
            # Get streak info
            streak = self.stats_manager.get_focus_streak()
            
            # Update UI
            profile_screen.ids.total_focus_time.text = focus_time_text
            profile_screen.ids.total_pomodoros.text = str(alltime_stats['pomodoros'])
            profile_screen.ids.current_streak.text = f"{streak['current']} days"
            profile_screen.ids.best_streak.text = f"{streak['best']} days"
            
        except Exception as e:
            print(f"Error loading profile data: {e}")
    
    def navigate_to_edit_profile(self):
        """Open the edit profile screen with current data pre-filled."""
        try:
            profile = self.profile_manager.get_profile()
            edit_screen = self.root.get_screen('edit_profile')
            edit_screen.ids.edit_username.text = profile.get('username') or ''
            edit_screen.ids.edit_email.text = profile.get('email') or ''
            # Password field removed - now in Security & Password screen
            self.root.current = 'edit_profile'
        except Exception as e:
            print(f"Error opening edit profile screen: {e}")
            import traceback
            traceback.print_exc()
    
    def cancel_edit_profile(self):
        """Return to the profile screen without saving."""
        self.root.current = 'profile'
    
    def save_profile_changes(self):
        """Save the edited profile data."""
        try:
            edit_screen = self.root.get_screen('edit_profile')
            username = edit_screen.ids.edit_username.text.strip()
            email = edit_screen.ids.edit_email.text.strip()
            
            # Update profile (password removed - now in Security & Password screen)
            self.profile_manager.update_profile(
                username=username,
                email=email
            )
            
            # Reload profile data and return to profile screen
            self.load_profile_data()
            self.root.current = 'profile'
        except Exception as e:
            print(f"Error saving profile changes: {e}")
    
    def attempt_login(self):
        """Attempt to log in with provided credentials."""
        try:
            login_screen = self.root.get_screen('login')
            username = login_screen.ids.login_username.text.strip()
            password = login_screen.ids.login_password.text.strip()
            
            if not username or not password:
                login_screen.ids.login_error.text = 'Please enter both username and password'
                return
            
            # Authenticate using ProfileManager
            if self.profile_manager.authenticate(username, password):
                login_screen.ids.login_error.text = ''
                login_screen.ids.login_username.text = ''
                login_screen.ids.login_password.text = ''
                self.root.current = 'home'
            else:
                login_screen.ids.login_error.text = 'Invalid username or password'
        except Exception as e:
            print(f"Login error: {e}")
            login_screen = self.root.get_screen('login')
            login_screen.ids.login_error.text = 'Login failed'
    
    def skip_login(self):
        """Skip login for first-time users (goes to home)."""
        try:
            login_screen = self.root.get_screen('login')
            login_screen.ids.login_error.text = ''
            login_screen.ids.login_username.text = ''
            login_screen.ids.login_password.text = ''
            self.root.current = 'home'
        except Exception as e:
            print(f"Skip login error: {e}")
    
    def logout(self):
        """Log out and return to login screen."""
        self.root.current = 'login'
    
    def navigate_to_notification_settings(self):
        """Open notification settings screen."""
        try:
            self.root.current = 'notification_settings'
            self.load_notification_preferences()
        except Exception as e:
            print(f"Error opening notification settings: {e}")
    
    def load_notification_preferences(self):
        """Load and display notification preferences."""
        try:
            settings_screen = self.root.get_screen('notification_settings')
            prefs = self.notification_manager.get_preferences()
            
            # Update checkboxes
            settings_screen.ids.session_reminders.active = prefs.get('session_reminders', True)
            settings_screen.ids.break_reminders.active = prefs.get('break_reminders', True)
            settings_screen.ids.daily_goals.active = prefs.get('daily_goals', True)
            settings_screen.ids.streak_alerts.active = prefs.get('streak_alerts', True)
            settings_screen.ids.task_deadlines.active = prefs.get('task_deadlines', True)
            settings_screen.ids.weekly_summary.active = prefs.get('weekly_summary', False)
            settings_screen.ids.achievements.active = prefs.get('achievements', True)
            settings_screen.ids.notification_sound.active = prefs.get('notification_sound', True)
            settings_screen.ids.quiet_hours_enabled.active = prefs.get('quiet_hours_enabled', False)
        except Exception as e:
            print(f"Error loading notification preferences: {e}")
    
    def toggle_notification(self, key, value):
        """Toggle a notification preference."""
        try:
            self.notification_manager.update_preference(key, value)
            print(f"Updated {key} to {value}")
        except Exception as e:
            print(f"Error toggling notification: {e}")
    
    def back_to_profile(self):
        """Return to profile screen."""
        self.root.current = 'profile'
    
    def test_notification(self):
        """Send a test notification to verify the system works."""
        try:
            from plyer import notification
            notification.notify(
                title='Test Notification 🔔',
                message='Great! Your notifications are working perfectly!',
                app_name='Time Manager',
                timeout=10
            )
            print("✓ Test notification sent successfully!")
        except Exception as e:
            print(f"Error sending test notification: {e}")
    
    def navigate_to_subscription(self):
        """Open subscription plans screen."""
        try:
            self.root.current = 'subscription'
        except Exception as e:
            print(f"Error opening subscription screen: {e}")
    
    def subscribe_plan(self, plan_name):
        """Handle subscription to a plan."""
        try:
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            
            plan_names = {
                'pro': 'Pro ($4.99/month)',
                'pro_plus': 'Pro+ ($9.99/month)'
            }
            
            popup = Popup(
                title='Subscription',
                content=Label(
                    text=f'You selected: {plan_names.get(plan_name, plan_name)}\n\n'
                         'Payment integration coming soon!\n'
                         'This will connect to your payment provider.',
                    halign='center',
                    valign='middle'
                ),
                size_hint=(0.8, 0.5),
                auto_dismiss=True
            )
            popup.open()
            print(f"User selected plan: {plan_name}")
        except Exception as e:
            print(f"Error subscribing to plan: {e}")
    
    def navigate_to_security_password(self):
        """Open security & password screen."""
        try:
            self.root.current = 'security_password'
            # Clear password fields
            security_screen = self.root.get_screen('security_password')
            security_screen.ids.current_password.text = ''
            security_screen.ids.new_password.text = ''
            security_screen.ids.confirm_password.text = ''
            security_screen.ids.strength_label.text = ''
        except Exception as e:
            print(f"Error opening security & password screen: {e}")
    
    def update_password_strength(self, password):
        """Update password strength indicator in real-time."""
        try:
            security_screen = self.root.get_screen('security_password')
            
            if not password:
                security_screen.ids.strength_label.text = ''
                # Clear the bar
                bar_container = security_screen.ids.strength_bar_container
                bar_container.canvas.before.clear()
                from kivy.graphics import Color, RoundedRectangle
                with bar_container.canvas.before:
                    Color(0.3, 0.3, 0.4, 1)
                    RoundedRectangle(radius=[4,], pos=bar_container.pos, size=bar_container.size)
                return
            
            # Calculate password strength
            score = 0
            if len(password) >= 8: score += 1
            if len(password) >= 12: score += 1
            if any(c.isupper() for c in password): score += 1
            if any(c.islower() for c in password): score += 1
            if any(c.isdigit() for c in password): score += 1
            if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password): score += 1
            
            # Determine strength level
            if score <= 2:
                strength = "Weak"
                color = (1, 0.3, 0.3, 1)  # Red
                width_percent = 0.33
            elif score <= 4:
                strength = "Medium"
                color = (1, 0.65, 0, 1)  # Orange
                width_percent = 0.66
            else:
                strength = "Strong"
                color = (0.3, 0.98, 0.6, 1)  # Green
                width_percent = 1.0
            
            security_screen.ids.strength_label.text = strength
            
            # Update the visual bar with color
            bar_container = security_screen.ids.strength_bar_container
            bar_container.canvas.before.clear()
            
            from kivy.graphics import Color, RoundedRectangle
            with bar_container.canvas.before:
                # Background (gray)
                Color(0.3, 0.3, 0.4, 1)
                RoundedRectangle(radius=[4,], pos=bar_container.pos, size=bar_container.size)
                # Colored strength bar
                Color(*color)
                RoundedRectangle(
                    radius=[4,],
                    pos=bar_container.pos,
                    size=(bar_container.width * width_percent, bar_container.height)
                )
            
        except Exception as e:
            print(f"Error updating password strength: {e}")
    
    def change_password(self):
        """Change user password with validation."""
        try:
            security_screen = self.root.get_screen('security_password')
            
            current_pw = security_screen.ids.current_password.text
            new_pw = security_screen.ids.new_password.text
            confirm_pw = security_screen.ids.confirm_password.text
            
            # Validation
            if not current_pw or not new_pw or not confirm_pw:
                self.show_message_popup('Error', 'Please fill in all password fields')
                return
            
            # Get current username
            profile = self.profile_manager.get_profile()
            username = profile.get('username', 'user')
            
            # Verify current password
            if not self.profile_manager.authenticate(username, current_pw):
                self.show_message_popup('Error', 'Current password is incorrect')
                return
            
            # Check if new passwords match
            if new_pw != confirm_pw:
                self.show_message_popup('Error', 'New passwords do not match')
                return
            
            # Check password length
            if len(new_pw) < 8:
                self.show_message_popup('Error', 'Password must be at least 8 characters long')
                return
            
            # Check if new password is same as current
            if current_pw == new_pw:
                self.show_message_popup('Error', 'New password must be different from current password')
                return
            
            # Save new password
            self.profile_manager.set_password(new_pw)
            
            # Clear fields
            security_screen.ids.current_password.text = ''
            security_screen.ids.new_password.text = ''
            security_screen.ids.confirm_password.text = ''
            security_screen.ids.strength_label.text = ''
            
            # Show success message
            self.show_message_popup('Success', 'Password changed successfully!')
            
        except Exception as e:
            print(f"Error changing password: {e}")
            self.show_message_popup('Error', f'Failed to change password: {str(e)}')
    
    def toggle_app_lock(self, is_enabled):
        """Toggle app lock/PIN feature."""
        try:
            if is_enabled:
                self.show_message_popup('App Lock', 'App Lock feature coming soon!\n\nThis will allow you to protect your app with a PIN code.')
            print(f"App lock toggled: {is_enabled}")
        except Exception as e:
            print(f"Error toggling app lock: {e}")
    
    def show_message_popup(self, title, message):
        """Show a simple message popup."""
        try:
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            
            popup = Popup(
                title=title,
                content=Label(
                    text=message,
                    halign='center',
                    valign='middle'
                ),
                size_hint=(0.8, 0.4),
                auto_dismiss=True
            )
            popup.open()
        except Exception as e:
            print(f"Error showing popup: {e}")
    
    def navigate_to_terms_conditions(self):
        """Open terms & conditions screen."""
        try:
            self.root.current = 'terms_conditions'
        except Exception as e:
            print(f"Error opening terms & conditions screen: {e}")
    
    def activate_voice_assistant(self):
        """Open voice chat popup and start listening."""
        try:
            # CRITICAL FIX: Check if popup is already open
            if self.voice_popup is not None:
                # Popup already exists, just bring it to front
                if hasattr(self.voice_popup, 'open'):
                    return  # Already open, don't create another
            
            from kivy.uix.popup import Popup
            # Create and store popup reference
            self.voice_popup = Factory.VoiceChatPopup()
            
            # CRITICAL FIX: Clean up when popup is dismissed
            def on_dismiss(instance):
                self._cleanup_voice_assistant()
                self.voice_popup = None
            
            self.voice_popup.bind(on_dismiss=on_dismiss)
            self.voice_popup.open()
            
            # Clear any sample messages (schedule to ensure UI is ready)
            Clock.schedule_once(lambda dt: self._initialize_voice_chat(), 0.1)
        except Exception as e:
            print(f"Error opening voice chat: {e}")
            import traceback
            traceback.print_exc()
    
    def _cleanup_voice_assistant(self):
        """Clean up voice assistant resources when popup closes."""
        try:
            if self.voice_handler:
                # Stop any ongoing listening or speaking
                self.voice_handler.is_listening = False
                self.voice_handler.is_speaking = False
                self.voice_handler.stop_speaking()
            
            # Clear popup reference to prevent memory leaks
            self.voice_popup = None
            
            print("✓ Voice assistant cleaned up successfully")
        except Exception as e:
            print(f"Error cleaning up voice assistant: {e}")
            import traceback
            traceback.print_exc()
    
    def _initialize_voice_chat(self):
        """Initialize voice chat UI (called after popup is ready)."""
        try:
            if not self.voice_popup or not hasattr(self.voice_popup, 'ids'):
                return
            
            # Clear any sample messages
            chat_container = self.voice_popup.ids.chat_messages
            if chat_container:
                chat_container.clear_widgets()
            
            # Add welcome message
            self.add_chat_message("Hi! I'm your AI assistant.\nType a message or hold the mic to speak!", is_user=False)
            
            # Don't auto-start listening - wait for user to press mic or type
        except Exception as e:
            print(f"Error initializing voice chat: {e}")
            import traceback
            traceback.print_exc()
    
    def send_text_message(self, text):
        """Send a text message to the AI assistant."""
        if not self.voice_popup:
            return
        
        # Get text and clear input
        message = text.strip()
        if not message:
            return
        
        try:
            # Clear the input field
            if hasattr(self.voice_popup, 'ids') and hasattr(self.voice_popup.ids, 'message_input'):
                Clock.schedule_once(lambda dt: setattr(self.voice_popup.ids.message_input, 'text', ''), 0)
            
            # Add user message to chat
            Clock.schedule_once(lambda dt: self.add_chat_message(message, is_user=True), 0)
            Clock.schedule_once(lambda dt: self.update_voice_status("Thinking..."), 0)
            
            # Process with AI
            self.process_chatgpt_response(message)
        except Exception as e:
            print(f"Error sending text message: {e}")
            import traceback
            traceback.print_exc()
    
    def start_push_to_talk(self):
        """Start listening when mic button is pressed (push-to-talk)."""
        if not self.voice_popup:
            return
        
        # Check if already listening
        if self.voice_handler.is_listening:
            print("Already listening, ignoring new request")
            return
        
        try:
            # Update status
            Clock.schedule_once(lambda dt: self.update_voice_status("Listening... (release to stop)"), 0)
            
            # Start speech recognition with longer timeout for push-to-talk
            self.voice_handler.listen(self.on_voice_input, timeout=30)
        except Exception as e:
            print(f"Error starting push-to-talk: {e}")
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self.update_voice_status(f"Error: {e}"), 0)
    
    def stop_push_to_talk(self):
        """Stop listening when mic button is released (push-to-talk)."""
        if not self.voice_popup:
            return
        
        try:
            # Stop listening by setting the flag
            if self.voice_handler.is_listening:
                self.voice_handler.is_listening = False
                Clock.schedule_once(lambda dt: self.update_voice_status("Processing..."), 0)
        except Exception as e:
            print(f"Error stopping push-to-talk: {e}")
            import traceback
            traceback.print_exc()
    
    def start_voice_listening(self):
        """Start listening for voice input (legacy method for compatibility)."""
        self.start_push_to_talk()
    
    def on_voice_input(self, text, error):
        """Handle voice input result (called from background thread - must use Clock for UI updates)."""
        if error:
            Clock.schedule_once(lambda dt: self.update_voice_status(f"Error: {error}"), 0)
            print(f"Voice input error: {error}")
            return
        
        if not text:
            Clock.schedule_once(lambda dt: self.update_voice_status("No speech detected"), 0)
            return
        
        print(f"User said: {text}")
        
        # All UI updates must be scheduled on main thread
        Clock.schedule_once(lambda dt: self.add_chat_message(text, is_user=True), 0)
        Clock.schedule_once(lambda dt: self.update_voice_status("Thinking..."), 0)
        
        # Process with ChatGPT (already runs in its own background thread, no need to schedule)
        self.process_chatgpt_response(text)
    
    def process_chatgpt_response(self, user_text):
        """Process user text with ChatGPT (runs in background thread to avoid UI blocking)."""
        def _process_in_background():
            try:
                # Check if app is shutting down
                if hasattr(self, '_is_shutting_down') and self._is_shutting_down:
                    return
                
                # Get AI response (this blocks, so run in background)
                ai_text, action = self.chatgpt_assistant.send_message(user_text)
                
                # Check again after API call (app might have closed)
                if hasattr(self, '_is_shutting_down') and self._is_shutting_down:
                    return
                
                # Execute action if present
                action_result = ""
                if action:
                    action_result = self.chatgpt_assistant.execute_action(action)
                
                # Check again before UI update
                if hasattr(self, '_is_shutting_down') and self._is_shutting_down:
                    return
                
                # Combine response
                full_response = ai_text
                if action_result:
                    full_response += f"\n\n{action_result}"
                
                # Add AI message to chat (schedule on main thread)
                Clock.schedule_once(lambda dt: self.add_chat_message(full_response, is_user=False) if not (hasattr(self, '_is_shutting_down') and self._is_shutting_down) else None, 0)
                
                # Text-to-speech disabled - only show responses in chat
                # from threading import Thread
                # Thread(target=lambda: self.voice_handler.speak(ai_text), daemon=True).start()
                
                # Update status (on main thread)
                Clock.schedule_once(lambda dt: self.update_voice_status("Tap mic to speak") if not (hasattr(self, '_is_shutting_down') and self._is_shutting_down) else None, 0)
                
            except Exception as e:
                # Don't update UI if shutting down
                if hasattr(self, '_is_shutting_down') and self._is_shutting_down:
                    return
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                print(f"ChatGPT processing error: {e}")
                import traceback
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.add_chat_message(error_msg, is_user=False) if not (hasattr(self, '_is_shutting_down') and self._is_shutting_down) else None, 0)
                Clock.schedule_once(lambda dt: self.update_voice_status("Error occurred") if not (hasattr(self, '_is_shutting_down') and self._is_shutting_down) else None, 0)
        
        # Run in background thread to avoid blocking UI
        from threading import Thread
        Thread(target=_process_in_background, daemon=True).start()
    
    def add_chat_message(self, text, is_user=False):
        """Add message bubble to chat UI (must be called from main thread via Clock.schedule_once)."""
        # Don't update UI if shutting down
        if hasattr(self, '_is_shutting_down') and self._is_shutting_down:
            return
        
        if not self.voice_popup:
            return
        
        try:
            # Verify popup still exists and has required IDs
            if not hasattr(self.voice_popup, 'ids'):
                return
            
            chat_container = self.voice_popup.ids.chat_messages
            if not chat_container:
                return
            
            # Create message bubble container
            message_box = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                padding=(0, dp(4)),
                spacing=dp(40)
            )
            message_box.bind(minimum_height=message_box.setter('height'))
            
            if is_user:
                # Right-aligned user message (green)
                message_box.add_widget(Widget(size_hint_x=0.2))
                
                bubble = BoxLayout(
                    orientation='vertical',
                    size_hint=(0.8, None),
                    padding=dp(12)
                )
                bubble.bind(minimum_height=bubble.setter('height'))
                
                # Green background
                with bubble.canvas.before:
                    Color(0.3, 0.98, 0.6, 0.3)
                    bubble.rect = RoundedRectangle(
                        radius=[15, 15, 0, 15],
                        pos=bubble.pos,
                        size=bubble.size
                    )
                bubble.bind(pos=lambda obj, val: setattr(obj.rect, 'pos', val))
                bubble.bind(size=lambda obj, val: setattr(obj.rect, 'size', val))
                
                label = Label(
                    text=text,
                    color=(1, 1, 1, 1),
                    font_size='14sp',
                    size_hint_y=None,
                    halign='left',
                    valign='top',
                    markup=True
                )
                label.bind(width=lambda *x: label.setter('text_size')(label, (label.width - dp(8), None)))
                label.bind(texture_size=lambda *x: label.setter('height')(label, label.texture_size[1] + dp(8)))
                
                bubble.add_widget(label)
                message_box.add_widget(bubble)
                
            else:
                # Left-aligned AI message (purple)
                bubble = BoxLayout(
                    orientation='vertical',
                    size_hint=(0.8, None),
                    padding=dp(12)
                )
                bubble.bind(minimum_height=bubble.setter('height'))
                
                # Purple background
                with bubble.canvas.before:
                    Color(0.66, 0.55, 0.98, 0.3)
                    bubble.rect = RoundedRectangle(
                        radius=[15, 15, 15, 0],
                        pos=bubble.pos,
                        size=bubble.size
                    )
                bubble.bind(pos=lambda obj, val: setattr(obj.rect, 'pos', val))
                bubble.bind(size=lambda obj, val: setattr(obj.rect, 'size', val))
                
                label = Label(
                    text=text,
                    color=(1, 1, 1, 1),
                    font_size='14sp',
                    size_hint_y=None,
                    halign='left',
                    valign='top',
                    markup=True
                )
                label.bind(width=lambda *x: label.setter('text_size')(label, (label.width - dp(8), None)))
                label.bind(texture_size=lambda *x: label.setter('height')(label, label.texture_size[1] + dp(8)))
                
                bubble.add_widget(label)
                message_box.add_widget(bubble)
                message_box.add_widget(Widget(size_hint_x=0.2))
            
            chat_container.add_widget(message_box)
            
            # Auto-scroll to bottom
            scroll_view = self.voice_popup.ids.chat_scroll
            Clock.schedule_once(lambda dt: setattr(scroll_view, 'scroll_y', 0), 0.1)
            
        except Exception as e:
            print(f"Error adding chat message: {e}")
    
    def update_voice_status(self, status_text):
        """Update voice status label (thread-safe)."""
        if self.voice_popup:
            try:
                # Ensure we're on main thread - if called from background thread, schedule it
                if hasattr(self.voice_popup, 'ids') and hasattr(self.voice_popup.ids, 'voice_status'):
                    self.voice_popup.ids.voice_status.text = status_text
            except Exception as e:
                print(f"Error updating voice status: {e}")
    
    # ===== Voice Command Action Methods =====
    
    def start_timer_voice(self, duration: int) -> str:
        """Start timer via voice command (thread-safe)."""
        try:
            # Timer access must happen on main thread
            from threading import current_thread, main_thread
            if current_thread() != main_thread():
                # We're in a background thread, need to start timer on main thread
                result = [None]
                
                def _start_on_main_thread(dt):
                    try:
                        # Timer is stored as self.timer in the app
                        # Use reset() to set duration, then start()
                        self.timer.reset(minutes=duration)
                        self.timer.start()
                        result[0] = 'success'
                    except Exception as e:
                        print(f"Error starting timer: {e}")
                        result[0] = {'error': str(e)}
                
                Clock.schedule_once(_start_on_main_thread, 0)
                
                # Wait for result (efficient polling with shorter intervals)
                import time
                start_time = time.time()
                timeout = 0.3  # Reduced timeout
                while result[0] is None and (time.time() - start_time) < timeout:
                    time.sleep(0.01)  # Shorter sleep interval for better responsiveness
                
                if result[0] is None or isinstance(result[0], dict):
                    return "Could not start timer"
            else:
                # Already on main thread
                # Use reset() to set duration, then start()
                self.timer.reset(minutes=duration)
                self.timer.start()
            
            return f"Started {duration}-minute focus timer!"
        except Exception as e:
            print(f"Error starting timer: {e}")
            import traceback
            traceback.print_exc()
            return "Could not start timer"
    
    def stop_timer_voice(self) -> str:
        """Stop timer via voice command (thread-safe)."""
        try:
            # Timer access must happen on main thread
            from threading import current_thread, main_thread
            if current_thread() != main_thread():
                # We're in a background thread, need to stop timer on main thread
                result = [None]
                
                def _stop_on_main_thread(dt):
                    try:
                        # Timer is stored as self.timer in the app
                        if self.timer.is_running:
                            self.timer.pause()
                            result[0] = "Timer paused"
                        else:
                            result[0] = "Timer is not running"
                    except Exception as e:
                        print(f"Error stopping timer: {e}")
                        result[0] = {'error': str(e)}
                
                Clock.schedule_once(_stop_on_main_thread, 0)
                
                # Wait for result (efficient polling with shorter intervals)
                import time
                start_time = time.time()
                timeout = 0.3  # Reduced timeout
                while result[0] is None and (time.time() - start_time) < timeout:
                    time.sleep(0.01)  # Shorter sleep interval for better responsiveness
                
                if result[0] is None or isinstance(result[0], dict):
                    return "Could not stop timer"
                
                return result[0]
            else:
                # Already on main thread
                if self.timer.is_running:
                    self.timer.pause()
                    return "Timer paused"
                else:
                    return "Timer is not running"
        except Exception as e:
            print(f"Error stopping timer: {e}")
            import traceback
            traceback.print_exc()
            return "Could not stop timer"
    
    def resume_timer_voice(self) -> str:
        """Resume timer via voice command (thread-safe)."""
        try:
            # Timer access must happen on main thread
            from threading import current_thread, main_thread
            if current_thread() != main_thread():
                # We're in a background thread, need to resume timer on main thread
                result = [None]
                
                def _resume_on_main_thread(dt):
                    try:
                        # Timer is stored as self.timer in the app
                        if not self.timer.is_running:
                            self.timer.start()
                            result[0] = "Timer resumed"
                        else:
                            result[0] = "Timer is already running"
                    except Exception as e:
                        print(f"Error resuming timer: {e}")
                        result[0] = {'error': str(e)}
                
                Clock.schedule_once(_resume_on_main_thread, 0)
                
                # Wait for result (efficient polling with shorter intervals)
                import time
                start_time = time.time()
                timeout = 0.3  # Reduced timeout
                while result[0] is None and (time.time() - start_time) < timeout:
                    time.sleep(0.01)  # Shorter sleep interval for better responsiveness
                
                if result[0] is None or isinstance(result[0], dict):
                    return "Could not resume timer"
                
                return result[0]
            else:
                # Already on main thread
                if not self.timer.is_running:
                    self.timer.start()
                    return "Timer resumed"
                else:
                    return "Timer is already running"
        except Exception as e:
            print(f"Error resuming timer: {e}")
            import traceback
            traceback.print_exc()
            return "Could not resume timer"
    
    def reset_timer_voice(self) -> str:
        """Reset timer via voice command (thread-safe)."""
        try:
            # Timer access must happen on main thread
            from threading import current_thread, main_thread
            if current_thread() != main_thread():
                # We're in a background thread, need to reset timer on main thread
                result = [None]
                
                def _reset_on_main_thread(dt):
                    try:
                        # Timer is stored as self.timer in the app
                        self.timer.reset(minutes=0)  # Reset to 00:00:00
                        result[0] = 'success'
                    except Exception as e:
                        print(f"Error resetting timer: {e}")
                        result[0] = {'error': str(e)}
                
                Clock.schedule_once(_reset_on_main_thread, 0)
                
                # Wait for result (efficient polling with shorter intervals)
                import time
                start_time = time.time()
                timeout = 0.3  # Reduced timeout
                while result[0] is None and (time.time() - start_time) < timeout:
                    time.sleep(0.01)  # Shorter sleep interval for better responsiveness
                
                if result[0] is None or isinstance(result[0], dict):
                    return "Could not reset timer"
            else:
                # Already on main thread
                self.timer.reset(minutes=0)  # Reset to 00:00:00
            
            return "Timer reset to 00:00:00"
        except Exception as e:
            print(f"Error resetting timer: {e}")
            import traceback
            traceback.print_exc()
            return "Could not reset timer"
    
    def _parse_date_hint(self, date_hint: str, title: str = "") -> 'date':
        """Parse various date formats from user input."""
        from datetime import datetime, date, timedelta
        import re
        
        # Combine date_hint and title for parsing
        text = f"{date_hint} {title}".lower()
        today = date.today()
        
        # Handle "today"
        if "today" in text or not date_hint or date_hint.lower() == "today":
            return today
        
        # Handle "tomorrow"
        if "tomorrow" in text:
            return today + timedelta(days=1)
        
        # Handle "next week"
        if "next week" in text:
            return today + timedelta(days=7)
        
        # Handle day names (e.g., "next Monday", "this Friday")
        day_names = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }
        
        for day_name, day_num in day_names.items():
            if day_name in text:
                current_day = today.weekday()
                days_ahead = day_num - current_day
                
                # If "next" is mentioned or the day has passed this week, go to next week
                if "next" in text or days_ahead <= 0:
                    days_ahead += 7
                
                return today + timedelta(days=days_ahead)
        
        # Handle specific dates like "December 5", "Dec 5", "12/5", "5th December"
        # Try MM/DD format
        match = re.search(r'(\d{1,2})[/-](\d{1,2})', date_hint)
        if match:
            try:
                month, day = int(match.group(1)), int(match.group(2))
                year = today.year
                target = date(year, month, day)
                # If date has passed this year, use next year
                if target < today:
                    target = date(year + 1, month, day)
                return target
            except ValueError:
                pass
        
        # Try "Month Day" format (e.g., "December 5", "Dec 5")
        month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        for month_name, month_num in month_names.items():
            if month_name in text:
                # Find day number near the month name
                match = re.search(rf'{month_name}\s*(\d{{1,2}})', text)
                if not match:
                    match = re.search(rf'(\d{{1,2}})\s*{month_name}', text)
                
                if match:
                    try:
                        day = int(match.group(1))
                        year = today.year
                        target = date(year, month_num, day)
                        # If date has passed this year, use next year
                        if target < today:
                            target = date(year + 1, month_num, day)
                        return target
                    except ValueError:
                        pass
        
        # Default to today if no date pattern matched
        return today
    
    def add_event_voice(self, title: str, time_str: str = "", date_hint: str = "") -> str:
        """Add event/appointment to calendar via voice command (thread-safe for SQLite)."""
        try:
            if not title:
                return "Please provide an event title"
            
            from datetime import datetime, date, timedelta
            
            # Parse date ONCE (before threading)
            target_date = self._parse_date_hint(date_hint, title)
            
            # Parse time if provided
            start_time = None
            if time_str:
                try:
                    # Simple time parsing (e.g., "4pm", "2:30pm", "14:00", "5:00 p.m.")
                    time_str_lower = time_str.lower().strip()
                    
                    # Remove spaces and dots (e.g., "5:00 p.m." -> "5:00pm")
                    time_str_lower = time_str_lower.replace(' ', '').replace('.', '')
                    
                    # Handle formats like "4pm", "4:30pm", "5:00pm"
                    if 'pm' in time_str_lower or 'am' in time_str_lower:
                        # Try parsing with different formats
                        for fmt in ['%I%p', '%I:%M%p', '%I:%M:%S%p']:
                            try:
                                time_obj = datetime.strptime(time_str_lower, fmt).time()
                                start_time = datetime.combine(target_date, time_obj).isoformat()
                                break
                            except:
                                continue
                    # Handle 24-hour format like "14:00" or "17:00"
                    elif ':' in time_str_lower:
                        try:
                            # Try with seconds first, then without
                            for fmt in ['%H:%M:%S', '%H:%M']:
                                try:
                                    time_obj = datetime.strptime(time_str_lower, fmt).time()
                                    start_time = datetime.combine(target_date, time_obj).isoformat()
                                    break
                                except:
                                    continue
                        except:
                            pass
                    
                    # If parsing still failed, use a default time (noon)
                    if start_time is None:
                        print(f"Warning: Could not parse time '{time_str}', using default 12:00 PM")
                        time_obj = datetime.strptime("12:00pm", "%I:%M%p").time()
                        start_time = datetime.combine(target_date, time_obj).isoformat()
                except Exception as e:
                    print(f"Error parsing time: {e}")
                    # Use default time if parsing completely fails
                    try:
                        time_obj = datetime.strptime("12:00pm", "%I:%M%p").time()
                        start_time = datetime.combine(target_date, time_obj).isoformat()
                    except:
                        pass
            
            # Format the response message (before threading)
            today = date.today()
            if target_date == today:
                date_display = "today"
            elif target_date == today + timedelta(days=1):
                date_display = "tomorrow"
            else:
                date_display = target_date.strftime("%B %d")  # e.g., "December 5"
            
            response_msg = f"Added '{title}' on {date_display} at {time_str}" if time_str else f"Added '{title}' on {date_display}"
            
            # SQLite access must happen on main thread
            from threading import current_thread, main_thread, Event
            result_container = {'conflict_message': None, 'done': False}
            result_event = Event()
            
            def _check_and_add_on_main_thread(dt):
                try:
                    # Check for conflicts with existing events at the same date and time
                    conflict_message = None
                    if start_time:
                            try:
                                dt_obj = datetime.fromisoformat(start_time)
                                event_date = dt_obj.date()
                                existing_events = self.db.get_schedule_by_date_range(event_date, event_date)
                                
                                # Early exit if no events exist
                                if not existing_events:
                                    conflict_message = None
                                else:
                                    # Pre-calculate date display (used multiple times)
                                    today_check = date.today()
                                    if event_date == today_check:
                                        date_display_check = "today"
                                    elif event_date == today_check + timedelta(days=1):
                                        date_display_check = "tomorrow"
                                    else:
                                        date_display_check = event_date.strftime("%B %d")
                                    
                                    # Pre-parse all event times for faster comparison
                                    event_times = {}
                                    for event in existing_events:
                                        if event[2]:  # start_time
                                            try:
                                                existing_dt = datetime.fromisoformat(event[2])
                                                if existing_dt.date() == event_date:
                                                    time_key = (existing_dt.hour, existing_dt.minute)
                                                    if time_key not in event_times:
                                                        event_times[time_key] = event[1] if len(event) > 1 else "an event"
                                            except:
                                                pass
                                    
                                    # Check for conflict using pre-parsed times
                                    time_key = (dt_obj.hour, dt_obj.minute)
                                    if time_key in event_times:
                                        conflicting_title = event_times[time_key]
                                        
                                        # Suggest alternative times (optimized - check pre-parsed times)
                                        suggestions = []
                                        for offset_minutes in [-60, -30, 30, 60]:
                                            alt_time = dt_obj + timedelta(minutes=offset_minutes)
                                            alt_time_key = (alt_time.hour, alt_time.minute)
                                            if alt_time_key not in event_times:
                                                # Format time in 12-hour format
                                                hour_12 = alt_time.hour % 12
                                                if hour_12 == 0:
                                                    hour_12 = 12
                                                ampm = "am" if alt_time.hour < 12 else "pm"
                                                minute_str = f":{alt_time.minute:02d}" if alt_time.minute > 0 else ""
                                                suggestions.append(f"{hour_12}{minute_str}{ampm}")
                                                if len(suggestions) >= 3:  # Limit to 3 suggestions
                                                    break
                                        
                                        # Build response message
                                        if suggestions:
                                            suggestions_str = ", ".join(suggestions)
                                            conflict_message = f"You already have '{conflicting_title}' at {time_str} on {date_display_check}. How about {suggestions_str} instead?"
                                        else:
                                            conflict_message = f"You already have '{conflicting_title}' at {time_str} on {date_display_check}. Please choose a different time."
                            except Exception as e:
                                print(f"Error checking for conflicts: {e}")
                    
                    # Store result
                    result_container['conflict_message'] = conflict_message
                    
                    # Only create event if no conflict
                    if conflict_message is None:
                        event = Task(title=title, start_time=start_time)
                        self.db.add_schedule_item(event)
                        # Refresh UI
                        self.load_calendar_events()
                        self.update_schedule_display()
                    
                    result_container['done'] = True
                    result_event.set()
                except Exception as e:
                    print(f"Error adding event: {e}")
                    result_container['done'] = True
                    result_event.set()
            
            if current_thread() != main_thread():
                # Schedule database and UI updates on main thread (non-blocking)
                Clock.schedule_once(_check_and_add_on_main_thread, 0)
                
                # Wait for result (with shorter timeout to reduce lag)
                result_event.wait(timeout=0.2)
                
                # Check if there was a conflict
                if result_container['conflict_message']:
                    return result_container['conflict_message']
                # No conflict, return success message
                return response_msg
            else:
                # Already on main thread - check conflicts directly (optimized)
                if start_time:
                    try:
                        dt_obj = datetime.fromisoformat(start_time)
                        event_date = dt_obj.date()
                        existing_events = self.db.get_schedule_by_date_range(event_date, event_date)
                        
                        # Early exit if no events exist
                        if existing_events:
                            # Pre-calculate date display (used multiple times)
                            today_check = date.today()
                            if event_date == today_check:
                                date_display_check = "today"
                            elif event_date == today_check + timedelta(days=1):
                                date_display_check = "tomorrow"
                            else:
                                date_display_check = event_date.strftime("%B %d")
                            
                            # Pre-parse all event times for faster comparison
                            event_times = {}
                            for event in existing_events:
                                if event[2]:  # start_time
                                    try:
                                        existing_dt = datetime.fromisoformat(event[2])
                                        if existing_dt.date() == event_date:
                                            time_key = (existing_dt.hour, existing_dt.minute)
                                            if time_key not in event_times:
                                                event_times[time_key] = event[1] if len(event) > 1 else "an event"
                                    except:
                                        pass
                            
                            # Check for conflict using pre-parsed times
                            time_key = (dt_obj.hour, dt_obj.minute)
                            if time_key in event_times:
                                conflicting_title = event_times[time_key]
                                
                                # Suggest alternative times (optimized - check pre-parsed times)
                                suggestions = []
                                for offset_minutes in [-60, -30, 30, 60]:
                                    alt_time = dt_obj + timedelta(minutes=offset_minutes)
                                    alt_time_key = (alt_time.hour, alt_time.minute)
                                    if alt_time_key not in event_times:
                                        # Format time in 12-hour format
                                        hour_12 = alt_time.hour % 12
                                        if hour_12 == 0:
                                            hour_12 = 12
                                        ampm = "am" if alt_time.hour < 12 else "pm"
                                        minute_str = f":{alt_time.minute:02d}" if alt_time.minute > 0 else ""
                                        suggestions.append(f"{hour_12}{minute_str}{ampm}")
                                        if len(suggestions) >= 3:  # Limit to 3 suggestions
                                            break
                                
                                # Build response message
                                if suggestions:
                                    suggestions_str = ", ".join(suggestions)
                                    return f"You already have '{conflicting_title}' at {time_str} on {date_display_check}. How about {suggestions_str} instead?"
                                else:
                                    return f"You already have '{conflicting_title}' at {time_str} on {date_display_check}. Please choose a different time."
                    except Exception as e:
                        print(f"Error checking for conflicts: {e}")
                
                # No conflict, create event
                event = Task(title=title, start_time=start_time)
                self.db.add_schedule_item(event)
                # Refresh UI
                self.load_calendar_events()
                self.update_schedule_display()
            
            return response_msg
        except Exception as e:
            print(f"Error adding event: {e}")
            import traceback
            traceback.print_exc()
            return "Could not add event"
    
    def add_task_voice(self, title: str, priority: str = "medium") -> str:
        """Add task via voice command (thread-safe for SQLite)."""
        try:
            if not title:
                return "Please provide a task title"
            
            # Normalize priority
            priority = priority.lower() if priority else "medium"
            if priority not in ["high", "medium", "low"]:
                priority = "medium"
            
            # Schedule on main thread (non-blocking)
            def _add_on_main_thread(dt):
                try:
                    task = Task(title=title, priority=priority)
                    self.db.add_task(task)
                    self.load_tasks()
                    self.update_schedule_display()
                except Exception as e:
                    print(f"Error adding task: {e}")
                    import traceback
                    traceback.print_exc()
            
            Clock.schedule_once(_add_on_main_thread, 0)
            
            priority_text = f" ({priority} priority)" if priority != "medium" else ""
            return f"Added task: {title}{priority_text}"
        except Exception as e:
            print(f"Error adding task: {e}")
            import traceback
            traceback.print_exc()
            return "Could not add task"
    
    def add_multiple_tasks_voice(self, tasks_list: list) -> str:
        """Add multiple tasks at once via voice command."""
        try:
            if not tasks_list:
                return "No tasks provided"
            
            def _add_on_main_thread(dt):
                try:
                    for task_data in tasks_list:
                        title = task_data.get('title', '').strip()
                        priority = task_data.get('priority', 'medium')
                        if title:
                            task = Task(title=title, priority=priority)
                            self.db.add_task(task)
                    
                    self.load_tasks()
                    self.update_schedule_display()
                except Exception as e:
                    print(f"Error adding multiple tasks: {e}")
            
            Clock.schedule_once(_add_on_main_thread, 0)
            
            return f"Added {len(tasks_list)} tasks to your list!"
        except Exception as e:
            print(f"Error adding multiple tasks: {e}")
            import traceback
            traceback.print_exc()
            return "Could not add tasks"
    
    def add_multiple_events_voice(self, events_list: list) -> str:
        """Add multiple events at once via voice command."""
        try:
            if not events_list:
                return "No events provided"
            
            added_count = 0
            for event_data in events_list:
                title = event_data.get('title', '').strip()
                time_str = event_data.get('time', '')
                date_hint = event_data.get('date', 'today')
                
                if title:
                    # Use existing add_event_voice logic
                    result = self.add_event_voice(title, time_str, date_hint)
                    if "Added" in result:
                        added_count += 1
            
            return f"Added {added_count} events to your calendar!"
        except Exception as e:
            print(f"Error adding multiple events: {e}")
            import traceback
            traceback.print_exc()
            return "Could not add events"
    
    def suggest_task_priorities_voice(self) -> str:
        """AI suggests which tasks to tackle first based on task count and priorities."""
        try:
            if not self.tasks_list:
                return "You have no tasks! Great job staying on top of things."
            
            task_count = len(self.tasks_list)
            
            # Sort by priority
            high_priority = [t for t in self.tasks_list if t.get('priority') == 'high']
            medium_priority = [t for t in self.tasks_list if t.get('priority') == 'medium']
            low_priority = [t for t in self.tasks_list if t.get('priority') == 'low']
            
            # Generate advice based on task count and priorities
            if task_count <= 3:
                if high_priority:
                    return f"You have {task_count} tasks. Start with '{high_priority[0]['title']}' (high priority) to make progress!"
                else:
                    return f"You have {task_count} tasks. Start with '{self.tasks_list[0]['title']}' and build momentum!"
            
            elif task_count <= 6:
                suggestion = f"You have {task_count} tasks - a manageable list. "
                if high_priority:
                    suggestion += f"Focus on '{high_priority[0]['title']}' first (high priority), then tackle 1-2 medium priority tasks."
                else:
                    suggestion += f"Start with '{self.tasks_list[0]['title']}', then work through the rest one by one."
                return suggestion
            
            else:  # More than 6 tasks
                suggestion = f"You have {task_count} tasks - that's quite a lot! Here's my advice:\n"
                
                if high_priority:
                    suggestion += f"1. Start with high priority: '{high_priority[0]['title']}'\n"
                    if len(high_priority) > 1:
                        suggestion += f"2. Then: '{high_priority[1]['title']}'\n"
                    suggestion += "3. Take a break after completing 2-3 tasks\n"
                    suggestion += f"4. Consider if any of the {len(low_priority)} low priority tasks can wait"
                else:
                    suggestion += "1. Pick your top 3 most urgent tasks\n"
                    suggestion += "2. Focus on completing those first\n"
                    suggestion += "3. Take a break, then reassess\n"
                    suggestion += "4. Consider delegating or postponing some tasks"
                
                suggestion += "\n\nWant to start a 25-minute focus session?"
                return suggestion
                
        except Exception as e:
            print(f"Error suggesting priorities: {e}")
            import traceback
            traceback.print_exc()
            return "Let me help you prioritize your tasks"
    
    def get_stats_voice(self, period="today") -> str:
        """Get stats via voice (uses cached data for speed)."""
        try:
            # Use cached stats data instead of querying database
            if period == "today":
                # Use the stats already displayed on home screen
                stats = getattr(self, '_cached_today_stats', {'pomodoros': 0, 'focus_minutes': 0})
                return f"Today: {stats['pomodoros']} pomodoros, {stats['focus_minutes']} minutes focused"
            elif period == "week":
                stats = getattr(self, '_cached_week_stats', {'pomodoros': 0, 'focus_minutes': 0})
                return f"This week: {stats['pomodoros']} pomodoros, {stats['focus_minutes']} minutes"
            elif period == "alltime":
                # Try to read from profile screen if available
                try:
                    profile_screen = self.root.get_screen('profile')
                    pomodoros = profile_screen.ids.total_pomodoros.text
                    focus_time = profile_screen.ids.total_focus_time.text
                    return f"All time: {pomodoros} pomodoros, {focus_time} focused"
                except:
                    return "All time stats: Check your profile page for details"
            else:
                return "Available periods: today, week, alltime"
        except Exception as e:
            print(f"Error getting stats: {e}")
            return "Could not get stats"
    
    def get_streak_voice(self) -> str:
        """Get current streak (uses cached data for speed)."""
        try:
            # Try to read from profile screen if available (cached)
            try:
                profile_screen = self.root.get_screen('profile')
                current = profile_screen.ids.current_streak.text
                best = profile_screen.ids.best_streak.text
                return f"Your current streak is {current}! Best: {best}"
            except:
                # Fallback to cached value
                streak = getattr(self, '_cached_streak', {'current': 0, 'best': 0})
                current = streak['current']
                best = streak['best']
                
                if current > 0:
                    return f"Your current streak is {current} days! Best: {best} days"
                else:
                    return f"Start a focus session today to begin your streak! Best: {best} days"
        except Exception as e:
            print(f"Error getting streak: {e}")
            return "Could not get streak"
    
    def get_schedule_voice(self, date_hint: str = "today") -> str:
        """Get schedule for a specific date (uses cached calendar events for speed)."""
        try:
            from datetime import datetime, date, timedelta
            
            # Parse the target date
            target_date = self._parse_date_hint(date_hint, "")
            today = date.today()
            
            # Format date for display
            if target_date == today:
                date_display = "today"
            elif target_date == today + timedelta(days=1):
                date_display = "tomorrow"
            else:
                date_display = target_date.strftime("%B %d")  # e.g., "December 5"
            
            # Use cached calendar_events instead of querying database
            target_events = []
            for event in self.calendar_events:
                if event.get('start_time'):
                    try:
                        dt = datetime.fromisoformat(event['start_time'])
                        if dt.date() == target_date:
                            target_events.append(event)
                    except:
                        pass
            
            if not target_events:
                return f"No events scheduled for {date_display}"
            
            # Format event list with time
            event_list = []
            for event in target_events[:5]:  # Show up to 5 events
                title = event.get('title', 'Event')
                start_time = event.get('start_time')
                
                if start_time:
                    try:
                        dt = datetime.fromisoformat(start_time)
                        time_str = dt.strftime("%I:%M %p").lstrip('0')
                        event_list.append(f"• {time_str}: {title}")
                    except:
                        event_list.append(f"• {title}")
                else:
                    event_list.append(f"• {title}")
            
            if len(target_events) > 5:
                event_list.append(f"... and {len(target_events) - 5} more")
            
            return f"Schedule for {date_display}:\n" + "\n".join(event_list)
        except Exception as e:
            print(f"Error getting schedule: {e}")
            return "Could not get schedule"
    
    def check_daily_notifications(self, dt=None):
        """Check and send daily goal reminders and streak alerts."""
        try:
            from datetime import datetime, time
            now = datetime.now()
            current_time = now.time()
            
            # Daily goal reminder at 9:00 AM (within 1 hour window)
            morning_start = time(9, 0)
            morning_end = time(10, 0)
            if morning_start <= current_time <= morning_end:
                # Check if we already sent today (simple check using last session date)
                today_stats = self.stats_manager.get_daily_stats()
                if today_stats['focus_minutes'] == 0:  # No sessions yet today
                    self.notification_service.notify_daily_goal()
            
            # Streak alert at 8:00 PM (within 1 hour window)
            evening_start = time(20, 0)
            evening_end = time(21, 0)
            if evening_start <= current_time <= evening_end:
                today_stats = self.stats_manager.get_daily_stats()
                if today_stats['focus_minutes'] == 0:  # No sessions yet today
                    streak = self.stats_manager.get_focus_streak()
                    current_streak = streak['current']
                    if current_streak > 0:  # Only alert if there's a streak to maintain
                        self.notification_service.notify_streak_alert(current_streak)
        except Exception as e:
            print(f"Error checking daily notifications: {e}")
    
    def _get_first_session_date(self):
        """Get the date of the first focus session."""
        try:
            cursor = self.stats_manager.conn.cursor()
            cursor.execute("""
                SELECT MIN(date) as first_date
                FROM focus_sessions
            """)
            row = cursor.fetchone()
            if row and row["first_date"]:
                return datetime.strptime(row["first_date"], "%Y-%m-%d").date()
        except Exception:
            pass
        return None
    
    def prev_month(self):
        """Navigate to previous month."""
        self.calendar_manager.prev_month()
    
    def next_month(self):
        """Navigate to next month."""
        self.calendar_manager.next_month()
    
    def navigate_to_today(self):
        """Navigate to today's month and date."""
        self.calendar_manager.navigate_to_today()
    
    def show_day_events(self, date_str):
        """Show events popup for a specific date."""
        self.calendar_manager.show_day_events(date_str)
    
    def render_event_list(self, calendar_screen):
        """Render the event list for the selected month."""
        events_container = calendar_screen.ids.events_list_container
        events_container.clear_widgets()
        
        if not self.calendar_events:
            # Show empty state
            empty_label = Label(
                text="No events for this month.\nTap + to add an event!",
                color=(0.8, 0.8, 1, 1),
                font_size="15sp",
                size_hint_y=None,
                height=dp(80),
                halign="center",
                valign="middle"
            )
            empty_label.text_size = (None, None)
            events_container.add_widget(empty_label)
        else:
            # Group events by date
            events_by_date = {}
            for event in self.calendar_events:
                if event['start_time']:
                    try:
                        dt = datetime.fromisoformat(event['start_time'])
                        event_date_str = dt.strftime("%Y-%m-%d")
                        if event_date_str not in events_by_date:
                            events_by_date[event_date_str] = []
                        events_by_date[event_date_str].append(event)
                    except:
                        pass
            
            # Sort by date
            sorted_dates = sorted(events_by_date.keys())
            
            for date_str in sorted_dates:
                # Date header
                dt = datetime.fromisoformat(date_str + " 00:00:00")
                date_header = Label(
                    text=dt.strftime("%B %d, %Y"),
                    color=(0.3, 0.98, 0.6, 1),
                    font_size="16sp",
                    bold=True,
                    size_hint_y=None,
                    height=dp(35),
                    halign="left",
                    valign="middle"
                )
                date_header.text_size = (None, None)
                events_container.add_widget(date_header)
                
                # Events for this date
                for event in events_by_date[date_str]:
                    dt = datetime.fromisoformat(event['start_time'])
                    time_str = dt.strftime("%I:%M %p").lstrip('0')
                    date_str_formatted = dt.strftime("%m/%d/%Y")
                    
                    event_item = Factory.EventListItem()
                    event_item.event_id = event['id']
                    event_item.event_title = event['title']
                    event_item.event_time = time_str
                    event_item.event_date = date_str_formatted
                    event_item.event_source = event['source']
                    events_container.add_widget(event_item)
    
    # Event management methods - delegated to EventManager
    def open_create_event_popup(self):
        self.event_manager.open_create_event_popup()
    
    def open_date_picker_for_event(self, event_popup):
        self.event_manager.open_date_picker_for_event(event_popup)
    
    def date_picker_prev_month(self):
        self.event_manager.date_picker_prev_month()
    
    def date_picker_next_month(self):
        self.event_manager.date_picker_next_month()
    
    def render_date_picker_calendar(self):
        self.event_manager.render_date_picker_calendar()
    
    def select_date_from_picker(self, date_str):
        self.event_manager.select_date_from_picker(date_str)
    
    def confirm_date_selection(self):
        self.event_manager.confirm_date_selection()
    
    def open_time_picker_for_event(self, event_popup):
        self.event_manager.open_time_picker_for_event(event_popup)
    
    def render_time_picker(self):
        self.event_manager.render_time_picker()
    
    def scroll_to_selected_time(self):
        self.event_manager.scroll_to_selected_time()
    
    def select_hour(self, hour):
        self.event_manager.select_hour(hour)
    
    def select_minute(self, minute):
        self.event_manager.select_minute(minute)
    
    def select_ampm(self, ampm):
        self.event_manager.select_ampm(ampm)
    
    def update_time_picker_highlighting(self):
        self.event_manager.update_time_picker_highlighting()
    
    def update_time_display(self):
        self.event_manager.update_time_display()
    
    def confirm_time_selection(self):
        self.event_manager.confirm_time_selection()
    
    def on_recurring_toggle_changed(self, popup, is_active):
        self.event_manager.on_recurring_toggle_changed(popup, is_active)
    
    def on_repeat_day_changed(self, day_num, state):
        self.event_manager.on_repeat_day_changed(day_num, state)
    
    def create_event_from_popup(self, popup):
        self.event_manager.create_event_from_popup(popup)
    
    def show_error_popup(self, message):
        self.event_manager.show_error_popup(message)
    
    def open_date_picker_for_edit_event(self, event_popup):
        self.event_manager.open_date_picker_for_edit_event(event_popup)
    
    def open_time_picker_for_edit_event(self, event_popup):
        self.event_manager.open_time_picker_for_edit_event(event_popup)
    
    def update_event_from_popup(self, popup):
        self.event_manager.update_event_from_popup(popup)
    
    def delete_event(self, event_id):
        self.event_manager.delete_event(event_id)
    
    def open_event_actions_popup(self, event_id, event_title):
        self.event_manager.open_event_actions_popup(event_id, event_title)
    
    def edit_event_from_day_popup(self, event_id):
        self.event_manager.edit_event_from_day_popup(event_id)
    
    def delete_event_from_day_popup(self, event_id):
        self.event_manager.delete_event_from_day_popup(event_id)
    
    def _on_request_close(self, *args):
        """Handle window close; run cleanup and allow exit."""
        try:
            # Prevent re-entrancy
            if getattr(self, "_is_shutting_down", False):
                return False
            self.on_stop()
        except Exception as e:
            print(f"[CLOSE] Error during request close: {e}")
        return False  # Return False so Kivy continues closing
    
    def on_stop(self):
        """Clean up resources when app closes."""
        try:
            print("[CLEANUP] Starting app cleanup...")
            
            # Set shutdown flag FIRST to prevent new operations
            self._is_shutting_down = True
            
            # CRITICAL: Stop timer first (prevents UI updates during shutdown)
            if hasattr(self, 'timer') and self.timer:
                try:
                    if hasattr(self.timer, '_scheduled_event') and self.timer._scheduled_event:
                        self.timer._scheduled_event.cancel()
                        self.timer._scheduled_event = None
                    self.timer.is_running = False
                    print("[CLEANUP] Stopped timer")
                except Exception as e:
                    print(f"[CLEANUP] Error stopping timer: {e}")
            
            # Unschedule all Clock events
            try:
                Clock.unschedule(self.check_daily_notifications)
                print("[CLEANUP] Unscheduled clock events")
            except:
                pass
            
            # Stop voice handler properly (call cleanup method)
            if hasattr(self, 'voice_handler') and self.voice_handler:
                try:
                    self.voice_handler.is_listening = False
                    self.voice_handler.is_speaking = False
                    self.voice_handler.cleanup()  # Call cleanup method
                    print("[CLEANUP] Stopped voice handler")
                except Exception as e:
                    print(f"[CLEANUP] Error stopping voice handler: {e}")
            
            # Ensure TTS engine is stopped and released to avoid shutdown hangs
            try:
                if hasattr(self, 'voice_handler') and self.voice_handler and hasattr(self.voice_handler, 'tts_engine'):
                    if self.voice_handler.tts_engine:
                        self.voice_handler.tts_engine.stop()
                        self.voice_handler.tts_engine = None
                        print("[CLEANUP] TTS engine stopped")
            except Exception as e:
                print(f"[CLEANUP] Error stopping TTS engine: {e}")
            
            # Close voice popup (don't wait)
            if hasattr(self, 'voice_popup') and self.voice_popup:
                try:
                    self.voice_popup.dismiss()
                    self.voice_popup = None
                    print("[CLEANUP] Dismissed voice popup")
                except Exception as e:
                    print(f"[CLEANUP] Error dismissing popup: {e}")
            
            # Close database connections (important!)
            try:
                if hasattr(self, 'db') and self.db and hasattr(self.db, 'conn'):
                    self.db.conn.close()
                    print("[CLEANUP] Closed main database")
            except Exception as e:
                print(f"[CLEANUP] Error closing main database: {e}")
            
            try:
                if hasattr(self, 'stats_manager') and self.stats_manager and hasattr(self.stats_manager, 'conn'):
                    self.stats_manager.conn.close()
                    print("[CLEANUP] Closed stats database")
            except Exception as e:
                print(f"[CLEANUP] Error closing stats database: {e}")
            
            try:
                if hasattr(self, 'profile_manager') and self.profile_manager and hasattr(self.profile_manager, 'conn'):
                    self.profile_manager.conn.close()
                    print("[CLEANUP] Closed profile database")
            except Exception as e:
                print(f"[CLEANUP] Error closing profile database: {e}")
            
            try:
                if hasattr(self, 'notification_manager') and self.notification_manager and hasattr(self.notification_manager, 'conn'):
                    self.notification_manager.conn.close()
                    print("[CLEANUP] Closed notification database")
            except Exception as e:
                print(f"[CLEANUP] Error closing notification database: {e}")
            
            print("[CLEANUP] Cleanup complete - app can close now")
        except Exception as e:
            print(f"[CLEANUP] Error during cleanup: {e}")
            import traceback
            traceback.print_exc()
        
        # Don't block - return immediately
        return False  # Allow Kivy to handle cleanup


if __name__ == '__main__':
    Home().run()

