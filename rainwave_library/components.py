import flask
import htpy
import markupsafe
import rainwave_library.channels
import rainwave_library.versions as v


def _base(content: htpy.Node) -> htpy.Element:
    return htpy.html(lang="en")[
        htpy.head[
            htpy.title["Rainwave Library"],
            htpy.meta(content="width=device-width, initial-scale=1", name="viewport"),
            _favicon(),
            _bs_stylesheet(),
            _bi_stylesheet(),
        ],
        htpy.body[
            htpy.div(".container-fluid")[
                content,
                htpy.div(".pt-3.row")[htpy.div(".col")[htpy.hr]],
            ],
            _nav_modal(),
            _bs_script(),
            _hx_script(),
        ],
    ]


def _bi_stylesheet():
    return htpy.link(
        href=flask.url_for("static", filename=f"bootstrap-icons-{v.bi}.css"),
        rel="stylesheet",
    )


def _bs_script():
    return htpy.script(
        src=flask.url_for("static", filename=f"bootstrap-{v.bs}.bundle.js")
    )


def _bs_stylesheet():
    return htpy.link(
        href=flask.url_for("static", filename=f"bootstrap-{v.bs}.css"), rel="stylesheet"
    )


def _favicon() -> htpy.Element:
    return htpy.link(href=flask.url_for("favicon"), rel="icon")


def _hx_script():
    return htpy.script(src=flask.url_for("static", filename=f"htmx-{v.hx}.js"))


def _nav_header(text: str) -> htpy.Element:
    return htpy.div(".align-items-center.d-flex.g-1.pt-3.row")[
        htpy.div(".col-auto.me-auto")[
            htpy.h1[
                htpy.a(
                    ".link-body-emphasis.text-decoration-none",
                    data_bs_target="#nav-modal",
                    data_bs_toggle="modal",
                    href="#",
                )[text, " ", htpy.i(".bi-caret-down-fill.small")]
            ]
        ],
        _sign_out_button(True),
    ]


def _nav_modal():
    return htpy.div("#nav-modal.modal")[
        htpy.div(".modal-dialog.modal-dialog-centered")[
            htpy.div(".modal-content")[
                htpy.div(".modal-body")[
                    htpy.div(".card.mb-3.text-center")[
                        htpy.div(".card-body")[
                            htpy.h2[
                                htpy.a(
                                    ".link-body-emphasis.stretched-link.text-decoration-none",
                                    href=flask.url_for("songs"),
                                )["Songs"]
                            ]
                        ]
                    ],
                    htpy.div(".card.mb-3.text-center")[
                        htpy.div(".card-body")[
                            htpy.h2[
                                htpy.a(
                                    ".link-body-emphasis.stretched-link.text-decoration-none",
                                    href=flask.url_for("listeners"),
                                )["Listeners"]
                            ]
                        ]
                    ],
                    htpy.div(".card.text-center")[
                        htpy.div(".card-body")[
                            htpy.h2[
                                htpy.a(
                                    ".link-body-emphasis.stretched-link.text-decoration-none",
                                    href=flask.url_for("get_ocremix"),
                                )["Get an OC ReMix"]
                            ]
                        ]
                    ],
                ]
            ]
        ]
    ]


def _sign_out_button(show_bsky: bool = False) -> htpy.Node:
    return [
        show_bsky
        and htpy.div(".col-auto")[
            htpy.button(
                ".btn.btn-outline-primary",
                data_bs_target="#bsky-modal",
                data_bs_toggle="modal",
            )[htpy.i(".bi-pencil-square"), " Post"]
        ],
        htpy.div(".col-auto")[
            htpy.a(".btn.btn-outline-danger", href=flask.url_for("sign_out"))[
                "Sign out"
            ]
        ],
        show_bsky
        and htpy.div("#bsky-modal.modal")[
            htpy.div(".modal-dialog.modal-dialog-centered")[
                htpy.div(".modal-content")[
                    htpy.div(".modal-body")[
                        htpy.form(
                            ".mb-0", action=flask.url_for("bluesky"), method="post"
                        )[
                            htpy.h5(".mb-3")[
                                htpy.label(for_="body")["Post to Bluesky"]
                            ],
                            htpy.textarea(
                                "#body.form-control.mb-3",
                                name="body",
                                required=True,
                                rows=10,
                            ),
                            htpy.div(".row")[
                                htpy.div(".col-auto.ms-auto")[
                                    htpy.button(
                                        ".btn.btn-outline-primary", type="submit"
                                    )["Post"]
                                ]
                            ],
                        ]
                    ]
                ]
            ]
        ],
    ]


