import flask
import htpy

from rainwave_library.models.mp3 import (
    Mp3TagValues,
)
from rainwave_library.models.rainwave import (
    channel_badge,
)
from rainwave_library.models.suggestions import (
    Suggestion,
    SuggestionDetail,
    SuggestionFileReview,
)

from ..common import _back_button, _base, _collapsible_card_header, _user_menu
from .activity import _suggestion_activity_block
from .content import (
    _suggestion_description_block,
    _suggestion_links_block,
    _suggestion_title_block,
)
from .files import _suggestion_files_card
from .release import (
    _suggestion_schedule_release_button,
    _suggestion_schedule_release_modal,
)
from .summary import (
    _suggestion_detail_table,
    _suggestion_edit_form,
    _suggestion_preview_staff_actions,
    _suggestion_status_badge,
    _suggestion_user_identity,
    _suggestion_value,
)


def suggestion_page(
    suggestion: SuggestionDetail,
    staged_files: tuple[tuple[str, int], ...] = (),
    *,
    folder_path: str | None = None,
    music_tags: dict[str, Mp3TagValues] | None = None,
    music_reviews: dict[str, SuggestionFileReview] | None = None,
    staged_mp3_duration_seconds: float = 0.0,
) -> str:
    channel_badges: htpy.Node = (
        htpy.fragment[
            [channel_badge(channel_id) for channel_id in suggestion.channel_ids]
        ]
        if suggestion.channel_ids
        else htpy.span(".text-secondary")["—"]
    )
    summary = _suggestion_detail_table(
        [
            ("Suggestion ID", htpy.code[suggestion.id]),
            ("Status", _suggestion_status_badge(suggestion.status)),
            (
                "Suggestion type",
                Suggestion.kind_labels.get(suggestion.kind, suggestion.kind),
            ),
            ("Channels", channel_badges),
            ("Suggested by", _suggestion_value(suggestion.requester_name)),
        ]
    )
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("suggestions"), "Music suggestions"),
            _user_menu(),
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Suggestion details"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.div(".card")[
                    _collapsible_card_header(
                        "suggestion-summary-card-body",
                        suggestion.title,
                        htpy.h5(".mb-0")[suggestion.title],
                    ),
                    htpy.div("#suggestion-summary-card-body.card-body.collapse.show")[
                        summary,
                        htpy.div(".d-flex.justify-content-start.mt-3")[
                            _suggestion_schedule_release_button()
                        ],
                    ],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.div(".card")[
                    _collapsible_card_header(
                        "suggestion-links-card-body",
                        "Links",
                        htpy.h5(".mb-0")["Links"],
                    ),
                    htpy.div("#suggestion-links-card-body.card-body.collapse.show")[
                        _suggestion_links_block(suggestion)
                    ],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.div(".card")[
                    _collapsible_card_header(
                        "suggestion-activity-card-body",
                        "Activity",
                        htpy.h5(".mb-0")["Activity"],
                    ),
                    htpy.div("#suggestion-activity-card-body.card-body.collapse.show")[
                        _suggestion_activity_block(suggestion)
                    ],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                _suggestion_files_card(
                    suggestion.id,
                    staged_files,
                    folder_path=folder_path,
                    music_tags=music_tags,
                    music_reviews=music_reviews,
                )
            ]
        ],
        _suggestion_schedule_release_modal(
            suggestion,
            staged_mp3_duration_seconds,
        ),
        htpy.div("#audio"),
    ]
    return str(_base(content))


def _suggestion_detail_item(title: str, content: htpy.Node) -> htpy.Element:
    return htpy.div(".col-auto")[
        htpy.div(".border-bottom.fw-bold.small.text-body-secondary.text-uppercase")[
            title
        ],
        content,
    ]


