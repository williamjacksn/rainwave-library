import flask
import htpy
import markupsafe

from rainwave_library.models.rainwave import (
    ChannelRootFolder,
    Song,
    channels,
    length_display,
)

from .common import _back_button, _base, _music_player, _user_menu


def _songs_change_channels_target(
    *,
    new_filename: str | None = None,
    error: str | None = None,
) -> htpy.Element:
    return htpy.div(
        "#song-change-channels-target.form-text.mt-3",
        aria_live="polite",
        role="status",
    )[
        htpy.div(".fw-semibold")["Potential new filename"],
        (
            htpy.code(".d-block.text-break.user-select-all")[new_filename]
            if new_filename is not None
            else htpy.span(class_="text-danger" if error else None)[
                error or "Choose a channel root folder to preview the new filename."
            ]
        ),
    ]


def songs_change_channels_target(
    *,
    new_filename: str | None = None,
    error: str | None = None,
) -> str:
    return str(
        _songs_change_channels_target(
            new_filename=new_filename,
            error=error,
        )
    )


def _songs_change_channels_form(
    song: Song,
    *,
    channel_root_folder: str = "",
    new_filename: str | None = None,
    error: str | None = None,
) -> htpy.Element:
    url = flask.url_for("songs_change_channels", song_id=song.id)
    return htpy.form(
        "#song-change-channels-form.modal-content",
        action=url,
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="outerHTML",
        hx_target="this",
        method="post",
    )[
        htpy.div(".modal-header")[
            htpy.h5("#song-change-channels-title.modal-title")["Change channels"],
            htpy.button(
                ".btn-close",
                aria_label="Close",
                data_bs_dismiss="modal",
                type="button",
            ),
        ],
        htpy.div(".modal-body")[
            error and htpy.div(".alert.alert-danger", role="alert")[error],
            htpy.div(".mb-3")[
                htpy.div(".form-label")["Current filename"],
                htpy.code(".d-block.text-break.user-select-all")[song.filename],
            ],
            htpy.label(
                ".form-label",
                for_="song-change-channels-root-folder",
            )["Channel root folder"],
            htpy.select(
                "#song-change-channels-root-folder.form-select",
                hx_get=flask.url_for(
                    "songs_change_channels_target",
                    song_id=song.id,
                ),
                hx_swap="outerHTML",
                hx_target="#song-change-channels-target",
                hx_trigger="change",
                name="channel-root-folder",
                required=True,
            )[
                htpy.option(
                    disabled=True,
                    selected=not channel_root_folder,
                    value="",
                )["Choose a channel root folder"],
                [
                    htpy.option(
                        selected=folder.value == channel_root_folder,
                        value=folder.value,
                    )[f"{folder.label} ({folder.value})"]
                    for folder in ChannelRootFolder
                ],
            ],
            _songs_change_channels_target(
                new_filename=new_filename,
            ),
        ],
        htpy.div(".justify-content-between.modal-footer")[
            htpy.button(
                ".btn.btn-secondary",
                data_bs_dismiss="modal",
                type="button",
            )["Cancel"],
            htpy.button(".btn.btn-primary", type="submit")[
                htpy.i(".bi-arrow-left-right"), " Change channels"
            ],
        ],
    ]


def songs_change_channels_form(
    song: Song,
    *,
    channel_root_folder: str = "",
    new_filename: str | None = None,
    error: str | None = None,
) -> str:
    return str(
        _songs_change_channels_form(
            song,
            channel_root_folder=channel_root_folder,
            new_filename=new_filename,
            error=error,
        )
    )


def _songs_change_channels_modal(song: Song) -> htpy.Element:
    return htpy.div(
        "#song-change-channels-modal.fade.modal",
        aria_hidden="true",
        aria_labelledby="song-change-channels-title",
        tabindex="-1",
    )[
        htpy.div(".modal-dialog.modal-dialog-centered.modal-lg")[
            _songs_change_channels_form(song)
        ]
    ]


