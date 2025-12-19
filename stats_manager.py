import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path


class FocusStatsManager:
    """Manages focus statistics tracking using SQLite database.
    
    Tracks:
    - Completed pomodoros per session
    - Focus time in minutes
    - Historical data with relationships to tasks
    """
    
    def __init__(self, db_name: str = "tasks.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure focus_sessions table exists."""
        cursor = self.conn.cursor()
        
        # Create focus_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                pomodoros INTEGER DEFAULT 1,
                focus_minutes INTEGER NOT NULL,
                task_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # Create index for faster date queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_focus_date 
            ON focus_sessions(date)
        """)
        
        self.conn.commit()
    
    def add_completed_session(self, focus_minutes: int, task_id: int = None) -> None:
        """Record a completed pomodoro session.
        
        Args:
            focus_minutes: Actual minutes spent focusing
            task_id: Optional ID of associated task
        """
        today = str(date.today())
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO focus_sessions (date, pomodoros, focus_minutes, task_id)
            VALUES (?, 1, ?, ?)
        """, (today, focus_minutes, task_id))
        
        self.conn.commit()
    
    def get_daily_stats(self, target_date: date = None) -> dict:
        """Get statistics for a specific date (default: today).
        
        Args:
            target_date: Date to query (default: today)
            
        Returns:
            dict with 'pomodoros' and 'focus_minutes'
        """
        if target_date is None:
            target_date = date.today()
        
        date_str = str(target_date)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as pomodoros,
                COALESCE(SUM(focus_minutes), 0) as focus_minutes
            FROM focus_sessions
            WHERE date = ?
        """, (date_str,))
        
        row = cursor.fetchone()
        return {
            "pomodoros": row["pomodoros"],
            "focus_minutes": row["focus_minutes"]
        }
    
    def get_all_time_stats(self) -> dict:
        """Get all-time cumulative statistics.
        
        Returns:
            dict with 'pomodoros' and 'focus_minutes'
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as pomodoros,
                COALESCE(SUM(focus_minutes), 0) as focus_minutes
            FROM focus_sessions
        """)
        
        row = cursor.fetchone()
        return {
            "pomodoros": row["pomodoros"],
            "focus_minutes": row["focus_minutes"]
        }
    
    def get_history_range(self, days: int) -> dict:
        """Get stats for the last N days (including today).
        
        Args:
            days: Number of days to retrieve (e.g., 7 for weekly, 30 for monthly)
            
        Returns:
            Dictionary with dates as keys and stats as values, sorted by date
        """
        today = date.today()
        start_date = today - timedelta(days=days - 1)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                date,
                COUNT(*) as pomodoros,
                COALESCE(SUM(focus_minutes), 0) as focus_minutes
            FROM focus_sessions
            WHERE date >= ? AND date <= ?
            GROUP BY date
            ORDER BY date
        """, (str(start_date), str(today)))
        
        # Build result dictionary with all dates (fill missing dates with 0)
        result = {}
        for i in range(days):
            target_date = start_date + timedelta(days=i)
            date_str = str(target_date)
            result[date_str] = {
                "pomodoros": 0,
                "focus_minutes": 0
            }
        
        # Fill in actual data
        for row in cursor.fetchall():
            date_str = row["date"]
            result[date_str] = {
                "pomodoros": row["pomodoros"],
                "focus_minutes": row["focus_minutes"]
            }
        
        return result
    
    def get_stats_by_date_range(self, start_date: date, end_date: date) -> list:
        """Get detailed session data for a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of session dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                id, date, pomodoros, focus_minutes, task_id, created_at
            FROM focus_sessions
            WHERE date >= ? AND date <= ?
            ORDER BY date, created_at
        """, (str(start_date), str(end_date)))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "id": row["id"],
                "date": row["date"],
                "pomodoros": row["pomodoros"],
                "focus_minutes": row["focus_minutes"],
                "task_id": row["task_id"],
                "created_at": row["created_at"]
            })
        
        return sessions
    
    def get_hourly_stats(self, days: int = 30) -> dict:
        """Get focus time aggregated by hour of day (0-23).
        
        Args:
            days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary with hour (0-23) as key and total minutes as value
        """
        cursor = self.conn.cursor()
        start_date = date.today() - timedelta(days=days)
        
        cursor.execute("""
            SELECT 
                CAST(strftime('%H', created_at) AS INTEGER) as hour,
                SUM(focus_minutes) as total_minutes
            FROM focus_sessions
            WHERE date >= ? AND created_at IS NOT NULL
            GROUP BY hour
            ORDER BY hour
        """, (str(start_date),))
        
        # Initialize all hours to 0
        hourly_data = {i: 0 for i in range(24)}
        
        # Fill in actual data
        for row in cursor.fetchall():
            hour = row["hour"]
            if 0 <= hour <= 23:
                hourly_data[hour] = row["total_minutes"]
        
        return hourly_data
    
    def get_day_of_week_stats(self, weeks: int = 4) -> dict:
        """Get focus time by day of week (0=Monday, 6=Sunday).
        
        Args:
            weeks: Number of weeks to look back (default: 4)
            
        Returns:
            Dictionary with day (0-6) as key and total minutes as value
        """
        cursor = self.conn.cursor()
        start_date = date.today() - timedelta(days=weeks * 7)
        
        cursor.execute("""
            SELECT 
                CAST(strftime('%w', date) AS INTEGER) as day_of_week,
                SUM(focus_minutes) as total_minutes
            FROM focus_sessions
            WHERE date >= ?
            GROUP BY day_of_week
            ORDER BY day_of_week
        """, (str(start_date),))
        
        # Initialize all days to 0 (0=Monday, 6=Sunday)
        day_data = {i: 0 for i in range(7)}
        
        # SQLite: 0=Sunday, 1=Monday, ..., 6=Saturday
        # Convert to Python: 0=Monday, 1=Tuesday, ..., 6=Sunday
        for row in cursor.fetchall():
            sqlite_day = row["day_of_week"]
            total_minutes = row["total_minutes"]
            # Convert: 0=Sun->6, 1=Mon->0, 2=Tue->1, ..., 6=Sat->5
            python_day = (sqlite_day + 6) % 7
            day_data[python_day] = total_minutes
        
        return day_data
    
    def get_session_duration_stats(self) -> dict:
        """Get average, min, max session durations.
        
        Returns:
            Dictionary with 'avg', 'min', 'max', 'total' keys
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                AVG(focus_minutes) as avg_duration,
                MIN(focus_minutes) as min_duration,
                MAX(focus_minutes) as max_duration,
                COUNT(*) as total_sessions
            FROM focus_sessions
        """)
        
        row = cursor.fetchone()
        avg = row["avg_duration"]
        
        return {
            'avg': int(avg) if avg else 0,
            'min': row["min_duration"] or 0,
            'max': row["max_duration"] or 0,
            'total': row["total_sessions"] or 0
        }
    
    def get_focus_streak(self) -> dict:
        """Get current and best focus streak (consecutive days with sessions).
        
        Returns:
            Dictionary with 'current', 'best', 'last_date' keys
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT date
            FROM focus_sessions
            ORDER BY date DESC
        """)
        
        dates = []
        for row in cursor.fetchall():
            try:
                dates.append(datetime.strptime(row["date"], "%Y-%m-%d").date())
            except:
                continue
        
        if not dates:
            return {'current': 0, 'best': 0, 'last_date': None}
        
        # Calculate current streak
        today = date.today()
        current_streak = 0
        check_date = today
        
        for d in dates:
            if d == check_date:
                current_streak += 1
                check_date = d - timedelta(days=1)
            elif d < check_date:
                break
        
        # Calculate best streak
        best_streak = 1 if dates else 0
        current_run = 1
        for i in range(1, len(dates)):
            if (dates[i-1] - dates[i]).days == 1:
                current_run += 1
                best_streak = max(best_streak, current_run)
            else:
                current_run = 1
        
        return {
            'current': current_streak,
            'best': best_streak,
            'last_date': dates[0] if dates else None
        }
    
    def reset_all_time_stats(self) -> None:
        """Reset all statistics (use with caution)."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM focus_sessions")
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
