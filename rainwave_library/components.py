import flask
import htpy
import markupsafe

import rainwave_library.versions as v
from rainwave_library.models.mp3 import ID3_TAG_LABELS, Mp3TagValues
from rainwave_library.models.rainwave import (
    Album,
    Artist,
    Listener,
    Song,
    channels,
    length_display,
)
from rainwave_library.models.suggestions import (
    Suggestion,
    SuggestionActivity,
    SuggestionDetail,
    SuggestionLink,
)


def _back_button(href: str, label: str) -> htpy.Renderable:
    return htpy.div(".col-auto.me-auto")[
        htpy.a(".btn.btn-outline-primary", href=href)[
            htpy.i(".bi-caret-left-fill"), " ", label
        ]
    ]


def _base(
    content: htpy.Node,
    *,
    body_class: str | None = None,
    stylesheets: tuple[str, ...] = (),
) -> htpy.Renderable:
    return htpy.html(lang="en")[
        htpy.head[
            htpy.title["Rainwave Library"],
            htpy.meta(content="width=device-width, initial-scale=1", name="viewport"),
            _favicon(),
            _bs_stylesheet(),
            _bi_stylesheet(),
            [htpy.link(href=href, rel="stylesheet") for href in stylesheets],
        ],
        htpy.body(class_=body_class)[
            htpy.div(".container-fluid")[
                content,
                htpy.div(".pt-3.row")[htpy.div(".col")[htpy.hr]],
            ],
            _bs_script(),
            _hx_script(),
        ],
    ]


def _bi_stylesheet() -> htpy.Renderable:
    return htpy.link(
        href=f"{_cdn}/bootstrap-icons@{v.bi}/font/bootstrap-icons.min.css",
        rel="stylesheet",
    )


def _bs_script() -> htpy.Renderable:
    return htpy.script(src=f"{_cdn}/bootstrap@{v.bs}/dist/js/bootstrap.bundle.min.js")


def _bs_stylesheet() -> htpy.Renderable:
    return htpy.link(
        href=f"{_cdn}/bootstrap@{v.bs}/dist/css/bootstrap.min.css", rel="stylesheet"
    )


_cdn = "https://cdn.jsdelivr.net/npm"


def _favicon() -> htpy.Renderable:
    return htpy.link(href=flask.url_for("favicon"), rel="icon")


def _hx_script() -> htpy.Renderable:
    return htpy.script(src=f"{_cdn}/htmx.org@{v.hx}/dist/htmx.js")


def _user_menu() -> htpy.Renderable:
    role = flask.session.get("role")
    impersonator = flask.session.get("impersonator")
    avatar_url = flask.g.discord_avatar_url
    display_name = flask.g.discord_display_name
    toggle: htpy.Node = (
        htpy.img(
            ".rounded-circle",
            alt=f"Avatar for {display_name}",
            height=40,
            src=avatar_url,
            width=40,
        )
        if avatar_url
        else htpy.i(".bi-person-circle")
    )
    return htpy.div(".col-auto")[
        htpy.div(".dropdown")[
            htpy.button(
                ".btn.btn-link.pe-0.pt-0", data_bs_toggle="dropdown", type="button"
            )[toggle],
            htpy.ul(".dropdown-menu.dropdown-menu-end")[
                htpy.li[htpy.span(".dropdown-item-text.fw-semibold")[display_name]],
                htpy.li[
                    htpy.span(".dropdown-item-text.text-secondary")[
                        "member (impersonating)" if impersonator else role
                    ]
                ],
                htpy.li[htpy.hr(".dropdown-divider")],
                role == "staff"
                and htpy.li[
                    htpy.a(
                        ".dropdown-item",
                        href=flask.url_for("impersonate_user"),
                    )[htpy.i(".bi-person-bounding-box.me-2"), "Impersonate user"]
                ],
                impersonator
                and htpy.li[
                    htpy.form(
                        action=flask.url_for("impersonate_stop"),
                        method="post",
                    )[
                        htpy.button(
                            ".dropdown-item.text-danger",
                            type="submit",
                        )[htpy.i(".bi-person-x.me-2"), "Stop impersonating"]
                    ]
                ],
                htpy.li[
                    htpy.a(
                        ".dropdown-item",
                        href=flask.url_for("sign_out"),
                    )["Sign out"]
                ],
            ],
        ]
    ]


def albums_detail(album: Album, songs: list[Song]) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("albums"), "Albums"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Album details"]]],
        htpy.div(".pt-3.row")[htpy.div(".col")[album.detail_table]],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.details[
                    htpy.summary[htpy.span(".h4")["Album art"]], album.art_table
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.h4["Songs"],
                htpy.table(".align-middle.table.table-bordered.table-sm.table-striped")[
                    Song.thead, htpy.tbody[(s.tr for s in songs)]
                ],
            ]
        ],
    ]
    return str(_base(content))


def albums_index() -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Albums"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.a(
                    ".btn.btn-outline-primary", href=flask.url_for("albums_missing_art")
                )[htpy.i(".bi-image"), " Missing art"]
            ]
        ],
        htpy.form(hx_target="tbody")[
            htpy.div(".align-items-center.d-flex.g-2.pt-3.row")[
                htpy.div(".col-12.col-sm-auto")[
                    htpy.input(
                        ".form-control",
                        aria_label="Search albums",
                        hx_indicator="#filters-indicator",
                        hx_post=flask.url_for("albums_rows"),
                        hx_trigger="search, keyup changed delay:300ms",
                        name="q",
                        placeholder="Search albums...",
                        title="Cast-insensitive search for album name",
                        type="search",
                    )
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
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
                                            hx_post=flask.url_for("albums_rows"),
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
                                            hx_post=flask.url_for("albums_rows"),
                                            name="sort-col",
                                            type="radio",
                                            value=c,
                                        ),
                                        htpy.label(
                                            ".form-check-label", for_=f"sort-col-{i}"
                                        )[label],
                                    ]
                                    for i, c, label in [
                                        ("id", "album_id", "ID"),
                                        ("album", "album_name", "Album name"),
                                        ("songs", "song_count", "Songs"),
                                    ]
                                ],
                            ]
                        ],
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
                htpy.table(
                    ".align-middle.d-block.table.table-bordered.table-sm.table-striped"
                )[
                    Album.thead,
                    htpy.tbody(hx_post=flask.url_for("albums_rows"), hx_trigger="load")[
                        htpy.tr[
                            htpy.td(".py-3.text-center", colspan=Album.colspan)[
                                htpy.span(
                                    ".htmx-indicator.spinner-border.spinner-border-sm"
                                )
                            ]
                        ]
                    ],
                ]
            ]
        ],
    ]
    return str(_base(content))


def albums_missing_art(albums: list[Album]) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("albums"), "Albums"), _user_menu()
        ],
        htpy.div(".pt-3.row")[
            htpy.h2["Albums missing art"],
            htpy.div(".col")[htpy.ul[(htpy.li[a.library_link] for a in albums)]],
        ],
    ]
    return str(_base(content))


def albums_rows(albums: list[Album], page: int) -> str:
    trs = []
    for i, album in enumerate(albums):
        if i < 100:
            trs.append(album.tr)
        else:
            trs.append(
                htpy.tr[
                    htpy.td(
                        ".py-3.text-center",
                        colspan=Album.colspan,
                        hx_include="form",
                        hx_post=flask.url_for("albums_rows", page=page + 1),
                        hx_swap="outerHTML",
                        hx_target="closest tr",
                        hx_trigger="revealed",
                    )[htpy.span(".htmx-indicator.spinner-border.spinner-border-sm")]
                ]
            )
    if not trs:
        trs.append(
            htpy.tr(".text-center")[
                htpy.td(colspan=Album.colspan)["No albums matched your criteria."]
            ]
        )
    content = htpy.fragment[trs]
    return str(content)


def artists_detail(
    artist: Artist,
    songs: list[Song],
    rename_result: tuple[str, str] | None = None,
) -> str:
    song_rows: list[htpy.Node] = [song.tr for song in songs]
    if not song_rows:
        song_rows.append(
            htpy.tr(".text-center")[
                htpy.td(colspan=Song.colspan)["This artist has no verified songs."]
            ]
        )
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("artists"), "Artists"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Artist details"]]],
        htpy.div(".pt-3.row")[htpy.div(".col")[artist.detail_table]],
        htpy.div(".pt-3.row")[
            htpy.div(".col-12.col-lg-6")[
                htpy.button(
                    ".btn.btn-outline-primary",
                    aria_controls="artist-rename",
                    aria_expanded="true" if rename_result else "false",
                    data_bs_target="#artist-rename",
                    data_bs_toggle="collapse",
                    type="button",
                )[htpy.i(".bi-pencil"), " Rename artist"],
                htpy.div(
                    "#artist-rename.collapse.show"
                    if rename_result
                    else "#artist-rename.collapse"
                )[
                    htpy.div(".card.card-body.mt-2")[
                        rename_result
                        and htpy.div(f".alert.{rename_result[0]}", role="alert")[
                            rename_result[1]
                        ],
                        htpy.form(
                            method="post",
                            onsubmit=(
                                "return window.confirm('Rename this artist in every "
                                "associated song file?')"
                            ),
                        )[
                            htpy.label(".form-label", for_="artist-name")[
                                "Artist name"
                            ],
                            htpy.div(".input-group")[
                                htpy.input(
                                    "#artist-name.form-control",
                                    name="artist-name",
                                    required=True,
                                    type="text",
                                    value=artist.name,
                                ),
                                htpy.button(".btn.btn-outline-primary", type="submit")[
                                    htpy.i(".bi-pencil"), " Rename"
                                ],
                            ],
                            htpy.div(".form-text")[
                                "Updates the artist tag in every verified song file "
                                "for this artist."
                            ],
                        ],
                    ]
                ],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.h4["Songs"],
                htpy.table(".align-middle.table.table-bordered.table-sm.table-striped")[
                    Song.thead, htpy.tbody[song_rows]
                ],
            ]
        ],
        htpy.div("#audio"),
    ]
    return str(_base(content))


def artists_index() -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Artists"]]],
        htpy.form(hx_target="tbody")[
            htpy.div(".align-items-center.d-flex.g-2.pt-3.row")[
                htpy.div(".col-12.col-sm-auto")[
                    htpy.input(
                        ".form-control",
                        aria_label="Search artists",
                        hx_indicator="#filters-indicator",
                        hx_post=flask.url_for("artists_rows"),
                        hx_trigger="search, keyup changed delay:300ms",
                        name="q",
                        placeholder="Search artists...",
                        title="Case-insensitive search for artist name",
                        type="search",
                    )
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
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
                                            f"#sort-dir-{direction}.form-check-input",
                                            checked=(direction == "asc"),
                                            hx_indicator="#filters-indicator",
                                            hx_post=flask.url_for("artists_rows"),
                                            name="sort-dir",
                                            type="radio",
                                            value=direction,
                                        ),
                                        htpy.label(
                                            ".form-check-label",
                                            for_=f"sort-dir-{direction}",
                                        )[label],
                                    ]
                                    for direction, label in [
                                        ("asc", "Ascending"),
                                        ("desc", "Descending"),
                                    ]
                                ],
                                htpy.hr,
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#sort-col-{field}.form-check-input",
                                            checked=(field == "id"),
                                            hx_indicator="#filters-indicator",
                                            hx_post=flask.url_for("artists_rows"),
                                            name="sort-col",
                                            type="radio",
                                            value=column,
                                        ),
                                        htpy.label(
                                            ".form-check-label",
                                            for_=f"sort-col-{field}",
                                        )[label],
                                    ]
                                    for field, column, label in [
                                        ("id", "artist_id", "ID"),
                                        ("artist", "artist_name", "Artist name"),
                                        ("songs", "song_count", "Songs"),
                                    ]
                                ],
                            ]
                        ],
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
                htpy.table(
                    ".align-middle.d-block.table.table-bordered.table-sm.table-striped"
                )[
                    Artist.thead,
                    htpy.tbody(
                        hx_post=flask.url_for("artists_rows"), hx_trigger="load"
                    )[
                        htpy.tr[
                            htpy.td(".py-3.text-center", colspan=Artist.colspan)[
                                htpy.span(
                                    ".htmx-indicator.spinner-border.spinner-border-sm"
                                )
                            ]
                        ]
                    ],
                ]
            ]
        ],
    ]
    return str(_base(content))


def artists_rows(artists: list[Artist], page: int) -> str:
    trs = []
    for index, artist in enumerate(artists):
        if index < 100:
            trs.append(artist.tr)
        else:
            trs.append(
                htpy.tr[
                    htpy.td(
                        ".py-3.text-center",
                        colspan=Artist.colspan,
                        hx_include="form",
                        hx_post=flask.url_for("artists_rows", page=page + 1),
                        hx_swap="outerHTML",
                        hx_target="closest tr",
                        hx_trigger="revealed",
                    )[htpy.span(".htmx-indicator.spinner-border.spinner-border-sm")]
                ]
            )
    if not trs:
        trs.append(
            htpy.tr(".text-center")[
                htpy.td(colspan=Artist.colspan)["No artists matched your criteria."]
            ]
        )
    return str(htpy.fragment[trs])


def bluesky_post() -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Post to Bluesky"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.form(action=flask.url_for("bluesky"), method="post")[
                    htpy.div(".mb-3")[
                        htpy.label(".form-label", for_="body")["Post"],
                        htpy.textarea(
                            "#body.form-control",
                            name="body",
                            required=True,
                            rows=10,
                        ),
                    ],
                    htpy.button(".btn.btn-outline-primary", type="submit")["Post"],
                ]
            ]
        ],
    ]
    return str(_base(content))


def favicon() -> str:
    # https://icons.getbootstrap.com/icons/boombox-fill/
    paths = [
        "M14 0a.5.5 0 0 1 .5.5V2h.5a1 1 0 0 1 1 1v2H0V3a1 1 0 0 1 1-1h12.5V.5A.5.5 0 0 "
        "1 14 0M2 3.5a.5.5 0 1 0 1 0 .5.5 0 0 0-1 0m2 0a.5.5 0 1 0 1 0 .5.5 0 0 0-1 0m7"
        ".5.5a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1m1.5-.5a.5.5 0 1 0 1 0 .5.5 0 0 0-1 0M9.5 3h"
        "-3a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1M6 10.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0m"
        "-1.5.5a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1m7 1a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3m."
        "5-1.5a.5.5 0 1 1-1 0 .5.5 0 0 1 1 0",
        "M0 6h16v8a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm2 4.5a2.5 2.5 0 1 0 5 0 2.5 2.5 0 0 0"
        "-5 0m7 0a2.5 2.5 0 1 0 5 0 2.5 2.5 0 0 0-5 0",
    ]
    content = htpy.svg(
        ".bi.bi-boombox-fill",
        fill="#ff7733",
        height="16",
        viewBox="0 0 16 16",
        width="16",
        xmlns="http://www.w3.org/2000/svg",
    )[(htpy.path(d=p) for p in paths)]
    return str(content)