def songs_detail(
    song: Song,
    *,
    file_size_bytes: int | None = None,
    audio_bitrate_bps: int | None = None,
) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("songs"), "Songs"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Song details"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.audio(
                    controls=True,
                    preload="metadata",
                    src=flask.url_for("stream_song", song_id=song.id),
                )
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".align-middle.d-block.table")[
                    htpy.tbody[
                        htpy.tr[
                            htpy.th["ID"],
                            htpy.td(".user-select-all")[htpy.code[song.id]],
                        ],
                        htpy.tr[
                            htpy.th["Album"],
                            htpy.td(".user-select-all")[song.album_name],
                        ],
                        htpy.tr[
                            htpy.th["Title"], htpy.td(".user-select-all")[song.title]
                        ],
                        htpy.tr[htpy.th["Artist"], htpy.td[song.artist_tag]],
                        htpy.tr[
                            htpy.th["Categories"],
                            htpy.td[
                                (
                                    htpy.span(".badge.me-1.text-bg-secondary")[cat]
                                    for cat in song.groups
                                )
                            ],
                        ],
                        htpy.tr[
                            htpy.th["Length"],
                            htpy.td[length_display(len(song))],
                        ],
                        htpy.tr[
                            htpy.th["File size"],
                            htpy.td[
                                (
                                    f"{file_size_bytes:,} bytes"
                                    if file_size_bytes is not None
                                    else htpy.span(".text-secondary")["—"]
                                )
                            ],
                        ],
                        htpy.tr[
                            htpy.th["Audio bitrate"],
                            htpy.td[
                                (
                                    f"{audio_bitrate_bps / 1000:.0f} kbps"
                                    if audio_bitrate_bps is not None
                                    else htpy.span(".text-secondary")["—"]
                                )
                            ],
                        ],
                        htpy.tr[
                            htpy.th["Added on"],
                            htpy.td[str(song.added_on)],
                        ],
                        htpy.tr[
                            htpy.th["Rating"],
                            htpy.td[
                                str(song.rating),
                                " (",
                                str(song.raw_rating_avg),
                                " raw)",
                            ],
                        ],
                        htpy.tr[
                            htpy.th["Rating count"],
                            htpy.td[
                                song.rating_count, " (", song.raw_rating_count, " raw)"
                            ],
                        ],
                        htpy.tr[htpy.th["Fave count"], htpy.td[song.fave_count]],
                        htpy.tr[htpy.th["Request count"], htpy.td[song.request_count]],
                        htpy.tr[
                            htpy.th["URL"],
                            htpy.td[
                                song.url
                                and htpy.a(
                                    ".text-decoration-none",
                                    href=song.url,
                                    target="_blank",
                                )[song.url]
                            ],
                        ],
                        htpy.tr[htpy.th["Link text"], htpy.td[song.link_text]],
                        htpy.tr[
                            htpy.th["Filename"],
                            htpy.td(".user-select-all")[
                                htpy.a(
                                    ".text-decoration-none",
                                    href=song.download_url,
                                    title=song.download_hint,
                                )[htpy.code[song.filename]]
                            ],
                        ],
                    ],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.a(
                    ".btn.btn-success.me-1",
                    href=flask.url_for("songs_edit", song_id=song.id),
                )[htpy.i(".bi-pencil"), " Edit tags"],
                htpy.button(
                    ".btn.btn-primary.me-1",
                    data_bs_target="#song-change-channels-modal",
                    data_bs_toggle="modal",
                    type="button",
                )[htpy.i(".bi-arrow-left-right"), " Change channels"],
                htpy.a(
                    ".btn.btn-danger",
                    href=flask.url_for("songs_remove", song_id=song.id),
                )[htpy.i(".bi-file-earmark-break"), " Remove file"],
            ]
        ],
        _songs_change_channels_modal(song),
    ]
    return str(_base(content))


