import flask
import htpy

from rainwave_library.models.rainwave import (
    Album,
    Song,
)

from .common import _back_button, _base, _user_menu


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
        htpy.div("#audio"),
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
                htpy.a(".btn.btn-warning", href=flask.url_for("albums_missing_art"))[
                    htpy.i(".bi-image"), " Missing art"
                ]
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
