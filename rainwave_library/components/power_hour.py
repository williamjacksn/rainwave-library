import datetime

import flask
import htpy

from rainwave_library.models.power_hour import PowerHourOverview
from rainwave_library.models.rainwave import channel_badge, length_display

from .common import _back_button, _base, _duration_hms, _user_menu


def _scheduling_time_display(value: datetime.datetime) -> str:
    hour = value.hour % 12 or 12
    return (
        f"{value:%A, %B} {value.day}, {value.year} at "
        f"{hour}:{value.minute:02d} {value.tzname()}"
    )


def power_hour(overview: PowerHourOverview) -> str:
    if overview.can_schedule:
        status = htpy.div(".alert.alert-success", role="status")[
            [
                htpy.i(".bi-check-circle-fill.me-2"),
                (
                    "The eligible songs meet the minimum duration for a New Music "
                    "Power Hour."
                ),
            ]
        ]
    else:
        status = htpy.div(".alert.alert-warning", role="alert")[
            [
                htpy.i(".bi-exclamation-triangle-fill.me-2"),
                (
                    "There is not enough eligible music to schedule a New Music "
                    "Power Hour. "
                ),
                htpy.strong[
                    _duration_hms(overview.remaining_duration_seconds), " more"
                ],
                " is required.",
            ]
        ]

    candidate_rows = [
        htpy.tr[
            htpy.td(".text-end")[
                htpy.a(
                    ".text-decoration-none",
                    href=flask.url_for("songs_detail", song_id=candidate.id),
                )[htpy.code[candidate.id]]
            ],
            htpy.td(".text-nowrap")[channel_badge(candidate.origin_channel_id)],
            htpy.td[candidate.album],
            htpy.td[candidate.title],
            htpy.td[candidate.artist],
            htpy.td(".text-end.text-nowrap")[
                [length_display(candidate.duration_seconds)]
            ],
        ]
        for candidate in overview.candidates
    ]
    if not candidate_rows:
        candidate_rows.append(
            htpy.tr[
                htpy.td(".py-3.text-center", colspan=6)[
                    "No songs are currently eligible."
                ]
            ]
        )

    content = [
        htpy.div(".g-1.pt-3.row")[
            [
                _back_button(flask.url_for("index"), "Home"),
                _user_menu(),
            ]
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["New Music Power Hours"]]],
        htpy.div(".pt-3.row")[htpy.div(".col")[status]],
        htpy.div(".g-3.row")[
            [
                htpy.div(".col-12.col-md-6.col-xl")[
                    htpy.div(".card.h-100")[
                        htpy.div(".card-body")[
                            htpy.div(".small.text-secondary")[
                                (
                                    "Next New Music Power Hour"
                                    if overview.can_schedule
                                    else "Next scheduling opportunity"
                                )
                            ],
                            htpy.div(".fw-semibold.mt-1")[
                                htpy.time(
                                    datetime=overview.next_scheduling_at.isoformat()
                                )[_scheduling_time_display(overview.next_scheduling_at)]
                            ],
                            htpy.div(".small.text-secondary")["America/New_York"],
                        ]
                    ]
                ],
                htpy.div(".col-12.col-md-6.col-xl")[
                    htpy.div(".card.h-100")[
                        htpy.div(".card-body")[
                            htpy.div(".small.text-secondary")["EU reprise"],
                            htpy.div(".fw-semibold.mt-1")[
                                htpy.time(
                                    datetime=overview.next_reprise_at.isoformat()
                                )[_scheduling_time_display(overview.next_reprise_at)]
                            ],
                            htpy.div(".small.text-secondary")["Europe/London"],
                        ]
                    ]
                ],
                htpy.div(".col-6.col-md-4.col-xl")[
                    htpy.div(".card.h-100")[
                        htpy.div(".card-body")[
                            htpy.div(".small.text-secondary")["Eligible songs"],
                            htpy.div(".fs-4.fw-semibold")[len(overview.candidates)],
                        ]
                    ]
                ],
                htpy.div(".col-6.col-md-4.col-xl")[
                    htpy.div(".card.h-100")[
                        htpy.div(".card-body")[
                            htpy.div(".small.text-secondary")["Total duration"],
                            htpy.div(".fs-4.fw-semibold")[
                                _duration_hms(overview.total_duration_seconds)
                            ],
                        ]
                    ]
                ],
                htpy.div(".col-12.col-md-4.col-xl")[
                    htpy.div(".card.h-100")[
                        htpy.div(".card-body")[
                            htpy.div(".small.text-secondary")["Required / target"],
                            htpy.div(".fs-4.fw-semibold")[
                                [
                                    _duration_hms(overview.minimum_duration_seconds),
                                    " / ",
                                    _duration_hms(overview.target_duration_seconds),
                                ]
                            ],
                        ]
                    ]
                ],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.details[
                    htpy.summary["Eligibility rules"],
                    htpy.ul(".mb-0.mt-2")[
                        [
                            htpy.li["The song has not previously played as new music."],
                            htpy.li[
                                "The song is verified and available on the All channel."
                            ],
                            htpy.li["The song origin is not the OC ReMix channel."],
                            htpy.li[
                                "New Music Power Hours can be scheduled on Monday, "
                                "Tuesday, and Thursday at 2:00 PM (America/New_York)."
                            ],
                            htpy.li[
                                "The EU reprise airs the following day at 10:00 AM "
                                "(Europe/London)."
                            ],
                        ]
                    ],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.div(".align-items-baseline.d-flex.gap-2.justify-content-between")[
                    [
                        htpy.h2(".h4")["Eligible songs"],
                        htpy.span(".small.text-secondary")[
                            "Selection order is randomized by the scheduler."
                        ],
                    ]
                ],
                htpy.div(".table-responsive")[
                    htpy.table(
                        ".align-middle.table.table-bordered.table-sm.table-striped"
                    )[
                        [
                            htpy.thead[
                                htpy.tr[
                                    htpy.th(".text-end", scope="col")["ID"],
                                    htpy.th(scope="col")["Origin"],
                                    htpy.th(scope="col")["Album"],
                                    htpy.th(scope="col")["Title"],
                                    htpy.th(scope="col")["Artist"],
                                    htpy.th(".text-end", scope="col")["Duration"],
                                ]
                            ],
                            htpy.tbody[candidate_rows],
                        ]
                    ]
                ],
            ]
        ],
    ]
    return str(_base(content))
