import datetime
import os
import sys
import time
from ctypes import Union
from pprint import pprint as pp
from typing import Any, List, Optional

# Google imports
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

# Other
from PySide6.QtCore import QObject, Signal, Slot

# Local imports
from calendar_alert.directories import app_data_dir

# LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
LOCAL_TIMEZONE = datetime.datetime.now().astimezone().tzinfo

# from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

EMAIL = None


class Calendar:
    """
    Google calendar data model
    """

    def __init__(self, data) -> None:
        self._data = data
        self.id = data["id"]
        self.primary = data.get("primary", False)
        self.summary = data.get("summaryOverride", data["summary"])
        self.selected = data.get(
            "selected", False
        )  # Is the user displaying this calendar by default

    def __repr__(self):
        if self.primary:
            return "<Calendar: PRIMARY>"
        return (
            "<Calendar: "
            + " ".join(
                [
                    self.summary,
                    f"ID: {self.id}",
                    f"Primary: {self.primary}",
                ]
            )
            + ">"
        )


class TimeEvent:
    """
    Calendar event data model for time-based events (not all day events).
    """

    def __init__(self, item: dict, calendar: Calendar):
        """
        Create the time event.

        Args:
            item (dict): Dictionary result from event query.
            calendar (Calendar): Calendar this event belongs to.

        Raises:
            ValueError: If item is not valid/not a valid event with a start date and time.
        """
        if (
            "start" not in item
            or "dateTime" not in item["start"]
            or item.get("eventType", "default")
            != "default"  # or ['default', 'focusTime', 'outOfOffice']:
        ):
            raise ValueError("Invalid data type - not a calendar event")
        self.calendar = calendar
        self._event = item  # type: dict
        self.summary = self._event["summary"]

        # Get start and end times as datetime objects
        st_time = self._event["start"]["dateTime"]
        self.start_time = datetime.datetime.fromisoformat(st_time)
        # self.start_time = datetime.datetime.strptime(st_time[:19], "%Y-%m-%dT%H:%M:%S")
        end_time = self._event["end"]["dateTime"]
        self.end_time = datetime.datetime.fromisoformat(end_time)
        self.id = self._event["id"]

    def __repr__(self):
        return (
            "<TimeEvent: "
            + "   ".join(
                [
                    (
                        self.summary
                        if len(self.summary) <= 50
                        else self.summary[:47] + "..."
                    ).ljust(50),
                    "Seconds till event:  "
                    + f"{self.get_seconds_till_event()/60:.2f}".ljust(7),
                    # f"Event Type: {self._event['eventType']}",
                    # "End Time:", self._event['endTime'],
                    # f"ID: {self.id}",
                    f"{self.calendar.summary}",
                    "DECLINED" if self.has_declined() else "        ",
                    # f"Declined: {self.has_declined()}",
                ]
            )
            + ">"
        )

    def get_seconds_till_event(self) -> float:
        now = datetime.datetime.now(LOCAL_TIMEZONE)
        return (self.start_time - now).total_seconds()

    def get_video_url(self) -> str:
        entry_points = self._event.get("conferenceData", {}).get("entryPoints", [])
        for entry_point in entry_points:
            if entry_point["entryPointType"] == "video":
                return entry_point["uri"]

        return ""

    def has_declined(self) -> bool:
        for attendee in self._event.get("attendees", []):
            # if attendee["email"] == "bwalters@wayfair.com":
            return attendee["responseStatus"] == "declined"
        return False

    def has_ended(self) -> bool:
        now = datetime.datetime.now(LOCAL_TIMEZONE)
        return (self.end_time - now).total_seconds() < 0


class GoogleCalDownloader:  # (QObject):
    primary_calendar: Calendar  # TODO: not used?
    calendars: list[Calendar] = []
    events: list[TimeEvent] = []
    last_update_time: float = 0.0

    # events_gathered_signal = Signal(list[Calendar])

    def __init__(self):
        super().__init__()
        self.creds = self.get_credentials()
        self.service = build("calendar", "v3", credentials=self.creds)  # type: Resource
        # self.primary_calendar: Calendar
        # print("CAL:", self.primary_calendar)

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
        else:
            print("NO CREDENTIALS", token_file_path)
        # If there are no (valid) credentials available, let the user log in.

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    print(" ================ Token is bad! ================")
                    try:
                        creds.refresh(Request())
                    except RefreshError:
                        os.remove(token_file_path)
                        return self.get_credentials()
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

    def update_calendars(self) -> None:
        result = self.service.calendarList().list().execute()
        cal_ids = []
        for cal in result["items"]:
            if 0:
                print("=" * 80)
                pp(cal)
                continue
            cal = Calendar(cal)
            cal_ids.append(cal)

        self.calendars = cal_ids

    # @Slot()
    def update_events(self) -> None:
        events = []
        for calendar in self.calendars:
            events += self.get_events(calendar)
        self.events = events
        print("   EVENTS UPDATED")
        self.last_update_time = time.time()
        # self.events_gathered_signal.emit()

    def get_events(self, calendar: Calendar) -> list[TimeEvent]:
        """Get amazing events.

        Args:
            calendar (Calendar): calendar to get events from.

        Returns:
            list[TimeEvent]
        """
        # Call the Calendar API

        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        # time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # time_max = now.replace(hour=23, minute=59, second=59, microsecond=0)
        now = datetime.datetime.now(LOCAL_TIMEZONE)
        time_min = now.replace(hour=0, minute=0, second=0)
        time_max = now.replace(hour=23, minute=59, second=59)
        # print("Cal:", calendar.summary, "---", calendar.id)
        events_query = self.service.events().list(  # type: ignore
            calendarId=calendar.id,
            maxAttendees=1,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=250,
            singleEvents=True,
            orderBy="startTime",
        )
        events_result = events_query.execute()

        # pp(events_result)
        # print("   Items:", len(events_result["items"]))

        items = events_result.get("items", [])
        result = []
        # Prints the start and name of the next 10 events
        for item in items:
            # Skip all day events.  All day events have a event['start']['date'] and not a 'dateTime']

            if 0:
                if "dateTime" not in item["start"]:
                    continue
                # print("=======")
                print(item["summary"])
                # print("    ", event.get("endTimeUnspecified"))
                print("   ", item.get("attendees"))
                continue
            try:
                event = TimeEvent(item, calendar)
            except ValueError:
                # print("Invalid event", item["summary"])
                continue
            result.append(event)

        return result


if __name__ == "__main__":
    gcal = GoogleCalDownloader()
    gcal.update_calendars()
    gcal.update_events()

    for cal in gcal.calendars:
        continue
        if cal.primary:
            events = gcal.get_events(cal)
            for event in events:
                print(event)
