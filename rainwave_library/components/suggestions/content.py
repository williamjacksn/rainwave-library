import flask
import htpy

from rainwave_library.models.suggestions import (
    Suggestion,
    SuggestionDetail,
    SuggestionLink,
)

from .summary import _suggestion_value


def _suggestion_link_item(
    link: SuggestionLink,
    suggestion_id: str,
    *,
    deletable: bool,
) -> htpy.Element:
    return htpy.div(".list-group-item")[
        htpy.div(".align-items-start.d-flex.gap-2.justify-content-between")[
            htpy.a(
                ".text-break",
                href=link.url,
                rel="noopener",
                target="_blank",
            )[
                link.label or link.url,
                " ",
                htpy.i(".bi-box-arrow-up-right"),
            ],
            deletable
            and htpy.button(
                ".btn.btn-link.p-0.text-danger",
                aria_label=f"Delete {link.label or link.url}",
                hx_confirm=f'Delete the link "{link.label or link.url}"?',
                hx_delete=flask.url_for(
                    "suggestion_link_delete",
                    suggestion_id=suggestion_id,
                    link_id=link.id,
                ),
                hx_disabled_elt="this",
                hx_swap="delete",
                hx_target="closest .list-group-item",
                title="Delete link",
                type="button",
            )[htpy.i(".bi-trash")],
        ],
        link.label and htpy.div(".small.text-secondary")[link.url],
    ]


def _suggestion_link_button(suggestion_id: str) -> htpy.Element:
    return htpy.button(
        ".btn.btn-primary.btn-sm",
        hx_get=flask.url_for("suggestion_link", suggestion_id=suggestion_id),
        hx_swap="innerHTML",
        hx_target=f"#suggestion-add-link-{suggestion_id}",
        type="button",
    )[htpy.i(".bi-link-45deg"), " Add a link"]


def suggestion_link_button(suggestion_id: str) -> str:
    return str(_suggestion_link_button(suggestion_id))


def _suggestion_link_form(
    suggestion_id: str,
    url: str = "",
    label: str = "",
    error: str | None = None,
) -> htpy.Element:
    post_url = flask.url_for("suggestion_link", suggestion_id=suggestion_id)
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=post_url,
        hx_swap="outerHTML",
        hx_target=f"#suggestion-links-{suggestion_id}",
    )[
        error and htpy.div(".alert.alert-danger.py-2", role="alert")[error],
        htpy.div(".g-2.row")[
            htpy.div(".col-12.col-sm-6")[
                htpy.input(
                    ".form-control",
                    aria_label="Link URL",
                    name="url",
                    placeholder="https://example.com",
                    required=True,
                    type="url",
                    value=url,
                ),
            ],
            htpy.div(".col")[
                htpy.input(
                    ".form-control",
                    aria_label="Link label",
                    name="label",
                    placeholder="Label",
                    type="text",
                    value=label,
                ),
            ],
        ],
        htpy.div(".d-flex.gap-2.mt-2")[
            htpy.button(".btn.btn-success.btn-sm", type="submit")[
                htpy.i(".bi-plus-lg"), " Save link"
            ],
            htpy.button(
                ".btn.btn-secondary.btn-sm",
                hx_get=flask.url_for(
                    "suggestion_link", suggestion_id=suggestion_id, close=1
                ),
                hx_swap="innerHTML",
                hx_target=f"#suggestion-add-link-{suggestion_id}",
                type="button",
            )["Cancel"],
        ],
    ]


def suggestion_link_form(
    suggestion_id: str,
    url: str = "",
    label: str = "",
    error: str | None = None,
) -> str:
    return str(_suggestion_link_form(suggestion_id, url, label, error))


def _suggestion_links_block(
    suggestion: SuggestionDetail,
    *,
    is_staff: bool | None = None,
) -> htpy.Element:
    is_owner = bool(suggestion.requester_discord_id) and (
        suggestion.requester_discord_id == str(flask.g.discord_id or "")
    )
    if is_staff is None:
        is_staff = flask.session.get("role") == "staff"
    can_add_link = is_staff or (
        is_owner and suggestion.status in Suggestion.owner_editable_statuses
    )
    can_delete_link = is_staff or (
        is_owner and suggestion.status in Suggestion.owner_editable_statuses
    )
    return htpy.div(id=f"suggestion-links-{suggestion.id}")[
        can_add_link
        and htpy.div(".mb-3", id=f"suggestion-add-link-{suggestion.id}")[
            _suggestion_link_button(suggestion.id)
        ],
        htpy.div(".list-group")[
            [
                _suggestion_link_item(
                    link,
                    suggestion.id,
                    deletable=can_delete_link,
                )
                for link in suggestion.links
            ]
        ]
        if suggestion.links
        else htpy.p(".text-secondary")["No links."],
    ]


def suggestion_links_block(suggestion: SuggestionDetail) -> str:
    return str(_suggestion_links_block(suggestion))


def _suggestion_description_block(
    suggestion: SuggestionDetail,
    *,
    editable: bool,
) -> htpy.Element:
    return htpy.div(".mt-3", id=f"suggestion-description-{suggestion.id}")[
        htpy.div(".align-items-center.d-flex.gap-2.mb-2")[
            htpy.h6(".mb-0")["Description"],
            editable
            and htpy.button(
                ".btn.btn-link.p-0.text-decoration-none",
                aria_label=f"Edit the description for {suggestion.title}",
                hx_get=flask.url_for(
                    "suggestion_description", suggestion_id=suggestion.id
                ),
                hx_swap="outerHTML",
                hx_target=f"#suggestion-description-{suggestion.id}",
                title="Edit description",
                type="button",
            )[htpy.i(".bi-pencil")],
        ],
        htpy.div(
            ".bg-body-tertiary.border.p-2.rounded",
            style="white-space: pre-wrap",
        )[_suggestion_value(suggestion.description)],
    ]


def suggestion_description_block(
    suggestion: SuggestionDetail,
    *,
    editable: bool,
) -> str:
    return str(_suggestion_description_block(suggestion, editable=editable))


def _suggestion_description_form(
    suggestion: SuggestionDetail,
    *,
    description: str | None = None,
    error: str | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_description", suggestion_id=suggestion.id)
    return htpy.div(".mt-3", id=f"suggestion-description-{suggestion.id}")[
        htpy.h6["Description"],
        htpy.form(
            hx_disabled_elt="button",
            hx_post=url,
            hx_swap="outerHTML",
            hx_target=f"#suggestion-description-{suggestion.id}",
        )[
            error and htpy.div(".alert.alert-danger.py-2", role="alert")[error],
            htpy.textarea(
                ".form-control",
                name="description",
                required=True,
                rows=6,
            )[suggestion.description if description is None else description],
            htpy.div(".d-flex.gap-2.mt-2")[
                htpy.button(".btn.btn-success.btn-sm", type="submit")[
                    htpy.i(".bi-file-earmark-text"), " Save description"
                ],
                htpy.button(
                    ".btn.btn-secondary.btn-sm",
                    hx_get=f"{url}?close=1",
                    hx_swap="outerHTML",
                    hx_target=f"#suggestion-description-{suggestion.id}",
                    type="button",
                )["Cancel"],
            ],
        ],
    ]


def suggestion_description_form(
    suggestion: SuggestionDetail,
    *,
    description: str | None = None,
    error: str | None = None,
) -> str:
    return str(
        _suggestion_description_form(
            suggestion,
            description=description,
            error=error,
        )
    )
