import sqlite3
from typing import Dict, Any


class NotificationManager:
    """Manages notification preferences and settings."""
    
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_table()
        self._ensure_preferences_row()
    
    def _ensure_table(self):
        """Create notification_preferences table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id INTEGER PRIMARY KEY,
                session_reminders BOOLEAN DEFAULT 1,
                break_reminders BOOLEAN DEFAULT 1,
                daily_goals BOOLEAN DEFAULT 1,
                streak_alerts BOOLEAN DEFAULT 1,
                task_deadlines BOOLEAN DEFAULT 1,
                weekly_summary BOOLEAN DEFAULT 0,
                achievements BOOLEAN DEFAULT 1,
                notification_sound BOOLEAN DEFAULT 1,
                quiet_hours_enabled BOOLEAN DEFAULT 0,
                quiet_hours_start TEXT DEFAULT '22:00',
                quiet_hours_end TEXT DEFAULT '08:00'
            )
        """)
        self.conn.commit()
    
    def _ensure_preferences_row(self):
        """Ensure a default preferences row exists."""
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM notification_preferences")
        count = cursor.fetchone()["count"]
        if count == 0:
            self.conn.execute("""
                INSERT INTO notification_preferences (id) VALUES (1)
            """)
            self.conn.commit()
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get all notification preferences."""
        cursor = self.conn.execute("SELECT * FROM notification_preferences WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            return {}
        return {
            "session_reminders": bool(row["session_reminders"]),
            "break_reminders": bool(row["break_reminders"]),
            "daily_goals": bool(row["daily_goals"]),
            "streak_alerts": bool(row["streak_alerts"]),
            "task_deadlines": bool(row["task_deadlines"]),
            "weekly_summary": bool(row["weekly_summary"]),
            "achievements": bool(row["achievements"]),
            "notification_sound": bool(row["notification_sound"]),
            "quiet_hours_enabled": bool(row["quiet_hours_enabled"]),
            "quiet_hours_start": row["quiet_hours_start"],
            "quiet_hours_end": row["quiet_hours_end"]
        }
    
    def update_preference(self, key: str, value: bool):
        """Update a single notification preference."""
        self.conn.execute(f"""
            UPDATE notification_preferences
            SET {key} = ?
            WHERE id = 1
        """, (1 if value else 0,))
        self.conn.commit()
    
    def update_quiet_hours(self, start_time: str, end_time: str):
        """Update quiet hours time range."""
        self.conn.execute("""
            UPDATE notification_preferences
            SET quiet_hours_start = ?, quiet_hours_end = ?
            WHERE id = 1
        """, (start_time, end_time))
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()


__all__ = ["NotificationManager"]

