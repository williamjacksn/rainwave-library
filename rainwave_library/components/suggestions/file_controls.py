import hashlib

import flask
import htpy

from rainwave_library.models.mp3 import (
    ID3_TAG_LABELS,
    Mp3FilenameNormalization,
)
from rainwave_library.models.rainwave import (
    length_display,
)
from rainwave_library.models.suggestions import (
    SuggestionFileReview,
)


def _suggestion_tag_values(values: tuple[str, ...]) -> htpy.Node:
    if not values:
        return htpy.span(".text-secondary")["—"]
    return htpy.div[
        [
            htpy.div(".text-break", style="white-space: pre-wrap")[value]
            for value in values
        ]
    ]


def _suggestion_tag_group_cell(
    tag_names: tuple[str, str],
    tag_values: dict[str, tuple[str, ...]],
) -> htpy.Element:
    return htpy.td[
        [
            (htpy.div(".border-bottom.mb-2.pb-2") if tag_index == 0 else htpy.div)[
                htpy.div(".fw-semibold.mb-1.small.text-secondary")[
                    ID3_TAG_LABELS[tag_name]
                ],
                _suggestion_tag_values(tag_values[tag_name]),
            ]
            for tag_index, tag_name in enumerate(tag_names)
        ]
    ]


def _suggestion_music_edit_button(row_index: int, path: str) -> htpy.Element:
    modal_id = f"suggestion-file-tags-{row_index}"
    return htpy.button(
        ".btn.btn-link.p-0",
        aria_label=f"Edit tags for {path}",
        data_bs_target=f"#{modal_id}",
        data_bs_toggle="modal",
        title="Edit tags",
        type="button",
    )[htpy.i(".bi-pencil")]


def _suggestion_music_tag_modal(
    suggestion_id: str,
    path: str,
    row_index: int,
    tag_values: dict[str, tuple[str, ...]],
) -> htpy.Element:
    modal_id = f"suggestion-file-tags-{row_index}"
    title_id = f"{modal_id}-title"
    update_url = flask.url_for(
        "suggestion_file_tags_update",
        suggestion_id=suggestion_id,
    )
    return htpy.div(
        f"#{modal_id}.fade.modal",
        aria_hidden="true",
        aria_labelledby=title_id,
        tabindex="-1",
    )[
        htpy.div(".modal-dialog.modal-dialog-scrollable.modal-lg")[
            htpy.form(
                ".modal-content",
                action=update_url,
                hx_disabled_elt="button",
                hx_post=update_url,
                hx_swap="outerHTML",
                hx_target="#suggestion-files-card",
                method="post",
            )[
                htpy.input(name="scope", type="hidden", value="file"),
                htpy.input(name="path", type="hidden", value=path),
                htpy.div(".modal-header")[
                    htpy.h5(".modal-title", id=title_id)["Edit MP3 tags"],
                    htpy.button(
                        ".btn-close",
                        aria_label="Close",
                        data_bs_dismiss="modal",
                        type="button",
                    ),
                ],
                htpy.div(".modal-body")[
                    htpy.div(".mb-3")[
                        htpy.div(".small.text-secondary")["File"],
                        htpy.code(".text-break")[path],
                    ],
                    htpy.div(".g-3.row")[
                        [
                            htpy.div(
                                ".col-12"
                                if tag_name in {"www", "comment"}
                                else ".col-12.col-md-6"
                            )[
                                htpy.label(
                                    ".form-label",
                                    for_=f"{modal_id}-{tag_name}",
                                )[label],
                                htpy.input(
                                    f"#{modal_id}-{tag_name}.form-control",
                                    name=tag_name,
                                    type="text",
                                    value=(
                                        tag_values[tag_name][0]
                                        if tag_values[tag_name]
                                        else ""
                                    ),
                                ),
                            ]
                            for tag_name, label in ID3_TAG_LABELS.items()
                        ]
                    ],
                    htpy.div(".form-text.mt-3")[
                        "Leave a field blank to remove that tag."
                    ],
                ],
                htpy.div(".justify-content-between.modal-footer")[
                    htpy.button(
                        ".btn.btn-secondary",
                        data_bs_dismiss="modal",
                        type="button",
                    )["Cancel"],
                    htpy.button(
                        ".btn.btn-primary",
                        data_bs_dismiss="modal",
                        type="submit",
                    )[htpy.i(".bi-tags"), " Save tags"],
                ],
            ]
        ]
    ]


