import flask
import htpy
import markupsafe

from .common import _back_button, _base, _user_menu


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
    return str(_base(content, body_class="sign-in-body"))


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
                                ".btn.btn-warning.mt-3",
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
