import flask
import htpy

from rainwave_library.models.rainwave import (
    Artist,
    Song,
)

from .common import _back_button, _base, _user_menu


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
                    ".btn.btn-warning",
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
                                htpy.button(".btn.btn-warning", type="submit")[
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
