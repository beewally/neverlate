import datetime
import os
from typing import Any

# Google imports
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from calendar_alert.directories import app_data_dir

# from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class GoogleCalDownloader:
    def __init__(self):
        self.creds = self.get_credentials()
        self.service = build("calendar", "v3", credentials=self.creds)  # type: Resource

    def get_credentials(self) -> Credentials:
        """Gets google authentication credentails."""
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        cred_file_path = os.path.join(os.path.dirname(__file__), "credentials.json")
        token_file_path = os.path.join(app_data_dir(), "token.json")
        if os.path.exists(token_file_path):
            creds = Credentials.from_authorized_user_file(token_file_path, SCOPES)
        # If there are no (valid) credentials available, let the user log in.

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    print("Token is bad!?")
                    import sys

                    for k, v in os.environ.items():
                        print(k, "->", v)

                    sys.exit(0)
                    # TODO: alert and terminate
            else:
                print("HERE WE GO")
                print(os.path.abspath(os.path.curdir))
                print("====")
                flow = InstalledAppFlow.from_client_secrets_file(cred_file_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_file_path, "w") as token_file:
                token_file.write(creds.to_json())
        print("CREDS", creds, "\nClass:", type(creds))
        return creds

    def get_events(self) -> list[dict[str, Any]]:
        """Get amazing events.

        Returns:
            list events
        """
        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        print("Getting the upcoming 10 events")
        events_query = self.service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        events_result = events_query.execute()

        print("EVENTS RESULT:")
        # pp(events_result)

        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return []

        # Prints the start and name of the next 10 events
        now = datetime.datetime.now()
        for event in events:
            # print("=" * 80)
            # pp(event)

            start = event["start"].get("dateTime", event["start"].get("date"))

            startdt = datetime.datetime.strptime(start[:19], "%Y-%m-%dT%H:%M:%S")

            seconds_till_event = (startdt - now).total_seconds()

            print(
                "Hours till start:",
                "{:.2f}".format(seconds_till_event / 60 / 60).rjust(60),
                "\t",
                start,
                event["summary"],
                "\t",
                event["status"],
            )  # event["start"].get("timeZone", "None")
        return events
