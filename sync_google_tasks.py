from google_calendar_service import get_upcoming_events
from database_manager import DatabaseManager
from task import Task

def sync_google_events_to_db():
    db = DatabaseManager()
    db.clear_google_tasks()  # Clear old events first
    events = get_upcoming_events(10)

    for e in events:
        task = Task(
            title=e['title'],
            start_time=e['start'],
            completed=False,
            source="google",
            event_id=e['id']
        )
        db.add_task(task)
    print("✅ Google Calendar events synced to local database.")


if __name__ == "__main__":
    sync_google_events_to_db()

    db = DatabaseManager()
    tasks = db.get_all_tasks()
    for t in tasks:
        print(t)