def get_ocremix_download() -> str:
    content = htpy.tr[
        htpy.th["File saved"],
        htpy.td[
            htpy.a(".btn.btn-outline-success", href=flask.url_for("get_ocremix"))[
                htpy.i(".bi-arrow-counterclockwise"), " Get another"
            ]
        ],
    ]
    return str(content)


def get_ocremix_fetch(ocr_info: dict, categories: list[str]) -> str:
    content = [
        htpy.tr[
            htpy.th["Download from"],
            htpy.td[
                htpy.input(
                    name="download-from",
                    type="hidden",
                    value=ocr_info.get("download_url"),
                ),
                htpy.code[ocr_info.get("download_url")],
            ],
        ],
        htpy.tr[
            htpy.th[htpy.label(for_="album")["Album"]],
            htpy.td[
                htpy.input(
                    "#album.form-control",
                    hx_include="form",
                    hx_indicator="#target-file-indicator",
                    hx_post=flask.url_for("get_ocremix_target_file"),
                    hx_target="#target-file",
                    hx_trigger="keyup changed delay:300ms",
                    name="album",
                    required=True,
                    type="text",
                    value=ocr_info.get("primary_game"),
                )
            ],
        ],
        htpy.tr[
            htpy.th[htpy.label(for_="title")["Title"]],
            htpy.td[
                htpy.input(
                    "#title.form-control",
                    hx_include="form",
                    hx_indicator="#target-file-indicator",
                    hx_post=flask.url_for("get_ocremix_target_file"),
                    hx_target="#target-file",
                    hx_trigger="keyup changed delay:300ms",
                    name="title",
                    required=True,
                    type="text",
                    value=ocr_info.get("title"),
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
                    value=", ".join(a.get("name") for a in ocr_info["artists"]),
                )
            ],
        ],
        htpy.tr[
            htpy.th[htpy.label(for_="url")["URL"]],
            htpy.td[
                htpy.input(
                    "#url.form-control",
                    name="url",
                    type="text",
                    value=ocr_info.get("url"),
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
                    value="Get @ OCR",
                )
            ],
        ],
        htpy.tr[
            htpy.th[htpy.label(for_="categories")["Categories"]],
            htpy.td[
                htpy.input(
                    "#categories.form-control",
                    name="categories",
                    required=True,
                    type="text",
                    value=", ".join(categories),
                )
            ],
        ],
        htpy.tr[
            htpy.th["Target file"],
            htpy.td[
                htpy.code(
                    "#target-file",
                    hx_include="form",
                    hx_indicator="closest td",
                    hx_post=flask.url_for("get_ocremix_target_file"),
                    hx_trigger="load",
                ),
                htpy.span(
                    "#target-file-indicator.htmx-indicator.spinner-border.spinner-border-sm"
                ),
            ],
        ],
        htpy.tr[
            htpy.td,
            htpy.td[
                htpy.a(
                    ".btn.btn-outline-success.me-1", href=flask.url_for("get_ocremix")
                )[htpy.i(".bi-arrow-counterclockwise"), " Start over"],
                htpy.button(
                    ".btn.btn-success.me-2",
                    hx_include="form",
                    hx_indicator="closest td",
                    hx_post=flask.url_for("get_ocremix_download"),
                    hx_swap="outerHTML",
                    hx_target="closest tr",
                    type="button",
                )[htpy.i(".bi-download"), " Download"],
                htpy.span(".htmx-indicator.spinner-border.spinner-border-sm"),
            ],
        ],
    ]
    return str(htpy.fragment[content])


def get_ocremix_start(max_ocr_num: int) -> str:
    tr_ocr_id = htpy.tr[
        htpy.th[htpy.label(for_="ocr-id")["OCR ID"]],
        htpy.td[
            htpy.input(
                "#ocr-id.form-control",
                min=1,
                name="ocr-id",
                step=1,
                type="number",
                value=max_ocr_num + 1,
            )
        ],
    ]
    tr_fetch = htpy.tr[
        htpy.td,
        htpy.td[
            htpy.button(
                ".btn.btn-success.me-2",
                hx_include="form",
                hx_indicator="closest td",
                hx_post=flask.url_for("get_ocremix_fetch"),
                hx_swap="outerHTML",
                hx_target="closest tr",
                type="button",
            )[htpy.i(".bi-search"), " Fetch info"],
            htpy.span(".htmx-indicator.spinner-border.spinner-border-sm"),
        ],
    ]
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["OC ReMix"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.form[
                    htpy.table(".align-middle.d-block.table")[
                        htpy.tbody[tr_ocr_id, tr_fetch]
                    ]
                ]
            ]
        ],
    ]
    return str(_base(content))


def listeners_detail(listener: Listener) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("listeners"), "Listeners"),
            _user_menu(),
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Listener details"]]],
        htpy.div(".pt-3.row")[htpy.div(".col")[listener.detail_table]],
        htpy.div(".pt-3.row")[htpy.div(".col")[listener.edit_btn]],
    ]
    return str(_base(content))


def listeners_edit(listener: Listener) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(
                flask.url_for("listeners_detail", listener_id=listener.id),
                "Listener details",
            ),
            _user_menu(),
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Edit listener"]]],
        htpy.div(".pt-3.row")[htpy.div(".col")[listener.edit_form]],
    ]
    return str(_base(content))


def listeners_index(ranks: list[dict]) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Listeners"]]],
        htpy.form(hx_target="tbody")[
            htpy.div(".align-items-center.d-flex.g-2.pt-3.row")[
                htpy.div(".col-12.col-sm-auto")[
                    htpy.input(
                        ".form-control",
                        aria_label="Search listeners",
                        hx_indicator="#filters-indicator",
                        hx_post=flask.url_for("listeners_rows"),
                        hx_trigger="search, keyup changed delay:300ms",
                        name="q",
                        placeholder="Search listeners...",
                        title="Case-insensitive search for username or Discord ID",
                        type="search",
                    )
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
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
                                            hx_post=flask.url_for("listeners_rows"),
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
                                            hx_post=flask.url_for("listeners_rows"),
                                            name="sort-col",
                                            type="radio",
                                            value=c,
                                        ),
                                        htpy.label(
                                            ".form-check-label", for_=f"sort-col-{i}"
                                        )[label],
                                    ]
                                    for i, c, label in [
                                        ("id", "user_id", "ID"),
                                        ("name", "user_name", "User name"),
                                        ("group", "group_name", "Group"),
                                        ("rank", "rank_title", "Rank"),
                                        ("ratings", "rating_count", "Ratings"),
                                        ("active", "radio_last_active", "Last active"),
                                    ]
                                ],
                            ]
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
                            data_bs_toggle="dropdown",
                            title="Rank selection",
                            type="button",
                        )[htpy.i(".bi-person-badge")],
                        htpy.div(".dropdown-menu")[
                            htpy.div(".px-2")[
                                htpy.h6(".dropdown-header")["RANK SELECTION"],
                                htpy.div(".form-check")[
                                    htpy.input(
                                        "#rank-none.form-check-input",
                                        checked=True,
                                        hx_indicator="#filters-indicator",
                                        hx_post=flask.url_for("listeners_rows"),
                                        name="ranks",
                                        type="checkbox",
                                        value=0,
                                    ),
                                    htpy.label(".form-check-label", for_="rank-none")[
                                        "(no rank)"
                                    ],
                                ],
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#rank-{r.get('rank_id')}.form-check-input",
                                            checked=True,
                                            hx_indicator="#filters-indicator",
                                            hx_post=flask.url_for("listeners_rows"),
                                            name="ranks",
                                            type="checkbox",
                                            value=r.get("rank_id"),
                                        ),
                                        htpy.label(
                                            ".form-check-label.text-nowrap",
                                            for_=f"rank-{r.get('rank_id')}",
                                        )[r.get("rank_title")],
                                    ]
                                    for r in ranks
                                ],
                            ]
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.span(
                        "#filters-indicator.htmx-indicator.spinner-border.spinner-border-sm"
                    )
                ],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(
                    ".align-middle.d-block.table.table-bordered.table-sm.table-striped"
                )[
                    Listener.thead,
                    htpy.tbody(
                        hx_post=flask.url_for("listeners_rows"), hx_trigger="load"
                    )[
                        htpy.tr[
                            htpy.td(".py-3.text-center", colspan=Listener.colspan)[
                                htpy.span(
                                    ".htmx-indicator.spinner-border.spinner-border-sm"
                                )
                            ]
                        ]
                    ],
                ]
            ]
        ],
    ]
    return str(_base(content))


def listeners_rows(listeners: list[Listener], page: int) -> str:
    trs = []
    for i, listener in enumerate(listeners):
        if i < 100:
            trs.append(listener.tr)
        else:
            trs.append(
                htpy.tr[
                    htpy.td(
                        ".py-3.text-center",
                        colspan=Listener.colspan,
                        hx_include="form",
                        hx_post=flask.url_for("listeners_rows", page=page + 1),
                        hx_swap="outerHTML",
                        hx_target="closest tr",
                        hx_trigger="revealed",
                    )[htpy.span(".htmx-indicator.spinner-border.spinner-border-sm")]
                ]
            )
    if not trs:
        trs.append(
            htpy.tr(".text-center")[
                htpy.td(colspan=Listener.colspan)["No listeners matched your criteria."]
            ]
        )
    content = htpy.fragment[trs]
    return str(content)


def sign_in() -> str:
    content = htpy.main(".align-items-center.d-flex.min-vh-100.py-4.sign-in-page")[
        htpy.div(".container")[
            htpy.div(".justify-content-center.row")[
                htpy.div(".col-12.col-lg-5.col-md-7.col-sm-9.col-xl-4")[
                    htpy.section(".card.rounded-4.shadow-sm", aria_label="Sign in")[
                        htpy.div(".card-body.p-4.p-sm-5.text-center")[
                            htpy.div(
                                ".align-items-center.brand-icon.d-flex.justify-content-center.mb-2.mx-auto.rounded-3",
                                aria_hidden="true",
                            )[htpy.i(".bi-boombox-fill")],
                            htpy.h1(".card-title.fs-2.fw-bold.mb-4")[
                                "Rainwave Library"
                            ],
                            htpy.a(
                                ".align-items-center.btn.btn-primary.d-flex.fw-bold.gap-2.justify-content-center.py-2.w-100",
                                href=flask.url_for("sign_in"),
                            )[
                                htpy.i(".bi-discord.fs-5"),
                                htpy.span["Continue with Discord"],
                            ],
                            htpy.p(".card-text.mb-0.mt-3.small.text-secondary")[
                                "You must be a member of the ",
                                htpy.a(href="https://discord.com/invite/rNCBhSz")[
                                    markupsafe.Markup(
                                        "Rainwave&nbsp;Discord&nbsp;server"
                                    )
                                ],
                                " to use this tool.",
                            ],
                        ]
                    ]
                ]
            ],
        ]
    ]
    return str(
        _base(
            content,
            body_class="sign-in-body",
            stylesheets=(flask.url_for("static", filename="sign-in.css"),),
        )
    )


def impersonate_user(discord_user_id: str = "", error: str | None = None) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Impersonate Discord user"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col-12.col-lg-6.col-xl-4")[
                htpy.div(".card")[
                    htpy.div(".card-body")[
                        error and htpy.div(".alert.alert-danger", role="alert")[error],
                        htpy.form(method="post")[
                            htpy.label(".form-label", for_="discord-user-id")[
                                "Discord user ID"
                            ],
                            htpy.input(
                                "#discord-user-id.form-control",
                                autocomplete="off",
                                autofocus=True,
                                inputmode="numeric",
                                name="discord-user-id",
                                pattern="[0-9]+",
                                required=True,
                                type="text",
                                value=discord_user_id,
                            ),
                            htpy.div(".form-text")[
                                "The session will use member permissions until you "
                                "stop impersonating."
                            ],
                            htpy.button(
                                ".btn.btn-outline-primary.mt-3",
                                type="submit",
                            )[
                                htpy.i(".bi-person-bounding-box"),
                                " Impersonate user",
                            ],
                        ],
                    ]
                ]
            ]
        ],
    ]
    return str(_base(content))


