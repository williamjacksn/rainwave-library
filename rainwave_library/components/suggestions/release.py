import datetime

import flask
import htpy

from rainwave_library.models.rainwave import (
    ChannelRootFolder,
)
from rainwave_library.models.suggestions import (
    SuggestionDetail,
)

from ..common import _duration_hms


def _suggestion_release_default_channel_folder(
    suggestion: SuggestionDetail,
) -> str | None:
    channel_folders = {
        1: ChannelRootFolder.GAME_ALL.value,
        2: ChannelRootFolder.OCR_ALL.value,
        3: ChannelRootFolder.COVERS_ALL.value,
        4: ChannelRootFolder.CHIPTUNE_ALL.value,
        6: ChannelRootFolder.CHILL_ONLY.value,
    }
    channel_ids = (
        (suggestion.primary_channel_id,)
        if suggestion.primary_channel_id is not None
        else ()
    ) + suggestion.channel_ids
    return next(
        (
            channel_folders[channel_id]
            for channel_id in channel_ids
            if channel_id in channel_folders
        ),
        None,
    )


def _suggestion_schedule_release_duration(
    staged_duration_seconds: float,
    *,
    release_immediately: bool = False,
    release_date: str = "",
    upcoming_duration_seconds: float | None = None,
) -> htpy.Element:
    selected_date_duration = (
        upcoming_duration_seconds
        if release_date and upcoming_duration_seconds is not None
        else None
    )
    return htpy.div(
        "#suggestion-release-duration.alert.alert-secondary.py-2",
        aria_live="polite",
        role="status",
    )[
        htpy.div[
            htpy.strong[
                "MP3 duration to be copied: "
                if release_immediately
                else "MP3 duration to be moved: "
            ],
            _duration_hms(staged_duration_seconds),
        ],
        selected_date_duration is not None
        and htpy.fragment[
            htpy.div[
                htpy.strong["Already in "],
                htpy.code[f"~upcoming/{release_date}"],
                htpy.strong[": "],
                _duration_hms(selected_date_duration),
            ],
            htpy.div[
                htpy.strong["Total after this release: "],
                _duration_hms(selected_date_duration + staged_duration_seconds),
            ],
        ],
    ]


def suggestion_schedule_release_duration(
    staged_duration_seconds: float,
    *,
    release_immediately: bool = False,
    release_date: str = "",
    upcoming_duration_seconds: float | None = None,
) -> str:
    return str(
        _suggestion_schedule_release_duration(
            staged_duration_seconds,
            release_immediately=release_immediately,
            release_date=release_date,
            upcoming_duration_seconds=upcoming_duration_seconds,
        )
    )


def _suggestion_schedule_release_target(
    suggestion_id: str,
    *,
    target_path: str | None = None,
    message: str = (
        "Choose a release date or select release immediately to preview the target "
        "folder."
    ),
    error: bool = False,
    initial_load: bool = False,
) -> htpy.Element:
    triggers = "change from:closest form, input changed delay:300ms from:closest form"
    if initial_load:
        triggers = f"load, {triggers}"
    return htpy.div(
        "#suggestion-release-target.form-text.mt-2",
        aria_live="polite",
        hx_get=flask.url_for(
            "suggestion_schedule_release_target",
            suggestion_id=suggestion_id,
        ),
        hx_include="closest form",
        hx_swap="outerHTML",
        hx_target="this",
        hx_trigger=triggers,
        role="status",
    )[
        htpy.div(".fw-semibold")["Target folder"],
        (
            htpy.code(".d-block.text-break.user-select-all")[target_path]
            if target_path is not None
            else htpy.span(class_="text-danger" if error else None)[message]
        ),
    ]


def suggestion_schedule_release_target(
    suggestion_id: str,
    *,
    target_path: str | None = None,
    message: str = (
        "Choose a release date or select release immediately to preview the target "
        "folder."
    ),
    error: bool = False,
) -> str:
    return str(
        _suggestion_schedule_release_target(
            suggestion_id,
            target_path=target_path,
            message=message,
            error=error,
        )
    )


