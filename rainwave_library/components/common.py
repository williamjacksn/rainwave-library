import flask
import htpy
import markupsafe

import rainwave_library.versions as v

_cdn = "https://cdn.jsdelivr.net/npm"


def _back_button(href: str, label: str) -> htpy.Renderable:
    return htpy.div(".col-auto.me-auto")[
        htpy.a(".btn.btn-primary", href=href)[htpy.i(".bi-caret-left-fill"), " ", label]
    ]


def _base(content: htpy.Node, *, body_class: str | None = None) -> htpy.Renderable:
    return htpy.html(
        data_bs_theme=getattr(flask.g, "color_mode", "light"),
        lang="en",
    )[
        htpy.head[
            htpy.title["Rainwave Library"],
            htpy.meta(content="width=device-width, initial-scale=1", name="viewport"),
            _favicon(),
            _bs_stylesheet(),
            _bi_stylesheet(),
            htpy.link(
                href=flask.url_for("static", filename="app.css"),
                rel="stylesheet",
            ),
        ],
        htpy.body(class_=body_class)[
            htpy.div(".container-fluid")[
                content,
                htpy.div(".pt-3.row")[htpy.div(".col")[htpy.hr]],
            ],
            _remote_modal(),
            _bs_script(),
            _hx_script(),
            _remote_modal_script(),
        ],
    ]


def _modal_loading_content() -> htpy.Element:
    return htpy.div("#modal-lg-content.modal-content")[
        htpy.div(".modal-body.text-center")[htpy.div(".spinner-border")]
    ]


def _remote_modal() -> htpy.Element:
    return htpy.div("#modal-lg.fade.modal", data_remote_modal="true")[
        htpy.div(".modal-dialog.modal-lg")[_modal_loading_content()],
        htpy.template("#modal-lg-loading-template")[_modal_loading_content()],
    ]


def _remote_modal_script() -> htpy.Element:
    script = markupsafe.Markup(
        """
        document.addEventListener("hidden.bs.modal", (event) => {
            const modal = event.target;
            if (
                !(modal instanceof Element) ||
                !modal.matches("[data-remote-modal]")
            ) {
                return;
            }
            const content = modal.querySelector(".modal-content");
            const template = modal.querySelector("#modal-lg-loading-template");
            if (
                content &&
                template instanceof HTMLTemplateElement
            ) {
                content.replaceWith(template.content.cloneNode(true));
            }
        });
        """
    )
    return htpy.script[script]


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
                        role, impersonator and " (impersonating)"
                    ]
                ],
                htpy.li[htpy.hr(".dropdown-divider")],
                htpy.li[
                    htpy.a(
                        ".dropdown-item",
                        href=flask.url_for("user_settings"),
                    )[htpy.i(".bi-gear.me-2"), "User settings"]
                ],
                role == "staff"
                and not impersonator
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


def _collapsible_card_header(
    collapse_id: str,
    label: str,
    content: htpy.Node,
) -> htpy.Element:
    return htpy.div(
        ".align-items-center.card-header.d-flex.gap-3."
        "justify-content-between.position-relative"
    )[
        htpy.div(".flex-grow-1", style="min-width: 0")[content],
        htpy.button(
            ".btn.btn-link.p-0.stretched-link.text-body",
            aria_controls=collapse_id,
            aria_expanded="true",
            aria_label=f"Toggle {label}",
            data_bs_target=f"#{collapse_id}",
            data_bs_toggle="collapse",
            title=f"Toggle {label}",
            type="button",
        )[
            htpy.i(".bi-chevron-down.flex-shrink-0"),
            htpy.span(".visually-hidden")[f"Toggle {label}"],
        ],
    ]


def _duration_hms(duration_seconds: float) -> str:
    total_seconds = int(duration_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"
