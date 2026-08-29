import flask
import htpy

from rainwave_library.models.rainwave import (
    channel_badge,
    channels,
)
from rainwave_library.models.storage import User
from rainwave_library.models.suggestions import (
    Suggestion,
    SuggestionDetail,
)


def _suggestion_status_badge(status: str) -> htpy.Element:
    status_classes = {
        "new": "text-bg-primary",
        "claimed": "text-bg-warning",
        "accepted": "text-bg-info",
        "completed": "text-bg-success",
        "declined": "text-bg-danger",
    }
    return htpy.span(f".badge.{status_classes.get(status, 'text-bg-light')}")[
        status.title()
    ]


def _suggestion_user_identity(
    name: str | None,
    avatar_url: str | None,
    *,
    empty_placeholder: bool = True,
) -> htpy.Element:
    return htpy.span(".fw-medium")[
        avatar_url
        and htpy.img(
            ".me-1.object-fit-cover.rounded-circle",
            alt="",
            height=24,
            loading="lazy",
            src=avatar_url,
            width=24,
        ),
        name or (empty_placeholder and htpy.span(".text-secondary")["—"]),
    ]


def _suggestion_staff_action_state(
    suggestion: Suggestion,
) -> tuple[bool, bool, bool, bool, bool, bool]:
    is_staff = flask.session.get("role") == "staff"
    is_unassigned = not (suggestion.claimed_by_name or suggestion.claimed_by_discord_id)
    claimable = (
        is_staff
        and is_unassigned
        and suggestion.status in Suggestion.claimable_statuses
    )
    assignable = (
        is_staff
        and is_unassigned
        and suggestion.status in Suggestion.assignable_statuses
    )
    releasable = (
        is_staff
        and suggestion.status == "claimed"
        and bool(suggestion.claimed_by_discord_id)
        and suggestion.claimed_by_discord_id == str(flask.g.discord_id or "")
    )
    resolvable = is_staff and suggestion.status == "claimed"
    completable = is_staff and suggestion.status == "accepted"
    return is_staff, claimable, assignable, releasable, resolvable, completable


def _suggestion_preview_staff_actions(suggestion: Suggestion) -> htpy.Node:
    is_staff, claimable, assignable, releasable, resolvable, completable = (
        _suggestion_staff_action_state(suggestion)
    )
    if not is_staff:
        return None

    return htpy.div(".d-flex.flex-wrap.gap-2.mb-3")[
        htpy.button(
            ".btn.btn-secondary.btn-sm",
            hx_get=flask.url_for(
                "suggestion_details",
                suggestion_id=suggestion.id,
            ),
            hx_swap="outerHTML",
            hx_target="closest tr",
            type="button",
        )[htpy.i(".bi-pencil"), " Edit suggestion"],
        claimable
        and htpy.button(
            ".btn.btn-primary.btn-sm",
            hx_confirm=f"Are you sure you want to claim {suggestion.title}?",
            hx_disabled_elt="this",
            hx_post=flask.url_for(
                "suggestion_claim",
                suggestion_id=suggestion.id,
            ),
            hx_swap="outerHTML",
            hx_target="closest tr",
            type="button",
        )[htpy.i(".bi-person-check"), " Claim suggestion"],
        assignable
        and htpy.button(
            ".btn.btn-secondary.btn-sm",
            data_bs_target="#modal-lg",
            data_bs_toggle="modal",
            hx_get=flask.url_for(
                "suggestion_assign",
                suggestion_id=suggestion.id,
            ),
            hx_swap="outerHTML",
            hx_target="#modal-lg-content",
            type="button",
        )[htpy.i(".bi-person-plus"), " Assign staff member"],
        releasable
        and htpy.button(
            ".btn.btn-outline-danger.btn-sm",
            hx_confirm=(
                f"Are you sure you want to release your claim on {suggestion.title}?"
            ),
            hx_disabled_elt="this",
            hx_post=flask.url_for(
                "suggestion_release",
                suggestion_id=suggestion.id,
            ),
            hx_swap="outerHTML",
            hx_target="closest tr",
            type="button",
        )[htpy.i(".bi-person-dash"), " Release claim"],
        resolvable
        and htpy.button(
            ".btn.btn-success.btn-sm",
            data_bs_target="#modal-lg",
            data_bs_toggle="modal",
            hx_get=flask.url_for(
                "suggestion_accept",
                suggestion_id=suggestion.id,
            ),
            hx_swap="outerHTML",
            hx_target="#modal-lg-content",
            type="button",
        )[htpy.i(".bi-check-circle"), " Accept suggestion"],
        resolvable
        and htpy.button(
            ".btn.btn-danger.btn-sm",
            data_bs_target="#modal-lg",
            data_bs_toggle="modal",
            hx_get=flask.url_for(
                "suggestion_decline",
                suggestion_id=suggestion.id,
            ),
            hx_swap="outerHTML",
            hx_target="#modal-lg-content",
            type="button",
        )[htpy.i(".bi-x-circle"), " Decline suggestion"],
        completable
        and htpy.button(
            ".btn.btn-success.btn-sm",
            hx_confirm=(
                f'Are you sure you want to mark "{suggestion.title}" as completed?'
            ),
            hx_disabled_elt="this",
            hx_post=flask.url_for(
                "suggestion_complete",
                suggestion_id=suggestion.id,
            ),
            hx_swap="outerHTML",
            hx_target="closest tr",
            type="button",
        )[htpy.i(".bi-check2-all"), " Mark completed"],
    ]


