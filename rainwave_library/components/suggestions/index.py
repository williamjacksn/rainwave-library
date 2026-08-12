import flask
import htpy

from rainwave_library.models.rainwave import (
    channel_badge,
    channels,
)
from rainwave_library.models.suggestions import (
    Suggestion,
    SuggestionFilterSet,
)

from ..common import _back_button, _base, _user_menu
from .forms import _staff_suggestion_create_modal, _suggestion_create_modal
from .summary import _suggestion_row


def _suggestions_sort_options_control(filters: SuggestionFilterSet) -> htpy.Element:
    rows_url = flask.url_for("suggestions_rows")
    return htpy.div(".dropdown")[
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
                            f"#suggestion-sort-dir-{value}.form-check-input",
                            checked=value == filters.sort_dir,
                            hx_indicator="#suggestion-filters-indicator",
                            hx_post=rows_url,
                            name="sort-dir",
                            type="radio",
                            value=value,
                        ),
                        htpy.label(
                            ".form-check-label",
                            for_=f"suggestion-sort-dir-{value}",
                        )[label],
                    ]
                    for value, label in (
                        ("asc", "Ascending"),
                        ("desc", "Descending"),
                    )
                ],
                htpy.hr,
                [
                    htpy.div(".form-check")[
                        htpy.input(
                            f"#suggestion-sort-col-{value}.form-check-input",
                            checked=value == filters.sort_col,
                            hx_indicator=("#suggestion-filters-indicator"),
                            hx_post=rows_url,
                            name="sort-col",
                            type="radio",
                            value=value,
                        ),
                        htpy.label(
                            ".form-check-label.text-nowrap",
                            for_=f"suggestion-sort-col-{value}",
                        )[label],
                    ]
                    for value, label in Suggestion.sort_fields
                ],
            ]
        ],
    ]


def _suggestions_claimed_by_filter(
    claimants: list[str], filters: SuggestionFilterSet
) -> htpy.Element:
    rows_url = flask.url_for("suggestions_rows")
    empty = len(filters.claimed_by) == 0
    return htpy.div(".dropdown")[
        htpy.button(
            ".btn.btn-primary.dropdown-toggle",
            data_bs_toggle="dropdown",
            title="Claimant selection",
            type="button",
        )[htpy.i(".bi-person-check")],
        htpy.div(".dropdown-menu")[
            htpy.div(".px-2")[
                htpy.h6(".dropdown-header")["CLAIMED BY"],
                htpy.div(".form-check")[
                    htpy.input(
                        "#suggestion-claimant-unclaimed.form-check-input",
                        checked="" in filters.claimed_by or empty,
                        hx_indicator="#suggestion-filters-indicator",
                        hx_post=rows_url,
                        name="claimed-by",
                        type="checkbox",
                        value="",
                    ),
                    htpy.label(
                        ".form-check-label.text-nowrap",
                        for_="suggestion-claimant-unclaimed",
                    )["(unclaimed)"],
                ],
                [
                    htpy.div(".form-check")[
                        htpy.input(
                            f"#suggestion-claimant-{index}.form-check-input",
                            checked=claimant in filters.claimed_by or empty,
                            hx_indicator="#suggestion-filters-indicator",
                            hx_post=rows_url,
                            name="claimed-by",
                            type="checkbox",
                            value=claimant,
                        ),
                        htpy.label(
                            ".form-check-label.text-nowrap",
                            for_=f"suggestion-claimant-{index}",
                        )[claimant],
                    ]
                    for index, claimant in enumerate(claimants)
                ],
            ]
        ],
    ]


def _suggestions_channel_filter(filters: SuggestionFilterSet) -> htpy.Element:
    rows_url = flask.url_for("suggestions_rows")
    rainwave_channels = sorted(
        (
            (channel_id, label)
            for channel_id, label in channels.items()
            if isinstance(channel_id, int) and channel_id in {1, 2, 3, 4, 6}
        ),
        key=lambda channel: channel[1].casefold(),
    )
    empty_channel_list = len(filters.channel) == 0
    return htpy.div(".dropdown")[
        htpy.button(
            ".btn.btn-primary.dropdown-toggle",
            data_bs_toggle="dropdown",
            title="Channel selection",
            type="button",
        )[htpy.i(".bi-broadcast-pin")],
        htpy.div(".dropdown-menu")[
            htpy.div(".px-2")[
                htpy.h6(".dropdown-header")["CHANNEL"],
                htpy.div(".form-check")[
                    htpy.input(
                        "#suggestion-channel-unassigned.form-check-input",
                        checked="unassigned" in filters.channel or empty_channel_list,
                        hx_indicator="#suggestion-filters-indicator",
                        hx_post=rows_url,
                        name="channels",
                        type="checkbox",
                        value="unassigned",
                    ),
                    htpy.label(
                        ".form-check-label.text-nowrap",
                        for_="suggestion-channel-unassigned",
                    )["(no channel)"],
                ],
                [
                    htpy.div(".form-check")[
                        htpy.input(
                            f"#suggestion-channel-{channel_id}.form-check-input",
                            checked=str(channel_id) in filters.channel
                            or empty_channel_list,
                            hx_indicator="#suggestion-filters-indicator",
                            hx_post=rows_url,
                            name="channels",
                            type="checkbox",
                            value=channel_id,
                        ),
                        htpy.label(
                            ".form-check-label.text-nowrap",
                            for_=f"suggestion-channel-{channel_id}",
                        )[channel_badge(channel_id)],
                    ]
                    for channel_id, _label in rainwave_channels
                ],
            ]
        ],
    ]


