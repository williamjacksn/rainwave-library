import flask
import htpy

from .common import _back_button, _base, _user_menu


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
                    htpy.button(".btn.btn-primary", type="submit")[
                        htpy.i(".bi-send"), " Post"
                    ],
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
            htpy.a(".btn.btn-success", href=flask.url_for("get_ocremix"))[
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
                htpy.a(".btn.btn-success.me-1", href=flask.url_for("get_ocremix"))[
                    htpy.i(".bi-arrow-counterclockwise"), " Start over"
                ],
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
