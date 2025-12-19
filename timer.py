from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.label import Label


class PomodoroTimer:
    """Simple countdown timer controller for the UI.

    Exposes start(), pause(), reset(minutes=None) and updates the
    label with id 'timer_label' on the app root every second.
    """

    def __init__(self, app, minutes: int = 25) -> None:
        self.app = app
        self.default_seconds = int(minutes) * 60
        self.remaining_seconds = self.default_seconds
        self._scheduled_event = None
        self.is_running = False
        self._notified = False
        self._session_start_seconds = None  # Track session start for focus time calculation
        self._session_start_time = None  # Track actual start time for elapsed calculation
        self._start_notification_sent = False  # Track if start notification was sent

    # ---- Internal helpers ----
    def _update_label(self) -> None:
        total = max(self.remaining_seconds, 0)
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        # Try to find the timer label in the home screen
        label = None
        try:
            root = getattr(self.app, 'root', None)
            if root:
                # Check if root is a ScreenManager and get the home screen
                if hasattr(root, 'get_screen'):
                    home_screen = root.get_screen('home')
                    # The home screen contains MyHome widget, which has the timer_label
                    # Try to find MyHome widget in the screen's children
                    for child in home_screen.children:
                        if hasattr(child, 'ids'):
                            label = getattr(child.ids, 'timer_label', None)
                            if label:
                                break
                # Fallback: try direct access (for backwards compatibility)
                if not label and hasattr(root, 'ids'):
                    label = getattr(root.ids, 'timer_label', None)
        except Exception:
            pass
        if label:
            label.text = f"{int(hours):02d}.{int(minutes):02d}.{int(seconds):02d}"

    def _tick(self, _dt: float) -> None:
        if not self.is_running:
            return
        # Count down if there's time remaining, otherwise count up from 0
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
        # If timer started at 0, it counts up (but we track elapsed time via _session_start_time)
        # Note: remaining_seconds stays at 0 for count-up, elapsed time is tracked separately
        self._update_label()
        # Only auto-pause and notify if we were counting down and reached 0
        if self._session_start_seconds and self._session_start_seconds > 0 and self.remaining_seconds <= 0:
            self.pause()  # stop at 00:00
            if not self._notified:
                self._notified = True
                self._show_done_popup()

    def _show_done_popup(self) -> None:
        """Show timer finished popup and automatically save stats."""
        try:
            # Send completion notification
            if hasattr(self.app, 'notification_service'):
                duration_minutes = self.get_elapsed_focus_minutes()
                self.app.notification_service.notify_session_complete(duration_minutes)
            
            # Automatically complete the session when timer reaches 0
            # This saves the stats without requiring user to click "Complete"
            if hasattr(self.app, 'complete_session'):
                self.app.complete_session()
            else:
                # Fallback: show simple popup if complete_session not available
                Popup(
                    title='Timer Finished',
                    content=Label(text='Timer ends', halign='center', valign='middle', text_size=(300, None)),
                    size_hint=(0.7, 0.3),
                    auto_dismiss=True,
                ).open()
        except Exception as e:
            # Silently ignore UI errors if popup cannot be created (e.g., during shutdown)
            print(f"Error in _show_done_popup: {e}")

    # ---- Public API ----
    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._notified = False
        # Record session start for focus time tracking
        # Store the initial remaining seconds when starting (for countdown tracking)
        if self._session_start_seconds is None:
            self._session_start_seconds = self.remaining_seconds
        # Always track the actual system time when starting (works for both countdown and count-up)
        # This is the primary method for tracking elapsed time
        if self._session_start_time is None:
            from time import time
            self._session_start_time = time()
            
            # Send start notification (only once per session)
            if not self._start_notification_sent and hasattr(self.app, 'notification_service'):
                duration_minutes = max(1, self.remaining_seconds // 60)
                self.app.notification_service.notify_session_start(duration_minutes)
                self._start_notification_sent = True
        
        if not self._scheduled_event:
            self._scheduled_event = Clock.schedule_interval(self._tick, 1)

    def pause(self) -> None:
        self.is_running = False
        # Don't reset session tracking on pause, so elapsed time is preserved

    def reset(self, minutes: int | None = None) -> None:
        """Stop the timer and set display to default.

        If minutes is provided, also change the default before resetting.
        Current behavior: default is 0 (00.00.00).
        """
        self.pause()
        if minutes is not None:
            self.default_seconds = int(minutes) * 60
        else:
            # ensure default is 0 when no value provided
            self.default_seconds = 0
        self.remaining_seconds = self.default_seconds
        self._notified = False
        self._session_start_seconds = None  # Reset session tracking
        self._session_start_time = None  # Reset session start time
        self._start_notification_sent = False  # Reset notification flag
        self._update_label()
    
    def get_elapsed_focus_minutes(self) -> int:
        """Calculate actual focus time in minutes for current session.
        
        Returns:
            Minutes of focus time (rounded down)
        """
        # Primary method: Use actual time tracking (most accurate, works for both countdown and count-up)
        if self._session_start_time is not None:
            from time import time
            elapsed_seconds = time() - self._session_start_time
            # Return elapsed time if timer was started (regardless of current running state)
            return max(0, int(elapsed_seconds // 60))
        
        # Fallback: Calculate from remaining seconds difference (for countdown timers only)
        # This works when timer was counting down from a set time
        if self._session_start_seconds is not None and self._session_start_seconds > 0:
            elapsed_seconds = self._session_start_seconds - self.remaining_seconds
            return max(0, int(elapsed_seconds // 60))
        
        return 0

    # Public: parse '25' or '25:00' then reset
    def set_minutes(self, value: str) -> None:
        if not value:
            return
        value = value.strip()
        try:
            if ':' in value:
                parts = value.split(':')
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                else:
                    # support hh:mm:ss too
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = int(parts[2]) if len(parts) > 2 else 0
                    minutes = hours * 60 + minutes
                total_seconds = max(0, minutes * 60 + seconds)
            else:
                minutes = int(float(value))
                total_seconds = max(0, minutes * 60)
        except ValueError:
            return

        self.pause()
        self.default_seconds = total_seconds
        self.remaining_seconds = total_seconds
        self._notified = False
        self._session_start_seconds = None  # Reset session tracking
        self._session_start_time = None  # Reset session start time
        self._start_notification_sent = False  # Reset notification flag
        self._update_label()

    def set_hm(self, hours: int, minutes: int) -> None:
        try:
            hours_i = int(hours)
            minutes_i = int(minutes)
        except (TypeError, ValueError):
            return
        total_seconds = max(0, hours_i * 3600 + minutes_i * 60)
        self.pause()
        self.default_seconds = total_seconds
        self.remaining_seconds = total_seconds
        self._notified = False
        self._session_start_seconds = None  # Reset session tracking
        self._session_start_time = None  # Reset session start time
        self._start_notification_sent = False  # Reset notification flag
        self._update_label()


