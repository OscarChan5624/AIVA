"""
Calendar Manager - Handles all calendar screen functionality
"""
import calendar
from datetime import date
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.factory import Factory


class CalendarManager:
    """Manages calendar screen functionality."""
    
    def __init__(self, app_instance):
        """Initialize calendar manager with app instance."""
        self.app = app_instance
    
    def initialize_calendar(self):
        """Initialize calendar with current date."""
        today = date.today()
        self.app.current_year = today.year
        self.app.current_month = today.month
        self.app.selected_year = today.year
        self.app.selected_month = today.month
        self.app.month_year_text = self.get_month_year_text()
        self.update_today_text()
        self.load_calendar_month(self.app.selected_year, self.app.selected_month)
    
    def get_month_year_text(self):
        """Get formatted month/year text."""
        month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                      'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        return f"{month_names[self.app.selected_month - 1]} {self.app.selected_year}"
    
    def update_today_text(self):
        """Update the today text label."""
        today = date.today()
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday = today.weekday()  # Monday is 0, Sunday is 6
        self.app.today_text = f"Today: {day_names[weekday]}, {month_names[today.month - 1]} {today.day}, {today.year}"
    
    def navigate_to_calendar(self):
        """Navigate to calendar screen."""
        self.app.root.current = 'calendar'
        # Refresh calendar when navigating to it
        self.load_calendar_month(self.app.selected_year, self.app.selected_month)
    
    def navigate_to_today(self):
        """Navigate to today's month and date."""
        today = date.today()
        self.app.selected_year = today.year
        self.app.selected_month = today.month
        self.load_calendar_month(self.app.selected_year, self.app.selected_month)
    
    def show_day_events(self, date_str):
        """Show events popup for a specific date."""
        if not date_str:
            return
        
        from datetime import datetime
        from kivy.uix.label import Label
        try:
            # Parse the date
            event_date = datetime.fromisoformat(date_str).date()
            
            # Get events for this date
            events = self.app.db.get_schedule_by_date_range(event_date, event_date)
            
            # Create popup
            popup = Factory.DayEventsPopup()
            
            # Store reference to popup and date in app for refreshing after edit/delete
            self.app.current_day_events_popup = popup
            self.app.current_day_events_date = date_str
            
            # Format date text
            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday = event_date.weekday()
            popup.date_text = f"{day_names[weekday]}, {month_names[event_date.month - 1]} {event_date.day}, {event_date.year}"
            
            # Populate events
            self._populate_day_events_popup(popup, events)
            
            popup.open()
        except Exception as e:
            print(f"Error showing day events: {e}")
    
    def _populate_day_events_popup(self, popup, events):
        """Populate the day events popup with events."""
        from datetime import datetime
        from kivy.uix.label import Label
        
        events_container = popup.ids.day_events_container
        events_container.clear_widgets()
        
        if not events:
            # Show empty state
            empty_label = Label(
                text="No events for this day.",
                color=(0.8, 0.8, 1, 1),
                font_size="15sp",
                size_hint_y=None,
                height=dp(60),
                halign="center",
                valign="middle"
            )
            empty_label.text_size = (None, None)
            events_container.add_widget(empty_label)
        else:
            # Add events
            for event in events:
                event_item = Factory.EventListItem()
                event_item.event_id = event[0]
                event_item.event_title = event[1]
                
                # Format time (only show time, not date since it's already in header)
                if event[2]:  # start_time
                    try:
                        dt = datetime.fromisoformat(event[2])
                        time_str = dt.strftime("%I:%M %p").lstrip("0")
                        # Remove leading space if hour was single digit
                        if time_str.startswith(" "):
                            time_str = time_str[1:]
                        event_item.event_time = time_str
                        event_item.event_date = ""  # Empty since date is in popup header
                    except:
                        event_item.event_time = ""
                        event_item.event_date = ""
                else:
                    event_item.event_time = ""
                    event_item.event_date = ""
                
                event_item.event_source = event[3] if len(event) > 3 else 'local'
                event_item.event_is_recurring = bool(event[6]) if len(event) > 6 else False
                events_container.add_widget(event_item)
    
    def refresh_day_events_popup(self):
        """Refresh the current day events popup with updated events."""
        if not hasattr(self.app, 'current_day_events_popup') or not self.app.current_day_events_popup:
            return
        if not hasattr(self.app, 'current_day_events_date') or not self.app.current_day_events_date:
            return
        
        from datetime import datetime
        try:
            date_str = self.app.current_day_events_date
            event_date = datetime.fromisoformat(date_str).date()
            events = self.app.db.get_schedule_by_date_range(event_date, event_date)
            popup = self.app.current_day_events_popup
            self._populate_day_events_popup(popup, events)
        except Exception as e:
            print(f"Error refreshing day events popup: {e}")
    
    def prev_month(self):
        """Navigate to previous month."""
        if self.app.selected_month == 1:
            self.app.selected_month = 12
            self.app.selected_year -= 1
        else:
            self.app.selected_month -= 1
        self.load_calendar_month(self.app.selected_year, self.app.selected_month)
    
    def next_month(self):
        """Navigate to next month."""
        if self.app.selected_month == 12:
            self.app.selected_month = 1
            self.app.selected_year += 1
        else:
            self.app.selected_month += 1
        self.load_calendar_month(self.app.selected_year, self.app.selected_month)
    
    def load_calendar_month(self, year, month):
        """Load calendar for a specific month."""
        self.app.selected_year = year
        self.app.selected_month = month
        self.app.month_year_text = self.get_month_year_text()
        # Update calendar display
        try:
            calendar_screen = self.app.root.get_screen('calendar')
            self.render_calendar_grid(calendar_screen)
            if hasattr(calendar_screen.ids, 'month_year_label'):
                calendar_screen.ids.month_year_label.text = self.app.month_year_text
        except:
            pass
    
    def render_calendar_grid(self, calendar_screen):
        """Render the calendar grid for the selected month."""
        grid_container = calendar_screen.ids.calendar_grid_container
        grid_container.clear_widgets()
        
        # Get calendar data
        cal = calendar.monthcalendar(self.app.selected_year, self.app.selected_month)
        today = date.today()
        
        # Get events for the current month to check which dates have events
        events = self.app.db.get_schedule_by_month(self.app.selected_year, self.app.selected_month)
        events_by_date = {}
        recurring_events_by_date = {}
        from datetime import datetime
        for event in events:
            if event[2]:  # start_time
                try:
                    dt = datetime.fromisoformat(event[2])
                    event_date = dt.date()
                    is_recurring = bool(event[6]) if len(event) > 6 else False
                    if is_recurring:
                        if event_date not in recurring_events_by_date:
                            recurring_events_by_date[event_date] = True
                    else:
                        if event_date not in events_by_date:
                            events_by_date[event_date] = True
                except:
                    pass
        
        # Weekday headers (Monday-first to match Python's calendar.monthcalendar)
        weekdays = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
        weekday_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30))
        for day_name in weekdays:
            label = Label(text=day_name, color=(0.8, 0.8, 1, 1), 
                         font_size='12sp', size_hint_x=1/7, halign='center', valign='middle')
            label.text_size = (None, None)
            weekday_row.add_widget(label)
        grid_container.add_widget(weekday_row)
        
        # Calendar rows - simple numbers only
        for week in cal:
            week_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
            for day in week:
                day_button = Factory.CalendarDayButton()
                if day == 0:
                    day_button.text = ""
                    day_button.day = 0
                    day_button.is_today = False
                    day_button.day_date = ""  # Empty for days outside month
                    day_button.has_events = False
                else:
                    day_button.text = str(day)
                    day_button.day = day
                    # Check if this is today's date
                    day_date = date(self.app.selected_year, self.app.selected_month, day)
                    day_button.is_today = (day_date == today)
                    day_button.day_date = day_date.isoformat()  # Store date as ISO string
                    # Check if this date has events
                    day_button.has_events = events_by_date.get(day_date, False)
                    day_button.has_recurring_events = recurring_events_by_date.get(day_date, False)
                day_button.size_hint_x = 1/7
                day_button.size_hint_y = None
                day_button.height = dp(45)
                week_row.add_widget(day_button)
            grid_container.add_widget(week_row)