def _suggestion_music_play_button(suggestion_id: str, path: str) -> htpy.Element:
    return htpy.button(
        ".btn.btn-lg.btn-primary",
        aria_label=f"Play {path}",
        hx_get=flask.url_for(
            "suggestion_file_play",
            suggestion_id=suggestion_id,
            path=path,
        ),
        hx_target="#audio",
        title="Play MP3",
        type="button",
    )[htpy.i(".bi-play-fill")]


def _suggestion_music_delete_button(suggestion_id: str, path: str) -> htpy.Element:
    return htpy.button(
        ".btn.btn-link.p-0.text-danger",
        aria_label=f"Delete {path}",
        hx_confirm=f'Delete the file "{path}"?',
        hx_delete=flask.url_for(
            "suggestion_file_delete",
            suggestion_id=suggestion_id,
            path=path,
        ),
        hx_disabled_elt="this",
        hx_swap="outerHTML",
        hx_target="#suggestion-files-card",
        title="Delete file",
        type="button",
    )[htpy.i(".bi-trash")]


def _suggestion_bulk_tag_form(suggestion_id: str) -> htpy.Element:
    update_url = flask.url_for(
        "suggestion_file_tags_update", suggestion_id=suggestion_id
    )
    return htpy.form(
        ".border.p-3.rounded",
        action=update_url,
        hx_confirm="Update this tag for every MP3 file in the suggestion folder?",
        hx_disabled_elt="button",
        hx_post=update_url,
        hx_swap="outerHTML",
        hx_target="#suggestion-files-card",
        method="post",
    )[
        htpy.input(name="scope", type="hidden", value="all"),
        htpy.div(".fw-semibold.mb-2")["Edit one tag for all MP3 files"],
        htpy.div(".align-items-end.g-2.row")[
            htpy.div(".col-sm-4")[
                htpy.label(".form-label", for_="suggestion-bulk-tag")["Tag"],
                htpy.select(
                    "#suggestion-bulk-tag.form-select",
                    name="tag",
                )[
                    [
                        htpy.option(value=tag_name)[label]
                        for tag_name, label in ID3_TAG_LABELS.items()
                    ]
                ],
            ],
            htpy.div(".col")[
                htpy.label(".form-label", for_="suggestion-bulk-tag-value")[
                    "Value (leave blank to remove tag)"
                ],
                htpy.input(
                    "#suggestion-bulk-tag-value.form-control", name="value", type="text"
                ),
            ],
            htpy.div(".col-sm-auto")[
                htpy.button(".btn.btn-primary", type="submit")["Apply to all"]
            ],
        ],
    ]


def _suggestion_music_file_details(
    size: int,
    duration_seconds: float | None,
) -> htpy.Element:
    duration = (
        length_display(int(duration_seconds)) if duration_seconds is not None else "—"
    )
    return htpy.div(".small.text-secondary")[
        duration,
        " · ",
        f"{size:,} bytes",
    ]


def _suggestion_music_review_control_id(
    suggestion_id: str,
    path: str,
    layout: str,
) -> str:
    digest = hashlib.sha256(f"{suggestion_id}\0{path}".encode()).hexdigest()[:16]
    return f"suggestion-music-review-{layout}-{digest}"


def _suggestion_music_review_form(
    suggestion_id: str,
    path: str,
    review: SuggestionFileReview | None,
    layout: str,
    *,
    oob: bool = False,
) -> htpy.Element:
    current_decision = review.decision if review is not None else "unreviewed"
    url = flask.url_for(
        "suggestion_file_review",
        suggestion_id=suggestion_id,
        path=path,
    )
    choices = (
        ("unreviewed", "Not reviewed", "secondary", "bi-circle"),
        ("keep", "Keep", "success", "bi-check-lg"),
        ("pass", "Pass", "danger", "bi-x-lg"),
    )
    return htpy.form(
        f"#{_suggestion_music_review_control_id(suggestion_id, path, layout)}",
        action=url,
        aria_label=f"Review decision for {path}",
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="none",
        hx_swap_oob="outerHTML" if oob else None,
        method="post",
    )[
        htpy.div(".btn-group.btn-group-sm", role="group")[
            [
                htpy.button(
                    f".btn.btn-{'' if decision == current_decision else 'outline-'}"
                    f"{color}",
                    aria_pressed=("true" if decision == current_decision else "false"),
                    name="decision",
                    type="submit",
                    value=decision,
                )[htpy.i(f".{icon}.bi.me-1"), label]
                for decision, label, color, icon in choices
            ]
        ]
    ]


