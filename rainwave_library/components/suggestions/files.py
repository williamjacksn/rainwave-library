import flask
import htpy

from rainwave_library.models.mp3 import (
    ID3_TAG_LABELS,
    Mp3TagValues,
)
from rainwave_library.models.suggestions import (
    SuggestionFileReview,
)

from ..common import _collapsible_card_header, _music_player
from .file_controls import (
    _suggestion_bulk_tag_form,
    _suggestion_music_delete_button,
    _suggestion_music_edit_button,
    _suggestion_music_file_details,
    _suggestion_music_play_button,
    _suggestion_music_review_form,
    _suggestion_music_tag_modal,
    _suggestion_normalize_filenames_button,
    _suggestion_tag_group_cell,
    _suggestion_tag_values,
)


def _suggestion_file_category(path: str) -> str:
    normalized_path = path.casefold()
    if normalized_path.endswith(".mp3"):
        return "music"
    if normalized_path.endswith((".jpg", ".png")):
        return "images"
    return "other-files"


def _suggestion_file_item(
    suggestion_id: str,
    path: str,
    size: int,
) -> htpy.Element:
    category = _suggestion_file_category(path)
    previewable = category == "images"
    playable = category == "music"
    return htpy.div(".d-flex.gap-3.justify-content-between.list-group-item.px-0")[
        htpy.div(".align-items-start.d-flex.flex-grow-1.gap-2")[
            htpy.code(".text-break")[path],
            previewable
            and htpy.button(
                ".btn.btn-link.p-0",
                aria_label=f"Preview {path}",
                data_bs_target="#modal-lg",
                data_bs_toggle="modal",
                hx_get=flask.url_for(
                    "suggestion_file_preview_modal",
                    suggestion_id=suggestion_id,
                    path=path,
                ),
                hx_swap="outerHTML",
                hx_target="#modal-lg-content",
                title="Preview image",
                type="button",
            )[htpy.i(".bi-eye")],
            playable
            and htpy.button(
                ".btn.btn-link.p-0",
                aria_label=f"Play {path}",
                hx_get=flask.url_for(
                    "suggestion_file_play",
                    suggestion_id=suggestion_id,
                    path=path,
                ),
                hx_target="#audio",
                title="Play MP3",
                type="button",
            )[htpy.i(".bi-play")],
        ],
        htpy.div(".align-items-center.d-flex.gap-2")[
            htpy.span(".small.text-nowrap.text-secondary")[f"{size:,} bytes"],
            htpy.button(
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
            )[htpy.i(".bi-trash")],
        ],
    ]


def _suggestion_file_section(
    suggestion_id: str,
    section_id: str,
    label: str,
    files: tuple[tuple[str, int], ...],
    music_tags: dict[str, Mp3TagValues],
    music_reviews: dict[str, SuggestionFileReview],
) -> htpy.Element:
    heading_id = f"suggestion-files-{section_id}-heading"
    return htpy.section(".mt-3", aria_labelledby=heading_id)[
        htpy.h6(".mb-0.py-2.text-secondary", id=heading_id)[label],
        _suggestion_music_file_table(
            suggestion_id,
            files,
            music_tags,
            music_reviews,
        )
        if section_id == "music"
        else htpy.div(".list-group.list-group-flush")[
            [_suggestion_file_item(suggestion_id, path, size) for path, size in files]
        ],
    ]


