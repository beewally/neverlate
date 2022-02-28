from __future__ import annotations

import datetime
import os
import time
import traceback
from pprint import pprint as pp
from typing import Any, Optional

# Google imports
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from neverlate.utils import app_local_data_dir, now_datetime

# from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

EMAIL = None


class Calendar:
    """
    Google calendar data model
    """

    summary: str
    id: str
    primary: bool
    selected: bool  # Is the user displaying the calendary by default

    def __init__(self, data: dict[Any, Any]) -> None:
        self._data = data
        self.id = data["id"]
        self.primary = data.get("primary", False)
        self.summary = data.get("summaryOverride", data.get("summary", "<No Title>"))
        if self.primary:
            self.selected = True
        elif self.summary == "Birthdays" or self.summary.lower().startswith("holiday"):
            self.selected = False
        else:
            self.selected = data.get("selected", False)

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

    calendar: Calendar

    def __init__(self, item: dict[Any, Any], calendar: Calendar):
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
        self._event = item  # type: dict[str, Any]
        self.summary = self._event.get("summary", "<No Title>")

        # Get start and end times as datetime objects
        st_time = self._event["start"]["dateTime"]
        self.start_time = datetime.datetime.fromisoformat(st_time)
        # self.start_time = datetime.datetime.strptime(st_time[:19], "%Y-%m-%dT%H:%M:%S")
        end_time = self._event["end"]["dateTime"]
        self.end_time = datetime.datetime.fromisoformat(end_time)
        self.id = "::".join(
            (
                self._event["id"],
                self.start_time.isoformat(),
                self.get_video_url(),
            )
        )

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
        return (self.start_time - now_datetime()).total_seconds()

    def get_video_url(self) -> str:
        entry_points = self._event.get("conferenceData", {}).get("entryPoints", [])
        for entry_point in entry_points:
            if entry_point.get("entryPointType", "") == "video":
                return entry_point["uri"]

        # Occasionally there are events with links that aren't categorized but have URIs...
        for entry_point in entry_points:
            if "entryPointType" not in entry_point and entry_point.get("uri"):
                return entry_point.get("uri")
        return ""

    def has_declined(self) -> bool:
        for attendee in self._event.get("attendees", []):
            # if attendee["email"] == "bwalters@wayfair.com":
            return attendee["responseStatus"] == "declined"
        return False

    def has_ended(self) -> bool:
        return (self.end_time - now_datetime()).total_seconds() < 0


class GoogleCalDownloader:  # (QObject):
    """Interface with Google. Credentials, downloading calendars, and downloading events."""

    primary_calendar: Calendar  # TODO: not used?
    calendars: list[Calendar] = []
    events: list[TimeEvent] = []
    last_update_time: float = 0.0

    # events_gathered_signal = Signal(list[Calendar])

    def __init__(self):
        super().__init__()
        self.service = None
        # self.service = build("calendar", "v3", credentials=self.creds)  # type: Resource
        self._cred_file_path = os.path.join(
            os.path.dirname(__file__), "credentials.json"
        )

        self.user_token_file_path = os.path.join(app_local_data_dir(), "token.json")

    def logout(self):
        """
        Remove the user token file and disconnect the service.
        """
        if os.path.exists(self.user_token_file_path):
            os.remove(self.user_token_file_path)

        self.service = None

    def login(self, require_existing_credentials: bool = False) -> bool:
        """Gets google authentication credentails."""
        creds = self.get_existing_credentials()
        if require_existing_credentials and not creds:
            return False
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                self._cred_file_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.user_token_file_path, "w") as token_file:
                token_file.write(creds.to_json())

        self.service = build("calendar", "v3", credentials=creds)  # type: Resource
        return True

    def get_existing_credentials(self) -> Credentials | None:
        """
        Check if we have valid credentials or not.

        Returns:
            Credentials|None
        """
        creds = None
        if not os.path.exists(self.user_token_file_path):
            return None
        creds = Credentials.from_authorized_user_file(self.user_token_file_path, SCOPES)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())

                # Save the credentials for the next run
                with open(self.user_token_file_path, "w") as token_file:
                    token_file.write(creds.to_json())
                return creds
            except RefreshError:
                return None

    def update_calendars(self) -> None:
        result = self.service.calendarList().list().execute()
        cal_ids = []
        for cal in result["items"]:
            if 0:
                print("=" * 80)
                pp(cal)
                continue
            if cal.get("deleted"):
                continue
            cal = Calendar(cal)
            cal_ids.append(cal)

        self.calendars = cal_ids

    def update_events(self, calendars: Optional[list[Calendar]] = None) -> None:
        events = []
        if calendars is None:
            calendars = self.calendars

        for calendar in calendars:
            events += self.get_events(calendar)
        self.events = events
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

        # now_ = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        # time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # time_max = now.replace(hour=23, minute=59, second=59, microsecond=0)
        now_ = now_datetime()
        time_min = now_.replace(hour=0, minute=0, second=0)
        time_max = now_.replace(hour=23, minute=59, second=59)
        # print("Cal:", calendar.summary, "---", calendar.id)
        events_query = self.service.events().list(  # type: ignore
            calendarId=calendar.id,
            maxAttendees=1,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=250,
            singleEvents=True,
            # orderBy="startTime",
        )
        events_result = events_query.execute()

        # pp(events_result)
        # print("   Items:", len(events_result["items"]))

        items = events_result.get("items", [])
        result = []
        # Prints the start and name of the next 10 events
        for item in items:
            try:
                event = TimeEvent(item, calendar)
            except ValueError:
                #  print("Invalid event", item.get("summary", "<No Title>"))
                continue
            except:
                # Unknown error needs to be handled
                print(traceback.format_exc())
                continue
            result.append(event)

        return result


if __name__ == "__main__":
    gcal = GoogleCalDownloader()
    gcal.update_calendars()
    gcal.update_events()