def _suggestion_row(suggestion: Suggestion) -> htpy.Element:
    _is_staff, claimable, _assignable, releasable, _resolvable, _completable = (
        _suggestion_staff_action_state(suggestion)
    )
    kind_label = Suggestion.kind_labels.get(suggestion.kind, suggestion.kind)
    return htpy.tr(id=f"suggestion-row-{suggestion.id}")[
        htpy.td(".text-center.text-nowrap")[
            htpy.a(
                ".text-decoration-none",
                aria_label=f"View details for {suggestion.title}",
                href="#",
                hx_get=flask.url_for(
                    "suggestion_details",
                    suggestion_id=suggestion.id,
                    view="1",
                ),
                hx_swap="outerHTML",
                hx_target="closest tr",
                title="View suggestion details",
            )[htpy.i(".bi-eye")],
        ],
        htpy.td(".d-table-cell.d-md-none")[
            htpy.div(".fw-semibold.text-break")[suggestion.title],
            htpy.div(".d-flex.flex-wrap.gap-1.mt-1")[
                _suggestion_status_badge(suggestion.status),
            ],
            htpy.div(".small.mt-2")[
                htpy.strong["Type: "],
                kind_label,
            ],
            htpy.div(".small.mt-2")[
                htpy.strong["Channels: "],
                [channel_badge(channel_id) for channel_id in suggestion.channel_ids]
                or htpy.span(".text-secondary")["—"],
            ],
            htpy.div(".small.mt-1")[
                htpy.strong["Suggested by: "],
                _suggestion_user_identity(
                    suggestion.requester_name,
                    suggestion.requester_avatar_url,
                ),
            ],
            suggestion.requested_at
            and htpy.div(".small.mt-1")[
                htpy.strong["Suggested at: "], suggestion.requested_at[:10]
            ],
            (suggestion.claimed_by_name or claimable or releasable)
            and htpy.div(".small.mt-1")[
                htpy.strong["Claimed by: "],
                _suggestion_user_identity(
                    suggestion.claimed_by_name,
                    suggestion.claimed_by_avatar_url,
                    empty_placeholder=not claimable,
                ),
                claimable
                and htpy.button(
                    ".btn.btn-link.ms-1.p-0.text-decoration-none",
                    aria_label=f"Claim {suggestion.title}",
                    hx_confirm=(f"Are you sure you want to claim {suggestion.title}?"),
                    hx_disabled_elt="this",
                    hx_post=flask.url_for(
                        "suggestion_claim", suggestion_id=suggestion.id
                    ),
                    hx_swap="outerHTML",
                    hx_target="closest tr",
                    title="Claim suggestion",
                    type="button",
                )[htpy.i(".bi-person-check")],
                releasable
                and htpy.button(
                    ".btn.btn-link.ms-1.p-0.text-danger.text-decoration-none",
                    aria_label=f"Release claim on {suggestion.title}",
                    hx_confirm=(
                        "Are you sure you want to release your claim on "
                        f"{suggestion.title}?"
                    ),
                    hx_disabled_elt="this",
                    hx_post=flask.url_for(
                        "suggestion_release", suggestion_id=suggestion.id
                    ),
                    hx_swap="outerHTML",
                    hx_target="closest tr",
                    title="Release claim",
                    type="button",
                )[htpy.i(".bi-person-dash")],
            ],
        ],
        htpy.td(".d-none.d-md-table-cell")[_suggestion_status_badge(suggestion.status)],
        htpy.td(".d-none.d-md-table-cell")[
            [channel_badge(channel_id) for channel_id in suggestion.channel_ids]
            or htpy.span(".text-secondary")["—"]
        ],
        htpy.td(".d-none.d-md-table-cell")[htpy.div(".fw-semibold")[suggestion.title],],
        htpy.td(".d-none.d-md-table-cell.text-nowrap")[kind_label],
        htpy.td(".d-none.d-md-table-cell.text-nowrap")[
            _suggestion_user_identity(
                suggestion.requester_name,
                suggestion.requester_avatar_url,
            ),
        ],
        htpy.td(".d-none.d-md-table-cell.text-nowrap")[
            suggestion.requested_at[:10]
            if suggestion.requested_at
            else htpy.span(".text-secondary")["—"]
        ],
        htpy.td(".d-none.d-md-table-cell.text-nowrap")[
            _suggestion_user_identity(
                suggestion.claimed_by_name,
                suggestion.claimed_by_avatar_url,
                empty_placeholder=not claimable,
            ),
            claimable
            and htpy.button(
                ".btn.btn-link.p-0.text-decoration-none",
                aria_label=f"Claim {suggestion.title}",
                hx_confirm=f"Are you sure you want to claim {suggestion.title}?",
                hx_disabled_elt="this",
                hx_post=flask.url_for("suggestion_claim", suggestion_id=suggestion.id),
                hx_swap="outerHTML",
                hx_target="closest tr",
                title="Claim suggestion",
                type="button",
            )[htpy.i(".bi-person-check")],
            releasable
            and htpy.button(
                ".btn.btn-link.ms-1.p-0.text-danger.text-decoration-none",
                aria_label=f"Release claim on {suggestion.title}",
                hx_confirm=(
                    "Are you sure you want to release your claim on "
                    f"{suggestion.title}?"
                ),
                hx_disabled_elt="this",
                hx_post=flask.url_for(
                    "suggestion_release", suggestion_id=suggestion.id
                ),
                hx_swap="outerHTML",
                hx_target="closest tr",
                title="Release claim",
                type="button",
            )[htpy.i(".bi-person-dash")],
        ],
    ]


