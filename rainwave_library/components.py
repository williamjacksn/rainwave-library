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
