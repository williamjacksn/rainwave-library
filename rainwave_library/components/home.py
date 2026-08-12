import pathlib

import flask
import htpy

from rainwave_library.models.storage import (
    UpcomingMusicDirectory,
    UpcomingMusicEntry,
)

from .common import _back_button, _base, _duration_hms, _user_menu


def _upcoming_music_entry(entry: UpcomingMusicEntry) -> htpy.Element:
    href = (
        flask.url_for("upcoming_music", path=entry.relative_path)
        if entry.is_directory
        else flask.url_for("upcoming_music_file", path=entry.relative_path)
    )
    return htpy.a(
        ".align-items-center.d-flex.gap-3.list-group-item.list-group-item-action",
        download=None if entry.is_directory else entry.name,
        href=href,
    )[
        htpy.i(
            ".bi-folder-fill.fs-4.text-warning"
            if entry.is_directory
            else ".bi-file-earmark.fs-4.text-secondary"
        ),
        htpy.div(".flex-grow-1.text-break")[entry.name],
        htpy.span(".small.text-nowrap.text-secondary")[
            (
                f"{_duration_hms(entry.duration_seconds or 0)} MP3"
                if entry.is_directory
                else f"{entry.size or 0:,} bytes"
            )
        ],
    ]


def _upcoming_music_breadcrumbs(relative_path: str) -> htpy.Element:
    parts = pathlib.PurePosixPath(relative_path).parts if relative_path else ()
    breadcrumbs = [
        htpy.li(
            ".active.breadcrumb-item" if not parts else ".breadcrumb-item",
            aria_current="page" if not parts else None,
        )[
            "Upcoming music"
            if not parts
            else htpy.a(href=flask.url_for("upcoming_music"))["Upcoming music"]
        ]
    ]
    for index, part in enumerate(parts):
        is_current = index == len(parts) - 1
        path = pathlib.PurePosixPath(*parts[: index + 1]).as_posix()
        breadcrumbs.append(
            htpy.li(
                ".active.breadcrumb-item" if is_current else ".breadcrumb-item",
                aria_current="page" if is_current else None,
            )[
                part
                if is_current
                else htpy.a(href=flask.url_for("upcoming_music", path=path))[part]
            ]
        )
    return htpy.nav(aria_label="Upcoming music folders")[
        htpy.ol(".breadcrumb")[breadcrumbs]
    ]


def _upcoming_music_empty_folder(directory: UpcomingMusicDirectory) -> htpy.Element:
    folder_name = pathlib.PurePosixPath(directory.relative_path).name
    delete_url = flask.url_for("upcoming_music_folder_delete")
    return htpy.div[
        htpy.p(".text-secondary")["This folder is empty."],
        directory.relative_path
        and htpy.form(
            action=delete_url,
            hx_confirm=f'Delete the empty folder "{folder_name}"?',
            hx_disabled_elt="button",
            hx_post=delete_url,
            hx_swap="none",
            method="post",
        )[
            htpy.input(
                name="path",
                type="hidden",
                value=directory.relative_path,
            ),
            htpy.button(".btn.btn-danger", type="submit")[
                htpy.i(".bi-trash"), " Delete empty folder"
            ],
        ],
    ]


def upcoming_music(directory: UpcomingMusicDirectory) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"),
            _user_menu(),
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.h1["Upcoming music"],
                htpy.code(".d-block.small.text-break.user-select-all")[
                    str(directory.path)
                ],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                _upcoming_music_breadcrumbs(directory.relative_path),
                (
                    htpy.div(".list-group")[
                        [_upcoming_music_entry(entry) for entry in directory.entries]
                    ]
                    if directory.entries
                    else (
                        _upcoming_music_empty_folder(directory)
                        if directory.exists
                        else htpy.div(".alert.alert-warning", role="alert")[
                            "The upcoming music folder does not exist."
                        ]
                    )
                ),
            ]
        ],
    ]
    return str(_base(content))


def welcome(role: str) -> str:
    tools: list[tuple[str, str, str]] = [
        (
            "suggestions",
            "Music suggestions",
            "Browse music suggested for the Rainwave library",
        )
    ]
    if role == "staff":
        tools.extend(
            [
                ("songs", "Songs", "Browse and manage songs in the Rainwave library"),
                ("albums", "Albums", "Browse albums and check for missing art"),
                ("artists", "Artists", "Browse artists and their song counts"),
                (
                    "listeners",
                    "Listeners",
                    "Browse and manage Rainwave listener accounts",
                ),
                (
                    "get_ocremix",
                    "OC ReMix",
                    "Download and tag remixes from ocremix.org",
                ),
                (
                    "upcoming_music",
                    "Upcoming music",
                    "Browse music staged in the upcoming library folder",
                ),
                (
                    "bluesky",
                    "Post to Bluesky",
                    "Post an update to the Rainwave Bluesky account",
                ),
                (
                    "settings",
                    "Application settings",
                    "View application configuration",
                ),
            ]
        )
    content = [
        htpy.div(".g-1.pt-3.row")[
            htpy.div(".col-auto.me-auto")[
                htpy.a(".btn.btn-secondary", href="#")[
                    htpy.i(".bi-boombox-fill", style="color: #f73"), " Rainwave Library"
                ]
            ],
            _user_menu(),
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.div(".list-group")[
                    [
                        htpy.a(
                            ".list-group-item.list-group-item-action",
                            href=flask.url_for(endpoint),
                        )[
                            htpy.div(".fw-semibold")[label],
                            htpy.div(".small.text-secondary")[description],
                        ]
                        for endpoint, label, description in tools
                    ]
                    if tools
                    else htpy.p["No tools are available for your account yet."]
                ]
            ]
        ],
    ]
    return str(_base(content))
