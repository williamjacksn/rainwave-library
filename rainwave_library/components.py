import flask
import htpy
import markupsafe

import rainwave_library.versions as v
from rainwave_library.models.rainwave import (
    Album,
    Artist,
    Listener,
    Song,
    channels,
    length_display,
)
from rainwave_library.models.suggestions import Suggestion, SuggestionDetail


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


def settings_index(settings: list[tuple[str, str, bool]]) -> str:
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
        "fulfilled": "text-bg-success",
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
    action = "Edit" if editable else "View details for"
    action_title = "Edit suggestion" if editable else "View suggestion details"
    kind_classes = {
        "removal": "text-bg-danger",
        "cleanup": "text-bg-dark",
    }
    kind_class = kind_classes.get(suggestion.kind, "text-bg-secondary")
    return htpy.tr(class_={"text-secondary": suggestion.archived})[
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
                suggestion.kind != "addition"
                and htpy.span(f".badge.{kind_class}")[suggestion.kind],
                suggestion.archived
                and htpy.span(".badge.text-bg-secondary")["archived"],
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
            (suggestion.claimed_by_name or claimable)
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
            ],
            suggestion.requested_at
            and htpy.div(".small.mt-1")[
                htpy.strong["Requested: "], suggestion.requested_at
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
        htpy.td(".d-none.d-md-table-cell")[
            htpy.div(".fw-semibold")[suggestion.title],
            htpy.div(".d-flex.flex-wrap.gap-1.mt-1")[
                suggestion.kind != "addition"
                and htpy.span(f".badge.{kind_class}")[suggestion.kind],
                suggestion.archived
                and htpy.span(".badge.text-bg-secondary")["archived"],
            ],
        ],
        htpy.td(".d-none.d-md-table-cell.text-nowrap")[
            suggestion.requester_name or htpy.span(".text-secondary")["—"],
            suggestion.requester_discord_id
            and htpy.i(
                ".bi-discord.ms-1",
                title=f"Discord user {suggestion.requester_discord_id}",
            ),
        ],
        htpy.td(".d-none.d-md-table-cell.text-nowrap")[
            suggestion.requested_at or htpy.span(".text-secondary")["—"]
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
                "Suggestion ID: ", htpy.code[suggestion.id]
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
                htpy.label(".form-label", for_="kind")["Kind"],
                htpy.select("#kind.form-select", name="kind")[
                    [
                        htpy.option(
                            selected=kind == suggestion.kind,
                            value=kind,
                        )[kind.title()]
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
        ],
        htpy.h6(".mt-4")["Request"],
        htpy.div(".g-3.row")[
            htpy.div(".col-12.col-lg-4")[
                htpy.label(".form-label", for_="requester-name")["Suggested by"],
                htpy.input(
                    "#requester-name.form-control",
                    name="requester-name",
                    type="text",
                    value=suggestion.requester_name or "",
                ),
            ],
            htpy.div(".col-12.col-lg-4")[
                htpy.label(".form-label", for_="requester-discord-id")[
                    "Suggested by Discord ID"
                ],
                htpy.input(
                    "#requester-discord-id.form-control",
                    name="requester-discord-id",
                    type="text",
                    value=suggestion.requester_discord_id or "",
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
        htpy.h6(".mt-4")["Resolution"],
        htpy.div(".g-3.row")[
            htpy.div(".col-12.col-lg-4")[
                htpy.label(".form-label", for_="resolved-at")["Resolved"],
                htpy.input(
                    "#resolved-at.form-control",
                    name="resolved-at",
                    type="text",
                    value=suggestion.resolved_at or "",
                ),
            ],
            htpy.div(".col-12.col-lg-8")[
                htpy.label(".form-label", for_="resolution-notes")["Resolution notes"],
                htpy.textarea(
                    "#resolution-notes.form-control",
                    name="resolution-notes",
                    rows=2,
                )[suggestion.resolution_notes or ""],
            ],
        ],
        htpy.h6(".mt-4")["Organization"],
        htpy.div(".g-3.row")[
            htpy.div(".col-12.col-lg-5")[
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
            htpy.div(".col-12.col-lg-3")[
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
            htpy.div(".col-12.col-lg-4")[
                htpy.label(".form-label", for_="sort-order")["Sort order"],
                htpy.input(
                    "#sort-order.form-control",
                    name="sort-order",
                    step="any",
                    type="number",
                    value=str(suggestion.sort_order),
                ),
            ],
        ],
        htpy.button(".btn.btn-outline-success.mt-3", type="submit")[
            htpy.i(".bi-file-earmark-play"), " Save suggestion"
        ],
    ]


def suggestion_detail_row(
    suggestion: SuggestionDetail,
    *,
    editable: bool = False,
    edit_result: tuple[str, str] | None = None,
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
            ("ID", htpy.code[suggestion.id]),
            ("Status", _suggestion_status_badge(suggestion.status)),
            ("Kind", suggestion.kind.title()),
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
                "Requested at",
                _suggestion_value(
                    suggestion.requested_at[:10]
                    if suggestion.requested_at is not None
                    else None
                ),
            ),
            ("Claimed at", _suggestion_value(suggestion.claimed_at)),
            ("Completed at", _suggestion_value(suggestion.resolved_at)),
        ]
    )
    links: htpy.Node = (
        htpy.div(".list-group")[
            [
                htpy.div(".list-group-item")[
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
                        htpy.span(".badge.text-bg-secondary")[link.type],
                    ],
                    htpy.div(".small.text-secondary")[
                        link.label and [link.url, htpy.br],
                        "ID: ",
                        htpy.code[link.id],
                        " · Sort order: ",
                        str(link.sort_order),
                        link.trello_attachment_id
                        and [
                            " · Trello attachment: ",
                            htpy.code[link.trello_attachment_id],
                        ],
                    ],
                ]
                for link in suggestion.links
            ]
        ]
        if suggestion.links
        else htpy.p(".text-secondary")["No links."]
    )
    activities: htpy.Node = (
        htpy.div(".list-group")[
            [
                htpy.div(".list-group-item")[
                    htpy.div(".d-flex.flex-wrap.gap-2.justify-content-between")[
                        htpy.strong[activity.type.replace("-", " ").title()],
                        htpy.span(".small.text-secondary")[activity.created_at],
                    ],
                    htpy.div(".small.text-secondary")[
                        "Actor: ",
                        activity.actor_name or "—",
                        activity.actor_discord_id
                        and [" · Discord: ", htpy.code[activity.actor_discord_id]],
                        activity.trello_member_id
                        and [
                            " · Trello member: ",
                            htpy.code[activity.trello_member_id],
                        ],
                    ],
                    activity.body
                    and htpy.div(".mt-2", style="white-space: pre-wrap")[activity.body],
                    (activity.old_value is not None or activity.new_value is not None)
                    and htpy.div(".mt-2")[
                        _suggestion_value(activity.old_value),
                        " → ",
                        _suggestion_value(activity.new_value),
                    ],
                    htpy.div(".small.text-secondary")[
                        "ID: ",
                        htpy.code[activity.id],
                        activity.trello_action_id
                        and [
                            " · Trello action: ",
                            htpy.code[activity.trello_action_id],
                        ],
                    ],
                ]
                for activity in suggestion.activities
            ]
        ]
        if suggestion.activities
        else htpy.p(".text-secondary")["No activity."]
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
                        htpy.h6(".mt-3")["Description"],
                        htpy.div(
                            ".bg-body-tertiary.border.p-2.rounded",
                            style="white-space: pre-wrap",
                        )[_suggestion_value(suggestion.description)],
                    ],
                    htpy.h6(".mt-3")["Links"],
                    links,
                    htpy.h6(".mt-3")["Activity"],
                    activities,
                ],
            ]
        ]
    ]
    return str(content)