def _suggestions_status_filter(filters: SuggestionFilterSet) -> htpy.Element:
    rows_url = flask.url_for("suggestions_rows")
    return htpy.div(".dropdown")[
        htpy.button(
            ".btn.btn-primary.dropdown-toggle",
            data_bs_toggle="dropdown",
            title="Status selection",
            type="button",
        )[htpy.i(".bi-flag")],
        htpy.div(".dropdown-menu")[
            htpy.div(".px-2")[
                htpy.h6(".dropdown-header")["STATUS"],
                [
                    htpy.div(".form-check")[
                        htpy.input(
                            f"#status-{status}.form-check-input",
                            checked=status in filters.status,
                            hx_indicator="#suggestion-filters-indicator",
                            hx_post=rows_url,
                            name="status",
                            type="checkbox",
                            value=status,
                        ),
                        htpy.label(
                            ".form-check-label",
                            for_=f"status-{status}",
                        )[status.title()],
                    ]
                    for status in Suggestion.statuses
                ],
            ]
        ],
    ]


def _suggestions_type_filter(filters: SuggestionFilterSet) -> htpy.Element:
    rows_url = flask.url_for("suggestions_rows")
    return htpy.div(".dropdown")[
        htpy.button(
            ".btn.btn-primary.dropdown-toggle",
            data_bs_toggle="dropdown",
            title="Suggestion type selection",
            type="button",
        )[htpy.i(".bi-tags")],
        htpy.div(".dropdown-menu")[
            htpy.div(".px-2")[
                htpy.h6(".dropdown-header")["SUGGESTION TYPE"],
                [
                    htpy.div(".form-check")[
                        htpy.input(
                            f"#suggestion-kind-{kind}.form-check-input",
                            checked=kind in filters.type,
                            hx_indicator="#suggestion-filters-indicator",
                            hx_post=rows_url,
                            name="kinds",
                            type="checkbox",
                            value=kind,
                        ),
                        htpy.label(
                            ".form-check-label.text-nowrap",
                            for_=f"suggestion-kind-{kind}",
                        )[label],
                    ]
                    for kind, label in Suggestion.kind_labels.items()
                ],
            ]
        ],
    ]


def _suggestions_other_filter_options(
    is_staff: bool,
    filters: SuggestionFilterSet,
    your_suggestions_active_count: int,
    your_suggestions_complete_count: int,
) -> htpy.Element:
    rows_url = flask.url_for("suggestions_rows")
    return htpy.div(".dropdown")[
        htpy.button(
            ".btn.btn-primary.dropdown-toggle",
            data_bs_toggle="dropdown",
            title="Filter options",
            type="button",
        )[htpy.i(".bi-list-check")],
        htpy.div(".dropdown-menu")[
            htpy.div(".px-2")[
                htpy.h6(".dropdown-header")["FILTER OPTIONS"],
                htpy.div(".form-check")[
                    htpy.input(
                        "#your-suggestions.form-check-input",
                        checked=filters.your_suggestions,
                        hx_indicator="#suggestion-filters-indicator",
                        hx_post=rows_url,
                        name="your-suggestions",
                        type="checkbox",
                        value="1",
                    ),
                    htpy.label(
                        ".form-check-label.text-nowrap",
                        for_="your-suggestions",
                    )[
                        "Your suggestions (",
                        str(your_suggestions_active_count),
                        " active, ",
                        str(your_suggestions_complete_count),
                        " complete",
                        ")",
                    ],
                ],
                is_staff
                and htpy.div(".form-check")[
                    htpy.input(
                        "#your-claims.form-check-input",
                        checked=filters.your_claims,
                        hx_indicator="#suggestion-filters-indicator",
                        hx_post=rows_url,
                        name="your-claims",
                        type="checkbox",
                        value="1",
                    ),
                    htpy.label(
                        ".form-check-label.text-nowrap",
                        for_="your-claims",
                    )["Your claims"],
                ],
            ]
        ],
    ]