def suggestion_row(suggestion: Suggestion) -> str:
    return str(_suggestion_row(suggestion))


def _suggestion_assign_form(
    suggestion: SuggestionDetail,
    staff_users: list[User],
    *,
    assignee_discord_id: str = "",
    error: str | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_assign", suggestion_id=suggestion.id)
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
        hx_target=f"#suggestion-row-{suggestion.id}",
        method="post",
        **{"hx-on:htmx:after-request": after_request},
    )[
        htpy.div(".modal-header")[
            htpy.h5(".modal-title")["Assign suggestion"],
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
                "Assign ",
                htpy.strong[suggestion.title],
                " to a staff member.",
            ],
            (
                htpy.div[
                    htpy.label(
                        ".form-label",
                        for_="suggestion-assignee-discord-id",
                    )["Staff member"],
                    htpy.select(
                        "#suggestion-assignee-discord-id.form-select",
                        name="assignee-discord-id",
                        required=True,
                    )[
                        htpy.option(value="")["Choose a staff member"],
                        [
                            htpy.option(
                                selected=(user.discord_id == assignee_discord_id),
                                value=user.discord_id,
                            )[
                                user.display_name or user.username or user.discord_id,
                                " (",
                                user.discord_id,
                                ")",
                            ]
                            for user in staff_users
                        ],
                    ],
                ]
                if staff_users
                else htpy.div(".alert.alert-warning.mb-0", role="alert")[
                    "No other staff members are available in the local user database."
                ]
            ),
        ],
        htpy.div(".justify-content-between.modal-footer")[
            htpy.button(
                ".btn.btn-secondary",
                data_bs_dismiss="modal",
                type="button",
            )["Cancel"],
            htpy.button(
                ".btn.btn-primary",
                disabled=not staff_users,
                type="submit",
            )[htpy.i(".bi-person-plus"), " Assign suggestion"],
        ],
    ]