def _suggestion_create_row(
    title: str = "",
    description: str = "",
    channel_id: int | None = None,
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
    return htpy.tr[
        htpy.td(colspan=Suggestion.colspan)[
            htpy.div(".card.my-2")[
                htpy.div(".align-items-center.card-header.d-flex.gap-2")[
                    htpy.button(
                        ".btn.btn-outline-secondary.btn-sm",
                        aria_label="Close new suggestion form",
                        hx_get=flask.url_for("suggestion_create", close=1),
                        hx_swap="innerHTML",
                        hx_target="closest tbody",
                        title="Close new suggestion form",
                        type="button",
                    )[htpy.i(".bi-x-lg")],
                    htpy.h5(".mb-0")["New suggestion"],
                ],
                htpy.div(".card-body")[
                    htpy.form(
                        action=url,
                        hx_disabled_elt="button",
                        hx_post=url,
                        hx_swap="outerHTML",
                        hx_target="closest tr",
                        method="post",
                    )[
                        result
                        and htpy.div(f".alert.{result[0]}.py-2", role="alert")[
                            result[1]
                        ],
                        htpy.div(".align-items-end.g-2.row")[
                            htpy.div(".col-12.col-lg-4")[
                                htpy.label(".form-label", for_="new-suggestion-title")[
                                    "Title"
                                ],
                                htpy.input(
                                    "#new-suggestion-title.form-control",
                                    name="title",
                                    required=True,
                                    type="text",
                                    value=title,
                                ),
                            ],
                            htpy.div(".col-12.col-sm-5.col-lg-2")[
                                htpy.label(
                                    ".form-label", for_="new-suggestion-channel"
                                )["Channel"],
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
                            htpy.div(".col-12.col-lg")[
                                htpy.label(
                                    ".form-label", for_="new-suggestion-description"
                                )["Details or links"],
                                htpy.textarea(
                                    "#new-suggestion-description.form-control",
                                    name="description",
                                    rows=2,
                                )[description],
                            ],
                            htpy.div(".col-auto")[
                                htpy.button(".btn.btn-outline-success", type="submit")[
                                    htpy.i(".bi-plus-lg"), " Add suggestion"
                                ]
                            ],
                        ],
                    ],
                ],
            ]
        ]
    ]


def suggestion_create_row(
    title: str = "",
    description: str = "",
    channel_id: int | None = None,
    result: tuple[str, str] | None = None,
) -> str:
    return str(_suggestion_create_row(title, description, channel_id, result))


def suggestion_discord_user_form(
    discord_username: str = "",
    discord_user_id: str = "",
    result: tuple[str, str] | None = None,
) -> str:
    url = flask.url_for("suggestions_requester_discord_id")
    return str(
        htpy.form(
            ".align-items-end.d-flex.flex-wrap.gap-2",
            action=url,
            hx_disabled_elt="button",
            hx_post=url,
            hx_swap="outerHTML",
            method="post",
        )[
            result
            and htpy.div(f".alert.{result[0]}.mb-0.py-2.w-100", role="alert")[
                result[1]
            ],
            htpy.div[
                htpy.label(".form-label.small", for_="bulk-discord-username")[
                    "Discord username"
                ],
                htpy.input(
                    "#bulk-discord-username.form-control",
                    autocomplete="off",
                    name="discord-username",
                    required=True,
                    type="text",
                    value=discord_username,
                ),
            ],
            htpy.div[
                htpy.label(".form-label.small", for_="bulk-discord-user-id")[
                    "Discord user ID"
                ],
                htpy.input(
                    "#bulk-discord-user-id.form-control",
                    autocomplete="off",
                    inputmode="numeric",
                    name="discord-user-id",
                    pattern="[0-9]+",
                    required=True,
                    type="text",
                    value=discord_user_id,
                ),
            ],
            htpy.button(".btn.btn-outline-primary", type="submit")[
                htpy.i(".bi-discord"), " Update suggestions"
            ],
        ]
    )


def suggestions_index(
    is_staff: bool,
    your_suggestions_active_count: int,
    your_suggestions_complete_count: int,
) -> str:
    rows_url = flask.url_for("suggestions_rows")
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Music suggestions"]]],
        htpy.div(".g-1.pt-3.row")[
            htpy.div(".col-auto")[
                htpy.button(
                    ".btn.btn-outline-success.mb-1",
                    hx_get=flask.url_for("suggestion_create"),
                    hx_swap="innerHTML",
                    hx_target="#suggestion-create",
                    type="button",
                )[htpy.i(".bi-plus-lg"), " New suggestion"]
            ],
            is_staff
            and htpy.div(".col-auto")[
                htpy.button(
                    ".btn.btn-outline-primary.mb-1",
                    hx_get=flask.url_for("suggestions_requester_discord_id"),
                    hx_swap="outerHTML",
                    title="Set suggestion Discord user IDs",
                    type="button",
                )[htpy.i(".bi-discord"), " Match Discord user"]
            ],
        ],
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
                                            checked=value == "asc",
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
                                            checked=value == "status",
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
                            title="Status selection",
                            type="button",
                        )[htpy.i(".bi-flag")],
                        htpy.div(".dropdown-menu")[
                            htpy.div(".px-2")[
                                htpy.h6(".dropdown-header")["STATUS SELECTION"],
                                [
                                    htpy.div(".form-check")[
                                        htpy.input(
                                            f"#status-{status}.form-check-input",
                                            checked=True,
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
                                htpy.div(".form-check")[
                                    htpy.input(
                                        "#missing-suggested-by-discord-id.form-check-input",
                                        hx_indicator="#suggestion-filters-indicator",
                                        hx_post=rows_url,
                                        name="missing-suggested-by-discord-id",
                                        type="checkbox",
                                        value="1",
                                    ),
                                    htpy.label(
                                        ".form-check-label.text-nowrap",
                                        for_="missing-suggested-by-discord-id",
                                    )["Suggested by without Discord ID"],
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
                                        "Suggestion",
                                        "Suggested by",
                                        "Suggested at",
                                        "Claimed by",
                                    )
                                ],
                            ]
                        ],
                        htpy.tbody("#suggestion-create"),
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
    content = htpy.div(
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
            htpy.div("#audio-metadata.pb-1")[
                htpy.strong[htpy.i(".bi-disc"), " ", song.album_name],
                htpy.br,
                htpy.strong[htpy.i(".bi-music-not-beamed"), " ", song.title],
                htpy.br,
                htpy.strong[htpy.i(".bi-person"), " ", song.artist_tag],
            ],
            htpy.audio(
                autoplay=True,
                controls=True,
                preload="metadata",
                src=flask.url_for("stream_song", song_id=song.id),
            ),
        ],
    ]
    return str(content)


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