def songs_edit(song: Song) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(
                flask.url_for("songs_detail", song_id=song.id),
                "Song details",
            ),
            _user_menu(),
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Edit tags"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.form(
                    hx_disabled_elt="button",
                    hx_post=flask.url_for("songs_edit", song_id=song.id),
                    hx_swap="outerHTML",
                )[
                    htpy.table(".align-middle.d-block.table")[
                        htpy.tbody[
                            htpy.tr[
                                htpy.th["Filename"],
                                htpy.td[htpy.code[song.filename]],
                            ],
                            htpy.tr[
                                htpy.th[htpy.label(for_="album")["Album"]],
                                htpy.td[
                                    htpy.input(
                                        "#album.form-control",
                                        name="album",
                                        required=True,
                                        type="text",
                                        value=song.album_name,
                                    )
                                ],
                            ],
                            htpy.tr[
                                htpy.th[htpy.label(for_="title")["Title"]],
                                htpy.td[
                                    htpy.input(
                                        "#title.form-control",
                                        name="title",
                                        required=True,
                                        type="text",
                                        value=song.title,
                                    )
                                ],
                            ],
                            htpy.tr[
                                htpy.th[htpy.label(for_="artist")["Artist"]],
                                htpy.td[
                                    htpy.input(
                                        "#artist.form-control",
                                        name="artist",
                                        required=True,
                                        type="text",
                                        value=song.artist_tag,
                                    )
                                ],
                            ],
                            htpy.tr[
                                htpy.th[htpy.label(for_="categories")["Categories"]],
                                htpy.td[
                                    htpy.input(
                                        "#categories.form-control",
                                        name="categories",
                                        type="text",
                                        value=", ".join(song.groups),
                                    )
                                ],
                            ],
                            htpy.tr[
                                htpy.th[htpy.label(for_="url")["URL"]],
                                htpy.td[
                                    htpy.input(
                                        "#url.form-control",
                                        name="url",
                                        type="url",
                                        value=song.url,
                                    )
                                ],
                            ],
                            htpy.tr[
                                htpy.th[htpy.label(for_="link-text")["Link text"]],
                                htpy.td[
                                    htpy.input(
                                        "#link-text.form-control",
                                        name="link-text",
                                        type="text",
                                        value=song.link_text,
                                    )
                                ],
                            ],
                        ]
                    ],
                    htpy.div(".align-items-center.d-flex.g-2.pt-3.row")[
                        htpy.div(".col-auto")[
                            htpy.button(".btn.btn-success", type="submit")[
                                htpy.i(".bi-file-earmark-play"), " Save"
                            ]
                        ],
                        htpy.div(".col-auto")[
                            htpy.span(
                                ".htmx-indicator.spinner-border.spinner-border-sm"
                            )
                        ],
                    ],
                ]
            ]
        ],
    ]
    return str(_base(content))


def songs_edit_result(alert_class: str, edit_result: str) -> str:
    return str(htpy.p(f".alert.{alert_class}")[edit_result])


def songs_index() -> str:
    search_input = htpy.input(
        ".form-control",
        aria_label="Search songs",
        autocapitalize="none",
        hx_indicator="#filters-indicator",
        hx_post=flask.url_for("songs_rows"),
        hx_trigger="search, keyup changed delay:300ms",
        name="q",
        onkeydown="return event.key !== 'Enter'",
        placeholder="Search songs...",
        title="Case-insensitive search for album, title, artist, filename, or URL",
        type="search",
    )
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Songs"]]],
        htpy.form(action=flask.url_for("songs_xlsx"), hx_target="tbody", method="post")[
            htpy.div(".align-items-center.d-flex.g-1.pt-3.row")[
                htpy.div(".col-12.col-sm-auto")[search_input],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-primary.dropdown-toggle",
                            data_bs_toggle="dropdown",
                            title="Sort options",
                            type="button",
                        )[htpy.i(".bi-sort-alpha-down")],
                        htpy.div(".dropdown-menu")[
                            htpy.div(".px-2")[
                                htpy.h6(".dropdown-header")["SORT OPTIONS"],
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#sort-dir-{k}.form-check-input",
                                            checked=(k == "asc"),
                                            hx_indicator="#filters-indicator",
                                            hx_post=flask.url_for("songs_rows"),
                                            name="sort-dir",
                                            type="radio",
                                            value=k,
                                        ),
                                        htpy.label(
                                            ".form-check-label", for_=f"sort-dir-{k}"
                                        )[label],
                                    ]
                                    for k, label in [
                                        ("asc", "Ascending"),
                                        ("desc", "Descending"),
                                    ]
                                ],
                                htpy.hr,
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#sort-col-{i}.form-check-input",
                                            checked=(i == "id"),
                                            hx_indicator="#filters-indicator",
                                            hx_post=flask.url_for("songs_rows"),
                                            name="sort-col",
                                            type="radio",
                                            value=c,
                                        ),
                                        htpy.label(
                                            ".form-check-label", for_=f"sort-col-{i}"
                                        )[label],
                                    ]
                                    for i, c, label in [
                                        ("id", "song_id", "ID"),
                                        ("album", "album_name", "Album"),
                                        ("title", "song_title", "Title"),
                                        ("rating", "song_rating", "Rating"),
                                        ("length", "song_length", "Length"),
                                        ("url", "song_url", "URL"),
                                        ("filename", "song_filename", "Filename"),
                                    ]
                                ],
                            ]
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-primary.dropdown-toggle",
                            data_bs_toggle="dropdown",
                            title="Channel selection",
                            type="button",
                        )[htpy.i(".bi-broadcast-pin")],
                        htpy.div(".dropdown-menu")[
                            htpy.div(".px-2")[
                                htpy.h6(".dropdown-header")["CHANNEL SELECTION"],
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#channels-{i}.form-check-input",
                                            checked=True,
                                            hx_indicator="#filters-indicator",
                                            hx_post=flask.url_for("songs_rows"),
                                            name="channels",
                                            type="checkbox",
                                            value=i,
                                        ),
                                        htpy.label(
                                            ".form-check-label", for_=f"channels-{i}"
                                        )[label],
                                    ]
                                    for i, label in channels.items()
                                    if isinstance(i, int)
                                ],
                            ]
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-primary.dropdown-toggle",
                            data_bs_toggle="dropdown",
                            title="Filter options",
                            type="button",
                        )[htpy.i(".bi-list-check")],
                        htpy.div(".dropdown-menu")[
                            htpy.div(".px-2")[
                                htpy.h6(".dropdown-header")["FILTER OPTIONS"],
                                htpy.div(".form-check")[
                                    htpy.input(
                                        "#include-unrated.form-check-input",
                                        checked=True,
                                        hx_indicator="#filters-indicator",
                                        hx_post=flask.url_for("songs_rows"),
                                        name="include-unrated",
                                        type="checkbox",
                                    ),
                                    htpy.label(
                                        ".form-check-label", for_="include-unrated"
                                    )["Include unrated"],
                                ],
                            ],
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.button(
                        ".btn.btn-primary",
                        href="#",
                        name="page",
                        title="Download XLSX",
                        type="submit",
                        value=0,
                    )[
                        htpy.i(".bi-file-earmark-spreadsheet"),
                        markupsafe.Markup(" &darr;"),
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.span(
                        "#filters-indicator.htmx-indicator.spinner-border.spinner-border-sm.text-primary"
                    )
                ],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".align-middle.table.table-bordered.table-sm.table-striped")[
                    Song.thead,
                    htpy.tbody(hx_post=flask.url_for("songs_rows"), hx_trigger="load")[
                        htpy.tr[
                            htpy.td(".py-3.text-center", colspan=Song.colspan)[
                                htpy.span(
                                    ".htmx-indicator.spinner-border.spinner-border-sm"
                                )
                            ]
                        ]
                    ],
                ]
            ]
        ],
        htpy.div("#audio"),
    ]
    return str(_base(content))


