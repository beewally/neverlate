from __future__ import print_function

import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main():
    """
    This is the summary.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    token_file_path = os.path.abspath("token.json")

    if os.path.exists(token_file_path):
        creds = Credentials.from_authorized_user_file(token_file_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("HERE WE GO")
            print(os.path.abspath(os.path.curdir))
            print("====")
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_file_path, "w") as token_file:
            token_file.write(creds.to_json())
    print(token_file_path)
    try:
        service = build("calendar", "v3", credentials=creds)  # type: Resource

        # Call the Calendar API
        now = (
            datetime.datetime.utcnow().isoformat() + "Z"
        )  # 'Z' indicates UTC time
        print("NOW:", now)
        print("Getting the upcoming 10 events")
        se = service.events()
        events_query = se.list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        events_result = events_query.execute()
        from pprint import pprint as pp

        print("EVENTS RESULT:")
        # pp(events_result)

        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        for event in events[1:]:
            print("=" * 80)
            pp(event)
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(start, event["summary"])

    except HttpError as error:
        print("An error occurred: %s" % error)


if __name__ == "__main__":
    main()