import flask
import htpy
import rainwave_library.versions as v


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


def sign_in() -> str:
    content = htpy.div(".pt-3.row")[
        htpy.div(".col")[
            htpy.a(".btn.btn-outline-primary", href=flask.url_for("sign_in"))["Sign in"]
        ]
    ]
    return str(_base(content))
