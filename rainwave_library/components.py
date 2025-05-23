import flask
import htpy
import rainwave_library.versions as v


def _base(content: htpy.Node) -> htpy.Element:
    return htpy.html(lang="en")[
        htpy.head[
            htpy.title["Rainwave Library"],
            htpy.meta(content="width=device-width, initial-scale=1", name="viewport"),
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
        htpy.div(".pt-3.row")[
            htpy.div(".col-auto")[
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
    for i, l in enumerate(listeners):
        if i < 100:
            trs.append(
                htpy.tr[
                    htpy.td(".text-center.text-nowrap")[
                        htpy.a(
                            ".text-decoration-none",
                            href=flask.url_for(
                                "listeners_detail", listener_id=l.get("user_id")
                            ),
                            title="Listener detail page",
                        )[htpy.i(".bi-info-circle.me-1")],
                        htpy.a(
                            ".text-decoration-none",
                            href=f"https://rainwave.cc/all/#!/listener/{l.get('user_id')}",
                            rel="noopener",
                            target="_blank",
                            title="Listener profile on rainwave.cc",
                        )[htpy.i(".bi-person-badge")],
                    ],
                    htpy.td(".text-end")[htpy.code[l.get("user_id")]],
                    htpy.td(".user-select-all")[l.get("user_name")],
                    htpy.td[l.get("group_name")],
                    htpy.td(".user-select-all")[l.get("rank_title")],
                    htpy.td[l.get("rating_count")],
                    htpy.td(".text-center")[
                        l.get("is_discord_user")
                        and htpy.i(".bi-check-lg", title=l.get("discord_user_id"))
                    ],
                    htpy.td[
                        l.get("radio_last_active")
                        and l.get("radio_last_active").date().isoformat()
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
