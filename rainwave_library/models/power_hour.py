import dataclasses
import datetime
from typing import TypedDict, cast
from zoneinfo import ZoneInfo

import fort

POWER_HOUR_TARGET_SID = 5
POWER_HOUR_TARGET_DURATION_SECONDS = 120 * 60
POWER_HOUR_MINIMUM_DURATION_SECONDS = 20 * 60
POWER_HOUR_ALLOWED_ISO_WEEKDAYS = frozenset({1, 2, 4})
POWER_HOUR_TIME_ZONE = ZoneInfo("America/New_York")
POWER_HOUR_START_TIME = datetime.time(hour=14)
POWER_HOUR_REPRISE_TIME_ZONE = ZoneInfo("Europe/London")
POWER_HOUR_REPRISE_START_TIME = datetime.time(hour=10)


class _PowerHourCandidateRow(TypedDict):
    album_name: str
    song_artist_tag: str
    song_id: int
    song_length: int
    song_origin_sid: int
    song_title: str


@dataclasses.dataclass(frozen=True)
class PowerHourCandidate:
    id: int
    origin_channel_id: int
    album: str
    title: str
    artist: str
    duration_seconds: int


@dataclasses.dataclass(frozen=True)
class PowerHourOverview:
    candidates: tuple[PowerHourCandidate, ...]
    next_scheduling_at: datetime.datetime
    minimum_duration_seconds: int = POWER_HOUR_MINIMUM_DURATION_SECONDS
    target_duration_seconds: int = POWER_HOUR_TARGET_DURATION_SECONDS

    @property
    def can_schedule(self) -> bool:
        return self.total_duration_seconds >= self.minimum_duration_seconds

    @property
    def remaining_duration_seconds(self) -> int:
        return max(0, self.minimum_duration_seconds - self.total_duration_seconds)

    @property
    def next_reprise_at(self) -> datetime.datetime:
        return power_hour_reprise_at(self.next_scheduling_at)

    @property
    def total_duration_seconds(self) -> int:
        return sum(candidate.duration_seconds for candidate in self.candidates)


def next_power_hour_scheduling_at(
    now: datetime.datetime | None = None,
) -> datetime.datetime:
    if now is None:
        local_now = datetime.datetime.now(tz=POWER_HOUR_TIME_ZONE)
    elif now.tzinfo is None:
        msg = "Power Hour scheduling requires a timezone-aware datetime."
        raise ValueError(msg)
    else:
        local_now = now.astimezone(POWER_HOUR_TIME_ZONE)

    for offset in range(8):
        date = local_now.date() + datetime.timedelta(days=offset)
        scheduling_at = datetime.datetime.combine(
            date,
            POWER_HOUR_START_TIME,
            tzinfo=POWER_HOUR_TIME_ZONE,
        )
        if (
            scheduling_at.isoweekday() in POWER_HOUR_ALLOWED_ISO_WEEKDAYS
            and scheduling_at > local_now
        ):
            return scheduling_at

    msg = "Could not determine the next Power Hour scheduling time."
    raise RuntimeError(msg)


def power_hour_reprise_at(
    scheduling_at: datetime.datetime,
) -> datetime.datetime:
    if scheduling_at.tzinfo is None:
        msg = (
            "New Music Power Hour reprise scheduling requires a timezone-aware "
            "datetime."
        )
        raise ValueError(msg)
    scheduling_date = scheduling_at.astimezone(POWER_HOUR_REPRISE_TIME_ZONE).date()
    return datetime.datetime.combine(
        scheduling_date + datetime.timedelta(days=1),
        POWER_HOUR_REPRISE_START_TIME,
        tzinfo=POWER_HOUR_REPRISE_TIME_ZONE,
    )


def power_hour_candidates_get(
    db: fort.PostgresDatabase,
) -> tuple[PowerHourCandidate, ...]:
    sql = """
        select
            a.album_name,
            s.song_artist_tag,
            s.song_id,
            s.song_length,
            s.song_origin_sid,
            s.song_title
        from r4_song_sid ss
        join r4_songs s on s.song_id = ss.song_id
        join r4_albums a on a.album_id = s.album_id
        where s.song_new_played is false
            and s.song_verified is true
            and ss.sid = %(target_sid)s
            and s.song_origin_sid != 2
        order by
            a.album_name collate "C",
            s.song_title collate "C",
            s.song_id
    """
    rows = cast(
        list[_PowerHourCandidateRow],
        cast(object, db.q(sql, {"target_sid": POWER_HOUR_TARGET_SID})),
    )
    return tuple(
        PowerHourCandidate(
            id=row["song_id"],
            origin_channel_id=row["song_origin_sid"],
            album=row["album_name"],
            title=row["song_title"],
            artist=row["song_artist_tag"],
            duration_seconds=row["song_length"],
        )
        for row in rows
    )


def power_hour_overview_get(
    db: fort.PostgresDatabase,
    *,
    now: datetime.datetime | None = None,
) -> PowerHourOverview:
    return PowerHourOverview(
        candidates=power_hour_candidates_get(db),
        next_scheduling_at=next_power_hour_scheduling_at(now),
    )
