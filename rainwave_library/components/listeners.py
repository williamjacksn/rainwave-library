import flask
import htpy

from rainwave_library.models.rainwave import (
    Listener,
)

from .common import _back_button, _base, _user_menu


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
                                        ("registered", "user_regdate", "Registered"),
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
                            ".btn.btn-primary.dropdown-toggle",
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