def songs_detail(song: Song) -> str:
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
                    ".btn.btn-outline-success.me-1",
                    href=flask.url_for("songs_edit", song_id=song.id),
                )[htpy.i(".bi-pencil"), " Edit tags"],
                htpy.a(
                    ".btn.btn-outline-danger",
                    href=flask.url_for("songs_remove", song_id=song.id),
                )[htpy.i(".bi-file-earmark-break"), " Remove file"],
            ]
        ],
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
                            htpy.button(".btn.btn-outline-success", type="submit")[
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


def settings_index(
    settings: list[tuple[str, str, bool]],
    *,
    key: str = "",
    value: str = "",
    protected: bool = False,
    result: tuple[str, str] | None = None,
) -> str:
    rows = [
        htpy.tr[
            htpy.td[htpy.code(".user-select-all")[key]],
            htpy.td(".text-break")[
                htpy.span(".badge.text-bg-secondary")["protected"]
                if protected
                else htpy.code(".user-select-all")[value]
            ],
        ]
        for key, value, protected in settings
    ]
    if not rows:
        rows.append(
            htpy.tr[htpy.td(".py-3.text-center", colspan=2)["No settings found."]]
        )
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Application settings"],]],
        htpy.div(".pt-3.row")[
            htpy.div(".col-lg-8")[
                htpy.div(".card")[
                    htpy.div(".card-header")[
                        htpy.h5(".mb-0")["Create or replace a setting"]
                    ],
                    htpy.div(".card-body")[
                        result
                        and htpy.div(f".alert.{result[0]}", role="alert")[result[1]],
                        htpy.p[
                            "Saving a key that already exists replaces its value. "
                            "Application settings are loaded at startup."
                        ],
                        htpy.form(
                            action=flask.url_for("settings"),
                            autocomplete="off",
                            method="post",
                        )[
                            htpy.div(".g-3.row")[
                                htpy.div(".col-md-5")[
                                    htpy.label(".form-label", for_="setting-key")[
                                        "Key"
                                    ],
                                    htpy.input(
                                        "#setting-key.form-control",
                                        name="key",
                                        required=True,
                                        type="text",
                                        value=key,
                                    ),
                                ],
                                htpy.div(".col-md-7")[
                                    htpy.label(".form-label", for_="setting-value")[
                                        "Value"
                                    ],
                                    htpy.input(
                                        "#setting-value.form-control",
                                        name="value",
                                        required=True,
                                        type="text",
                                        value=value,
                                    ),
                                ],
                            ],
                            htpy.div(".form-check.mt-3")[
                                htpy.input(
                                    "#setting-protected.form-check-input",
                                    checked=protected,
                                    name="protected",
                                    type="checkbox",
                                    value="1",
                                ),
                                htpy.label(
                                    ".form-check-label",
                                    for_="setting-protected",
                                )["Protect value"],
                                htpy.div(".form-text")[
                                    "Protected values are hidden on this page. "
                                    "An existing protected setting remains protected."
                                ],
                            ],
                            htpy.button(".btn.btn-primary.mt-3", type="submit")[
                                htpy.i(".bi-floppy"), " Save setting"
                            ],
                        ],
                    ],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(
                    ".align-middle.d-block.table.table-bordered.table-sm.table-striped"
                )[
                    htpy.thead[htpy.tr[htpy.th["Key"], htpy.th["Value"]]],
                    htpy.tbody[rows],
                ]
            ]
        ],
    ]
    return str(_base(content))


def _suggestion_status_badge(status: str) -> htpy.Element:
    status_classes = {
        "new": "text-bg-primary",
        "claimed": "text-bg-warning",
        "accepted": "text-bg-info",
        "uploaded": "text-bg-success",
        "declined": "text-bg-danger",
    }
    return htpy.span(f".badge.{status_classes.get(status, 'text-bg-light')}")[
        status.title()
    ]


def _suggestion_row(suggestion: Suggestion) -> htpy.Element:
    editable = flask.session.get("role") == "staff"
    claimable = (
        editable
        and suggestion.status == "new"
        and not suggestion.claimed_by_name
        and not suggestion.claimed_by_discord_id
    )
    releasable = (
        suggestion.status == "claimed"
        and bool(suggestion.claimed_by_discord_id)
        and suggestion.claimed_by_discord_id == str(flask.g.discord_id or "")
    )
    action = "Edit" if editable else "View details for"
    action_title = "Edit suggestion" if editable else "View suggestion details"
    kind_label = Suggestion.kind_labels.get(suggestion.kind, suggestion.kind)
    return htpy.tr()[
        htpy.td(".text-center.text-nowrap")[
            htpy.a(
                ".text-decoration-none",
                aria_label=f"{action} {suggestion.title}",
                href="#",
                hx_get=flask.url_for("suggestion_details", suggestion_id=suggestion.id),
                hx_swap="outerHTML",
                hx_target="closest tr",
                title=action_title,
            )[htpy.i(".bi-pencil" if editable else ".bi-eye")],
        ],
        htpy.td(".d-table-cell.d-md-none")[
            htpy.div(".fw-semibold.text-break")[suggestion.title],
            htpy.div(".d-flex.flex-wrap.gap-1.mt-1")[
                _suggestion_status_badge(suggestion.status),
            ],
            htpy.div(".small.mt-2")[
                htpy.strong["Type: "],
                kind_label,
            ],
            htpy.div(".small.mt-2")[
                htpy.strong["Channels: "],
                [
                    htpy.span(".badge.border.me-1.text-bg-light.text-dark")[
                        channels.get(channel_id, str(channel_id))
                    ]
                    for channel_id in suggestion.channel_ids
                ]
                or htpy.span(".text-secondary")["—"],
            ],
            htpy.div(".small.mt-1")[
                htpy.strong["Suggested by: "],
                suggestion.requester_name or htpy.span(".text-secondary")["—"],
                suggestion.requester_discord_id
                and htpy.i(
                    ".bi-discord.ms-1",
                    title=f"Discord user {suggestion.requester_discord_id}",
                ),
            ],
            suggestion.requested_at
            and htpy.div(".small.mt-1")[
                htpy.strong["Suggested at: "], suggestion.requested_at[:10]
            ],
            (suggestion.claimed_by_name or claimable or releasable)
            and htpy.div(".small.mt-1")[
                htpy.strong["Claimed by: "],
                suggestion.claimed_by_name,
                suggestion.claimed_by_discord_id
                and htpy.i(
                    ".bi-discord.ms-1",
                    title=f"Discord user {suggestion.claimed_by_discord_id}",
                ),
                claimable
                and htpy.button(
                    ".btn.btn-link.ms-1.p-0.text-decoration-none",
                    aria_label=f"Claim {suggestion.title}",
                    hx_disabled_elt="this",
                    hx_post=flask.url_for(
                        "suggestion_claim", suggestion_id=suggestion.id
                    ),
                    hx_swap="outerHTML",
                    hx_target="closest tr",
                    title="Claim suggestion",
                    type="button",
                )[htpy.i(".bi-person-check")],
                releasable
                and htpy.button(
                    ".btn.btn-link.ms-1.p-0.text-danger.text-decoration-none",
                    aria_label=f"Release claim on {suggestion.title}",
                    hx_disabled_elt="this",
                    hx_post=flask.url_for(
                        "suggestion_release", suggestion_id=suggestion.id
                    ),
                    hx_swap="outerHTML",
                    hx_target="closest tr",
                    title="Release claim",
                    type="button",
                )[htpy.i(".bi-person-dash")],
            ],
        ],
        htpy.td(".d-none.d-md-table-cell")[_suggestion_status_badge(suggestion.status)],
        htpy.td(".d-none.d-md-table-cell")[
            [
                htpy.span(".badge.border.me-1.text-bg-light.text-dark")[
                    channels.get(channel_id, str(channel_id))
                ]
                for channel_id in suggestion.channel_ids
            ]
            or htpy.span(".text-secondary")["—"]
        ],
        htpy.td(".d-none.d-md-table-cell")[htpy.div(".fw-semibold")[suggestion.title],],
        htpy.td(".d-none.d-md-table-cell.text-nowrap")[kind_label],
        htpy.td(".d-none.d-md-table-cell.text-nowrap")[
            suggestion.requester_name or htpy.span(".text-secondary")["—"],
            suggestion.requester_discord_id
            and htpy.i(
                ".bi-discord.ms-1",
                title=f"Discord user {suggestion.requester_discord_id}",
            ),
        ],
        htpy.td(".d-none.d-md-table-cell.text-nowrap")[
            suggestion.requested_at[:10]
            if suggestion.requested_at
            else htpy.span(".text-secondary")["—"]
        ],
        htpy.td(".d-none.d-md-table-cell.text-nowrap")[
            suggestion.claimed_by_name
            or (not claimable and htpy.span(".text-secondary")["—"]),
            suggestion.claimed_by_discord_id
            and htpy.i(
                ".bi-discord.ms-1",
                title=f"Discord user {suggestion.claimed_by_discord_id}",
            ),
            claimable
            and htpy.button(
                ".btn.btn-link.p-0.text-decoration-none",
                aria_label=f"Claim {suggestion.title}",
                hx_disabled_elt="this",
                hx_post=flask.url_for("suggestion_claim", suggestion_id=suggestion.id),
                hx_swap="outerHTML",
                hx_target="closest tr",
                title="Claim suggestion",
                type="button",
            )[htpy.i(".bi-person-check")],
            releasable
            and htpy.button(
                ".btn.btn-link.ms-1.p-0.text-danger.text-decoration-none",
                aria_label=f"Release claim on {suggestion.title}",
                hx_disabled_elt="this",
                hx_post=flask.url_for(
                    "suggestion_release", suggestion_id=suggestion.id
                ),
                hx_swap="outerHTML",
                hx_target="closest tr",
                title="Release claim",
                type="button",
            )[htpy.i(".bi-person-dash")],
        ],
    ]


def suggestion_row(suggestion: Suggestion) -> str:
    return str(_suggestion_row(suggestion))


def _suggestion_value(value: str | int | float | None) -> htpy.Node:
    if value is None or value == "":
        return htpy.span(".text-secondary")["—"]
    return str(value)


def _suggestion_detail_table(
    rows: list[tuple[str, htpy.Node]],
) -> htpy.Element:
    return htpy.table(".table.table-sm")[
        htpy.tbody[
            [
                htpy.tr[
                    htpy.th(".text-nowrap", scope="row")[label],
                    htpy.td(".text-break")[display_value],
                ]
                for label, display_value in rows
            ]
        ]
    ]


def _suggestion_edit_requester_discord_id_field(
    requester_discord_id: str = "",
) -> htpy.VoidElement:
    return htpy.input(
        "#requester-discord-id.form-control",
        name="requester-discord-id",
        type="text",
        value=requester_discord_id,
    )


def suggestion_edit_requester_discord_id_field(
    requester_discord_id: str = "",
) -> str:
    return str(
        _suggestion_edit_requester_discord_id_field(requester_discord_id),
    )


def _suggestion_edit_form(
    suggestion: SuggestionDetail,
    edit_result: tuple[str, str] | None,
) -> htpy.Element:
    rainwave_channels = [
        (channel_id, label)
        for channel_id, label in channels.items()
        if isinstance(channel_id, int) and channel_id in range(1, 7)
    ]
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=flask.url_for("suggestion_update", suggestion_id=suggestion.id),
        hx_swap="outerHTML",
        hx_target="closest tr",
    )[
        edit_result
        and htpy.div(f".alert.{edit_result[0]}", role="alert")[edit_result[1]],
        htpy.div(".g-3.row")[
            htpy.div(".col-12.small.text-secondary")[
                "Suggestion ID: ",
                htpy.a(
                    href=flask.url_for(
                        "suggestion_page",
                        suggestion_id=suggestion.id,
                    )
                )[htpy.code[suggestion.id]],
            ],
            htpy.div(".col-12")[
                htpy.label(".form-label", for_="title")["Title"],
                htpy.input(
                    "#title.form-control",
                    name="title",
                    required=True,
                    type="text",
                    value=suggestion.title,
                ),
            ],
            htpy.div(".col-12.col-md-6")[
                htpy.label(".form-label", for_="kind")["Suggestion type"],
                htpy.select("#kind.form-select", name="kind")[
                    [
                        htpy.option(
                            selected=kind == suggestion.kind,
                            value=kind,
                        )[Suggestion.kind_labels[kind]]
                        for kind in Suggestion.kinds
                    ]
                ],
            ],
            htpy.div(".col-12.col-md-6")[
                htpy.label(".form-label", for_="status")["Status"],
                htpy.select("#status.form-select", name="status")[
                    [
                        htpy.option(
                            selected=status == suggestion.status,
                            value=status,
                        )[status.title()]
                        for status in Suggestion.statuses
                    ]
                ],
            ],
            htpy.div(".col-12")[
                htpy.label(".form-label", for_="description")["Description"],
                htpy.textarea(
                    "#description.form-control",
                    name="description",
                    rows=6,
                )[suggestion.description],
            ],
            htpy.div(".col-12.col-lg-4")[
                htpy.label(".form-label", for_="requester-name")["Suggested by"],
                htpy.input(
                    "#requester-name.form-control",
                    hx_get=flask.url_for(
                        "suggestion_staff_requester_discord_id",
                        target="edit",
                    ),
                    hx_include="this",
                    hx_swap="outerHTML",
                    hx_sync="this:replace",
                    hx_target="#requester-discord-id",
                    hx_trigger="input changed delay:300ms",
                    name="requester-name",
                    type="text",
                    value=suggestion.requester_name or "",
                ),
            ],
            htpy.div(".col-12.col-lg-4")[
                htpy.label(".form-label", for_="requester-discord-id")[
                    "Suggested by Discord ID"
                ],
                _suggestion_edit_requester_discord_id_field(
                    suggestion.requester_discord_id or ""
                ),
            ],
            htpy.div(".col-12.col-lg-4")[
                htpy.label(".form-label", for_="requested-at")["Suggested at"],
                htpy.input(
                    "#requested-at.form-control",
                    name="requested-at",
                    type="text",
                    value=suggestion.requested_at or "",
                ),
            ],
        ],
        htpy.div(".g-3.mt-4.row")[
            htpy.div(".col-12.col-lg-7")[
                htpy.div(".form-label")["Channels"],
                htpy.div(".d-flex.flex-wrap.gap-3")[
                    [
                        htpy.div(".form-check")[
                            htpy.input(
                                f"#channel-{channel_id}.form-check-input",
                                checked=channel_id in suggestion.channel_ids,
                                name="channels",
                                type="checkbox",
                                value=channel_id,
                            ),
                            htpy.label(
                                ".form-check-label", for_=f"channel-{channel_id}"
                            )[label],
                        ]
                        for channel_id, label in rainwave_channels
                    ]
                ],
            ],
            htpy.div(".col-12.col-lg-5")[
                htpy.label(".form-label", for_="primary-channel")["Primary channel"],
                htpy.select("#primary-channel.form-select", name="primary-channel")[
                    htpy.option(value="")["None"],
                    [
                        htpy.option(
                            selected=channel_id == suggestion.primary_channel_id,
                            value=channel_id,
                        )[label]
                        for channel_id, label in rainwave_channels
                    ],
                ],
                htpy.div(".form-text")[
                    "The primary channel is automatically included above."
                ],
            ],
        ],
        htpy.div(".d-flex.gap-2.justify-content-between.mt-3")[
            htpy.button(".btn.btn-outline-success.btn-sm", type="submit")[
                htpy.i(".bi-file-earmark-play"), " Save suggestion"
            ],
            htpy.button(
                ".btn.btn-outline-danger.btn-sm",
                hx_confirm=(
                    f'Delete the suggestion "{suggestion.title}"? '
                    "This cannot be undone."
                ),
                hx_delete=flask.url_for(
                    "suggestion_delete", suggestion_id=suggestion.id
                ),
                hx_disabled_elt="this",
                hx_swap="delete",
                hx_target="closest tr",
                type="button",
            )[htpy.i(".bi-trash"), " Delete suggestion"],
        ],
    ]


def _suggestion_activity_actor(activity: SuggestionActivity) -> htpy.Element:
    name = activity.actor_name or "—"
    if activity.actor_discord_id:
        return htpy.strong(title=f"Discord user {activity.actor_discord_id}")[name]
    if activity.trello_member_id:
        return htpy.strong(title=f"Trello member {activity.trello_member_id}")[name]
    return htpy.strong[name]


def _suggestion_activity_details(activity: SuggestionActivity) -> htpy.Node:
    details: list[htpy.Node] = []
    if activity.body:
        details.append(
            htpy.div(style="white-space: pre-wrap")[activity.body],
        )
    if activity.old_value is not None or activity.new_value is not None:
        change = htpy.div(".mt-2") if details else htpy.div
        details.append(
            change[
                _suggestion_value(activity.old_value),
                " → ",
                _suggestion_value(activity.new_value),
            ]
        )
    if not details:
        return None

    details_length = sum(
        len(value or "")
        for value in (activity.body, activity.old_value, activity.new_value)
    )
    if details_length > 300:
        return htpy.details(".mt-2")[
            htpy.summary["Show details"],
            htpy.div(".mt-2")[details],
        ]
    return htpy.div(".mt-2")[details]


def _suggestion_activity_item(activity: SuggestionActivity) -> htpy.Element:
    return htpy.div(".list-group-item")[
        htpy.div(".d-flex.flex-wrap.gap-2.justify-content-between")[
            htpy.span[
                _suggestion_activity_actor(activity),
                " ",
                activity.type.replace("-", " "),
            ],
            htpy.span(".small.text-secondary")[
                activity.created_at,
                " · ",
                htpy.code[activity.id],
            ],
        ],
        _suggestion_activity_details(activity),
        activity.trello_action_id
        and htpy.div(".small.text-secondary")[
            "Trello action: ",
            htpy.code[activity.trello_action_id],
        ],
    ]


