import datetime


class Event:
    """
    Calendar event data model.
    """

    def __init__(self, google_event):
        self._event = google_event  # type: dict

        start_time = self._event["start"].get(
            "dateTime", self._event["start"].get("date")
        )
        self.start = datetime.datetime.strptime(start_time[:19], "%Y-%m-%dT%H:%M:%S")
        self.summary = self._event["summary"]
        self.attending = True

    def __repr__(self):
        return f"<{self.summary}>"

    def get_time_till_event(self):
        now = datetime.datetime.now()
        return (self.start - now).total_seconds()
