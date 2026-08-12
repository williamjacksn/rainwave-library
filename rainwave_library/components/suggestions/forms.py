import flask
import htpy

from rainwave_library.models.rainwave import (
    channels,
)
from rainwave_library.models.suggestions import (
    Suggestion,
)

from .detail import _suggestion_link_fields
from .wizard import _suggestion_wizard_body


def _suggestion_create_form(
    title: str = "",
    description: str = "",
    channel_id: int | None = None,
    links: tuple[tuple[str, str], ...] = (),
    result: tuple[str, str] | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_create")
    rainwave_channels = sorted(
        (
            (value, label)
            for value, label in channels.items()
            if isinstance(value, int) and value in {1, 2, 3, 4, 6}
        ),
        key=lambda item: item[1].casefold(),
    )
    return htpy.form(
        "#new-suggestion-form",
        action=url,
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="outerHTML",
        hx_target="this",
        method="post",
    )[
        result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
        htpy.div(".g-2.row")[
            htpy.div(".col-12.col-sm-8")[
                htpy.label(".form-label", for_="new-suggestion-title")["Title"],
                htpy.input(
                    "#new-suggestion-title.form-control",
                    name="title",
                    required=True,
                    type="text",
                    value=title,
                ),
            ],
            htpy.div(".col-12.col-sm-4")[
                htpy.label(".form-label", for_="new-suggestion-channel")["Channel"],
                htpy.select(
                    "#new-suggestion-channel.form-select",
                    name="channel",
                    required=True,
                )[
                    htpy.option(
                        disabled=True,
                        selected=channel_id is None,
                        value="",
                    )["Choose a channel"],
                    [
                        htpy.option(
                            selected=value == channel_id,
                            value=value,
                        )[label]
                        for value, label in rainwave_channels
                    ],
                ],
            ],
            htpy.div(".col-12")[
                htpy.label(".form-label", for_="new-suggestion-description")["Details"],
                htpy.textarea(
                    "#new-suggestion-description.form-control",
                    name="description",
                    required=True,
                    rows=3,
                )[description],
            ],
        ],
        htpy.div(".mt-3")[
            htpy.label(".form-label")["Links"],
            htpy.div("#new-suggestion-links.d-flex.flex-column.gap-2")[
                [
                    _suggestion_link_fields(url, label, required=True)
                    for url, label in links
                ]
            ],
            htpy.button(
                ".btn.btn-info.btn-sm.mt-2",
                hx_get=flask.url_for("suggestion_link_row", required=1),
                hx_swap="beforeend",
                hx_target="#new-suggestion-links",
                type="button",
            )[htpy.i(".bi-plus-lg"), " Add link"],
        ],
        htpy.div(".mt-3")[
            htpy.button(".btn.btn-success", type="submit")[
                htpy.i(".bi-plus-lg"), " Add suggestion"
            ]
        ],
    ]


def suggestion_create_form(
    title: str = "",
    description: str = "",
    channel_id: int | None = None,
    links: tuple[tuple[str, str], ...] = (),
    result: tuple[str, str] | None = None,
) -> str:
    return str(_suggestion_create_form(title, description, channel_id, links, result))


def _staff_suggestion_requester_discord_id_field(
    requester_discord_id: str = "",
) -> htpy.VoidElement:
    return htpy.input(
        "#staff-suggestion-requester-discord-id.form-control",
        name="requester-discord-id",
        type="text",
        value=requester_discord_id,
    )


def staff_suggestion_requester_discord_id_field(
    requester_discord_id: str = "",
) -> str:
    return str(
        _staff_suggestion_requester_discord_id_field(requester_discord_id),
    )


def _staff_suggestion_create_form(
    title: str = "",
    description: str = "",
    channel_id: int | None = None,
    kind: str = Suggestion.default_kind,
    requester_name: str = "",
    requester_discord_id: str = "",
    links: tuple[tuple[str, str], ...] = (),
    result: tuple[str, str] | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_staff_create")
    rainwave_channels = sorted(
        (
            (value, label)
            for value, label in channels.items()
            if isinstance(value, int) and value in {1, 2, 3, 4, 6}
        ),
        key=lambda item: item[1].casefold(),
    )
    return htpy.form(
        "#staff-suggestion-form",
        action=url,
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="outerHTML",
        hx_target="this",
        method="post",
    )[
        result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
        htpy.div(".g-3.row")[
            htpy.div(".col-12.col-md-6")[
                htpy.label(".form-label", for_="staff-suggestion-channel")["Channel"],
                htpy.select(
                    "#staff-suggestion-channel.form-select",
                    name="channel",
                    required=True,
                )[
                    htpy.option(
                        disabled=True,
                        selected=channel_id is None,
                        value="",
                    )["Choose a channel"],
                    [
                        htpy.option(
                            selected=value == channel_id,
                            value=value,
                        )[label]
                        for value, label in rainwave_channels
                    ],
                ],
            ],
            htpy.div(".col-12.col-md-6")[
                htpy.label(".form-label", for_="staff-suggestion-kind")[
                    "Suggestion type"
                ],
                htpy.select(
                    "#staff-suggestion-kind.form-select",
                    name="kind",
                    required=True,
                )[
                    [
                        htpy.option(selected=value == kind, value=value)[label]
                        for value, label in Suggestion.kind_labels.items()
                    ]
                ],
            ],
            htpy.div(".col-12")[
                htpy.label(".form-label", for_="staff-suggestion-title")[
                    "Suggestion title"
                ],
                htpy.input(
                    "#staff-suggestion-title.form-control",
                    name="title",
                    required=True,
                    type="text",
                    value=title,
                ),
            ],
            htpy.div(".col-12")[
                htpy.label(".form-label", for_="staff-suggestion-description")[
                    "Description"
                ],
                htpy.textarea(
                    "#staff-suggestion-description.form-control",
                    name="description",
                    required=True,
                    rows=6,
                )[description],
            ],
            htpy.div(".col-12.col-md-6")[
                htpy.label(".form-label", for_="staff-suggestion-requester-name")[
                    "Suggested by"
                ],
                htpy.input(
                    "#staff-suggestion-requester-name.form-control",
                    hx_get=flask.url_for("suggestion_staff_requester_discord_id"),
                    hx_include="this",
                    hx_swap="outerHTML",
                    hx_sync="this:replace",
                    hx_target="#staff-suggestion-requester-discord-id",
                    hx_trigger="input changed delay:300ms",
                    name="requester-name",
                    type="text",
                    value=requester_name,
                ),
            ],
            htpy.div(".col-12.col-md-6")[
                htpy.label(
                    ".form-label",
                    for_="staff-suggestion-requester-discord-id",
                )["Suggested by Discord ID"],
                _staff_suggestion_requester_discord_id_field(requester_discord_id),
            ],
            htpy.div(".col-12.form-text")[
                "Leave both Suggested by fields blank to attribute the suggestion "
                "to yourself. Enter a name in Suggested by to auto-fill the Discord ID "
                "based on existing suggestions."
            ],
        ],
        htpy.div(".mt-3")[
            htpy.label(".form-label")["Links"],
            htpy.div("#staff-suggestion-links.d-flex.flex-column.gap-2")[
                [
                    _suggestion_link_fields(url, label, required=True)
                    for url, label in links
                ]
            ],
            htpy.button(
                ".btn.btn-info.btn-sm.mt-2",
                hx_get=flask.url_for("suggestion_link_row", required=1),
                hx_swap="beforeend",
                hx_target="#staff-suggestion-links",
                type="button",
            )[htpy.i(".bi-plus-lg"), " Add link"],
        ],
        htpy.div(".mt-3")[
            htpy.button(".btn.btn-success", type="submit")[
                htpy.i(".bi-plus-lg"), " Create suggestion"
            ]
        ],
    ]


def staff_suggestion_create_form(
    title: str = "",
    description: str = "",
    channel_id: int | None = None,
    kind: str = Suggestion.default_kind,
    requester_name: str = "",
    requester_discord_id: str = "",
    links: tuple[tuple[str, str], ...] = (),
    result: tuple[str, str] | None = None,
) -> str:
    return str(
        _staff_suggestion_create_form(
            title=title,
            description=description,
            channel_id=channel_id,
            kind=kind,
            requester_name=requester_name,
            requester_discord_id=requester_discord_id,
            links=links,
            result=result,
        )
    )


def _suggestion_create_modal(song_count: int, song_count_as_of: str) -> htpy.Element:
    return htpy.div(
        "#new-suggestion-modal.fade.modal",
        aria_hidden="true",
        aria_labelledby="new-suggestion-modal-title",
        tabindex="-1",
    )[
        htpy.div(".modal-dialog.modal-dialog-scrollable.modal-lg")[
            htpy.div(".modal-content")[
                htpy.div(".modal-header")[
                    htpy.h5("#new-suggestion-modal-title.modal-title")[
                        "New suggestion"
                    ],
                    htpy.button(
                        ".btn-close",
                        aria_label="Close",
                        data_bs_dismiss="modal",
                        type="button",
                    ),
                ],
                htpy.div("#new-suggestion-modal-body.modal-body")[
                    _suggestion_wizard_body(
                        1,
                        song_count=song_count,
                        song_count_as_of=song_count_as_of,
                    )
                ],
            ]
        ]
    ]


def _staff_suggestion_create_modal() -> htpy.Element:
    return htpy.div(
        "#staff-suggestion-modal.fade.modal",
        aria_hidden="true",
        aria_labelledby="staff-suggestion-modal-title",
        tabindex="-1",
    )[
        htpy.div(".modal-dialog.modal-dialog-scrollable.modal-lg")[
            htpy.div(".modal-content")[
                htpy.div(".modal-header")[
                    htpy.h5("#staff-suggestion-modal-title.modal-title")[
                        "Create a suggestion"
                    ],
                    htpy.button(
                        ".btn-close",
                        aria_label="Close",
                        data_bs_dismiss="modal",
                        type="button",
                    ),
                ],
                htpy.div(".modal-body")[_staff_suggestion_create_form()],
            ]
        ]
    ]