def _suggestion_comment_button(suggestion_id: str) -> htpy.Element:
    return htpy.button(
        ".btn.btn-outline-primary.btn-sm",
        hx_get=flask.url_for("suggestion_comment", suggestion_id=suggestion_id),
        hx_swap="innerHTML",
        hx_target=f"#suggestion-comment-{suggestion_id}",
        type="button",
    )[htpy.i(".bi-chat-left-text"), " Add a comment"]


def suggestion_comment_button(suggestion_id: str) -> str:
    return str(_suggestion_comment_button(suggestion_id))


def _suggestion_comment_form(
    suggestion_id: str,
    body: str = "",
    error: str | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_comment", suggestion_id=suggestion_id)
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="outerHTML",
        hx_target=f"#suggestion-activity-{suggestion_id}",
    )[
        error and htpy.div(".alert.alert-danger.py-2", role="alert")[error],
        htpy.textarea(
            ".form-control",
            aria_label="Comment",
            name="body",
            required=True,
            rows=3,
        )[body],
        htpy.div(".d-flex.gap-2.mt-2")[
            htpy.button(".btn.btn-outline-success.btn-sm", type="submit")[
                htpy.i(".bi-send"), " Save comment"
            ],
            htpy.button(
                ".btn.btn-outline-secondary.btn-sm",
                hx_get=flask.url_for(
                    "suggestion_comment", suggestion_id=suggestion_id, close=1
                ),
                hx_swap="innerHTML",
                hx_target=f"#suggestion-comment-{suggestion_id}",
                type="button",
            )["Cancel"],
        ],
    ]


def suggestion_comment_form(
    suggestion_id: str,
    body: str = "",
    error: str | None = None,
) -> str:
    return str(_suggestion_comment_form(suggestion_id, body, error))


def _suggestion_activity_block(
    suggestion: SuggestionDetail,
    *,
    comments_only: bool = False,
) -> htpy.Element:
    activity_url = flask.url_for(
        "suggestion_activity",
        suggestion_id=suggestion.id,
        comments_only="1",
    )
    if comments_only:
        activity_url = flask.url_for(
            "suggestion_activity",
            suggestion_id=suggestion.id,
        )
    activities = (
        tuple(
            activity for activity in suggestion.activities if activity.type == "comment"
        )
        if comments_only
        else suggestion.activities
    )
    return htpy.div(id=f"suggestion-activity-{suggestion.id}")[
        htpy.div(".d-flex.flex-wrap.gap-2.mb-3")[
            htpy.div(id=f"suggestion-comment-{suggestion.id}")[
                _suggestion_comment_button(suggestion.id)
            ],
            htpy.button(
                ".btn.btn-outline-primary.btn-sm",
                hx_disabled_elt="this",
                hx_get=activity_url,
                hx_swap="outerHTML",
                hx_target=f"#suggestion-activity-{suggestion.id}",
                type="button",
            )[
                htpy.i(".bi-chat-square-text"),
                " Show all activity" if comments_only else " Show only comments",
            ],
        ],
        htpy.div(".list-group")[
            [_suggestion_activity_item(activity) for activity in activities]
        ]
        if activities
        else htpy.p(".text-secondary")[
            "No comments." if comments_only else "No activity."
        ],
    ]


def suggestion_activity_block(
    suggestion: SuggestionDetail,
    *,
    comments_only: bool = False,
) -> str:
    return str(_suggestion_activity_block(suggestion, comments_only=comments_only))


def _suggestion_link_item(
    link: SuggestionLink,
    suggestion_id: str,
    *,
    deletable: bool,
) -> htpy.Element:
    return htpy.div(".list-group-item")[
        htpy.div(".align-items-start.d-flex.gap-2.justify-content-between")[
            htpy.a(
                ".text-break",
                href=link.url,
                rel="noopener",
                target="_blank",
            )[
                link.label or link.url,
                " ",
                htpy.i(".bi-box-arrow-up-right"),
            ],
            htpy.div(".align-items-center.d-flex.gap-2")[
                htpy.span(".badge.text-bg-secondary")[link.type],
                deletable
                and htpy.button(
                    ".btn.btn-link.p-0.text-danger",
                    aria_label=f"Delete {link.label or link.url}",
                    hx_confirm=f'Delete the link "{link.label or link.url}"?',
                    hx_delete=flask.url_for(
                        "suggestion_link_delete",
                        suggestion_id=suggestion_id,
                        link_id=link.id,
                    ),
                    hx_disabled_elt="this",
                    hx_swap="delete",
                    hx_target="closest .list-group-item",
                    title="Delete link",
                    type="button",
                )[htpy.i(".bi-trash")],
            ],
        ],
        htpy.div(".small.text-secondary")[
            link.label and [link.url, htpy.br],
            "ID: ",
            htpy.code[link.id],
            link.trello_attachment_id
            and [
                " · Trello attachment: ",
                htpy.code[link.trello_attachment_id],
            ],
        ],
    ]


def _suggestion_link_button(suggestion_id: str) -> htpy.Element:
    return htpy.button(
        ".btn.btn-outline-primary.btn-sm",
        hx_get=flask.url_for("suggestion_link", suggestion_id=suggestion_id),
        hx_swap="innerHTML",
        hx_target=f"#suggestion-add-link-{suggestion_id}",
        type="button",
    )[htpy.i(".bi-link-45deg"), " Add a link"]


def suggestion_link_button(suggestion_id: str) -> str:
    return str(_suggestion_link_button(suggestion_id))


def _suggestion_link_form(
    suggestion_id: str,
    url: str = "",
    label: str = "",
    error: str | None = None,
) -> htpy.Element:
    post_url = flask.url_for("suggestion_link", suggestion_id=suggestion_id)
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=post_url,
        hx_swap="outerHTML",
        hx_target=f"#suggestion-links-{suggestion_id}",
    )[
        error and htpy.div(".alert.alert-danger.py-2", role="alert")[error],
        htpy.div(".g-2.row")[
            htpy.div(".col-12.col-sm-6")[
                htpy.input(
                    ".form-control",
                    aria_label="Link URL",
                    name="url",
                    placeholder="https://example.com",
                    required=True,
                    type="url",
                    value=url,
                ),
            ],
            htpy.div(".col")[
                htpy.input(
                    ".form-control",
                    aria_label="Link label",
                    name="label",
                    placeholder="Label",
                    type="text",
                    value=label,
                ),
            ],
        ],
        htpy.div(".d-flex.gap-2.mt-2")[
            htpy.button(".btn.btn-outline-success.btn-sm", type="submit")[
                htpy.i(".bi-plus-lg"), " Save link"
            ],
            htpy.button(
                ".btn.btn-outline-secondary.btn-sm",
                hx_get=flask.url_for(
                    "suggestion_link", suggestion_id=suggestion_id, close=1
                ),
                hx_swap="innerHTML",
                hx_target=f"#suggestion-add-link-{suggestion_id}",
                type="button",
            )["Cancel"],
        ],
    ]


def suggestion_link_form(
    suggestion_id: str,
    url: str = "",
    label: str = "",
    error: str | None = None,
) -> str:
    return str(_suggestion_link_form(suggestion_id, url, label, error))


def _suggestion_links_block(suggestion: SuggestionDetail) -> htpy.Element:
    is_owner = bool(suggestion.requester_discord_id) and (
        suggestion.requester_discord_id == str(flask.g.discord_id or "")
    )
    is_staff = flask.session.get("role") == "staff"
    can_add_link = is_staff or (
        is_owner and suggestion.status in Suggestion.owner_editable_statuses
    )
    can_delete_link = is_staff or (
        is_owner and suggestion.status in Suggestion.owner_editable_statuses
    )
    return htpy.div(id=f"suggestion-links-{suggestion.id}")[
        can_add_link
        and htpy.div(".mb-3", id=f"suggestion-add-link-{suggestion.id}")[
            _suggestion_link_button(suggestion.id)
        ],
        htpy.div(".list-group")[
            [
                _suggestion_link_item(
                    link,
                    suggestion.id,
                    deletable=can_delete_link,
                )
                for link in suggestion.links
            ]
        ]
        if suggestion.links
        else htpy.p(".text-secondary")["No links."],
    ]


def suggestion_links_block(suggestion: SuggestionDetail) -> str:
    return str(_suggestion_links_block(suggestion))


def _suggestion_description_block(
    suggestion: SuggestionDetail,
    *,
    editable: bool,
) -> htpy.Element:
    return htpy.div(".mt-3", id=f"suggestion-description-{suggestion.id}")[
        htpy.div(".align-items-center.d-flex.gap-2.mb-2")[
            htpy.h6(".mb-0")["Description"],
            editable
            and htpy.button(
                ".btn.btn-link.p-0.text-decoration-none",
                aria_label=f"Edit the description for {suggestion.title}",
                hx_get=flask.url_for(
                    "suggestion_description", suggestion_id=suggestion.id
                ),
                hx_swap="outerHTML",
                hx_target=f"#suggestion-description-{suggestion.id}",
                title="Edit description",
                type="button",
            )[htpy.i(".bi-pencil")],
        ],
        htpy.div(
            ".bg-body-tertiary.border.p-2.rounded",
            style="white-space: pre-wrap",
        )[_suggestion_value(suggestion.description)],
    ]


def suggestion_description_block(
    suggestion: SuggestionDetail,
    *,
    editable: bool,
) -> str:
    return str(_suggestion_description_block(suggestion, editable=editable))


def _suggestion_description_form(
    suggestion: SuggestionDetail,
    *,
    description: str | None = None,
    error: str | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_description", suggestion_id=suggestion.id)
    return htpy.div(".mt-3", id=f"suggestion-description-{suggestion.id}")[
        htpy.h6["Description"],
        htpy.form(
            hx_disabled_elt="button",
            hx_post=url,
            hx_swap="outerHTML",
            hx_target=f"#suggestion-description-{suggestion.id}",
        )[
            error and htpy.div(".alert.alert-danger.py-2", role="alert")[error],
            htpy.textarea(
                ".form-control",
                name="description",
                required=True,
                rows=6,
            )[suggestion.description if description is None else description],
            htpy.div(".d-flex.gap-2.mt-2")[
                htpy.button(".btn.btn-outline-success.btn-sm", type="submit")[
                    htpy.i(".bi-file-earmark-play"), " Save description"
                ],
                htpy.button(
                    ".btn.btn-outline-secondary.btn-sm",
                    hx_get=f"{url}?close=1",
                    hx_swap="outerHTML",
                    hx_target=f"#suggestion-description-{suggestion.id}",
                    type="button",
                )["Cancel"],
            ],
        ],
    ]


def suggestion_description_form(
    suggestion: SuggestionDetail,
    *,
    description: str | None = None,
    error: str | None = None,
) -> str:
    return str(
        _suggestion_description_form(
            suggestion,
            description=description,
            error=error,
        )
    )


def _music_player(metadata: htpy.Node, source_url: str) -> htpy.Element:
    return htpy.div(
        ".bottom-0.fade.m-1.position-fixed.show.start-50.toast.translate-middle-x"
    )[
        htpy.div(".toast-header")[
            htpy.div(".me-auto")["Music player"],
            htpy.button(
                ".btn-close",
                data_bs_dismiss="toast",
                hx_get=flask.url_for("nothing"),
                hx_target="#audio",
                type="button",
            ),
        ],
        htpy.div(".toast-body")[
            htpy.div("#audio-metadata.pb-1")[metadata],
            htpy.audio(
                autoplay=True,
                controls=True,
                preload="metadata",
                src=source_url,
            ),
        ],
    ]


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
                data_bs_target="#suggestion-image-preview-modal",
                data_bs_toggle="modal",
                data_preview_name=path,
                data_preview_url=flask.url_for(
                    "suggestion_file_preview",
                    suggestion_id=suggestion_id,
                    path=path,
                ),
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
) -> htpy.Element:
    heading_id = f"suggestion-files-{section_id}-heading"
    return htpy.section(".mt-3", aria_labelledby=heading_id)[
        htpy.h6(".mb-0.py-2.text-secondary", id=heading_id)[label],
        _suggestion_music_file_table(suggestion_id, files, music_tags)
        if section_id == "music"
        else htpy.div(".list-group.list-group-flush")[
            [_suggestion_file_item(suggestion_id, path, size) for path, size in files]
        ],
    ]


def _suggestion_tag_values(values: tuple[str, ...]) -> htpy.Node:
    if not values:
        return htpy.span(".text-secondary")["—"]
    return htpy.div[
        [
            htpy.div(".text-break", style="white-space: pre-wrap")[value]
            for value in values
        ]
    ]


def _suggestion_tag_cell(
    suggestion_id: str,
    path: str,
    row_index: int,
    tag_name: str,
    values: tuple[str, ...],
) -> htpy.Element:
    label = ID3_TAG_LABELS[tag_name]
    editor_id = f"suggestion-tag-{row_index}-{tag_name}"
    update_url = flask.url_for(
        "suggestion_file_tags_update",
        suggestion_id=suggestion_id,
    )
    return htpy.td[
        htpy.div(".align-items-start.d-flex.gap-2.justify-content-between")[
            _suggestion_tag_values(values),
            htpy.button(
                ".btn.btn-link.flex-shrink-0.p-0",
                aria_controls=editor_id,
                aria_expanded="false",
                aria_label=f"Edit {label} for {path}",
                data_bs_target=f"#{editor_id}",
                data_bs_toggle="collapse",
                title=f"Edit {label}",
                type="button",
            )[htpy.i(".bi-pencil")],
        ],
        htpy.form(
            f"#{editor_id}.collapse.mt-2",
            action=update_url,
            hx_disabled_elt="button",
            hx_post=update_url,
            hx_swap="outerHTML",
            hx_target="#suggestion-files-card",
            method="post",
        )[
            htpy.input(name="path", type="hidden", value=path),
            htpy.input(name="tag", type="hidden", value=tag_name),
            htpy.textarea(
                ".form-control.form-control-sm",
                aria_label=f"{label} value",
                name="value",
                rows=2,
            )["\n".join(values)],
            htpy.div(".d-flex.gap-2.mt-2")[
                htpy.button(".btn.btn-primary.btn-sm", type="submit")["Save"],
                htpy.button(
                    ".btn.btn-outline-secondary.btn-sm",
                    data_bs_target=f"#{editor_id}",
                    data_bs_toggle="collapse",
                    type="button",
                )["Cancel"],
            ],
            htpy.div(".form-text")["Leave blank to remove this tag."],
        ],
    ]