def favicon() -> str:
    # https://icons.getbootstrap.com/icons/boombox-fill/
    paths = [
        "M14 0a.5.5 0 0 1 .5.5V2h.5a1 1 0 0 1 1 1v2H0V3a1 1 0 0 1 1-1h12.5V.5A.5.5 0 0 1 14 0M2 3.5a.5.5 0 1 0 1 0 "
        ".5.5 0 0 0-1 0m2 0a.5.5 0 1 0 1 0 .5.5 0 0 0-1 0m7.5.5a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1m1.5-.5a.5.5 0 1 0 1 0 "
        ".5.5 0 0 0-1 0M9.5 3h-3a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1M6 10.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 "
        "0m-1.5.5a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1m7 1a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3m.5-1.5a.5.5 0 1 1-1 0 .5.5 0 0 "
        "1 1 0",
        "M0 6h16v8a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm2 4.5a2.5 2.5 0 1 0 5 0 2.5 2.5 0 0 0-5 0m7 0a2.5 2.5 0 1 0 5 0 2.5 "
        "2.5 0 0 0-5 0",
    ]
    content = htpy.svg(
        ".bi.bi-boombox-fill",
        fill="#f47d37",
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
                    value=", ".join(a.get("name") for a in ocr_info.get("artists")),
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
        _nav_header("Get an OC ReMix"),
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


_listeners_table_cols = 8


def listeners_detail(listener: dict) -> str:
    trs = [
        htpy.tr[
            htpy.th["ID"],
            htpy.td(".user-select-all")[htpy.code[listener.get("user_id")]],
        ],
        htpy.tr[
            htpy.th["User name"],
            htpy.td(".user-select-all")[listener.get("user_name")],
        ],
        htpy.tr[
            htpy.th["Rank"],
            htpy.td(".user-select-all")[listener.get("rank_title")],
        ],
        htpy.tr[
            htpy.th["Discord user ID"],
            htpy.td(".user-select-all")[listener.get("discord_user_id")],
        ],
        htpy.tr[
            htpy.th["Last active"],
            htpy.td[
                listener.get("radio_last_active")
                and listener.get("radio_last_active").date().isoformat()
            ],
        ],
    ]
    content = [
        htpy.div(".g-1.pt-3.row")[
            htpy.div(".col-auto.me-auto")[
                htpy.a(".btn.btn-outline-primary", href=flask.url_for("listeners"))[
                    htpy.i(".bi-caret-left-fill"), " Listeners"
                ]
            ],
            _sign_out_button(True),
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Listener details"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[htpy.table(".align-middle.d-block.table")[htpy.tbody[trs]]]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.a(
                    ".btn.btn-outline-success",
                    href=flask.url_for(
                        "listeners_edit", listener_id=listener.get("user_id")
                    ),
                )[htpy.i(".bi-pencil"), " Edit listener"]
            ]
        ],
    ]
    return str(_base(content))


def listeners_edit(listener: dict) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            htpy.div(".col-auto.me-auto")[
                htpy.a(
                    ".btn.btn-outline-primary",
                    href=flask.url_for(
                        "listeners_detail", listener_id=listener.get("user_id")
                    ),
                )[htpy.i(".bi-caret-left-fill"), " Listener details"]
            ],
            _sign_out_button(True),
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Edit listener"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.form(method="post")[
                    htpy.table(".align-middle.d-block.table")[
                        htpy.tbody[
                            htpy.tr[
                                htpy.th["ID"],
                                htpy.td[htpy.code[listener.get("user_id")]],
                            ],
                            htpy.tr[
                                htpy.th["User name"], htpy.td[listener.get("user_name")]
                            ],
                            htpy.tr[
                                htpy.th[
                                    htpy.label(for_="discord_user_id")[
                                        "Discord user ID"
                                    ]
                                ],
                                htpy.td[
                                    htpy.input(
                                        "#discord_user_id.form-control",
                                        name="discord_user_id",
                                        type="text",
                                        value=listener.get("discord_user_id") or "",
                                    )
                                ],
                            ],
                        ]
                    ],
                    htpy.button(".btn.btn-outline-success", type="submit")[
                        htpy.i(".bi-file-earmark-play"), " Save"
                    ],
                ]
            ]
        ],
    ]
    return str(_base(content))


