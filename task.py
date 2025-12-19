class Task:
    def __init__(self, title, start_time=None, completed=False, source="local", event_id=None, is_recurring=False, repeat_days=None, priority='medium'):
        self.title = title
        self.start_time = start_time  # datetime string
        self.completed = completed
        self.source = source          # "local" or "google"
        self.event_id = event_id      # Google event ID if from calendar
        self.is_recurring = is_recurring  # Boolean: True if event repeats weekly
        self.repeat_days = repeat_days    # Comma-separated string of weekday numbers (0=Monday, 6=Sunday)
        self.priority = priority       # 'high', 'medium', 'low'

    def __repr__(self):
        return f"<Task(title={self.title}, time={self.start_time}, completed={self.completed}, source={self.source}, is_recurring={self.is_recurring}, repeat_days={self.repeat_days}, priority={self.priority})>"