def _suggestion_bulk_tag_form(suggestion_id: str) -> htpy.Element:
    update_url = flask.url_for(
        "suggestion_file_tags_update",
        suggestion_id=suggestion_id,
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
                htpy.label(".form-label", for_="suggestion-bulk-tag-value")["Value"],
                htpy.textarea(
                    "#suggestion-bulk-tag-value.form-control",
                    name="value",
                    rows=1,
                ),
                htpy.div(".form-text")[
                    "Enter one value per line. Leave blank to remove the tag."
                ],
            ],
            htpy.div(".col-sm-auto")[
                htpy.button(".btn.btn-primary", type="submit")["Apply to all"]
            ],
        ],
    ]


def _suggestion_music_file_table(
    suggestion_id: str,
    files: tuple[tuple[str, int], ...],
    music_tags: dict[str, Mp3TagValues],
) -> htpy.Element:
    headers = tuple(ID3_TAG_LABELS.values())
    rows = []
    for row_index, (path, size) in enumerate(files):
        tags = music_tags.get(path, Mp3TagValues())
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
                htpy.td[
                    htpy.div(".align-items-start.d-flex.gap-2")[
                        htpy.code(".text-break")[path],
                        htpy.button(
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
                    htpy.div(".small.text-secondary")[f"{size:,} bytes"],
                    tags.error
                    and htpy.div(".small.text-danger", role="status")[tags.error],
                ],
                [
                    _suggestion_tag_cell(
                        suggestion_id,
                        path,
                        row_index,
                        tag_name,
                        tag_values[tag_name],
                    )
                    for tag_name in ID3_TAG_LABELS
                ],
                htpy.td(".text-center")[
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
                    )[htpy.i(".bi-trash")]
                ],
            ]
        )
    return htpy.div[
        _suggestion_bulk_tag_form(suggestion_id),
        htpy.div(".mt-3.table-responsive")[
            htpy.table(".align-middle.mb-0.table.table-bordered.table-sm")[
                htpy.thead[
                    htpy.tr[
                        htpy.th(scope="col")["File"],
                        [htpy.th(scope="col")[label] for label in headers],
                        htpy.th(scope="col")[htpy.span(".visually-hidden")["Actions"]],
                    ]
                ],
                htpy.tbody[rows],
            ]
        ],
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


def _suggestion_image_preview_modal() -> htpy.Element:
    preview_script = markupsafe.Markup(
        """
        (() => {
            const modal = document.getElementById(
                "suggestion-image-preview-modal"
            );
            if (!modal) return;
            const image = document.getElementById(
                "suggestion-image-preview-image"
            );
            const title = document.getElementById(
                "suggestion-image-preview-title"
            );
            modal.addEventListener("show.bs.modal", (event) => {
                const trigger = event.relatedTarget;
                if (!(trigger instanceof HTMLElement)) return;
                const name = trigger.dataset.previewName || "Image preview";
                image.src = trigger.dataset.previewUrl || "";
                image.alt = name;
                title.textContent = name;
            });
            modal.addEventListener("hidden.bs.modal", () => {
                image.removeAttribute("src");
                image.alt = "";
            });
        })();
        """
    )
    return htpy.div[
        htpy.div(
            "#suggestion-image-preview-modal.fade.modal",
            aria_hidden="true",
            aria_labelledby="suggestion-image-preview-title",
            tabindex="-1",
        )[
            htpy.div(".modal-dialog.modal-dialog-centered.modal-xl")[
                htpy.div(".bg-dark.modal-content.text-white")[
                    htpy.div(".border-0.modal-header")[
                        htpy.h5("#suggestion-image-preview-title.mb-0.modal-title")[
                            "Image preview"
                        ],
                        htpy.button(
                            ".btn-close.btn-close-white",
                            aria_label="Close",
                            data_bs_dismiss="modal",
                            type="button",
                        ),
                    ],
                    htpy.div(".modal-body.p-2.text-center")[
                        htpy.img(
                            "#suggestion-image-preview-image.img-fluid",
                            alt="",
                            style="max-height: calc(100vh - 9rem)",
                        )
                    ],
                ]
            ]
        ],
        htpy.script[preview_script],
    ]


def _suggestion_files_card(
    suggestion_id: str,
    staged_files: tuple[tuple[str, int], ...],
    result: tuple[str, str] | None = None,
    *,
    folder_path: str | None = None,
    music_tags: dict[str, Mp3TagValues] | None = None,
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
    return htpy.div(".card", id="suggestion-files-card")[
        htpy.div(".card-header")[
            htpy.h5(".mb-1" if folder_path else ".mb-0")["Files"],
            folder_path
            and htpy.code(".d-block.small.text-break.user-select-all")[folder_path],
        ],
        htpy.div(".card-body")[
            result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
            htpy.form(
                action=upload_url,
                enctype="multipart/form-data",
                hx_disabled_elt="button",
                hx_encoding="multipart/form-data",
                hx_indicator="#suggestion-files-upload-progress",
                hx_post=upload_url,
                hx_swap="outerHTML",
                hx_target="#suggestion-files-card",
                method="post",
                **{
                    "hx-on:htmx:before-request": upload_before_request,
                    "hx-on:htmx:xhr:progress": upload_progress,
                },
            )[
                htpy.div(".align-items-end.g-2.row")[
                    htpy.div(".col")[
                        htpy.label(".form-label", for_="suggestion-files")[
                            "Upload files"
                        ],
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
            [
                _suggestion_file_section(
                    suggestion_id,
                    section_id,
                    label,
                    files,
                    music_tags,
                )
                for section_id, label, files in file_sections
                if files
            ]
            if staged_files
            else htpy.p(".mb-0.mt-3.text-secondary")["No staged files."],
        ],
        any(_suggestion_file_category(path) == "images" for path, _ in staged_files)
        and _suggestion_image_preview_modal(),
    ]


def suggestion_files_card(
    suggestion_id: str,
    staged_files: tuple[tuple[str, int], ...],
    result: tuple[str, str] | None = None,
    *,
    folder_path: str | None = None,
    music_tags: dict[str, Mp3TagValues] | None = None,
) -> str:
    return str(
        _suggestion_files_card(
            suggestion_id,
            staged_files,
            result,
            folder_path=folder_path,
            music_tags=music_tags,
        )
    )


def suggestion_page(
    suggestion: SuggestionDetail,
    staged_files: tuple[tuple[str, int], ...] = (),
    *,
    folder_path: str | None = None,
    music_tags: dict[str, Mp3TagValues] | None = None,
) -> str:
    channel_badges: htpy.Node = (
        htpy.fragment[
            [
                htpy.span(".badge.border.me-1.text-bg-light.text-dark")[
                    channels.get(channel_id, str(channel_id))
                ]
                for channel_id in suggestion.channel_ids
            ]
        ]
        if suggestion.channel_ids
        else htpy.span(".text-secondary")["—"]
    )
    summary = _suggestion_detail_table(
        [
            ("Suggestion ID", htpy.code[suggestion.id]),
            ("Status", _suggestion_status_badge(suggestion.status)),
            (
                "Suggestion type",
                Suggestion.kind_labels.get(suggestion.kind, suggestion.kind),
            ),
            ("Channels", channel_badges),
            ("Suggested by", _suggestion_value(suggestion.requester_name)),
        ]
    )
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("suggestions"), "Music suggestions"),
            _user_menu(),
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Suggestion details"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.div(".card")[
                    htpy.div(".card-header")[htpy.h5(".mb-0")[suggestion.title]],
                    htpy.div(".card-body")[summary],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                _suggestion_files_card(
                    suggestion.id,
                    staged_files,
                    folder_path=folder_path,
                    music_tags=music_tags,
                )
            ]
        ],
        htpy.div("#audio"),
    ]
    return str(_base(content))


def suggestion_detail_row(
    suggestion: SuggestionDetail,
    *,
    editable: bool = False,
    edit_result: tuple[str, str] | None = None,
) -> str:
    description_editable = (
        bool(suggestion.requester_discord_id)
        and suggestion.requester_discord_id == str(flask.g.discord_id or "")
        and suggestion.status in Suggestion.owner_editable_statuses
    )
    channel_badges: htpy.Node = (
        htpy.fragment[
            [
                htpy.span(".badge.border.me-1.text-bg-light.text-dark")[
                    channels.get(channel_id, str(channel_id))
                ]
                for channel_id in suggestion.channel_ids
            ]
        ]
        if suggestion.channel_ids
        else htpy.span(".text-secondary")["—"]
    )
    summary = _suggestion_detail_table(
        [
            ("ID", htpy.code[suggestion.id]),
            ("Status", _suggestion_status_badge(suggestion.status)),
            (
                "Suggestion type",
                Suggestion.kind_labels.get(suggestion.kind, suggestion.kind),
            ),
            ("Channels", channel_badges),
        ]
    )
    people_details = _suggestion_detail_table(
        [
            ("Suggested by", _suggestion_value(suggestion.requester_name)),
            ("Claimed by", _suggestion_value(suggestion.claimed_by_name)),
        ]
    )
    timeline_details = _suggestion_detail_table(
        [
            (
                "Suggested at",
                _suggestion_value(
                    suggestion.requested_at[:10]
                    if suggestion.requested_at is not None
                    else None
                ),
            ),
            (
                "Claimed at",
                _suggestion_value(
                    suggestion.claimed_at[:10]
                    if suggestion.claimed_at is not None
                    else None
                ),
            ),
            (
                "Completed at",
                _suggestion_value(
                    suggestion.resolved_at[:10]
                    if suggestion.resolved_at is not None
                    else None
                ),
            ),
        ]
    )
    content = htpy.tr[
        htpy.td(colspan=Suggestion.colspan)[
            htpy.div(".card.my-2")[
                htpy.div(".align-items-center.card-header.d-flex.gap-2")[
                    htpy.button(
                        ".btn.btn-outline-secondary.btn-sm",
                        aria_label="Close suggestion details",
                        hx_get=flask.url_for(
                            "suggestion_row", suggestion_id=suggestion.id
                        ),
                        hx_swap="outerHTML",
                        hx_target="closest tr",
                        title="Close suggestion details",
                        type="button",
                    )[htpy.i(".bi-x-lg")],
                    htpy.h5(".mb-0")[suggestion.title],
                ],
                htpy.div(".card-body")[
                    editable and _suggestion_edit_form(suggestion, edit_result),
                    not editable
                    and htpy.fragment[
                        htpy.div(".g-3.row")[
                            htpy.div(".col-12.col-xl-6")[htpy.h6["Summary"], summary],
                            htpy.div(".col-12.col-xl-6")[
                                htpy.h6["Timeline"], timeline_details
                            ],
                            htpy.div(".col-12.col-xl-6")[
                                htpy.h6["People"], people_details
                            ],
                        ],
                        _suggestion_description_block(
                            suggestion,
                            editable=description_editable,
                        ),
                    ],
                    htpy.h6(".mt-3")["Links"],
                    _suggestion_links_block(suggestion),
                    htpy.h6(".mt-3")["Activity"],
                    _suggestion_activity_block(suggestion),
                ],
            ]
        ]
    ]
    return str(content)


def _suggestion_link_fields(
    url: str = "",
    label: str = "",
    *,
    required: bool = False,
) -> htpy.Element:
    return htpy.div(".align-items-center.g-2.row.suggestion-link-fields")[
        htpy.div(".col-12.col-sm-5")[
            htpy.input(
                ".form-control",
                aria_label="Link URL",
                name="link-url",
                placeholder="https://example.com",
                required=required,
                type="url",
                value=url,
            ),
        ],
        htpy.div(".col")[
            htpy.input(
                ".form-control",
                aria_label="Link label",
                name="link-label",
                placeholder="Label",
                required=required,
                type="text",
                value=label,
            ),
        ],
        htpy.div(".col-auto")[
            htpy.button(
                ".btn.btn-outline-danger",
                aria_label="Remove link",
                hx_get=flask.url_for("suggestion_link_row", close=1),
                hx_swap="outerHTML",
                hx_target="closest .suggestion-link-fields",
                title="Remove link",
                type="button",
            )[htpy.i(".bi-x-lg")],
        ],
    ]


def suggestion_link_fields(*, required: bool = False) -> str:
    return str(_suggestion_link_fields(required=required))


def _suggestion_create_notice(song_count: int, song_count_as_of: str) -> htpy.Element:
    return htpy.div[
        htpy.p[
            "Rainwave is an online radio station run by volunteers. The "
            "extensive Rainwave music library includes:"
        ],
        htpy.ul[
            htpy.li["original video game soundtracks, both modern and classic"],
            htpy.li["original chiptune music not featured in video games"],
            htpy.li[
                "covers and remixes of video game music from a wide variety of "
                "sources, including OverClocked ReMix"
            ],
        ],
        htpy.p[
            "While the Rainwave music library is substantial (over "
            f"{song_count:,} songs as of {song_count_as_of}), we understand "
            "that we may not have your favorite soundtrack or music from "
            "recently released games."
        ],
        htpy.p[
            "You are welcome to make suggestions for new music to be added to "
            "the Rainwave music library. However, as volunteers who maintain "
            "the site and library, we cannot guarantee that new music will be "
            "added."
        ],
        htpy.p[
            "You can also use this form to suggest metadata updates or the "
            "removal of music from the library."
        ],
    ]


def _suggestion_create_form(
    title: str = "",
    description: str = "",
    channel_id: int | None = None,
    links: tuple[tuple[str, str], ...] = (),
    result: tuple[str, str] | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_create")
    rainwave_channels = sorted(
        (
            (value, label)
            for value, label in channels.items()
            if isinstance(value, int) and value in {1, 2, 3, 4, 6}
        ),
        key=lambda item: item[1].casefold(),
    )
    return htpy.form(
        "#new-suggestion-form",
        action=url,
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="outerHTML",
        hx_target="this",
        method="post",
    )[
        result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
        htpy.div(".g-2.row")[
            htpy.div(".col-12.col-sm-8")[
                htpy.label(".form-label", for_="new-suggestion-title")["Title"],
                htpy.input(
                    "#new-suggestion-title.form-control",
                    name="title",
                    required=True,
                    type="text",
                    value=title,
                ),
            ],
            htpy.div(".col-12.col-sm-4")[
                htpy.label(".form-label", for_="new-suggestion-channel")["Channel"],
                htpy.select(
                    "#new-suggestion-channel.form-select",
                    name="channel",
                    required=True,
                )[
                    htpy.option(
                        disabled=True,
                        selected=channel_id is None,
                        value="",
                    )["Choose a channel"],
                    [
                        htpy.option(
                            selected=value == channel_id,
                            value=value,
                        )[label]
                        for value, label in rainwave_channels
                    ],
                ],
            ],
            htpy.div(".col-12")[
                htpy.label(".form-label", for_="new-suggestion-description")["Details"],
                htpy.textarea(
                    "#new-suggestion-description.form-control",
                    name="description",
                    required=True,
                    rows=3,
                )[description],
            ],
        ],
        htpy.div(".mt-3")[
            htpy.label(".form-label")["Links"],
            htpy.div("#new-suggestion-links.d-flex.flex-column.gap-2")[
                [
                    _suggestion_link_fields(url, label, required=True)
                    for url, label in links
                ]
            ],
            htpy.button(
                ".btn.btn-outline-secondary.btn-sm.mt-2",
                hx_get=flask.url_for("suggestion_link_row", required=1),
                hx_swap="beforeend",
                hx_target="#new-suggestion-links",
                type="button",
            )[htpy.i(".bi-plus-lg"), " Add link"],
        ],
        htpy.div(".mt-3")[
            htpy.button(".btn.btn-outline-success", type="submit")[
                htpy.i(".bi-plus-lg"), " Add suggestion"
            ]
        ],
    ]


def suggestion_create_form(
    title: str = "",
    description: str = "",
    channel_id: int | None = None,
    links: tuple[tuple[str, str], ...] = (),
    result: tuple[str, str] | None = None,
) -> str:
    return str(_suggestion_create_form(title, description, channel_id, links, result))


def _staff_suggestion_requester_discord_id_field(
    requester_discord_id: str = "",
) -> htpy.VoidElement:
    return htpy.input(
        "#staff-suggestion-requester-discord-id.form-control",
        name="requester-discord-id",
        type="text",
        value=requester_discord_id,
    )


def staff_suggestion_requester_discord_id_field(
    requester_discord_id: str = "",
) -> str:
    return str(
        _staff_suggestion_requester_discord_id_field(requester_discord_id),
    )


def _staff_suggestion_create_form(
    title: str = "",
    description: str = "",
    channel_id: int | None = None,
    kind: str = Suggestion.default_kind,
    requester_name: str = "",
    requester_discord_id: str = "",
    links: tuple[tuple[str, str], ...] = (),
    result: tuple[str, str] | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_staff_create")
    rainwave_channels = sorted(
        (
            (value, label)
            for value, label in channels.items()
            if isinstance(value, int) and value in {1, 2, 3, 4, 6}
        ),
        key=lambda item: item[1].casefold(),
    )
    return htpy.form(
        "#staff-suggestion-form",
        action=url,
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="outerHTML",
        hx_target="this",
        method="post",
    )[
        result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
        htpy.div(".g-3.row")[
            htpy.div(".col-12.col-md-6")[
                htpy.label(".form-label", for_="staff-suggestion-channel")["Channel"],
                htpy.select(
                    "#staff-suggestion-channel.form-select",
                    name="channel",
                    required=True,
                )[
                    htpy.option(
                        disabled=True,
                        selected=channel_id is None,
                        value="",
                    )["Choose a channel"],
                    [
                        htpy.option(
                            selected=value == channel_id,
                            value=value,
                        )[label]
                        for value, label in rainwave_channels
                    ],
                ],
            ],
            htpy.div(".col-12.col-md-6")[
                htpy.label(".form-label", for_="staff-suggestion-kind")[
                    "Suggestion type"
                ],
                htpy.select(
                    "#staff-suggestion-kind.form-select",
                    name="kind",
                    required=True,
                )[
                    [
                        htpy.option(selected=value == kind, value=value)[label]
                        for value, label in Suggestion.kind_labels.items()
                    ]
                ],
            ],
            htpy.div(".col-12")[
                htpy.label(".form-label", for_="staff-suggestion-title")[
                    "Suggestion title"
                ],
                htpy.input(
                    "#staff-suggestion-title.form-control",
                    name="title",
                    required=True,
                    type="text",
                    value=title,
                ),
            ],
            htpy.div(".col-12")[
                htpy.label(".form-label", for_="staff-suggestion-description")[
                    "Description"
                ],
                htpy.textarea(
                    "#staff-suggestion-description.form-control",
                    name="description",
                    required=True,
                    rows=6,
                )[description],
            ],
            htpy.div(".col-12.col-md-6")[
                htpy.label(".form-label", for_="staff-suggestion-requester-name")[
                    "Suggested by"
                ],
                htpy.input(
                    "#staff-suggestion-requester-name.form-control",
                    hx_get=flask.url_for("suggestion_staff_requester_discord_id"),
                    hx_include="this",
                    hx_swap="outerHTML",
                    hx_sync="this:replace",
                    hx_target="#staff-suggestion-requester-discord-id",
                    hx_trigger="input changed delay:300ms",
                    name="requester-name",
                    type="text",
                    value=requester_name,
                ),
            ],
            htpy.div(".col-12.col-md-6")[
                htpy.label(
                    ".form-label",
                    for_="staff-suggestion-requester-discord-id",
                )["Suggested by Discord ID"],
                _staff_suggestion_requester_discord_id_field(requester_discord_id),
            ],
            htpy.div(".col-12.form-text")[
                "Leave both Suggested by fields blank to attribute the suggestion "
                "to yourself. Enter a name in Suggested by to auto-fill the Discord ID "
                "based on existing suggestions."
            ],
        ],
        htpy.div(".mt-3")[
            htpy.label(".form-label")["Links"],
            htpy.div("#staff-suggestion-links.d-flex.flex-column.gap-2")[
                [
                    _suggestion_link_fields(url, label, required=True)
                    for url, label in links
                ]
            ],
            htpy.button(
                ".btn.btn-outline-secondary.btn-sm.mt-2",
                hx_get=flask.url_for("suggestion_link_row", required=1),
                hx_swap="beforeend",
                hx_target="#staff-suggestion-links",
                type="button",
            )[htpy.i(".bi-plus-lg"), " Add link"],
        ],
        htpy.div(".mt-3")[
            htpy.button(".btn.btn-success", type="submit")[
                htpy.i(".bi-plus-lg"), " Create suggestion"
            ]
        ],
    ]


def staff_suggestion_create_form(
    title: str = "",
    description: str = "",
    channel_id: int | None = None,
    kind: str = Suggestion.default_kind,
    requester_name: str = "",
    requester_discord_id: str = "",
    links: tuple[tuple[str, str], ...] = (),
    result: tuple[str, str] | None = None,
) -> str:
    return str(
        _staff_suggestion_create_form(
            title=title,
            description=description,
            channel_id=channel_id,
            kind=kind,
            requester_name=requester_name,
            requester_discord_id=requester_discord_id,
            links=links,
            result=result,
        )
    )


def _suggestion_wizard_hidden_request_fields(
    description: str,
    links: tuple[tuple[str, str], ...],
) -> htpy.Node:
    return htpy.fragment[
        htpy.input(name="description", type="hidden", value=description),
        [
            htpy.fragment[
                htpy.input(name="link-url", type="hidden", value=url),
                htpy.input(name="link-label", type="hidden", value=label),
            ]
            for url, label in links
        ],
    ]


def _suggestion_wizard_step1(
    channel_id: int | None = None,
    kind: str | None = None,
    result: tuple[str, str] | None = None,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
) -> htpy.Element:
    url = flask.url_for("suggestion_wizard")
    rainwave_channels = sorted(
        (
            (value, label)
            for value, label in channels.items()
            if isinstance(value, int) and value in {1, 2, 3, 4, 6}
        ),
        key=lambda item: item[1].casefold(),
    )
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="innerHTML",
        hx_target="#new-suggestion-modal-body",
    )[
        htpy.input(name="title", type="hidden", value=title),
        _suggestion_wizard_hidden_request_fields(description, links),
        result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
        htpy.p[
            "Choose the channel and suggestion type that best match what you "
            "want to submit."
        ],
        htpy.div(".g-2.row")[
            htpy.div(".col-12.col-sm-6")[
                htpy.label(".form-label", for_="new-suggestion-channel")["Channel"],
                htpy.select(
                    "#new-suggestion-channel.form-select",
                    name="channel",
                    required=True,
                )[
                    htpy.option(
                        disabled=True,
                        selected=channel_id is None,
                        value="",
                    )["Choose a channel"],
                    [
                        htpy.option(selected=value == channel_id, value=value)[label]
                        for value, label in rainwave_channels
                    ],
                ],
            ],
            htpy.div(".col-12.col-sm-6")[
                htpy.label(".form-label", for_="new-suggestion-kind")[
                    "Suggestion type"
                ],
                htpy.select(
                    "#new-suggestion-kind.form-select",
                    name="kind",
                    required=True,
                )[
                    htpy.option(
                        disabled=True,
                        selected=kind is None,
                        value="",
                    )["Choose a type"],
                    [
                        htpy.option(selected=value == kind, value=value)[label]
                        for value, label in Suggestion.kind_labels.items()
                    ],
                ],
            ],
        ],
        htpy.div(".d-flex.justify-content-end.mt-3")[
            htpy.button(
                ".btn.btn-outline-primary",
                name="step",
                type="submit",
                value="2",
            )["Next ", htpy.i(".bi-caret-right-fill")],
        ],
    ]


def _suggestion_safe_for_work_guidelines() -> htpy.Element:
    return htpy.div[
        htpy.h5["Safe-for-work guidelines"],
        htpy.p[
            "Rainwave is strictly safe-for-work. Songs must not contain NSFW "
            "lyrics, although titles may be masked with stars. Any associated "
            "game must also meet all of these criteria:"
        ],
        htpy.ul[
            htpy.li[
                "You can explain the game to an office co-worker who does not "
                "play video games."
            ],
            htpy.li[
                "You can discuss the game with an office co-worker who knows "
                "what the game is."
            ],
            htpy.li[
                "You can read the game's Wikipedia page or perform a Google "
                "Images search without encountering any red-flag words or images."
            ],
        ],
    ]


def _suggestion_game_rules() -> htpy.Element:
    return htpy.div[
        htpy.p["The Game channel plays video game OSTs from the 16-bit era onward."],
        htpy.h5["Submission requirements"],
        htpy.ul[
            htpy.li["The music must be from a video game."],
            htpy.li[
                "A new album must contain at least four tracks eligible for "
                "the Game channel."
            ],
            htpy.li[
                'Tracks must have distinct names (not "Track 01," "Track 02," '
                'etc.) and an identifiable artist (not "Unknown Artist").'
            ],
            htpy.li[
                "Provide an MP3 download link for the album using Dropbox, "
                "MediaFire, or any other reliable service. Whenever possible, "
                "include the entire album rather than only your favorite tracks."
            ],
            htpy.li[
                "Provide a condensed list of your favorite tracks. This saves "
                "review time and makes those tracks more likely to get on the air."
            ],
        ],
        htpy.h5["Quality guidelines"],
        htpy.ul[
            htpy.li[
                "Tracks should be recognizable and up-tempo, generally between "
                "1 and 5 minutes long, with little to no silence. Generic "
                "orchestral or movie-like soundtracks generally do not fit "
                "the channel."
            ],
            htpy.li[
                "The channel has an easy-listening format, so rap, hip-hop, "
                "hardcore techno, and similar styles generally do not fit."
            ],
            htpy.li["Lyrical tracks are not accepted, with few exceptions."],
            htpy.li[
                "Chip-based music from the NES, Game Boy, Game Boy Color, and "
                "older systems generally belongs on the Chiptune channel."
            ],
        ],
        _suggestion_safe_for_work_guidelines(),
    ]


def _suggestion_oc_remix_rules() -> htpy.Element:
    return htpy.div[
        htpy.div(".alert.alert-info", role="alert")[
            "Rainwave automatically adds every remix and album published on ",
            htpy.a(href="https://ocremix.org/")["OC ReMix"],
            ". You do not need to suggest new OC ReMix music or ask for it to "
            "be added to an existing album.",
        ],
        htpy.h5["When to make a suggestion"],
        htpy.ul[
            htpy.li[
                htpy.strong["Correct a metadata problem: "],
                "Use a Metadata update suggestion when a title, artist, album, "
                "source game, arrangement credit, or other library information "
                "is missing or incorrect.",
            ],
            htpy.li[
                htpy.strong["Report a Content ID restriction: "],
                "If an OC ReMix track becomes subject to Content ID restrictions, "
                "use a Metadata update suggestion to request that it be moved "
                "to the Covers channel.",
            ],
        ],
        htpy.p[
            "Keeping the OC ReMix channel free of Content ID restrictions makes "
            "it suitable for background music in Twitch streams and other "
            "broadcasts."
        ],
        htpy.h5["What to include"],
        htpy.ul[
            htpy.li[
                "Provide a direct link to the remix or album on ocremix.org and, "
                "when available, the corresponding Rainwave library page."
            ],
            htpy.li[
                "For metadata corrections, identify the current value, the "
                "correct value, and a reliable source for the correction."
            ],
            htpy.li[
                "For Content ID reports, identify the affected track, the "
                "claiming party, the platform where the restriction occurred, "
                "and any available evidence of the claim."
            ],
        ],
        htpy.p[
            "Music that has not been published on ocremix.org should not be "
            "suggested for the OC ReMix channel. Suggest eligible remixes and "
            "arrangements for the Covers channel instead."
        ],
    ]


def _suggestion_covers_rules() -> htpy.Element:
    return htpy.div[
        htpy.p[
            "The Covers channel plays video game OST covers, remixes not found "
            "on OC ReMix, official arrangements, and video-game-inspired music."
        ],
        htpy.p[
            "Think of it as OC ReMix radio with additional remixes and original "
            "music submitted directly by independent artists. You'll hear "
            "familiar artists alongside groups from around the world, covering "
            "a variety of genres while maintaining a consistent overall sound."
        ],
        htpy.h5["Submission requirements"],
        htpy.ul[
            htpy.li["The music must come from an independent source."],
            htpy.li["Provide a link to the artist's main page or the project page."],
            htpy.li[
                "The page must provide a way to contact the artist. We must be "
                "able to obtain permission before adding the music unless the "
                "site already grants it, such as through a Creative Commons license."
            ],
            htpy.li[
                "If the artist releases only singles, create a best-of "
                "collection, upload it, and provide a download link. If the "
                "artist releases albums, identify the albums you most want added."
            ],
            htpy.li[
                "Suggest one artist at a time. A single suggestion may include "
                "multiple albums, but they must all be by the same artist."
            ],
            htpy.li[
                'Tracks must have distinct names (not "Track 01," "Track 02," etc.).'
            ],
        ],
        htpy.h5["Quality guidelines"],
        htpy.ul[
            htpy.li[
                "The music must be high quality. With the exception of chiptune "
                "remixes, it should sound like something that could be featured "
                "on OC ReMix."
            ],
            htpy.li[
                "Any style is welcome if the music meets the quality standard "
                "and fits the channel's overall sound."
            ],
        ],
        _suggestion_safe_for_work_guidelines(),
    ]


def _suggestion_chiptune_rules() -> htpy.Element:
    return htpy.div[
        htpy.p[
            "The Chiptune channel plays both chiptune video game soundtracks "
            "and modern chiptunes. Modern chiptunes are created entirely with "
            "8-bit sound elements."
        ],
        htpy.h5["Submission requirements"],
        htpy.ul[
            htpy.li["Provide artist and platform information."],
            htpy.li[
                "Provide an MP3 download link for the album using Dropbox, "
                "MediaFire, or any other reliable service. Suggestions with "
                "download links can usually be reviewed much faster."
            ],
            htpy.li[
                "Optionally, provide a list of the tracks you think should go "
                "on the air. Most chiptune albums are short, so this is not "
                "strictly necessary, but it can help ensure that your favorite "
                "tracks make the cut."
            ],
        ],
        htpy.h5["Video game soundtrack guidelines"],
        htpy.ul[
            htpy.li["The music must be from a video game."],
            htpy.li["The music must be chip-based or too lo-fi for the Game channel."],
            htpy.li[
                'Tracks must have distinct English-language titles (not "Track '
                '01," "死なばもろとも," etc.), except in cases of artistic license.'
            ],
            htpy.li["Tracks should be interesting, recognizable in-game music."],
            htpy.li[
                "Tracks should generally be between 1 and 5 minutes long. "
                "There is limited flexibility for exceptional tracks."
            ],
            htpy.li[
                "Eligible soundtracks often come from the following systems, "
                "although exceptions exist:",
                htpy.ul[
                    htpy.li["Nintendo Entertainment System / Famicom"],
                    htpy.li["Game Boy / Game Boy Color"],
                    htpy.li["Sega Master System"],
                    htpy.li["Commodore 64"],
                    htpy.li["Amiga"],
                    htpy.li["MSX"],
                    htpy.li["Virtual Boy"],
                    htpy.li["PC (modern chiptunes)"],
                    htpy.li[
                        "Game Boy Advance (when a suggestion for the Game "
                        "channel is rejected as too lo-fi)"
                    ],
                    htpy.li[
                        "Super Nintendo Entertainment System (when a suggestion "
                        "for the Game channel is rejected as too lo-fi)"
                    ],
                    htpy.li[
                        "Sega Genesis / Mega Drive (when a suggestion for the "
                        "Game channel is rejected as too lo-fi)"
                    ],
                ],
            ],
        ],
        htpy.h5["Original chiptune and arrangement guidelines"],
        htpy.ul[
            htpy.li[
                "The music must be either an original composition or an "
                "arrangement of existing music."
            ],
            htpy.li[
                "The music must be chiptune and should sound as though it was "
                "produced entirely with one of the systems listed above. "
                "Otherwise, it probably belongs on the Covers channel."
            ],
            htpy.li["Tracks should be interesting, upbeat, and high quality."],
            htpy.li[
                "Tracks should generally be between 1 and 5 minutes long. "
                "There is limited flexibility for exceptional tracks."
            ],
            htpy.li[
                "We must be able to obtain the artist's permission before "
                "adding the music. We'll handle the permission request, but "
                "providing contact information will speed up the process."
            ],
        ],
        _suggestion_safe_for_work_guidelines(),
    ]


def _suggestion_chill_rules() -> htpy.Element:
    return htpy.div[
        htpy.p[
            "The Chill channel plays relaxed, low-intensity video game music, "
            "covers, and remixes. It is intended for background listening, "
            "studying, relaxing, and winding down."
        ],
        htpy.h5["Submission requirements"],
        htpy.ul[
            htpy.li[
                "Identify the source game, album, and artist. For covers and "
                "remixes, also identify the source track."
            ],
            htpy.li[
                'Tracks must have distinct names (not "Track 01," "Track 02," '
                'etc.) and an identifiable artist (not "Unknown Artist").'
            ],
            htpy.li[
                "Provide an MP3 download link for the album using Dropbox, "
                "MediaFire, or any other reliable service. Whenever possible, "
                "include the entire album rather than only the suggested tracks."
            ],
            htpy.li[
                "Provide a focused list of the tracks that best fit the Chill "
                "channel. An album does not need to be uniformly chill, and "
                "tracks that do not fit should be left off the list."
            ],
            htpy.li[
                "For independently released covers and remixes, provide an "
                "artist or project page with contact information. We must be "
                "able to obtain permission before adding the music unless the "
                "site already grants it, such as through a Creative Commons license."
            ],
        ],
        htpy.h5["Quality guidelines"],
        htpy.ul[
            htpy.li[
                "The music must be connected to video games: a video game "
                "soundtrack or a cover or remix of game music."
            ],
            htpy.li[
                "Tracks should maintain a calm, comfortable mood. Ambient, "
                "acoustic, orchestral, jazz, electronic, and lo-fi styles can "
                "all fit when their overall energy remains restrained."
            ],
            htpy.li[
                "Avoid tracks dominated by intense combat energy, aggressive "
                "percussion, abrasive sounds, sudden volume changes, or other "
                "elements that disrupt relaxed listening."
            ],
            htpy.li[
                "Tracks should work as standalone music and should not contain "
                "excessive silence, long non-musical passages, or abrupt endings."
            ],
            htpy.li[
                "Instrumental tracks are preferred. Vocals may be accepted when "
                "they are subdued, complement the music, and do not distract "
                "from the channel's relaxed flow."
            ],
            htpy.li[
                "Audio must be clean and high quality, without clipping, "
                "obvious recording artifacts, or inconsistent mastering."
            ],
        ],
        _suggestion_safe_for_work_guidelines(),
    ]


def _suggestion_wizard_step2(
    channel_id: int | None = None,
    kind: str | None = None,
    open_count: int = 0,
    limits_apply: bool = True,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
) -> htpy.Element:
    url = flask.url_for("suggestion_wizard")
    channel_label = channels.get(channel_id, "—") if channel_id else "—"
    kind_label = Suggestion.kind_labels.get(kind or "", "—")
    over_limit = limits_apply and open_count > 5
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="innerHTML",
        hx_target="#new-suggestion-modal-body",
    )[
        htpy.input(name="channel", type="hidden", value=channel_id or ""),
        htpy.input(name="kind", type="hidden", value=kind or ""),
        htpy.input(name="title", type="hidden", value=title),
        _suggestion_wizard_hidden_request_fields(description, links),
        htpy.div(".alert.alert-secondary", role="alert")[
            htpy.p(".mb-1")[
                "You are suggesting: ",
                htpy.strong[kind_label],
                " on the ",
                htpy.strong[channel_label],
                " channel.",
            ],
            htpy.p(".mb-0")[
                "You currently have ",
                htpy.strong[str(open_count)],
                f" open suggestion{'' if open_count == 1 else 's'} for the ",
                htpy.strong[channel_label],
                " channel.",
            ],
            not limits_apply
            and htpy.p(".mb-0.mt-1")["Suggestion limits do not apply to staff."],
        ],
        over_limit
        and htpy.div(".alert.alert-warning", role="alert")[
            "The ",
            htpy.strong[channel_label],
            " channel allows up to 5 open suggestions at a time. Please wait "
            "until one of your suggestions is resolved before adding another.",
        ],
        not over_limit and channel_id == 1 and _suggestion_game_rules(),
        not over_limit and channel_id == 2 and _suggestion_oc_remix_rules(),
        not over_limit and channel_id == 3 and _suggestion_covers_rules(),
        not over_limit and channel_id == 4 and _suggestion_chiptune_rules(),
        not over_limit and channel_id == 6 and _suggestion_chill_rules(),
        not over_limit
        and htpy.div(".alert.alert-info", role="alert")[
            "If your suggestion complies with these guidelines, continue to "
            "the next step."
        ],
        htpy.div(".d-flex.justify-content-between.mt-3")[
            htpy.button(
                ".btn.btn-outline-secondary",
                name="step",
                type="submit",
                value="1",
            )[htpy.i(".bi-caret-left-fill"), " Back"],
            htpy.button(
                ".btn.btn-outline-primary",
                disabled=over_limit,
                name="step",
                type="submit",
                value="3",
            )["Next ", htpy.i(".bi-caret-right-fill")],
        ],
    ]


def _suggestion_wizard_step3(
    channel_id: int | None = None,
    kind: str | None = None,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
    result: tuple[str, str] | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_wizard")
    channel_label = channels.get(channel_id, "—") if channel_id else "—"
    kind_label = Suggestion.kind_labels.get(kind or "", "—")
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="innerHTML",
        hx_target="#new-suggestion-modal-body",
    )[
        htpy.input(name="channel", type="hidden", value=channel_id or ""),
        htpy.input(name="kind", type="hidden", value=kind or ""),
        _suggestion_wizard_hidden_request_fields(description, links),
        result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
        htpy.div(".alert.alert-secondary", role="alert")[
            "You are suggesting: ",
            htpy.strong[kind_label],
            " on the ",
            htpy.strong[channel_label],
            " channel.",
        ],
        htpy.h5["Suggestion title"],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="new-suggestion-title")[
                "Enter the suggestion title"
            ],
            htpy.input(
                "#new-suggestion-title.form-control",
                aria_describedby="new-suggestion-title-help",
                autofocus=True,
                name="title",
                required=True,
                value=title,
            ),
            htpy.div("#new-suggestion-title-help.form-text")[
                htpy.ul(".mb-0.mt-2")[
                    kind == "new-album"
                    and htpy.li["For a game soundtrack, use the name of the game."],
                    kind == "new-album"
                    and htpy.li[
                        "If the game has different names in different regions, "
                        "use the name of the North American release."
                    ],
                    kind == "new-album"
                    and htpy.li[
                        "For a cover or remix album, use the official album title."
                    ],
                    kind != "new-album"
                    and htpy.li[
                        "For an existing album, use the album name "
                        "exactly as it currently appears on Rainwave."
                    ],
                ]
            ],
        ],
        htpy.div(".d-flex.justify-content-between.mt-3")[
            htpy.button(
                ".btn.btn-outline-secondary",
                formnovalidate=True,
                name="step",
                type="submit",
                value="2",
            )[htpy.i(".bi-caret-left-fill"), " Back"],
            htpy.button(
                ".btn.btn-outline-primary",
                name="step",
                type="submit",
                value="4",
            )["Next ", htpy.i(".bi-caret-right-fill")],
        ],
    ]