def listeners_index(ranks: list[dict]) -> str:
    content = [
        _nav_header("Listeners"),
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
                    htpy.thead[
                        htpy.tr(".text-center")[
                            htpy.th,
                            htpy.th["ID"],
                            htpy.th["User name"],
                            htpy.th["Group"],
                            htpy.th["Rank"],
                            htpy.th["Ratings"],
                            htpy.th["Discord"],
                            htpy.th["Last active"],
                        ]
                    ],
                    htpy.tbody(
                        hx_post=flask.url_for("listeners_rows"), hx_trigger="load"
                    )[
                        htpy.tr[
                            htpy.td(".py-3.text-center", colspan=_listeners_table_cols)[
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


def listeners_rows(listeners: list[dict], page: int) -> str:
    trs = []
    for i, listener in enumerate(listeners):
        if i < 100:
            trs.append(
                htpy.tr[
                    htpy.td(".text-center.text-nowrap")[
                        htpy.a(
                            ".text-decoration-none",
                            href=flask.url_for(
                                "listeners_detail", listener_id=listener.get("user_id")
                            ),
                            title="Listener detail page",
                        )[htpy.i(".bi-info-circle.me-1")],
                        htpy.a(
                            ".text-decoration-none",
                            href=f"https://rainwave.cc/all/#!/listener/{listener.get('user_id')}",
                            rel="noopener",
                            target="_blank",
                            title="Listener profile on rainwave.cc",
                        )[htpy.i(".bi-person-badge")],
                    ],
                    htpy.td(".text-end")[htpy.code[listener.get("user_id")]],
                    htpy.td(".user-select-all")[listener.get("user_name")],
                    htpy.td[listener.get("group_name")],
                    htpy.td(".user-select-all")[listener.get("rank_title")],
                    htpy.td[listener.get("rating_count")],
                    htpy.td(".text-center")[
                        listener.get("is_discord_user")
                        and htpy.i(
                            ".bi-check-lg", title=listener.get("discord_user_id")
                        )
                    ],
                    htpy.td[
                        listener.get("radio_last_active")
                        and listener.get("radio_last_active").date().isoformat()
                    ],
                ]
            )
        else:
            trs.append(
                htpy.tr[
                    htpy.td(
                        ".py-3.text-center",
                        colspan=_listeners_table_cols,
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
                htpy.td(colspan=_listeners_table_cols)[
                    "No listeners matched your criteria."
                ]
            ]
        )
    content = htpy.fragment[trs]
    return str(content)


def not_authorized() -> str:
    content = htpy.div(".align-items-center.d-flex.g-1.pt-3.row")[
        htpy.div(".col-auto.me-auto")[htpy.h1["Not authorized"]],
        _sign_out_button(False),
    ]
    return str(_base(content))


def sign_in() -> str:
    content = htpy.div(".pt-3.row")[
        htpy.div(".col")[
            htpy.a(".btn.btn-outline-primary", href=flask.url_for("sign_in"))["Sign in"]
        ]
    ]
    return str(_base(content))


def songs_index() -> str:
    content = [
        _nav_header("Songs"),
        htpy.form(action=flask.url_for("songs_xlsx"), hx_target="tbody", method="post")[
            htpy.div(".align-items-center.d-flex.g-2.pt-3.row")[
                htpy.div(".col-12.col-sm-auto")[
                    htpy.input(
                        ".form-control",
                        aria_label="Search songs",
                        hx_indicator="#filters-indicator",
                        hx_post=flask.url_for("songs_rows"),
                        hx_trigger="search, keyup changed delay:300ms",
                        name="q",
                        placeholder="Search songs...",
                        title="Case-insensitive search for album, title, artist, filename, or URL",
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
                                    for i, label in rainwave_library.channels.channels.items()
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
                htpy.table(".align-middle.table.table-bordered.table-sm")[
                    htpy.thead[
                        htpy.tr(".d-table-row.d-md-none.text-center")[
                            htpy.th, htpy.th["Info"]
                        ],
                        htpy.tr(".d-none.d-md-table-row.text-center")[
                            [
                                htpy.th[label]
                                for label in (
                                    "",
                                    "ID",
                                    "Album",
                                    "Title",
                                    "Artist",
                                    "Rating",
                                    "Ratings",
                                    "Length",
                                    "URL",
                                    "Filename",
                                )
                            ]
                        ],
                    ],
                    htpy.tbody(hx_post=flask.url_for("songs_rows"), hx_trigger="load")[
                        htpy.tr[
                            htpy.td(".py-3.text-center", colspan=10)[
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