def _suggestion_music_file_table(
    suggestion_id: str,
    files: tuple[tuple[str, int], ...],
    music_tags: dict[str, Mp3TagValues],
    music_reviews: dict[str, SuggestionFileReview],
) -> htpy.Element:
    tag_groups = (
        ("album", "title"),
        ("artist", "genre"),
        ("www", "comment"),
    )
    rows = []
    cards = []
    modals = []
    for row_index, (path, size) in enumerate(files):
        tags = music_tags.get(path, Mp3TagValues())
        review = music_reviews.get(path)
        tag_values = {
            "album": tags.album,
            "title": tags.title,
            "artist": tags.artist,
            "genre": tags.genre,
            "www": tags.www,
            "comment": tags.comment,
        }
        rows.append(
            htpy.tr[
                htpy.td(".table-cell-fit.text-center.text-nowrap")[
                    _suggestion_music_play_button(suggestion_id, path)
                ],
                htpy.td[
                    htpy.code(".text-break")[path],
                    _suggestion_music_file_details(size, tags.duration_seconds),
                    tags.error
                    and htpy.div(".small.text-danger", role="status")[tags.error],
                    htpy.div(".mt-2")[
                        _suggestion_music_review_form(
                            suggestion_id,
                            path,
                            review,
                            "desktop",
                        )
                    ],
                ],
                [
                    _suggestion_tag_group_cell(
                        tag_names,
                        tag_values,
                    )
                    for tag_names in tag_groups
                ],
                htpy.td(".table-cell-fit.text-center")[
                    htpy.div(".d-flex.gap-2.justify-content-center")[
                        _suggestion_music_edit_button(row_index, path),
                        _suggestion_music_delete_button(suggestion_id, path),
                    ]
                ],
            ]
        )
        cards.append(
            htpy.article(".card.mb-3")[
                htpy.div(".card-header")[
                    htpy.div(".align-items-start.d-flex.gap-3.justify-content-between")[
                        _suggestion_music_play_button(suggestion_id, path),
                        htpy.div(".flex-grow-1", style="min-width: 0")[
                            htpy.code(".text-break")[path],
                            _suggestion_music_file_details(
                                size,
                                tags.duration_seconds,
                            ),
                            tags.error
                            and htpy.div(".small.text-danger", role="status")[
                                tags.error
                            ],
                        ],
                        htpy.div(".d-flex.gap-2")[
                            _suggestion_music_edit_button(row_index, path),
                            _suggestion_music_delete_button(suggestion_id, path),
                        ],
                    ]
                ],
                htpy.div(".card-body")[
                    htpy.div(".border-bottom.mb-3.pb-3")[
                        htpy.div(".fw-semibold.mb-2.small.text-secondary")[
                            "Review decision"
                        ],
                        _suggestion_music_review_form(
                            suggestion_id,
                            path,
                            review,
                            "mobile",
                        ),
                    ],
                    [
                        (
                            htpy.div(".border-bottom.mb-3.pb-3")
                            if tag_index < len(ID3_TAG_LABELS) - 1
                            else htpy.div
                        )[
                            htpy.div(".fw-semibold.mb-1.small.text-secondary")[label],
                            _suggestion_tag_values(tag_values[tag_name]),
                        ]
                        for tag_index, (tag_name, label) in enumerate(
                            ID3_TAG_LABELS.items()
                        )
                    ],
                ],
            ]
        )
        modals.append(
            _suggestion_music_tag_modal(
                suggestion_id,
                path,
                row_index,
                tag_values,
            )
        )
    return htpy.div[
        _suggestion_bulk_tag_form(suggestion_id),
        htpy.div(".d-none.d-md-block.mt-3.table-responsive")[
            htpy.table(".align-middle.mb-0.table.table-sm")[htpy.tbody[rows],]
        ],
        htpy.div(".d-md-none.mt-3")[cards],
        modals,
    ]


def suggestion_file_player(suggestion_id: str, path: str) -> str:
    metadata = htpy.strong[
        htpy.i(".bi-music-note-beamed"),
        " ",
        path,
    ]
    return str(
        _music_player(
            metadata,
            flask.url_for(
                "suggestion_file_stream",
                suggestion_id=suggestion_id,
                path=path,
            ),
        )
    )


def suggestion_image_preview_modal(suggestion_id: str, path: str) -> str:
    return str(
        htpy.div("#modal-lg-content.bg-dark.modal-content.text-white")[
            htpy.div(".border-0.modal-header")[
                htpy.h5(".mb-0.modal-title")[path],
                htpy.button(
                    ".btn-close.btn-close-white",
                    aria_label="Close",
                    data_bs_dismiss="modal",
                    type="button",
                ),
            ],
            htpy.div(".modal-body.p-2.text-center")[
                htpy.img(
                    ".img-fluid.suggestion-image-preview",
                    alt=path,
                    src=flask.url_for(
                        "suggestion_file_preview",
                        suggestion_id=suggestion_id,
                        path=path,
                    ),
                )
            ],
        ]
    )