def suggestion_assign_form(
    suggestion: SuggestionDetail,
    staff_users: list[User],
    *,
    assignee_discord_id: str = "",
    error: str | None = None,
) -> str:
    return str(
        _suggestion_assign_form(
            suggestion,
            staff_users,
            assignee_discord_id=assignee_discord_id,
            error=error,
        )
    )


def _suggestion_value(value: str | float | None) -> htpy.Node:
    if value is None or value == "":
        return htpy.span(".text-secondary")["—"]
    return str(value)


def _suggestion_detail_table(
    rows: list[tuple[str, htpy.Node]],
) -> htpy.Element:
    return htpy.table(".d-block.table.table-sm")[
        htpy.tbody[
            [
                htpy.tr[
                    htpy.th(".text-nowrap", scope="row")[label],
                    htpy.td(".text-break")[display_value],
                ]
                for label, display_value in rows
            ]
        ]
    ]


def _suggestion_resolution_form(
    suggestion: SuggestionDetail,
    *,
    resolution: str,
) -> htpy.Element:
    if resolution not in {"accept", "decline"}:
        msg = "Invalid suggestion resolution."
        raise ValueError(msg)
    accepting = resolution == "accept"
    resolved_status = "accepted" if accepting else "declined"
    action_label = "Accept suggestion" if accepting else "Decline suggestion"
    url = flask.url_for(
        "suggestion_accept" if accepting else "suggestion_decline",
        suggestion_id=suggestion.id,
    )
    claim_details: htpy.Node
    if suggestion.claimed_by_name or suggestion.claimed_by_discord_id:
        claim_details = _suggestion_user_identity(
            suggestion.claimed_by_name or suggestion.claimed_by_discord_id,
            suggestion.claimed_by_avatar_url,
        )
    else:
        claim_details = htpy.span(".text-secondary")["Unclaimed"]
    channel_badges: htpy.Node = (
        htpy.fragment[
            [channel_badge(channel_id) for channel_id in suggestion.channel_ids]
        ]
        if suggestion.channel_ids
        else htpy.span(".text-secondary")["—"]
    )
    after_request = (
        "if (event.detail.successful) {"
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
        hx_target=f"#suggestion-row-{suggestion.id}",
        method="post",
        **{"hx-on:htmx:after-request": after_request},
    )[
        htpy.div(".modal-header")[
            htpy.h5(f"#suggestion-{resolution}-modal-title.modal-title")[action_label],
            htpy.button(
                ".btn-close",
                aria_label="Close",
                data_bs_dismiss="modal",
                type="button",
            ),
        ],
        htpy.div(".modal-body")[
            htpy.p[
                "Review the suggestion and claim details before "
                f"{'accepting' if accepting else 'declining'} it."
            ],
            _suggestion_detail_table(
                [
                    ("Suggestion title", suggestion.title),
                    ("Channel", channel_badges),
                    (
                        "Suggested by",
                        _suggestion_user_identity(
                            suggestion.requester_name,
                            suggestion.requester_avatar_url,
                        ),
                    ),
                    ("Status", _suggestion_status_badge(suggestion.status)),
                    ("Claimed by", claim_details),
                    (
                        "Claimed at",
                        (
                            suggestion.claimed_at[:10]
                            if suggestion.claimed_at
                            else htpy.span(".text-secondary")["—"]
                        ),
                    ),
                ]
            ),
            htpy.div(".mt-3")[
                htpy.label(
                    ".form-label",
                    for_=f"suggestion-{resolution}-comment",
                )["Comment (optional)"],
                htpy.textarea(
                    f"#suggestion-{resolution}-comment.form-control",
                    name="comment",
                    rows=4,
                ),
                htpy.div(".form-text")[
                    "The comment will be added at the same time as the suggestion "
                    f"is {resolved_status}."
                ],
            ],
            htpy.div(".form-check.mt-3")[
                htpy.input(
                    f"#suggestion-{resolution}-send-discord-notification.form-check-input",
                    checked=True,
                    name="send-discord-notification",
                    type="checkbox",
                    value="1",
                ),
                htpy.label(
                    ".form-check-label",
                    for_=f"suggestion-{resolution}-send-discord-notification",
                )["Send Discord notification"],
            ],
        ],
        htpy.div(".justify-content-between.modal-footer")[
            htpy.button(
                ".btn.btn-secondary",
                data_bs_dismiss="modal",
                type="button",
            )["Cancel"],
            htpy.button(
                ".btn.btn-success" if accepting else ".btn.btn-danger",
                type="submit",
            )[
                htpy.i(".bi-check-circle" if accepting else ".bi-x-circle"),
                f" {action_label}",
            ],
        ],
    ]