def songs_play(song: Song) -> str:
    metadata = htpy.fragment[
        htpy.strong[htpy.i(".bi-disc"), " ", song.album_name],
        htpy.br,
        htpy.strong[htpy.i(".bi-music-note-beamed"), " ", song.title],
        htpy.br,
        htpy.strong[htpy.i(".bi-person"), " ", song.artist_tag],
    ]
    return str(
        _music_player(
            metadata,
            flask.url_for("stream_song", song_id=song.id),
        )
    )


def songs_remove(song: Song, new_loc: str) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(
                flask.url_for("songs_detail", song_id=song.id),
                "Song details",
            ),
            _user_menu(),
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.h1["Remove file"],
                htpy.p[
                    (
                        "This operation will move the file to the new location "
                        "specified below. The removal reason will be recorded "
                        "in a text file in the same location."
                    )
                ],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.form(method="post")[
                    htpy.table(".align-middle.d-block.table")[
                        htpy.tbody[
                            htpy.tr[
                                htpy.th["Current location"],
                                htpy.td[htpy.code[song.filename]],
                            ],
                            htpy.tr[
                                htpy.th["New location"], htpy.td[htpy.code[new_loc]]
                            ],
                            htpy.tr[
                                htpy.th[htpy.label(for_="reason")["Removal reason"]],
                                htpy.td[
                                    htpy.input(
                                        "#reason.form-control",
                                        name="reason",
                                        required=True,
                                        type="text",
                                    )
                                ],
                            ],
                        ]
                    ],
                    htpy.button(".btn.btn-danger", type="submit")[
                        htpy.i(".bi-file-earmark-break"), " Remove file"
                    ],
                ]
            ]
        ],
    ]
    return str(_base(content))


def songs_rows(songs: list[Song], page: int) -> str:
    trs = []
    for i, song in enumerate(songs):
        if i < 100:
            trs.append(song.tr)
        else:
            trs.append(
                htpy.tr[
                    htpy.td(
                        ".py-3.text-center",
                        colspan=Song.colspan,
                        hx_include="form",
                        hx_post=flask.url_for("songs_rows", page=page + 1),
                        hx_target="closest tr",
                        hx_trigger="revealed",
                        hx_swap="outerHTML",
                    )[htpy.span(".htmx-indicator.spinner-border.spinner-border-sm")]
                ]
            )
    if not trs:
        trs.append(
            htpy.tr(".text-center")[
                htpy.td(colspan=Song.colspan)["No songs matched your criteria."]
            ]
        )
    return str(htpy.fragment[trs])