def _suggestion_wizard_step4(
    channel_id: int | None = None,
    kind: str | None = None,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
    title_matches: tuple[str, ...] = (),
    result: tuple[str, str] | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_wizard")
    channel_label = channels.get(channel_id, "—") if channel_id else "—"
    kind_label = Suggestion.kind_labels.get(kind or "", "—")
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="innerHTML",
        hx_target="#new-suggestion-modal-body",
    )[
        htpy.input(name="channel", type="hidden", value=channel_id or ""),
        htpy.input(name="kind", type="hidden", value=kind or ""),
        htpy.input(name="title", type="hidden", value=title),
        result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
        htpy.div(".alert.alert-secondary", role="alert")[
            htpy.p(".mb-1")[
                "You are suggesting: ",
                htpy.strong[kind_label],
                " on the ",
                htpy.strong[channel_label],
                " channel.",
            ],
            htpy.p(".mb-0")["Suggestion title: ", htpy.strong[title]],
        ],
        title_matches
        and htpy.div(".alert.alert-warning", role="alert")[
            htpy.p(".fw-semibold.mb-1")[
                "This title may already be in use. Review these matches before "
                "continuing:"
            ],
            htpy.ul(".mb-0")[
                "open-suggestion" in title_matches
                and htpy.li["An open suggestion already uses this title."],
                "declined-suggestion" in title_matches
                and htpy.li["A declined suggestion already uses this title."],
                "album" in title_matches
                and htpy.li[
                    "An album with this name already exists in the Rainwave library."
                ],
            ],
        ],
        htpy.h5["Suggestion details"],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="new-suggestion-description")[
                "Describe your suggestion"
            ],
            htpy.div("#new-suggestion-description-help.form-text.mb-2.mt-0")[
                "Include enough information for the staff to understand and "
                "complete your suggestion."
            ],
            htpy.textarea(
                "#new-suggestion-description.form-control",
                aria_describedby="new-suggestion-description-help",
                autofocus=True,
                name="description",
                required=True,
                rows=5,
            )[description],
        ],
        htpy.h5["Links"],
        htpy.p(".form-text")[
            (
                "Add any relevant download, artist, album, source, cover art, "
                "or evidence links."
            )
        ],
        htpy.div("#new-suggestion-links.d-flex.flex-column.gap-2")[
            [
                _suggestion_link_fields(link_url, label, required=True)
                for link_url, label in links
            ]
        ],
        htpy.button(
            ".btn.btn-outline-secondary.btn-sm.mt-2",
            hx_get=flask.url_for("suggestion_link_row", required=1),
            hx_swap="beforeend",
            hx_target="#new-suggestion-links",
            type="button",
        )[htpy.i(".bi-plus-lg"), " Add link"],
        htpy.div(".d-flex.justify-content-between.mt-3")[
            htpy.button(
                ".btn.btn-outline-secondary",
                formnovalidate=True,
                name="step",
                type="submit",
                value="3",
            )[htpy.i(".bi-caret-left-fill"), " Back"],
            htpy.button(
                ".btn.btn-outline-primary",
                name="step",
                type="submit",
                value="5",
            )["Next ", htpy.i(".bi-caret-right-fill")],
        ],
    ]