def suggestion_detail_row(
    suggestion: SuggestionDetail,
    *,
    editable: bool = False,
    edit_result: tuple[str, str] | None = None,
) -> str:
    owner_editable = (
        not editable
        and bool(suggestion.requester_discord_id)
        and suggestion.requester_discord_id == str(flask.g.discord_id or "")
        and suggestion.status in Suggestion.owner_editable_statuses
    )
    channel_badges: htpy.Node = (
        htpy.fragment[
            [channel_badge(channel_id) for channel_id in suggestion.channel_ids]
        ]
        if suggestion.channel_ids
        else htpy.span(".text-secondary")["—"]
    )
    content = htpy.tr(id=f"suggestion-row-{suggestion.id}")[
        htpy.td(".p-0", colspan=Suggestion.colspan)[
            htpy.div(".border-0.card.rounded-0")[
                htpy.div(".align-items-center.card-header.d-flex.gap-2.px-2.rounded-0")[
                    htpy.button(
                        ".btn.btn-secondary.btn-sm",
                        aria_label="Close suggestion details",
                        hx_get=flask.url_for(
                            "suggestion_row", suggestion_id=suggestion.id
                        ),
                        hx_swap="outerHTML",
                        hx_target="closest tr",
                        title="Close suggestion details",
                        type="button",
                    )[htpy.i(".bi-x-lg")],
                    _suggestion_title_block(
                        suggestion,
                        editable=owner_editable,
                    ),
                ],
                htpy.div(".card-body.p-2")[
                    editable and _suggestion_edit_form(suggestion, edit_result),
                    not editable
                    and htpy.fragment[
                        _suggestion_preview_staff_actions(suggestion),
                        htpy.div(".g-3.row")[
                            _suggestion_detail_item(
                                "Suggestion type",
                                Suggestion.kind_labels.get(
                                    suggestion.kind, suggestion.kind
                                ),
                            ),
                            _suggestion_detail_item("Channel", channel_badges),
                            _suggestion_detail_item(
                                "Status", _suggestion_status_badge(suggestion.status)
                            ),
                            _suggestion_detail_item(
                                "Suggested by",
                                _suggestion_user_identity(
                                    suggestion.requester_name,
                                    suggestion.requester_avatar_url,
                                ),
                            ),
                            _suggestion_detail_item(
                                "Suggested at",
                                _suggestion_value(
                                    suggestion.requested_at[:10]
                                    if suggestion.requested_at is not None
                                    else None
                                ),
                            ),
                            _suggestion_detail_item(
                                "Claimed by",
                                _suggestion_user_identity(
                                    suggestion.claimed_by_name,
                                    suggestion.claimed_by_avatar_url,
                                ),
                            ),
                            _suggestion_detail_item(
                                "Claimed at",
                                _suggestion_value(
                                    suggestion.claimed_at[:10]
                                    if suggestion.claimed_at is not None
                                    else None
                                ),
                            ),
                            _suggestion_detail_item(
                                "Completed at",
                                _suggestion_value(
                                    suggestion.resolved_at[:10]
                                    if suggestion.resolved_at is not None
                                    else None
                                ),
                            ),
                        ],
                        _suggestion_description_block(
                            suggestion,
                            editable=owner_editable,
                        ),
                    ],
                    htpy.h6(".mt-3")["Links"],
                    _suggestion_links_block(suggestion, is_staff=editable),
                    htpy.h6(".mt-3")["Activity"],
                    _suggestion_activity_block(suggestion),
                ],
            ]
        ]
    ]
    return str(content)


def _suggestion_link_fields(
    url: str = "",
    label: str = "",
    *,
    required: bool = False,
) -> htpy.Element:
    return htpy.div(".align-items-center.g-2.row.suggestion-link-fields")[
        htpy.div(".col-12.col-sm-5")[
            htpy.input(
                ".form-control",
                aria_label="Link URL",
                name="link-url",
                placeholder="https://example.com",
                required=required,
                type="url",
                value=url,
            ),
        ],
        htpy.div(".col")[
            htpy.input(
                ".form-control",
                aria_label="Link label",
                name="link-label",
                placeholder="Label",
                required=required,
                type="text",
                value=label,
            ),
        ],
        htpy.div(".col-auto")[
            htpy.button(
                ".btn.btn-danger",
                aria_label="Remove link",
                hx_get=flask.url_for("suggestion_link_row", close=1),
                hx_swap="outerHTML",
                hx_target="closest .suggestion-link-fields",
                title="Remove link",
                type="button",
            )[htpy.i(".bi-x-lg")],
        ],
    ]


def suggestion_link_fields(*, required: bool = False) -> str:
    return str(_suggestion_link_fields(required=required))
