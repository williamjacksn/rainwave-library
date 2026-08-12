import flask
import htpy

from rainwave_library.models.suggestions import (
    Suggestion,
    SuggestionActivity,
    SuggestionDetail,
)

from .summary import _suggestion_value


def _suggestion_activity_actor(activity: SuggestionActivity) -> htpy.Element:
    name = activity.actor_name or "—"
    if activity.actor_discord_id:
        return htpy.strong(title=f"Discord user {activity.actor_discord_id}")[name]
    if activity.trello_member_id:
        return htpy.strong(title=f"Trello member {activity.trello_member_id}")[name]
    return htpy.strong[name]


def _suggestion_activity_details(activity: SuggestionActivity) -> htpy.Node:
    details: list[htpy.Node] = []
    if activity.body:
        details.append(
            htpy.div(style="white-space: pre-wrap")[activity.body],
        )
    if activity.old_value is not None or activity.new_value is not None:
        change = htpy.div(".mt-2") if details else htpy.div
        details.append(
            change[
                _suggestion_value(activity.old_value),
                " → ",
                _suggestion_value(activity.new_value),
            ]
        )
    if not details:
        return None

    details_length = sum(
        len(value or "")
        for value in (activity.body, activity.old_value, activity.new_value)
    )
    if activity.type != "comment" and details_length > 300:
        return htpy.details(".mt-2")[
            htpy.summary["Show details"],
            htpy.div(".mt-2")[details],
        ]
    return htpy.div(".mt-2")[details]


def _suggestion_activity_item(activity: SuggestionActivity) -> htpy.Element:
    return htpy.div(".list-group-item")[
        htpy.div(".d-flex.flex-wrap.gap-2.justify-content-between")[
            htpy.span[
                _suggestion_activity_actor(activity),
                " ",
                activity.type.replace("-", " "),
            ],
            htpy.span(".small.text-secondary")[activity.created_at],
        ],
        _suggestion_activity_details(activity),
    ]


def _suggestion_comment_button(suggestion_id: str) -> htpy.Element:
    return htpy.button(
        ".btn.btn-primary.btn-sm",
        data_bs_target="#modal-lg",
        data_bs_toggle="modal",
        hx_get=flask.url_for("suggestion_comment", suggestion_id=suggestion_id),
        hx_swap="outerHTML",
        hx_target="#modal-lg-content",
        type="button",
    )[htpy.i(".bi-chat-left-text"), " Add a comment"]


def suggestion_comment_button(suggestion_id: str) -> str:
    return str(_suggestion_comment_button(suggestion_id))


def _suggestion_comment_form(
    suggestion: SuggestionDetail,
    body: str = "",
    error: str | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_comment", suggestion_id=suggestion.id)
    after_request = (
        "if (event.detail.successful && "
        "!event.detail.xhr.getResponseHeader('HX-Retarget')) {"
        "bootstrap.Modal.getOrCreateInstance("
        "document.getElementById('modal-lg')).hide();"
        "}"
    )
    return htpy.form(
        "#modal-lg-content.modal-content",
        action=url,
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="outerHTML",
        hx_target=f"#suggestion-activity-{suggestion.id}",
        method="post",
        **{"hx-on:htmx:after-request": after_request},
    )[
        htpy.div(".modal-header")[
            htpy.h5(".modal-title")["Add a comment"],
            htpy.button(
                ".btn-close",
                aria_label="Close",
                data_bs_dismiss="modal",
                type="button",
            ),
        ],
        htpy.div(".modal-body")[
            error and htpy.div(".alert.alert-danger", role="alert")[error],
            htpy.p[
                "Add a comment to ",
                htpy.strong[suggestion.title],
                ".",
            ],
            htpy.label(".form-label", for_="suggestion-comment-body")["Comment"],
            htpy.textarea(
                "#suggestion-comment-body.form-control",
                name="body",
                required=True,
                rows=4,
            )[body],
        ],
        htpy.div(".justify-content-between.modal-footer")[
            htpy.button(
                ".btn.btn-secondary",
                data_bs_dismiss="modal",
                type="button",
            )["Cancel"],
            htpy.button(".btn.btn-primary", type="submit")[
                htpy.i(".bi-chat-left-text"), " Add comment"
            ],
        ],
    ]


def suggestion_comment_form(
    suggestion: SuggestionDetail,
    body: str = "",
    error: str | None = None,
) -> str:
    return str(_suggestion_comment_form(suggestion, body, error))


def _suggestion_activity_block(
    suggestion: SuggestionDetail,
    *,
    comments_only: bool = False,
) -> htpy.Element:
    activity_url = flask.url_for(
        "suggestion_activity",
        suggestion_id=suggestion.id,
        comments_only="1",
    )
    if comments_only:
        activity_url = flask.url_for(
            "suggestion_activity",
            suggestion_id=suggestion.id,
        )
    activities = (
        tuple(
            activity for activity in suggestion.activities if activity.type == "comment"
        )
        if comments_only
        else suggestion.activities
    )
    return htpy.div(id=f"suggestion-activity-{suggestion.id}")[
        htpy.div(".d-flex.flex-wrap.gap-2.mb-3")[
            htpy.button(
                ".btn.btn-primary.btn-sm",
                hx_disabled_elt="this",
                hx_get=activity_url,
                hx_swap="outerHTML",
                hx_target=f"#suggestion-activity-{suggestion.id}",
                type="button",
            )[
                htpy.i(".bi-chat-square-text"),
                " Show all activity" if comments_only else " Show only comments",
            ],
            suggestion.status in Suggestion.open_statuses
            and _suggestion_comment_button(suggestion.id),
        ],
        htpy.div(".list-group")[
            [_suggestion_activity_item(activity) for activity in activities]
        ]
        if activities
        else htpy.p(".text-secondary")[
            "No comments." if comments_only else "No activity."
        ],
    ]


def suggestion_activity_block(
    suggestion: SuggestionDetail,
    *,
    comments_only: bool = False,
) -> str:
    return str(_suggestion_activity_block(suggestion, comments_only=comments_only))