def suggestions_index(
    is_staff: bool,
    claimants: list[str],
    filters: SuggestionFilterSet,
    your_suggestions_active_count: int,
    your_suggestions_complete_count: int,
    song_count: int = 0,
    song_count_as_of: str = "",
) -> str:
    rows_url = flask.url_for("suggestions_rows")
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Music suggestions"]]],
        htpy.div(".g-1.pt-3.row")[
            htpy.div(".col-auto")[
                htpy.button(
                    ".btn.btn-success.mb-1",
                    data_bs_target="#new-suggestion-modal",
                    data_bs_toggle="modal",
                    type="button",
                )[htpy.i(".bi-plus-lg"), " New suggestion"]
            ],
            is_staff
            and htpy.div(".col-auto")[
                htpy.button(
                    ".btn.btn-success.mb-1",
                    data_bs_target="#staff-suggestion-modal",
                    data_bs_toggle="modal",
                    type="button",
                )[htpy.i(".bi-lightning-charge"), " Quick add suggestion"]
            ],
        ],
        _suggestion_create_modal(song_count, song_count_as_of),
        is_staff and _staff_suggestion_create_modal(),
        htpy.form(
            "#suggestion-filters",
            hx_include="#suggestion-filters",
            hx_target="#suggestion-rows",
            onsubmit="return false",
        )[
            htpy.div(".align-items-center.g-1.pt-3.row")[
                htpy.div(".col-12.col-md-5")[
                    htpy.input(
                        ".form-control",
                        aria_label="Search music suggestions",
                        hx_indicator="#suggestion-filters-indicator",
                        hx_post=rows_url,
                        hx_trigger="search, keyup changed delay:300ms",
                        name="q",
                        placeholder="Search suggestions...",
                        type="search",
                    )
                ],
                htpy.div(".col-auto")[_suggestions_sort_options_control(filters)],
                htpy.div(".col-auto")[
                    _suggestions_claimed_by_filter(claimants, filters)
                ],
                htpy.div(".col-auto")[_suggestions_channel_filter(filters)],
                htpy.div(".col-auto")[_suggestions_status_filter(filters)],
                htpy.div(".col-auto")[_suggestions_type_filter(filters)],
                htpy.div(".col-auto")[
                    _suggestions_other_filter_options(
                        is_staff,
                        filters,
                        your_suggestions_active_count,
                        your_suggestions_complete_count,
                    )
                ],
                htpy.div(".col-auto")[
                    htpy.span(
                        "#suggestion-filters-indicator.htmx-indicator.spinner-border.spinner-border-sm.text-primary"
                    )
                ],
                htpy.div(".align-items-center.col-auto.d-flex.ms-auto")[
                    htpy.div("#suggestion-filter-save-result.small"),
                    htpy.button(
                        ".btn.btn-success.ms-2",
                        hx_include="#suggestion-filters",
                        hx_indicator="#suggestion-filters-indicator",
                        hx_post=flask.url_for("suggestion_default_filters"),
                        hx_swap="innerHTML",
                        hx_target="#suggestion-filter-save-result",
                        title="Use the current sort and filter selections by default",
                        type="button",
                    )[htpy.i(".bi-bookmark-heart")],
                ],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.div[
                    htpy.table(
                        ".align-middle.table.table-bordered.table-sm.table-striped"
                    )[
                        htpy.thead[
                            htpy.tr(".text-center")[
                                htpy.th,
                                htpy.th(".d-table-cell.d-md-none")["Suggestion"],
                                [
                                    htpy.th(".d-none.d-md-table-cell.text-nowrap")[
                                        label
                                    ]
                                    for label in (
                                        "Status",
                                        "Channels",
                                        "Suggestion title",
                                        "Suggestion type",
                                        "Suggested by",
                                        "Suggested at",
                                        "Claimed by",
                                    )
                                ],
                            ]
                        ],
                        htpy.tbody(
                            "#suggestion-rows",
                            hx_include="#suggestion-filters",
                            hx_post=rows_url,
                            hx_trigger="load",
                        )[
                            htpy.tr[
                                htpy.td(
                                    ".py-3.text-center", colspan=Suggestion.colspan
                                )[
                                    htpy.span(
                                        ".htmx-indicator.spinner-border.spinner-border-sm"
                                    )
                                ]
                            ]
                        ],
                    ]
                ]
            ]
        ],
    ]
    return str(_base(content))


def suggestion_default_filters_saved() -> str:
    return str(
        htpy.span(".text-success")[
            htpy.i(".bi-check-circle-fill"), " Default filters saved"
        ]
    )


def suggestions_rows(suggestions: list[Suggestion], page: int) -> str:
    rows = []
    for index, suggestion in enumerate(suggestions):
        if index < 100:
            rows.append(_suggestion_row(suggestion))
        else:
            rows.append(
                htpy.tr[
                    htpy.td(
                        ".py-3.text-center",
                        colspan=Suggestion.colspan,
                        hx_include="#suggestion-filters",
                        hx_post=flask.url_for("suggestions_rows", page=page + 1),
                        hx_swap="outerHTML",
                        hx_target="closest tr",
                        hx_trigger="revealed",
                    )[htpy.span(".htmx-indicator.spinner-border.spinner-border-sm")]
                ]
            )
    if not rows:
        rows.append(
            htpy.tr[
                htpy.td(".py-3.text-center", colspan=Suggestion.colspan)[
                    "No suggestions found."
                ]
            ]
        )
    clear_save_result = page == 1 and htpy.div(
        "#suggestion-filter-save-result", hx_swap_oob="innerHTML"
    )
    return str(htpy.fragment[rows, clear_save_result])
