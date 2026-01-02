# google_calendar_service.py
from __future__ import print_function
import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the token.json file.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_service():
    """Authenticate and return the Google Calendar API service"""
    creds = None
    # token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no valid credentials, log in and save them
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save credentials for next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service

def get_upcoming_events(max_results=10):
    """Retrieve upcoming Google Calendar events"""
    service = get_calendar_service()

    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' = UTC time
    print('Getting the upcoming {} events...'.format(max_results))

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
        return []

    results = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        results.append({
            'title': event['summary'],
            'start': start,
            'id': event['id']
        })
    return results

if __name__ == '__main__':
    # Test by printing upcoming events
    events = get_upcoming_events(5)
    for e in events:
        print(f"{e['start']} - {e['title']}")