def _suggestion_wizard_step5(
    channel_id: int | None = None,
    kind: str | None = None,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
) -> htpy.Element:
    wizard_url = flask.url_for("suggestion_wizard")
    create_url = flask.url_for("suggestion_create")
    channel_label = channels.get(channel_id, "—") if channel_id else "—"
    kind_label = Suggestion.kind_labels.get(kind or "", "—")
    description_display = (
        htpy.div(style="white-space: pre-wrap")[description]
        if description
        else _suggestion_value(None)
    )
    links_display = (
        htpy.ul(".mb-0.ps-3")[
            [
                htpy.li[
                    label and htpy.strong[label],
                    label and ": ",
                    url or htpy.span(".text-secondary")["No URL provided"],
                ]
                for url, label in links
            ]
        ]
        if links
        else _suggestion_value(None)
    )
    return htpy.form(
        action=create_url,
        hx_disabled_elt="button",
        hx_swap="innerHTML",
        hx_target="#new-suggestion-modal-body",
        method="post",
    )[
        htpy.input(name="channel", type="hidden", value=channel_id or ""),
        htpy.input(name="kind", type="hidden", value=kind or ""),
        htpy.input(name="title", type="hidden", value=title),
        _suggestion_wizard_hidden_request_fields(description, links),
        htpy.h5["Confirm suggestion"],
        htpy.p["Review your suggestion before submitting it."],
        _suggestion_detail_table(
            [
                ("Channel", channel_label),
                ("Suggestion type", kind_label),
                ("Suggestion title", title),
                ("Suggestion details", description_display),
                ("Links", links_display),
            ]
        ),
        htpy.div(".d-flex.justify-content-between.mt-3")[
            htpy.button(
                ".btn.btn-outline-secondary",
                formaction=wizard_url,
                formnovalidate=True,
                hx_post=wizard_url,
                name="step",
                type="submit",
                value="4",
            )[htpy.i(".bi-caret-left-fill"), " Back"],
            htpy.button(
                ".btn.btn-success",
                hx_post=create_url,
                type="submit",
            )[htpy.i(".bi-check-lg"), " Submit suggestion"],
        ],
    ]