def _suggestion_files_card(
    suggestion_id: str,
    staged_files: tuple[tuple[str, int], ...],
    result: tuple[str, str] | None = None,
    *,
    folder_path: str | None = None,
    music_tags: dict[str, Mp3TagValues] | None = None,
    music_reviews: dict[str, SuggestionFileReview] | None = None,
) -> htpy.Element:
    upload_url = flask.url_for(
        "suggestion_files_upload",
        suggestion_id=suggestion_id,
    )
    upload_before_request = (
        "const bar=document.getElementById('suggestion-files-upload-bar');"
        "const label=document.getElementById('suggestion-files-upload-label');"
        "bar.style.width='0%';"
        "bar.setAttribute('aria-valuenow','0');"
        "bar.textContent='0%';"
        "label.textContent='Uploading files\u2026';"
    )
    upload_progress = (
        "if(!event.detail.total){return;}"
        "const percent=Math.round(event.detail.loaded/event.detail.total*100);"
        "const bar=document.getElementById('suggestion-files-upload-bar');"
        "const label=document.getElementById('suggestion-files-upload-label');"
        "bar.style.width=percent+'%';"
        "bar.setAttribute('aria-valuenow',String(percent));"
        "bar.textContent=percent+'%';"
        "label.textContent=percent>=100"
        "?'Processing files\u2026':'Uploading files\u2026';"
    )
    file_sections = tuple(
        (
            section_id,
            label,
            tuple(
                file
                for file in staged_files
                if _suggestion_file_category(file[0]) == section_id
            ),
        )
        for section_id, label in (
            ("music", "Music"),
            ("images", "Images"),
            ("other-files", "Other files"),
        )
    )
    music_tags = music_tags or {}
    music_reviews = music_reviews or {}
    has_music = any(
        _suggestion_file_category(path) == "music" for path, _ in staged_files
    )
    collapse_id = "suggestion-files-card-body"
    return htpy.div(".card", id="suggestion-files-card")[
        _collapsible_card_header(
            collapse_id,
            "Files",
            htpy.div[
                htpy.h5(".mb-1" if folder_path else ".mb-0")["Files"],
                folder_path
                and htpy.code(".d-block.small.text-break.user-select-all")[folder_path],
            ],
        ),
        htpy.div(f"#{collapse_id}.card-body.collapse.show")[
            result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
            htpy.form(
                {
                    "hx-on:htmx:before-request": upload_before_request,
                    "hx-on:htmx:xhr:progress": upload_progress,
                },
                action=upload_url,
                enctype="multipart/form-data",
                hx_disabled_elt="button",
                hx_encoding="multipart/form-data",
                hx_indicator="#suggestion-files-upload-progress",
                hx_post=upload_url,
                hx_swap="outerHTML",
                hx_target="#suggestion-files-card",
                method="post",
            )[
                htpy.div(".align-items-end.g-2.row")[
                    htpy.div(".col-12.col-sm-auto")[
                        htpy.label(".form-label", for_="suggestion-files")[
                            "Upload files"
                        ],
                        htpy.div(".form-text")["The maximum upload size is 1 GB."],
                        htpy.input(
                            "#suggestion-files.form-control",
                            multiple=True,
                            name="files",
                            required=True,
                            type="file",
                        ),
                    ],
                    htpy.div(".col-auto")[
                        htpy.button(".btn.btn-primary", type="submit")[
                            htpy.i(".bi-upload"), " Upload"
                        ]
                    ],
                ],
                htpy.div(
                    "#suggestion-files-upload-progress.htmx-indicator.mt-3",
                    aria_live="polite",
                    role="status",
                )[
                    htpy.div(".mb-1.small", id="suggestion-files-upload-label")[
                        "Uploading files\u2026"
                    ],
                    htpy.div(
                        ".progress",
                        aria_label="File upload progress",
                    )[
                        htpy.div(
                            "#suggestion-files-upload-bar."
                            "progress-bar.progress-bar-animated.progress-bar-striped",
                            aria_valuemax="100",
                            aria_valuemin="0",
                            aria_valuenow="0",
                            role="progressbar",
                            style="width: 0%",
                        )["0%"]
                    ],
                ],
            ],
            has_music
            and htpy.div(".mt-3")[
                _suggestion_normalize_filenames_button(suggestion_id)
            ],
            [
                _suggestion_file_section(
                    suggestion_id,
                    section_id,
                    label,
                    files,
                    music_tags,
                    music_reviews,
                )
                for section_id, label, files in file_sections
                if files
            ]
            if staged_files
            else htpy.p(".mb-0.mt-3.text-secondary")["No staged files."],
        ],
    ]


def suggestion_files_card(
    suggestion_id: str,
    staged_files: tuple[tuple[str, int], ...],
    result: tuple[str, str] | None = None,
    *,
    folder_path: str | None = None,
    music_tags: dict[str, Mp3TagValues] | None = None,
    music_reviews: dict[str, SuggestionFileReview] | None = None,
) -> str:
    return str(
        _suggestion_files_card(
            suggestion_id,
            staged_files,
            result,
            folder_path=folder_path,
            music_tags=music_tags,
            music_reviews=music_reviews,
        )
    )