def _suggestion_accept_form(suggestion: SuggestionDetail) -> htpy.Element:
    return _suggestion_resolution_form(suggestion, resolution="accept")


def suggestion_accept_form(suggestion: SuggestionDetail) -> str:
    return str(_suggestion_accept_form(suggestion))


def _suggestion_decline_form(suggestion: SuggestionDetail) -> htpy.Element:
    return _suggestion_resolution_form(suggestion, resolution="decline")


def suggestion_decline_form(suggestion: SuggestionDetail) -> str:
    return str(_suggestion_decline_form(suggestion))


def _suggestion_edit_requester_discord_id_field(
    requester_discord_id: str = "",
) -> htpy.VoidElement:
    return htpy.input(
        "#requester-discord-id.form-control",
        name="requester-discord-id",
        type="text",
        value=requester_discord_id,
    )


def suggestion_edit_requester_discord_id_field(
    requester_discord_id: str = "",
) -> str:
    return str(
        _suggestion_edit_requester_discord_id_field(requester_discord_id),
    )


def _suggestion_edit_form(
    suggestion: SuggestionDetail,
    edit_result: tuple[str, str] | None,
) -> htpy.Element:
    rainwave_channels = [
        (channel_id, label)
        for channel_id, label in channels.items()
        if isinstance(channel_id, int) and channel_id in range(1, 7)
    ]
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=flask.url_for("suggestion_update", suggestion_id=suggestion.id),
        hx_swap="outerHTML",
        hx_target="closest tr",
    )[
        edit_result
        and htpy.div(f".alert.{edit_result[0]}", role="alert")[edit_result[1]],
        htpy.div(".g-3.row")[
            htpy.div(".col-12.small.text-secondary")[
                "Suggestion ID: ",
                htpy.a(
                    href=flask.url_for(
                        "suggestion_page",
                        suggestion_id=suggestion.id,
                    )
                )[htpy.code[suggestion.id]],
            ],
            htpy.div(".col-12")[
                htpy.label(".form-label", for_="title")["Title"],
                htpy.input(
                    "#title.form-control",
                    name="title",
                    required=True,
                    type="text",
                    value=suggestion.title,
                ),
            ],
            htpy.div(".col-12.col-md-6")[
                htpy.label(".form-label", for_="kind")["Suggestion type"],
                htpy.select("#kind.form-select", name="kind")[
                    [
                        htpy.option(
                            selected=kind == suggestion.kind,
                            value=kind,
                        )[Suggestion.kind_labels[kind]]
                        for kind in Suggestion.kinds
                    ]
                ],
            ],
            htpy.div(".col-12.col-md-6")[
                htpy.label(".form-label", for_="status")["Status"],
                htpy.select("#status.form-select", name="status")[
                    [
                        htpy.option(
                            selected=status == suggestion.status,
                            value=status,
                        )[status.title()]
                        for status in Suggestion.statuses
                    ]
                ],
            ],
            htpy.div(".col-12")[
                htpy.label(".form-label", for_="description")["Description"],
                htpy.textarea(
                    "#description.form-control",
                    name="description",
                    rows=6,
                )[suggestion.description],
            ],
            htpy.div(".col-12.col-lg-4")[
                htpy.label(".form-label", for_="requester-name")["Suggested by"],
                htpy.input(
                    "#requester-name.form-control",
                    hx_get=flask.url_for(
                        "suggestion_staff_requester_discord_id",
                        target="edit",
                    ),
                    hx_include="this",
                    hx_swap="outerHTML",
                    hx_sync="this:replace",
                    hx_target="#requester-discord-id",
                    hx_trigger="input changed delay:300ms",
                    name="requester-name",
                    type="text",
                    value=suggestion.requester_name or "",
                ),
            ],
            htpy.div(".col-12.col-lg-4")[
                htpy.label(".form-label", for_="requester-discord-id")[
                    "Suggested by Discord ID"
                ],
                _suggestion_edit_requester_discord_id_field(
                    suggestion.requester_discord_id or ""
                ),
            ],
            htpy.div(".col-12.col-lg-4")[
                htpy.label(".form-label", for_="requested-at")["Suggested at"],
                htpy.input(
                    "#requested-at.form-control",
                    name="requested-at",
                    type="text",
                    value=suggestion.requested_at or "",
                ),
            ],
        ],
        htpy.div(".g-3.mt-4.row")[
            htpy.div(".col-12.col-lg-7")[
                htpy.div(".form-label")["Channels"],
                htpy.div(".d-flex.flex-wrap.gap-3")[
                    [
                        htpy.div(".form-check")[
                            htpy.input(
                                f"#channel-{channel_id}.form-check-input",
                                checked=channel_id in suggestion.channel_ids,
                                name="channels",
                                type="checkbox",
                                value=channel_id,
                            ),
                            htpy.label(
                                ".form-check-label", for_=f"channel-{channel_id}"
                            )[label],
                        ]
                        for channel_id, label in rainwave_channels
                    ]
                ],
            ],
            htpy.div(".col-12.col-lg-5")[
                htpy.label(".form-label", for_="primary-channel")["Primary channel"],
                htpy.select("#primary-channel.form-select", name="primary-channel")[
                    htpy.option(value="")["None"],
                    [
                        htpy.option(
                            selected=channel_id == suggestion.primary_channel_id,
                            value=channel_id,
                        )[label]
                        for channel_id, label in rainwave_channels
                    ],
                ],
                htpy.div(".form-text")[
                    "The primary channel is automatically included above."
                ],
            ],
        ],
        htpy.div(".d-flex.gap-2.justify-content-between.mt-3")[
            htpy.button(".btn.btn-success.btn-sm", type="submit")[
                htpy.i(".bi-file-earmark-play"), " Save suggestion"
            ],
            htpy.button(
                ".btn.btn-danger.btn-sm",
                hx_confirm=(
                    f'Delete the suggestion "{suggestion.title}"? '
                    "This cannot be undone."
                ),
                hx_delete=flask.url_for(
                    "suggestion_delete", suggestion_id=suggestion.id
                ),
                hx_disabled_elt="this",
                hx_swap="delete",
                hx_target="closest tr",
                type="button",
            )[htpy.i(".bi-trash"), " Delete suggestion"],
        ],
    ]