def suggestion_music_review_controls(
    suggestion_id: str,
    path: str,
    review: SuggestionFileReview | None,
) -> str:
    return str(
        htpy.fragment[
            _suggestion_music_review_form(
                suggestion_id,
                path,
                review,
                "desktop",
                oob=True,
            ),
            _suggestion_music_review_form(
                suggestion_id,
                path,
                review,
                "mobile",
                oob=True,
            ),
        ]
    )


def _suggestion_normalize_filenames_button(suggestion_id: str) -> htpy.Element:
    return htpy.button(
        ".btn.btn-secondary",
        data_bs_target="#modal-lg",
        data_bs_toggle="modal",
        hx_get=flask.url_for(
            "suggestion_files_normalize",
            suggestion_id=suggestion_id,
        ),
        hx_swap="outerHTML",
        hx_target="#modal-lg-content",
        type="button",
    )[htpy.i(".bi-input-cursor-text"), " Normalize filenames"]


def suggestion_normalize_filenames_form(
    suggestion_id: str,
    normalizations: tuple[Mp3FilenameNormalization, ...],
) -> str:
    has_errors = any(item.error is not None for item in normalizations)
    changed_count = sum(item.changed for item in normalizations)
    can_submit = bool(normalizations) and not has_errors and changed_count > 0
    url = flask.url_for(
        "suggestion_files_normalize",
        suggestion_id=suggestion_id,
    )
    if not normalizations:
        status: htpy.Node = htpy.div(".alert.alert-warning", role="alert")[
            "There are no MP3 files to normalize."
        ]
    elif has_errors:
        status = htpy.div(".alert.alert-danger", role="alert")[
            "Resolve the filename problems shown below before normalizing."
        ]
    elif changed_count == 0:
        status = htpy.div(".alert.alert-info", role="alert")[
            "All MP3 filenames are already normalized."
        ]
    else:
        status = htpy.div(".alert.alert-secondary", role="status")[
            f"{changed_count} MP3 filename"
            f"{'' if changed_count == 1 else 's'} will change."
        ]

    return str(
        htpy.form(
            "#modal-lg-content.modal-content",
            action=url,
            hx_disabled_elt="button",
            hx_post=url,
            hx_swap="outerHTML",
            hx_target="#suggestion-files-card",
            method="post",
        )[
            htpy.div(".modal-header")[
                htpy.h5(".modal-title")["Normalize filenames"],
                htpy.button(
                    ".btn-close",
                    aria_label="Close",
                    data_bs_dismiss="modal",
                    type="button",
                ),
            ],
            htpy.div(".modal-body")[
                htpy.p[
                    "Each MP3 will be renamed using its first title tag with special "
                    "characters and spaces removed.",
                ],
                status,
                normalizations
                and htpy.div(".table-responsive")[
                    htpy.table(".align-middle.mb-0.table.table-sm")[
                        htpy.thead[
                            htpy.tr[
                                htpy.th["Existing file"],
                                htpy.th["Title tag"],
                                htpy.th["Target file"],
                            ]
                        ],
                        htpy.tbody[
                            [
                                htpy.tr[
                                    htpy.td[htpy.code(".text-break")[item.source_path]],
                                    htpy.td(".text-break")[
                                        item.title or htpy.span(".text-secondary")["—"]
                                    ],
                                    htpy.td[
                                        (
                                            htpy.code(".text-break")[item.target_path]
                                            if item.target_path
                                            else htpy.span(".text-secondary")["—"]
                                        ),
                                        item.error
                                        and htpy.div(".small.text-danger")[item.error],
                                        item.target_path == item.source_path
                                        and htpy.div(".small.text-secondary")[
                                            "No change"
                                        ],
                                    ],
                                ]
                                for item in normalizations
                            ]
                        ],
                    ]
                ],
            ],
            htpy.div(".justify-content-between.modal-footer")[
                htpy.button(
                    ".btn.btn-secondary",
                    data_bs_dismiss="modal",
                    type="button",
                )["Cancel"],
                htpy.button(
                    ".btn.btn-primary",
                    data_bs_dismiss="modal",
                    disabled=not can_submit,
                    type="submit",
                )[htpy.i(".bi-input-cursor-text"), " Normalize filenames"],
            ],
        ]
    )
