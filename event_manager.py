from kivy.factory import Factory
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.clock import Clock
from task import Task
from datetime import datetime, date
import calendar


class EventManager:
    """Manages all event-related operations including creation, editing, deletion, and date/time pickers."""
    
    def __init__(self, app_instance):
        """Initialize with reference to the main app instance."""
        self.app = app_instance
    
    def open_create_event_popup(self):
        """Open the create event popup."""
        popup = Factory.EventCreatePopup()
        # Store reference to the popup
        self.app.current_event_popup = popup
        # Reset date and time buttons
        popup.ids.event_date_button.text = 'Select Date'
        popup.ids.event_time_button.text = 'Select Time'
        self.app.selected_event_date = None
        self.app.selected_event_time = None
        # Initialize recurring event settings
        self.app.is_recurring = False
        self.app.selected_repeat_days = []  # List of weekday numbers (0=Monday, 6=Sunday)
        # Initialize date picker to current month or selected month
        self.app.date_picker_year = self.app.selected_year
        self.app.date_picker_month = self.app.selected_month
        popup.open()
    
    def open_date_picker_for_event(self, event_popup):
        """Open date picker popup for event creation."""
        self.app.current_event_popup = event_popup
        date_picker = Factory.DatePickerPopup()
        self.app.date_picker_popup = date_picker
        self.render_date_picker_calendar()
        date_picker.open()
    
    def date_picker_prev_month(self):
        """Navigate to previous month in date picker."""
        if self.app.date_picker_month == 1:
            self.app.date_picker_month = 12
            self.app.date_picker_year -= 1
        else:
            self.app.date_picker_month -= 1
        if hasattr(self.app, 'date_picker_popup'):
            self.render_date_picker_calendar()
    
    def date_picker_next_month(self):
        """Navigate to next month in date picker."""
        if self.app.date_picker_month == 12:
            self.app.date_picker_month = 1
            self.app.date_picker_year += 1
        else:
            self.app.date_picker_month += 1
        if hasattr(self.app, 'date_picker_popup'):
            self.render_date_picker_calendar()
    
    def render_date_picker_calendar(self):
        """Render the calendar grid in the date picker."""
        if not hasattr(self.app, 'date_picker_popup'):
            return
        
        grid_container = self.app.date_picker_popup.ids.date_picker_calendar_grid
        grid_container.clear_widgets()
        
        # Update month/year label
        month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                      'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        month_text = f"{month_names[self.app.date_picker_month - 1]} {self.app.date_picker_year}"
        self.app.date_picker_popup.ids.date_picker_month_label.text = month_text
        
        # Get calendar data
        cal = calendar.monthcalendar(self.app.date_picker_year, self.app.date_picker_month)
        today = date.today()
        
        # Weekday headers
        weekdays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']
        weekday_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30))
        for day_name in weekdays:
            label = Label(text=day_name, color=(0.8, 0.8, 1, 1), 
                         font_size='12sp', size_hint_x=1/7, halign='center', valign='middle')
            label.text_size = (None, None)
            weekday_row.add_widget(label)
        grid_container.add_widget(weekday_row)
        
        # Calendar rows
        for week in cal:
            week_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
            for day in week:
                day_button = Button()
                if day == 0:
                    day_button.text = ""
                    day_button.background_color = 0, 0, 0, 0
                    day_button.disabled = True
                else:
                    day_button.text = str(day)
                    day_date = date(self.app.date_picker_year, self.app.date_picker_month, day)
                    # Highlight today
                    if day_date == today:
                        day_button.background_color = 0.2, 0.5, 0.95, 0.3
                    else:
                        day_button.background_color = 0.15, 0.15, 0.26, 1
                    day_button.color = (1, 1, 1, 1)
                    day_button.font_size = '14sp'
                    day_button.background_normal = ''
                    # Store date on button and use closure to capture date
                    day_date_iso = day_date.isoformat()
                    # Use a closure factory to capture the date value
                    def make_date_handler(d):
                        return lambda btn: self.select_date_from_picker(d)
                    day_button.bind(on_release=make_date_handler(day_date_iso))
                day_button.size_hint_x = 1/7
                day_button.size_hint_y = None
                day_button.height = dp(45)
                week_row.add_widget(day_button)
            grid_container.add_widget(week_row)
    
    def select_date_from_picker(self, date_str):
        """Handle date selection from date picker."""
        self.app.selected_event_date = date_str
        # Update button text (works for both create and edit popups)
        selected_date = datetime.fromisoformat(date_str).date()
        formatted_date = selected_date.strftime("%Y-%m-%d")
        if hasattr(self.app.current_event_popup, 'ids'):
            if 'event_date_button' in self.app.current_event_popup.ids:
                self.app.current_event_popup.ids.event_date_button.text = formatted_date
            elif 'edit_event_date_button' in self.app.current_event_popup.ids:
                self.app.current_event_popup.ids.edit_event_date_button.text = formatted_date
        # Close date picker and open time picker
        self.app.date_picker_popup.dismiss()
        # Check if it's edit or create popup
        if hasattr(self.app.current_event_popup, 'event_id') and self.app.current_event_popup.event_id:
            self.open_time_picker_for_edit_event(self.app.current_event_popup)
        else:
            self.open_time_picker_for_event(self.app.current_event_popup)
    
    def confirm_date_selection(self):
        """Confirm date selection (if needed)."""
        if self.app.selected_event_date:
            selected_date = datetime.fromisoformat(self.app.selected_event_date).date()
            formatted_date = selected_date.strftime("%Y-%m-%d")
            if hasattr(self.app.current_event_popup, 'ids'):
                if 'event_date_button' in self.app.current_event_popup.ids:
                    self.app.current_event_popup.ids.event_date_button.text = formatted_date
                elif 'edit_event_date_button' in self.app.current_event_popup.ids:
                    self.app.current_event_popup.ids.edit_event_date_button.text = formatted_date
            self.app.date_picker_popup.dismiss()
            # Check if it's edit or create popup
            if hasattr(self.app.current_event_popup, 'event_id') and self.app.current_event_popup.event_id:
                self.open_time_picker_for_edit_event(self.app.current_event_popup)
            else:
                self.open_time_picker_for_event(self.app.current_event_popup)
    
    def open_time_picker_for_event(self, event_popup):
        """Open time picker popup for event creation."""
        self.app.current_event_popup = event_popup
        # Reset time selection to default 12:00 PM when opening time picker
        self.app.selected_hour = 12
        self.app.selected_minute = 0
        self.app.selected_ampm = 'PM'
        time_picker = Factory.EventTimePickerPopup()
        self.app.time_picker_popup = time_picker
        self.render_time_picker()
        time_picker.open()
    
    def render_time_picker(self):
        """Render the time picker with scrollable hour, minute, and AM/PM selectors."""
        if not hasattr(self.app, 'time_picker_popup'):
            return
        
        hour_grid = self.app.time_picker_popup.ids.hour_grid
        minute_grid = self.app.time_picker_popup.ids.minute_grid
        ampm_grid = self.app.time_picker_popup.ids.ampm_grid
        hour_grid.clear_widgets()
        minute_grid.clear_widgets()
        ampm_grid.clear_widgets()
        
        # Initialize default values to 12:00 PM if not already set
        if not hasattr(self.app, 'selected_hour') or self.app.selected_hour is None:
            self.app.selected_hour = 12
        if not hasattr(self.app, 'selected_minute') or self.app.selected_minute is None:
            self.app.selected_minute = 0
        if not hasattr(self.app, 'selected_ampm') or self.app.selected_ampm is None:
            self.app.selected_ampm = 'PM'
        
        # Create hour buttons (1-12)
        for hour in range(1, 13):
            hour_btn = Button()
            hour_btn.text = str(hour).zfill(2)
            hour_btn.size_hint_y = None
            hour_btn.height = dp(50)
            hour_btn.background_normal = ''
            # Highlight selected hour
            if hour == self.app.selected_hour:
                hour_btn.background_color = (0.3, 0.98, 0.6, 0.5)
            else:
                hour_btn.background_color = (0.15, 0.15, 0.26, 1)
            hour_btn.color = (1, 1, 1, 1)
            hour_btn.font_size = '16sp'
            hour_btn.hour_value = hour
            # Use a closure to capture the hour value
            def make_hour_handler(h):
                return lambda btn: self.select_hour(h)
            hour_btn.bind(on_release=make_hour_handler(hour))
            hour_grid.add_widget(hour_btn)
        
        # Create minute buttons (0-59, in 5-minute intervals for better UX)
        for minute in range(0, 60, 5):
            minute_btn = Button()
            minute_btn.text = str(minute).zfill(2)
            minute_btn.size_hint_y = None
            minute_btn.height = dp(50)
            minute_btn.background_normal = ''
            # Highlight selected minute
            if minute == self.app.selected_minute:
                minute_btn.background_color = (0.3, 0.98, 0.6, 0.5)
            else:
                minute_btn.background_color = (0.15, 0.15, 0.26, 1)
            minute_btn.color = (1, 1, 1, 1)
            minute_btn.font_size = '16sp'
            minute_btn.minute_value = minute
            # Use a closure to capture the minute value
            def make_minute_handler(m):
                return lambda btn: self.select_minute(m)
            minute_btn.bind(on_release=make_minute_handler(minute))
            minute_grid.add_widget(minute_btn)
        
        # Create AM/PM buttons
        for ampm in ['AM', 'PM']:
            ampm_btn = Button()
            ampm_btn.text = ampm
            ampm_btn.size_hint_y = None
            ampm_btn.height = dp(50)
            ampm_btn.background_normal = ''
            # Highlight selected AM/PM
            if ampm == self.app.selected_ampm:
                ampm_btn.background_color = (0.3, 0.98, 0.6, 0.5)
            else:
                ampm_btn.background_color = (0.15, 0.15, 0.26, 1)
            ampm_btn.color = (1, 1, 1, 1)
            ampm_btn.font_size = '16sp'
            ampm_btn.ampm_value = ampm
            # Use a closure to capture the AM/PM value
            def make_ampm_handler(a):
                return lambda btn: self.select_ampm(a)
            ampm_btn.bind(on_release=make_ampm_handler(ampm))
            ampm_grid.add_widget(ampm_btn)
        
        # Update display with default values
        self.update_time_display()
        
        # Scroll to selected values after widgets are laid out
        Clock.schedule_once(lambda dt: self.scroll_to_selected_time(), 0.2)
    
    def scroll_to_selected_time(self):
        """Scroll the time picker to show the selected values."""
        if not hasattr(self.app, 'time_picker_popup'):
            return
        
        try:
            # Scroll to selected hour (12 is at index 11, which should be near the bottom)
            hour_grid = self.app.time_picker_popup.ids.hour_grid
            hour_scroll = self.app.time_picker_popup.ids.hour_scroll
            if self.app.selected_hour:
                # Calculate total height of all buttons
                button_height = dp(50)
                spacing = dp(4)
                total_height = (button_height + spacing) * 12 - spacing  # 12 buttons
                
                # Calculate position of selected button (0-based index from top)
                selected_index = self.app.selected_hour - 1  # 0-11
                button_top = selected_index * (button_height + spacing)
                
                # Scroll to center the selected button in the visible area
                scroll_view_height = hour_scroll.height
                if scroll_view_height > 0 and total_height > scroll_view_height:
                    # Center the selected button
                    target_y = button_top - (scroll_view_height - button_height) / 2
                    # Normalize to 0-1 (0 = bottom, 1 = top in ScrollView)
                    scroll_y = 1.0 - (target_y / (total_height - scroll_view_height))
                    scroll_y = max(0, min(1, scroll_y))
                    hour_scroll.scroll_y = scroll_y
            
            # Scroll to selected minute (00 is at the top)
            minute_grid = self.app.time_picker_popup.ids.minute_grid
            minute_scroll = self.app.time_picker_popup.ids.minute_scroll
            if self.app.selected_minute is not None:
                button_height = dp(50)
                spacing = dp(4)
                # Minutes are in 5-minute intervals: 0, 5, 10, ..., 55 (12 buttons)
                total_minutes = 12
                total_height = (button_height + spacing) * total_minutes - spacing
                
                selected_index = self.app.selected_minute // 5
                button_top = selected_index * (button_height + spacing)
                
                scroll_view_height = minute_scroll.height
                if scroll_view_height > 0 and total_height > scroll_view_height:
                    target_y = button_top - (scroll_view_height - button_height) / 2
                    scroll_y = 1.0 - (target_y / (total_height - scroll_view_height))
                    scroll_y = max(0, min(1, scroll_y))
                    minute_scroll.scroll_y = scroll_y
            
            # Scroll to selected AM/PM (PM is at index 1)
            ampm_grid = self.app.time_picker_popup.ids.ampm_grid
            ampm_scroll = self.app.time_picker_popup.ids.ampm_scroll
            if self.app.selected_ampm:
                button_height = dp(50)
                spacing = dp(4)
                total_height = (button_height + spacing) * 2 - spacing  # 2 buttons
                
                ampm_index = 0 if self.app.selected_ampm == 'AM' else 1
                button_top = ampm_index * (button_height + spacing)
                
                scroll_view_height = ampm_scroll.height
                if scroll_view_height > 0 and total_height > scroll_view_height:
                    target_y = button_top - (scroll_view_height - button_height) / 2
                    scroll_y = 1.0 - (target_y / (total_height - scroll_view_height))
                    scroll_y = max(0, min(1, scroll_y))
                    ampm_scroll.scroll_y = scroll_y
        except Exception as e:
            print(f"Error scrolling to selected time: {e}")
            pass
    
    def select_hour(self, hour):
        """Handle hour selection (1-12)."""
        self.app.selected_hour = hour
        # Update button highlighting
        self.update_time_picker_highlighting()
        self.update_time_display()
    
    def select_minute(self, minute):
        """Handle minute selection."""
        self.app.selected_minute = minute
        # Update button highlighting
        self.update_time_picker_highlighting()
        self.update_time_display()
    
    def select_ampm(self, ampm):
        """Handle AM/PM selection."""
        self.app.selected_ampm = ampm
        # Update button highlighting
        self.update_time_picker_highlighting()
        self.update_time_display()
    
    def update_time_picker_highlighting(self):
        """Update the highlighting of selected hour, minute, and AM/PM buttons."""
        if not hasattr(self.app, 'time_picker_popup'):
            return
        
        try:
            # Update hour buttons
            hour_grid = self.app.time_picker_popup.ids.hour_grid
            for child in hour_grid.children:
                if hasattr(child, 'hour_value'):
                    if child.hour_value == self.app.selected_hour:
                        child.background_color = (0.3, 0.98, 0.6, 0.5)
                    else:
                        child.background_color = (0.15, 0.15, 0.26, 1)
            
            # Update minute buttons
            minute_grid = self.app.time_picker_popup.ids.minute_grid
            for child in minute_grid.children:
                if hasattr(child, 'minute_value'):
                    if child.minute_value == self.app.selected_minute:
                        child.background_color = (0.3, 0.98, 0.6, 0.5)
                    else:
                        child.background_color = (0.15, 0.15, 0.26, 1)
            
            # Update AM/PM buttons
            ampm_grid = self.app.time_picker_popup.ids.ampm_grid
            for child in ampm_grid.children:
                if hasattr(child, 'ampm_value'):
                    if child.ampm_value == self.app.selected_ampm:
                        child.background_color = (0.3, 0.98, 0.6, 0.5)
                    else:
                        child.background_color = (0.15, 0.15, 0.26, 1)
        except:
            pass
    
    def update_time_display(self):
        """Update the selected time display in time picker."""
        if not hasattr(self.app, 'time_picker_popup'):
            return
        
        if self.app.selected_hour is not None and self.app.selected_minute is not None and self.app.selected_ampm is not None:
            # Format time with lowercase am/pm
            ampm_lower = self.app.selected_ampm.lower()
            time_str = f"{self.app.selected_hour:02d}:{self.app.selected_minute:02d} {ampm_lower}"
            self.app.time_picker_popup.ids.selected_time_label.text = f'Selected: {time_str}'
        else:
            self.app.time_picker_popup.ids.selected_time_label.text = 'Selected: 12:00 pm'
    
    def confirm_time_selection(self):
        """Confirm time selection and update event popup."""
        if self.app.selected_hour is not None and self.app.selected_minute is not None and self.app.selected_ampm is not None:
            # Convert 12-hour format to 24-hour format for storage
            hour_24 = self.app.selected_hour
            if self.app.selected_ampm == 'PM' and self.app.selected_hour != 12:
                hour_24 = self.app.selected_hour + 12
            elif self.app.selected_ampm == 'AM' and self.app.selected_hour == 12:
                hour_24 = 0
            
            # Store in 24-hour format for database
            time_str = f"{hour_24:02d}:{self.app.selected_minute:02d}"
            self.app.selected_event_time = time_str
            
            # Format time in 12-hour format for display (hours are 1-12) with lowercase am/pm
            if self.app.selected_ampm == 'AM':
                if self.app.selected_hour == 12:
                    display_time = f"12:{self.app.selected_minute:02d} am"
                else:
                    display_time = f"{self.app.selected_hour}:{self.app.selected_minute:02d} am"
            else:  # PM
                if self.app.selected_hour == 12:
                    display_time = f"12:{self.app.selected_minute:02d} pm"
                else:
                    display_time = f"{self.app.selected_hour}:{self.app.selected_minute:02d} pm"
            # Update button text (works for both create and edit popups)
            if hasattr(self.app.current_event_popup, 'ids'):
                if 'event_time_button' in self.app.current_event_popup.ids:
                    self.app.current_event_popup.ids.event_time_button.text = display_time
                elif 'edit_event_time_button' in self.app.current_event_popup.ids:
                    self.app.current_event_popup.ids.edit_event_time_button.text = display_time
            self.app.time_picker_popup.dismiss()
        else:
            # If no time selected, just close
            self.app.time_picker_popup.dismiss()
    
    def on_recurring_toggle_changed(self, popup, is_active):
        """Handle recurring event toggle change."""
        self.app.is_recurring = is_active
        # Show/hide repeat days container
        if hasattr(popup.ids, 'repeat_days_container'):
            container = popup.ids.repeat_days_container
            if is_active:
                container.height = dp(60)
                container.opacity = 1
            else:
                container.height = 0
                container.opacity = 0
                # Clear selected days
                self.app.selected_repeat_days = []
        elif hasattr(popup.ids, 'edit_repeat_days_container'):
            container = popup.ids.edit_repeat_days_container
            if is_active:
                container.height = dp(60)
                container.opacity = 1
            else:
                container.height = 0
                container.opacity = 0
                # Clear selected days
                self.app.selected_repeat_days = []
    
    def on_repeat_day_changed(self, day_num, state):
        """Handle repeat day toggle change."""
        day_num_int = int(day_num)
        if state == 'down':
            if day_num_int not in self.app.selected_repeat_days:
                self.app.selected_repeat_days.append(day_num_int)
        else:
            if day_num_int in self.app.selected_repeat_days:
                self.app.selected_repeat_days.remove(day_num_int)
    
    def create_event_from_popup(self, popup):
        """Create a new event from the popup."""
        title = popup.ids.event_title_input.text.strip()
        
        # Validate inputs and show error popups
        if not title:
            self.show_error_popup("Please enter an event title")
            return
        
        # Get date and time from selected values
        if not hasattr(self.app, 'selected_event_date') or not self.app.selected_event_date:
            self.show_error_popup("Please select a date")
            return
        if not hasattr(self.app, 'selected_event_time') or not self.app.selected_event_time:
            self.show_error_popup("Please select a time")
            return
        
        # Validate recurring event
        is_recurring = hasattr(self.app, 'is_recurring') and self.app.is_recurring
        if is_recurring:
            if not hasattr(self.app, 'selected_repeat_days') or not self.app.selected_repeat_days:
                self.show_error_popup("Please select at least one day for repeating events")
                return
        
        try:
            # Combine date and time
            datetime_str = f"{self.app.selected_event_date} {self.app.selected_event_time}:00"
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            iso_datetime = dt.isoformat()
            
            # Check for conflicts with existing events at the same date and time
            event_date = dt.date()
            existing_events = self.app.db.get_schedule_by_date_range(event_date, event_date)
            
            # Check if any existing event has the same time
            for event in existing_events:
                if event[2]:  # start_time
                    try:
                        existing_dt = datetime.fromisoformat(event[2])
                        # Compare date and time (hour and minute)
                        if existing_dt.date() == event_date and existing_dt.hour == dt.hour and existing_dt.minute == dt.minute:
                            self.show_error_popup("An event already exists at this date and time. Please choose a different time.")
                            return
                    except:
                        pass
            
            # Prepare repeat_days string
            repeat_days_str = None
            if is_recurring and self.app.selected_repeat_days:
                repeat_days_str = ','.join(map(str, sorted(self.app.selected_repeat_days)))
            
            # Create task
            task = Task(
                title=title,
                start_time=iso_datetime,
                completed=False,
                source="local",
                is_recurring=is_recurring,
                repeat_days=repeat_days_str
            )
            self.app.db.add_schedule_item(task)
            
            # Refresh calendar to show dots on new event dates
            self.app.calendar_manager.load_calendar_month(self.app.selected_year, self.app.selected_month)
            popup.dismiss()
            
            # Update home screen schedule
            self.app.update_schedule_display()
        except Exception as e:
            self.show_error_popup(f"Error creating event: {str(e)}")
    
    def show_error_popup(self, message):
        """Show an error popup with the given message."""
        error_popup = Factory.ErrorPopup()
        error_popup.message = message
        error_popup.open()
    
    def open_date_picker_for_edit_event(self, event_popup):
        """Open date picker popup for event editing."""
        self.app.current_event_popup = event_popup
        date_picker = Factory.DatePickerPopup()
        self.app.date_picker_popup = date_picker
        self.render_date_picker_calendar()
        date_picker.open()
    
    def open_time_picker_for_edit_event(self, event_popup):
        """Open time picker popup for event editing."""
        self.app.current_event_popup = event_popup
        # Reset time selection to default 12:00 PM when opening time picker (only if not already set)
        if not hasattr(self.app, 'selected_hour') or self.app.selected_hour is None:
            self.app.selected_hour = 12
            self.app.selected_minute = 0
            self.app.selected_ampm = 'PM'
        time_picker = Factory.EventTimePickerPopup()
        self.app.time_picker_popup = time_picker
        self.render_time_picker()
        time_picker.open()
    
    def update_event_from_popup(self, popup):
        """Update an event from the edit popup."""
        event_id = popup.event_id
        title = popup.ids.edit_event_title_input.text.strip()
        
        if not title:
            self.show_error_popup("Please enter an event title.")
            return
        
        if not hasattr(self.app, 'selected_event_date') or not self.app.selected_event_date:
            self.show_error_popup("Please select a date.")
            return
        
        if not hasattr(self.app, 'selected_event_time') or not self.app.selected_event_time:
            self.show_error_popup("Please select a time.")
            return
        
        # Validate recurring event
        is_recurring = hasattr(self.app, 'is_recurring') and self.app.is_recurring
        if is_recurring:
            if not hasattr(self.app, 'selected_repeat_days') or not self.app.selected_repeat_days:
                self.show_error_popup("Please select at least one day for repeating events")
                return
        
        try:
            # Combine date and time
            datetime_str = f"{self.app.selected_event_date} {self.app.selected_event_time}:00"
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            iso_datetime = dt.isoformat()
            
            # Check for conflicts with existing events at the same date and time (excluding current event)
            event_date = dt.date()
            existing_events = self.app.db.get_schedule_by_date_range(event_date, event_date)
            
            # Check if any existing event (other than the one being edited) has the same time
            for event in existing_events:
                # Skip the event being edited
                if event[0] == event_id:  # event[0] is the id
                    continue
                    
                if event[2]:  # start_time
                    try:
                        existing_dt = datetime.fromisoformat(event[2])
                        # Compare date and time (hour and minute)
                        if existing_dt.date() == event_date and existing_dt.hour == dt.hour and existing_dt.minute == dt.minute:
                            self.show_error_popup("An event already exists at this date and time. Please choose a different time.")
                            return
                    except:
                        pass
            
            # Prepare repeat_days string
            repeat_days_str = None
            if is_recurring and self.app.selected_repeat_days:
                repeat_days_str = ','.join(map(str, sorted(self.app.selected_repeat_days)))
            
            # Update task
            self.app.db.update_task(
                event_id,
                title=title,
                start_time=iso_datetime,
                is_recurring=is_recurring,
                repeat_days=repeat_days_str
            )
            
            # Refresh calendar
            self.app.calendar_manager.load_calendar_month(self.app.selected_year, self.app.selected_month)
            # Refresh day events popup if it's open
            self.app.calendar_manager.refresh_day_events_popup()
            popup.dismiss()
            
            # Update home screen schedule
            self.app.update_schedule_display()
        except Exception as e:
            self.show_error_popup(f"Error updating event: {str(e)}")
            print(f"Error updating event: {e}")
    
    def delete_event(self, event_id):
        """Delete an event with confirmation."""
        # For now, delete directly. Can add confirmation popup later
        success = self.app.db.delete_task(event_id)
        if success:
            # Refresh calendar
            self.app.calendar_manager.load_calendar_month(self.app.selected_year, self.app.selected_month)
            # Update home screen schedule
            self.app.update_schedule_display()
    
    def open_event_actions_popup(self, event_id, event_title):
        """Open the event actions popup (edit/delete)."""
        popup = Factory.EventActionsPopup()
        popup.event_id = event_id
        popup.event_title = event_title
        popup.open()
    
    def edit_event_from_day_popup(self, event_id):
        """Edit an event from the day events popup."""
        event_data = self.app.db.get_schedule_item_by_id(event_id)
        if not event_data:
            return
        
        popup = Factory.EventEditPopup()
        popup.event_id = event_id
        self.app.current_event_popup = popup  # Store reference for date/time pickers
        
        # Pre-fill form
        popup.ids.edit_event_title_input.text = event_data['title']
        if event_data['start_time']:
            try:
                dt = datetime.fromisoformat(event_data['start_time'])
                # Set date button text
                popup.ids.edit_event_date_button.text = dt.strftime("%Y-%m-%d")
                self.app.selected_event_date = dt.date().isoformat()
                # Set time button text in 12-hour format
                time_12h = dt.strftime("%I:%M %p").lstrip("0")
                if time_12h.startswith(" "):
                    time_12h = time_12h[1:]
                popup.ids.edit_event_time_button.text = time_12h
                # Store time in 24-hour format
                self.app.selected_event_time = dt.strftime("%H:%M")
                # Set default time picker values
                hour_12 = dt.hour % 12
                if hour_12 == 0:
                    hour_12 = 12
                self.app.selected_hour = hour_12
                self.app.selected_minute = dt.minute
                self.app.selected_ampm = 'AM' if dt.hour < 12 else 'PM'
            except:
                popup.ids.edit_event_date_button.text = 'Select Date'
                popup.ids.edit_event_time_button.text = 'Select Time'
                self.app.selected_event_date = None
                self.app.selected_event_time = None
        else:
            popup.ids.edit_event_date_button.text = 'Select Date'
            popup.ids.edit_event_time_button.text = 'Select Time'
            self.app.selected_event_date = None
            self.app.selected_event_time = None
        
        # Load recurring event settings
        self.app.is_recurring = event_data.get('is_recurring', False)
        popup.ids.edit_event_recurring_checkbox.active = self.app.is_recurring
        
        # Load repeat days
        self.app.selected_repeat_days = []
        repeat_days_str = event_data.get('repeat_days')
        if repeat_days_str:
            self.app.selected_repeat_days = [int(d) for d in repeat_days_str.split(',') if d.strip()]
            # Set toggle buttons
            day_buttons = {
                '0': 'edit_day_mon',
                '1': 'edit_day_tue',
                '2': 'edit_day_wed',
                '3': 'edit_day_thu',
                '4': 'edit_day_fri',
                '5': 'edit_day_sat',
                '6': 'edit_day_sun'
            }
            for day_num in self.app.selected_repeat_days:
                day_key = str(day_num)
                if day_key in day_buttons and day_buttons[day_key] in popup.ids:
                    popup.ids[day_buttons[day_key]].state = 'down'
        
        # Show/hide repeat days container
        if self.app.is_recurring:
            popup.ids.edit_repeat_days_container.height = dp(60)
            popup.ids.edit_repeat_days_container.opacity = 1
        else:
            popup.ids.edit_repeat_days_container.height = 0
            popup.ids.edit_repeat_days_container.opacity = 0
        
        # Initialize date picker to event date or current month
        if self.app.selected_event_date:
            try:
                event_date = datetime.fromisoformat(self.app.selected_event_date).date()
                self.app.date_picker_year = event_date.year
                self.app.date_picker_month = event_date.month
            except:
                self.app.date_picker_year = self.app.selected_year
                self.app.date_picker_month = self.app.selected_month
        else:
            self.app.date_picker_year = self.app.selected_year
            self.app.date_picker_month = self.app.selected_month
        
        popup.open()
    
    def delete_event_from_day_popup(self, event_id):
        """Delete an event from the day events popup."""
        success = self.app.db.delete_task(event_id)
        if success:
            # Refresh calendar
            self.app.calendar_manager.load_calendar_month(self.app.selected_year, self.app.selected_month)
            # Refresh day events popup if it's open
            self.app.calendar_manager.refresh_day_events_popup()
            # Update home screen schedule
            self.app.update_schedule_display()