def _suggestion_wizard_body(
    step: int,
    channel_id: int | None = None,
    kind: str | None = None,
    result: tuple[str, str] | None = None,
    song_count: int = 0,
    song_count_as_of: str = "",
    open_count: int = 0,
    limits_apply: bool = True,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
    title_matches: tuple[str, ...] = (),
) -> htpy.Node:
    if step == 5:
        return _suggestion_wizard_step5(channel_id, kind, title, description, links)
    if step == 4:
        return _suggestion_wizard_step4(
            channel_id, kind, title, description, links, title_matches, result
        )
    if step == 3:
        return _suggestion_wizard_step3(
            channel_id, kind, title, description, links, result
        )
    if step == 2:
        return _suggestion_wizard_step2(
            channel_id,
            kind,
            open_count,
            limits_apply,
            title,
            description,
            links,
        )
    return htpy.fragment[
        _suggestion_create_notice(song_count, song_count_as_of),
        _suggestion_wizard_step1(channel_id, kind, result, title, description, links),
    ]


def suggestion_wizard_body(
    step: int,
    channel_id: int | None = None,
    kind: str | None = None,
    result: tuple[str, str] | None = None,
    song_count: int = 0,
    song_count_as_of: str = "",
    open_count: int = 0,
    limits_apply: bool = True,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
    title_matches: tuple[str, ...] = (),
) -> str:
    return str(
        _suggestion_wizard_body(
            step,
            channel_id,
            kind,
            result,
            song_count,
            song_count_as_of,
            open_count,
            limits_apply,
            title,
            description,
            links,
            title_matches,
        )
    )


def _suggestion_create_modal(song_count: int, song_count_as_of: str) -> htpy.Element:
    return htpy.div(
        "#new-suggestion-modal.fade.modal",
        aria_hidden="true",
        aria_labelledby="new-suggestion-modal-title",
        tabindex="-1",
    )[
        htpy.div(".modal-dialog.modal-dialog-scrollable.modal-lg")[
            htpy.div(".modal-content")[
                htpy.div(".modal-header")[
                    htpy.h5("#new-suggestion-modal-title.modal-title")[
                        "New suggestion"
                    ],
                    htpy.button(
                        ".btn-close",
                        aria_label="Close",
                        data_bs_dismiss="modal",
                        type="button",
                    ),
                ],
                htpy.div("#new-suggestion-modal-body.modal-body")[
                    _suggestion_wizard_body(
                        1,
                        song_count=song_count,
                        song_count_as_of=song_count_as_of,
                    )
                ],
            ]
        ]
    ]


def _staff_suggestion_create_modal() -> htpy.Element:
    return htpy.div(
        "#staff-suggestion-modal.fade.modal",
        aria_hidden="true",
        aria_labelledby="staff-suggestion-modal-title",
        tabindex="-1",
    )[
        htpy.div(".modal-dialog.modal-dialog-scrollable.modal-lg")[
            htpy.div(".modal-content")[
                htpy.div(".modal-header")[
                    htpy.h5("#staff-suggestion-modal-title.modal-title")[
                        "Create a suggestion"
                    ],
                    htpy.button(
                        ".btn-close",
                        aria_label="Close",
                        data_bs_dismiss="modal",
                        type="button",
                    ),
                ],
                htpy.div(".modal-body")[_staff_suggestion_create_form()],
            ]
        ]
    ]


def suggestions_index(
    is_staff: bool,
    claimants: list[str],
    your_suggestions_active_count: int,
    your_suggestions_complete_count: int,
    song_count: int = 0,
    song_count_as_of: str = "",
) -> str:
    rows_url = flask.url_for("suggestions_rows")
    rainwave_channels = sorted(
        (
            (channel_id, label)
            for channel_id, label in channels.items()
            if isinstance(channel_id, int) and channel_id in {1, 2, 3, 4, 6}
        ),
        key=lambda channel: channel[1].casefold(),
    )
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Music suggestions"]]],
        htpy.div(".g-1.pt-3.row")[
            htpy.div(".col-auto")[
                htpy.button(
                    ".btn.btn-outline-success.mb-1",
                    data_bs_target="#new-suggestion-modal",
                    data_bs_toggle="modal",
                    type="button",
                )[htpy.i(".bi-plus-lg"), " New suggestion"]
            ],
            is_staff
            and htpy.div(".col-auto")[
                htpy.button(
                    ".btn.btn-outline-primary.mb-1",
                    data_bs_target="#staff-suggestion-modal",
                    data_bs_toggle="modal",
                    type="button",
                )[htpy.i(".bi-lightning-charge"), " Quick add suggestion"]
            ],
        ],
        _suggestion_create_modal(song_count, song_count_as_of),
        is_staff and _staff_suggestion_create_modal(),
        htpy.form(
            "#suggestion-filters",
            hx_include="#suggestion-filters",
            hx_target="#suggestion-rows",
            onsubmit="return false",
        )[
            htpy.div(".align-items-center.g-2.pt-3.row")[
                htpy.div(".col-12.col-md-5")[
                    htpy.input(
                        ".form-control",
                        aria_label="Search music suggestions",
                        hx_indicator="#suggestion-filters-indicator",
                        hx_post=rows_url,
                        hx_trigger="search, keyup changed delay:300ms",
                        name="q",
                        placeholder="Search suggestions...",
                        type="search",
                    )
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
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
                                            f"#suggestion-sort-dir-{value}.form-check-input",
                                            checked=value == "desc",
                                            hx_indicator=(
                                                "#suggestion-filters-indicator"
                                            ),
                                            hx_post=rows_url,
                                            name="sort-dir",
                                            type="radio",
                                            value=value,
                                        ),
                                        htpy.label(
                                            ".form-check-label",
                                            for_=f"suggestion-sort-dir-{value}",
                                        )[label],
                                    ]
                                    for value, label in (
                                        ("asc", "Ascending"),
                                        ("desc", "Descending"),
                                    )
                                ],
                                htpy.hr,
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#suggestion-sort-col-{value}.form-check-input",
                                            checked=value == "requested_at",
                                            hx_indicator=(
                                                "#suggestion-filters-indicator"
                                            ),
                                            hx_post=rows_url,
                                            name="sort-col",
                                            type="radio",
                                            value=value,
                                        ),
                                        htpy.label(
                                            ".form-check-label.text-nowrap",
                                            for_=f"suggestion-sort-col-{value}",
                                        )[label],
                                    ]
                                    for value, label in Suggestion.sort_fields
                                ],
                            ]
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
                            data_bs_toggle="dropdown",
                            title="Claimant selection",
                            type="button",
                        )[htpy.i(".bi-person-check")],
                        htpy.div(".dropdown-menu")[
                            htpy.div(".px-2")[
                                htpy.h6(".dropdown-header")["CLAIMED BY"],
                                htpy.div(".form-check")[
                                    htpy.input(
                                        "#suggestion-claimant-unclaimed.form-check-input",
                                        hx_indicator="#suggestion-filters-indicator",
                                        hx_post=rows_url,
                                        name="claimed-by",
                                        type="checkbox",
                                        value="",
                                    ),
                                    htpy.label(
                                        ".form-check-label.text-nowrap",
                                        for_="suggestion-claimant-unclaimed",
                                    )["(unclaimed)"],
                                ],
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#suggestion-claimant-{index}.form-check-input",
                                            hx_indicator=(
                                                "#suggestion-filters-indicator"
                                            ),
                                            hx_post=rows_url,
                                            name="claimed-by",
                                            type="checkbox",
                                            value=claimant,
                                        ),
                                        htpy.label(
                                            ".form-check-label.text-nowrap",
                                            for_=f"suggestion-claimant-{index}",
                                        )[claimant],
                                    ]
                                    for index, claimant in enumerate(claimants)
                                ],
                            ]
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
                            data_bs_toggle="dropdown",
                            title="Channel selection",
                            type="button",
                        )[htpy.i(".bi-broadcast-pin")],
                        htpy.div(".dropdown-menu")[
                            htpy.div(".px-2")[
                                htpy.h6(".dropdown-header")["CHANNEL"],
                                htpy.div(".form-check")[
                                    htpy.input(
                                        "#suggestion-channel-unassigned.form-check-input",
                                        checked=True,
                                        hx_indicator="#suggestion-filters-indicator",
                                        hx_post=rows_url,
                                        name="channels",
                                        type="checkbox",
                                        value="unassigned",
                                    ),
                                    htpy.label(
                                        ".form-check-label.text-nowrap",
                                        for_="suggestion-channel-unassigned",
                                    )["(no channel)"],
                                ],
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#suggestion-channel-{channel_id}.form-check-input",
                                            checked=True,
                                            hx_indicator=(
                                                "#suggestion-filters-indicator"
                                            ),
                                            hx_post=rows_url,
                                            name="channels",
                                            type="checkbox",
                                            value=channel_id,
                                        ),
                                        htpy.label(
                                            ".form-check-label.text-nowrap",
                                            for_=f"suggestion-channel-{channel_id}",
                                        )[label],
                                    ]
                                    for channel_id, label in rainwave_channels
                                ],
                            ]
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
                            data_bs_toggle="dropdown",
                            title="Status selection",
                            type="button",
                        )[htpy.i(".bi-flag")],
                        htpy.div(".dropdown-menu")[
                            htpy.div(".px-2")[
                                htpy.h6(".dropdown-header")["STATUS"],
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#status-{status}.form-check-input",
                                            checked=status in ("new", "claimed"),
                                            hx_indicator=(
                                                "#suggestion-filters-indicator"
                                            ),
                                            hx_post=rows_url,
                                            name="status",
                                            type="checkbox",
                                            value=status,
                                        ),
                                        htpy.label(
                                            ".form-check-label",
                                            for_=f"status-{status}",
                                        )[status.title()],
                                    ]
                                    for status in Suggestion.statuses
                                ],
                            ]
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
                            data_bs_toggle="dropdown",
                            title="Suggestion type selection",
                            type="button",
                        )[htpy.i(".bi-tags")],
                        htpy.div(".dropdown-menu")[
                            htpy.div(".px-2")[
                                htpy.h6(".dropdown-header")["SUGGESTION TYPE"],
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#suggestion-kind-{kind}.form-check-input",
                                            checked=True,
                                            hx_indicator=(
                                                "#suggestion-filters-indicator"
                                            ),
                                            hx_post=rows_url,
                                            name="kinds",
                                            type="checkbox",
                                            value=kind,
                                        ),
                                        htpy.label(
                                            ".form-check-label.text-nowrap",
                                            for_=f"suggestion-kind-{kind}",
                                        )[label],
                                    ]
                                    for kind, label in Suggestion.kind_labels.items()
                                ],
                            ]
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
                            data_bs_toggle="dropdown",
                            title="Filter options",
                            type="button",
                        )[htpy.i(".bi-list-check")],
                        htpy.div(".dropdown-menu")[
                            htpy.div(".px-2")[
                                htpy.h6(".dropdown-header")["FILTER OPTIONS"],
                                htpy.div(".form-check")[
                                    htpy.input(
                                        "#your-suggestions.form-check-input",
                                        hx_indicator="#suggestion-filters-indicator",
                                        hx_post=rows_url,
                                        name="your-suggestions",
                                        type="checkbox",
                                        value="1",
                                    ),
                                    htpy.label(
                                        ".form-check-label.text-nowrap",
                                        for_="your-suggestions",
                                    )[
                                        "Your suggestions (",
                                        str(your_suggestions_active_count),
                                        " active, ",
                                        str(your_suggestions_complete_count),
                                        " complete",
                                        ")",
                                    ],
                                ],
                                is_staff
                                and htpy.div(".form-check")[
                                    htpy.input(
                                        "#your-claims.form-check-input",
                                        hx_indicator="#suggestion-filters-indicator",
                                        hx_post=rows_url,
                                        name="your-claims",
                                        type="checkbox",
                                        value="1",
                                    ),
                                    htpy.label(
                                        ".form-check-label.text-nowrap",
                                        for_="your-claims",
                                    )["Your claims"],
                                ],
                            ]
                        ],
                    ]
                ],
                htpy.div(".col-auto")[
                    htpy.span(
                        "#suggestion-filters-indicator.htmx-indicator.spinner-border.spinner-border-sm.text-primary"
                    )
                ],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.div(".table-responsive")[
                    htpy.table(
                        ".align-middle.table.table-bordered.table-sm.table-striped"
                    )[
                        htpy.thead[
                            htpy.tr(".text-center")[
                                htpy.th,
                                htpy.th(".d-table-cell.d-md-none")["Suggestion"],
                                [
                                    htpy.th(".d-none.d-md-table-cell.text-nowrap")[
                                        label
                                    ]
                                    for label in (
                                        "Status",
                                        "Channels",
                                        "Suggestion title",
                                        "Suggestion type",
                                        "Suggested by",
                                        "Suggested at",
                                        "Claimed by",
                                    )
                                ],
                            ]
                        ],
                        htpy.tbody(
                            "#suggestion-rows",
                            hx_include="#suggestion-filters",
                            hx_post=rows_url,
                            hx_trigger="load",
                        )[
                            htpy.tr[
                                htpy.td(
                                    ".py-3.text-center", colspan=Suggestion.colspan
                                )[
                                    htpy.span(
                                        ".htmx-indicator.spinner-border.spinner-border-sm"
                                    )
                                ]
                            ]
                        ],
                    ]
                ]
            ]
        ],
    ]
    return str(_base(content))


def suggestions_rows(suggestions: list[Suggestion], page: int) -> str:
    rows = []
    for index, suggestion in enumerate(suggestions):
        if index < 100:
            rows.append(_suggestion_row(suggestion))
        else:
            rows.append(
                htpy.tr[
                    htpy.td(
                        ".py-3.text-center",
                        colspan=Suggestion.colspan,
                        hx_include="#suggestion-filters",
                        hx_post=flask.url_for("suggestions_rows", page=page + 1),
                        hx_swap="outerHTML",
                        hx_target="closest tr",
                        hx_trigger="revealed",
                    )[htpy.span(".htmx-indicator.spinner-border.spinner-border-sm")]
                ]
            )
    if not rows:
        rows.append(
            htpy.tr[
                htpy.td(".py-3.text-center", colspan=Suggestion.colspan)[
                    "No suggestions found."
                ]
            ]
        )
    return str(htpy.fragment[rows])


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
            htpy.div(".align-items-center.d-flex.g-2.pt-3.row")[
                htpy.div(".col-12.col-sm-auto")[search_input],
                htpy.div(".col-auto")[
                    htpy.div(".dropdown")[
                        htpy.button(
                            ".btn.btn-outline-primary.dropdown-toggle",
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
                            ".btn.btn-outline-primary.dropdown-toggle",
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
                            ".btn.btn-outline-primary.dropdown-toggle",
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
                        ".btn.btn-outline-primary",
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
        htpy.strong[htpy.i(".bi-music-not-beamed"), " ", song.title],
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
                    htpy.button(".btn.btn-outline-danger", type="submit")[
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
                htpy.a(".btn.btn-outline-dark.pe-none", href="#")[
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
