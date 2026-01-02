import sqlite3
from task import Task

class DatabaseManager:
    def __init__(self, db_name="tasks.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_time TEXT,
            completed INTEGER DEFAULT 0,
            source TEXT DEFAULT 'local',
            event_id TEXT,
            is_recurring INTEGER DEFAULT 0,
            repeat_days TEXT
        )
        """
        self.conn.execute(query)
        
        # Add new columns if they don't exist (for existing databases)
        try:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN is_recurring INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN repeat_days TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'medium'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create focus_sessions table for pomodoro tracking
        focus_query = """
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            pomodoros INTEGER DEFAULT 1,
            focus_minutes INTEGER NOT NULL,
            task_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
        """
        self.conn.execute(focus_query)
        
        # Create index for faster date queries
        index_query = """
        CREATE INDEX IF NOT EXISTS idx_focus_date 
        ON focus_sessions(date)
        """
        self.conn.execute(index_query)
        
        self.conn.commit()

    def add_task(self, task: Task):
        query = "INSERT INTO tasks (title, start_time, completed, source, event_id, is_recurring, repeat_days, priority) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        self.conn.execute(query, (task.title, task.start_time, int(task.completed), task.source, task.event_id, int(task.is_recurring), task.repeat_days, task.priority))
        self.conn.commit()

    def get_all_tasks(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY start_time ASC")
        rows = cursor.fetchall()
        tasks = []
        for row in rows:
            is_recurring = bool(row[6]) if len(row) > 6 else False
            repeat_days = row[7] if len(row) > 7 else None
            t = Task(row[1], row[2], bool(row[3]), row[4], row[5], is_recurring, repeat_days)
            tasks.append(t)
        return tasks

    def clear_google_tasks(self):
        """Remove old Google Calendar events before syncing new ones."""
        self.conn.execute("DELETE FROM tasks WHERE source='google'")
        self.conn.commit()
    
    def get_today_schedule(self, limit=3):
        """Get today's scheduled appointments/meetings (items with date and time), including recurring events."""
        from datetime import date, datetime
        
        today = date.today()
        today_str = str(today)
        weekday = today.weekday()  # 0=Monday, 6=Sunday
        
        cursor = self.conn.cursor()
        
        # Get non-recurring events for today
        cursor.execute("""
            SELECT title, start_time
            FROM tasks
            WHERE start_time IS NOT NULL
            AND DATE(start_time) = ?
            AND completed = 0
            AND (is_recurring = 0 OR is_recurring IS NULL)
            ORDER BY start_time ASC
        """, (today_str,))
        
        events = list(cursor.fetchall())
        
        # Get recurring events that repeat on today's weekday
        cursor.execute("""
            SELECT title, start_time, repeat_days
            FROM tasks
            WHERE start_time IS NOT NULL
            AND is_recurring = 1
            AND repeat_days IS NOT NULL
            AND completed = 0
        """)
        
        recurring_events = cursor.fetchall()
        
        # Add recurring events that match today's weekday
        for event in recurring_events:
            repeat_days_str = event[2] if len(event) > 2 else ""
            if repeat_days_str and str(weekday) in repeat_days_str.split(','):
                try:
                    original_dt = datetime.fromisoformat(event[1])
                    event_time = original_dt.time()
                    event_datetime = datetime.combine(today, event_time)
                    # Add as a new event instance
                    events.append((event[0], event_datetime.isoformat()))
                except:
                    pass
        
        # Sort all events by start_time and limit
        events.sort(key=lambda x: x[1] if x[1] else "")
        return events[:limit]
    
    def get_tasks_by_status(self, completed=False, limit=None):
        """Get ongoing tasks by completion status (excludes schedule items with time)."""
        cursor = self.conn.cursor()
        query = """
            SELECT id, title, start_time, source, completed, event_id, is_recurring, repeat_days, priority
            FROM tasks
            WHERE completed = ?
            AND start_time IS NULL
            ORDER BY priority DESC, id DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (int(completed),))
        return cursor.fetchall()
    
    def toggle_task_completion(self, task_id):
        """Mark task as complete/incomplete."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE tasks
            SET completed = NOT completed
            WHERE id = ?
        """, (task_id,))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete_task(self, task_id):
        """Delete a task."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def update_task(self, task_id, title=None, start_time=None, is_recurring=None, repeat_days=None):
        """Update task details."""
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        
        if start_time is not None:
            updates.append("start_time = ?")
            params.append(start_time)
        
        if is_recurring is not None:
            updates.append("is_recurring = ?")
            params.append(int(is_recurring))
        
        if repeat_days is not None:
            updates.append("repeat_days = ?")
            params.append(repeat_days)
        
        if updates:
            params.append(task_id)
            query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
            self.conn.execute(query, params)
            self.conn.commit()
    
    def add_schedule_item(self, task: Task):
        """Add a schedule item (appointment/meeting) with date and time.
        Note: start_time must be provided for schedule items."""
        if not task.start_time:
            raise ValueError("Schedule items must have a start_time")
        self.add_task(task)
    
    def get_schedule_by_month(self, year, month):
        """Get all schedule items for a specific month, including recurring events."""
        from datetime import date, timedelta, datetime
        
        # Get first and last day of month
        if month == 12:
            first_day = date(year, month, 1)
            last_day = date(year + 1, 1, 1)
        else:
            first_day = date(year, month, 1)
            last_day = date(year, month + 1, 1)
        
        cursor = self.conn.cursor()
        
        # Get non-recurring events
        cursor.execute("""
            SELECT id, title, start_time, source, completed, event_id, is_recurring, repeat_days
            FROM tasks
            WHERE start_time IS NOT NULL
            AND DATE(start_time) >= ?
            AND DATE(start_time) < ?
            AND completed = 0
            AND (is_recurring = 0 OR is_recurring IS NULL)
            ORDER BY start_time ASC
        """, (str(first_day), str(last_day)))
        
        events = list(cursor.fetchall())
        
        # Get recurring events
        cursor.execute("""
            SELECT id, title, start_time, source, completed, event_id, is_recurring, repeat_days
            FROM tasks
            WHERE start_time IS NOT NULL
            AND is_recurring = 1
            AND repeat_days IS NOT NULL
            AND completed = 0
        """)
        
        recurring_events = cursor.fetchall()
        
        # Generate recurring event instances for the month
        current_date = first_day
        while current_date < last_day:
            weekday = current_date.weekday()  # 0=Monday, 6=Sunday
            for event in recurring_events:
                repeat_days_str = event[7] if len(event) > 7 else ""
                if repeat_days_str and str(weekday) in repeat_days_str.split(','):
                    # Create an event instance for this date
                    from datetime import datetime
                    try:
                        original_dt = datetime.fromisoformat(event[2])
                        event_date = current_date
                        event_time = original_dt.time()
                        event_datetime = datetime.combine(event_date, event_time)
                        # Add as a new event instance (with a special ID to indicate it's recurring)
                        events.append((
                            event[0],  # id
                            event[1],  # title
                            event_datetime.isoformat(),  # start_time (adjusted date)
                            event[3],  # source
                            event[4],  # completed
                            event[5],  # event_id
                            event[6],  # is_recurring
                            event[7]   # repeat_days
                        ))
                    except:
                        pass
            current_date += timedelta(days=1)
        
        # Sort all events by start_time
        events.sort(key=lambda x: x[2] if x[2] else "")
        return events
    
    def get_schedule_by_date_range(self, start_date, end_date):
        """Get events in a date range, including recurring events."""
        from datetime import timedelta, datetime
        
        cursor = self.conn.cursor()
        
        # Get non-recurring events
        cursor.execute("""
            SELECT id, title, start_time, source, completed, event_id, is_recurring, repeat_days
            FROM tasks
            WHERE start_time IS NOT NULL
            AND DATE(start_time) >= ?
            AND DATE(start_time) <= ?
            AND completed = 0
            AND (is_recurring = 0 OR is_recurring IS NULL)
            ORDER BY start_time ASC
        """, (str(start_date), str(end_date)))
        
        events = list(cursor.fetchall())
        
        # Get recurring events
        cursor.execute("""
            SELECT id, title, start_time, source, completed, event_id, is_recurring, repeat_days
            FROM tasks
            WHERE start_time IS NOT NULL
            AND is_recurring = 1
            AND repeat_days IS NOT NULL
            AND completed = 0
        """)
        
        recurring_events = cursor.fetchall()
        
        # Generate recurring event instances for the date range
        # Note: weekday() returns 0=Monday, 6=Sunday
        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.weekday()  # 0=Monday, 6=Sunday
            for event in recurring_events:
                repeat_days_str = event[7] if len(event) > 7 else ""
                if repeat_days_str and str(weekday) in repeat_days_str.split(','):
                    # Create an event instance for this date
                    try:
                        original_dt = datetime.fromisoformat(event[2])
                        event_date = current_date
                        event_time = original_dt.time()
                        event_datetime = datetime.combine(event_date, event_time)
                        # Add as a new event instance
                        events.append((
                            event[0],  # id
                            event[1],  # title
                            event_datetime.isoformat(),  # start_time (adjusted date)
                            event[3],  # source
                            event[4],  # completed
                            event[5],  # event_id
                            event[6],  # is_recurring
                            event[7]   # repeat_days
                        ))
                    except Exception as e:
                        pass
            current_date += timedelta(days=1)
        
        # Sort all events by start_time
        events.sort(key=lambda x: x[2] if x[2] else "")
        return events
    
    def get_schedule_item_by_id(self, task_id):
        """Get single schedule item by ID for editing."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, title, start_time, source, completed, event_id, is_recurring, repeat_days
            FROM tasks
            WHERE id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'title': row[1],
                'start_time': row[2],
                'source': row[3],
                'completed': bool(row[4]),
                'event_id': row[5],
                'is_recurring': bool(row[6]) if len(row) > 6 else False,
                'repeat_days': row[7] if len(row) > 7 else None
            }
        return None
    
    def get_today_schedule_full(self, limit=3):
        """Get today's schedule with full data (id, source, etc.), including recurring events."""
        from datetime import date, datetime
        
        today = date.today()
        today_str = str(today)
        weekday = today.weekday()  # 0=Monday, 6=Sunday
        
        cursor = self.conn.cursor()
        
        # Get non-recurring events for today
        cursor.execute("""
            SELECT id, title, start_time, source, completed, event_id, is_recurring, repeat_days
            FROM tasks
            WHERE start_time IS NOT NULL
            AND DATE(start_time) = ?
            AND completed = 0
            AND (is_recurring = 0 OR is_recurring IS NULL)
            ORDER BY start_time ASC
        """, (today_str,))
        
        events = list(cursor.fetchall())
        
        # Get recurring events that repeat on today's weekday
        cursor.execute("""
            SELECT id, title, start_time, source, completed, event_id, is_recurring, repeat_days
            FROM tasks
            WHERE start_time IS NOT NULL
            AND is_recurring = 1
            AND repeat_days IS NOT NULL
            AND completed = 0
        """)
        
        recurring_events = cursor.fetchall()
        
        # Add recurring events that match today's weekday
        for event in recurring_events:
            repeat_days_str = event[7] if len(event) > 7 else ""
            if repeat_days_str and str(weekday) in repeat_days_str.split(','):
                try:
                    original_dt = datetime.fromisoformat(event[2])
                    event_time = original_dt.time()
                    event_datetime = datetime.combine(today, event_time)
                    # Add as a new event instance
                    events.append((
                        event[0],  # id
                        event[1],  # title
                        event_datetime.isoformat(),  # start_time (adjusted date)
                        event[3],  # source
                        event[4],  # completed
                        event[5],  # event_id
                        event[6],  # is_recurring
                        event[7]   # repeat_days
                    ))
                except:
                    pass
        
        # Sort all events by start_time and limit
        events.sort(key=lambda x: x[2] if x[2] else "")
        return events[:limit]