def _suggestion_schedule_release_form(
    suggestion: SuggestionDetail,
    *,
    release_date: str = "",
    release_immediately: bool = False,
    channel_folder: str | None = None,
    folder_path: str | None = None,
    staged_duration_seconds: float = 0.0,
    upcoming_duration_seconds: float | None = None,
    error: str | None = None,
) -> htpy.Element:
    url = flask.url_for(
        "suggestion_schedule_release",
        suggestion_id=suggestion.id,
    )
    duration_url = flask.url_for(
        "suggestion_schedule_release_duration",
        suggestion_id=suggestion.id,
    )
    selected_channel_folder = (
        _suggestion_release_default_channel_folder(suggestion)
        if channel_folder is None
        else channel_folder
    )
    minimum_release_date = (
        datetime.date.today() + datetime.timedelta(days=1)
    ).isoformat()
    return htpy.form(
        "#suggestion-schedule-release-form.modal-content",
        action=url,
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="outerHTML",
        hx_target="this",
        method="post",
    )[
        htpy.div(".modal-header")[
            htpy.h5("#suggestion-schedule-release-title.modal-title")[
                "Release suggestion"
            ],
            htpy.button(
                ".btn-close",
                aria_label="Close",
                data_bs_dismiss="modal",
                type="button",
            ),
        ],
        htpy.div(".modal-body")[
            error and htpy.div(".alert.alert-danger", role="alert")[error],
            htpy.p[
                "Files staged for ",
                htpy.strong[suggestion.title],
                " can be moved into the upcoming music folder for a future date or "
                "copied directly into the library immediately.",
            ],
            _suggestion_schedule_release_duration(
                staged_duration_seconds,
                release_immediately=release_immediately,
                release_date=release_date,
                upcoming_duration_seconds=upcoming_duration_seconds,
            ),
            htpy.div(".g-3.row")[
                htpy.div(".col-12")[
                    htpy.div(".form-check")[
                        htpy.input(
                            "#suggestion-release-immediately.form-check-input",
                            checked=release_immediately,
                            hx_get=duration_url,
                            hx_include="closest form",
                            hx_swap="outerHTML",
                            hx_target="#suggestion-release-duration",
                            hx_trigger="change",
                            name="release-immediately",
                            onchange=(
                                "document.getElementById('suggestion-release-date')"
                                ".required = !this.checked"
                            ),
                            type="checkbox",
                            value="1",
                        ),
                        htpy.label(
                            ".form-check-label",
                            for_="suggestion-release-immediately",
                        )["Release immediately"],
                    ],
                    htpy.div(".form-text")[
                        "Copies the staged files directly into the selected channel "
                        "folder under the library root. If the destination already "
                        "exists, files are merged into it and matching files are "
                        "replaced."
                    ],
                ],
                htpy.div(".col-12.col-md-6")[
                    htpy.label(
                        ".form-label",
                        for_="suggestion-release-date",
                    )["Release date"],
                    htpy.input(
                        "#suggestion-release-date.form-control",
                        hx_get=duration_url,
                        hx_include="closest form",
                        hx_swap="outerHTML",
                        hx_target="#suggestion-release-duration",
                        hx_trigger="change",
                        min=minimum_release_date,
                        name="release-date",
                        required=not release_immediately,
                        type="date",
                        value=release_date,
                    ),
                    htpy.div(".form-text")[
                        "Required for scheduled releases and must be in the future."
                    ],
                ],
                htpy.div(".col-12.col-md-6")[
                    htpy.label(
                        ".form-label",
                        for_="suggestion-release-channel-folder",
                    )["Channel folder"],
                    htpy.select(
                        "#suggestion-release-channel-folder.form-select",
                        name="channel-folder",
                        required=True,
                    )[
                        htpy.option(
                            disabled=True,
                            selected=not selected_channel_folder,
                            value="",
                        )["Choose a channel folder"],
                        [
                            htpy.option(
                                selected=folder.value == selected_channel_folder,
                                value=folder.value,
                            )[f"{folder.label} ({folder.value})"]
                            for folder in ChannelRootFolder
                        ],
                    ],
                ],
                htpy.div(".col-12")[
                    htpy.label(
                        ".form-label",
                        for_="suggestion-release-folder-path",
                    )["Folder path"],
                    htpy.input(
                        "#suggestion-release-folder-path.form-control",
                        name="folder-path",
                        placeholder="~Category/Album Name",
                        required=True,
                        type="text",
                        value=(
                            suggestion.title if folder_path is None else folder_path
                        ),
                    ),
                    htpy.div(".form-text")[
                        "Separate nested folders with forward slashes. For example, "
                        "~Category/Album Name."
                    ],
                    _suggestion_schedule_release_target(
                        suggestion.id,
                        initial_load=True,
                    ),
                ],
            ],
        ],
        htpy.div(".justify-content-between.modal-footer")[
            htpy.button(
                ".btn.btn-secondary",
                data_bs_dismiss="modal",
                type="button",
            )["Cancel"],
            htpy.button(".btn.btn-primary", type="submit")[
                htpy.i(".bi-check-circle"), " Release suggestion"
            ],
        ],
    ]


def suggestion_schedule_release_form(
    suggestion: SuggestionDetail,
    *,
    release_date: str = "",
    release_immediately: bool = False,
    channel_folder: str | None = None,
    folder_path: str | None = None,
    staged_duration_seconds: float = 0.0,
    upcoming_duration_seconds: float | None = None,
    error: str | None = None,
) -> str:
    return str(
        _suggestion_schedule_release_form(
            suggestion,
            release_date=release_date,
            release_immediately=release_immediately,
            channel_folder=channel_folder,
            folder_path=folder_path,
            staged_duration_seconds=staged_duration_seconds,
            upcoming_duration_seconds=upcoming_duration_seconds,
            error=error,
        )
    )


def _suggestion_schedule_release_modal(
    suggestion: SuggestionDetail,
    staged_duration_seconds: float,
) -> htpy.Element:
    return htpy.div(
        "#suggestion-schedule-release-modal.fade.modal",
        aria_hidden="true",
        aria_labelledby="suggestion-schedule-release-title",
        tabindex="-1",
    )[
        htpy.div(".modal-dialog.modal-dialog-centered.modal-lg")[
            _suggestion_schedule_release_form(
                suggestion,
                staged_duration_seconds=staged_duration_seconds,
            )
        ]
    ]


def _suggestion_schedule_release_button() -> htpy.Element:
    return htpy.button(
        ".btn.btn-primary",
        data_bs_target="#suggestion-schedule-release-modal",
        data_bs_toggle="modal",
        type="button",
    )[htpy.i(".bi-calendar-plus"), " Release suggestion"]
