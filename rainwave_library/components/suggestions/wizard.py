import flask
import htpy

from rainwave_library.models.rainwave import (
    channels,
)
from rainwave_library.models.suggestions import (
    Suggestion,
)

from .detail import _suggestion_link_fields
from .guidelines import (
    _suggestion_chill_rules,
    _suggestion_chiptune_rules,
    _suggestion_covers_rules,
    _suggestion_game_rules,
    _suggestion_oc_remix_rules,
)
from .summary import _suggestion_detail_table, _suggestion_value


def _suggestion_create_notice(song_count: int, song_count_as_of: str) -> htpy.Element:
    return htpy.div[
        htpy.p[
            "Rainwave is an online radio station run by volunteers. The "
            "extensive Rainwave music library includes:"
        ],
        htpy.ul[
            htpy.li["original video game soundtracks, both modern and classic"],
            htpy.li["original chiptune music not featured in video games"],
            htpy.li[
                "covers and remixes of video game music from a wide variety of "
                "sources, including OverClocked ReMix"
            ],
        ],
        htpy.p[
            "While the Rainwave music library is substantial (over "
            f"{song_count:,} songs as of {song_count_as_of}), we understand "
            "that we may not have your favorite soundtrack or music from "
            "recently released games."
        ],
        htpy.p[
            "You are welcome to make suggestions for new music to be added to "
            "the Rainwave music library. However, as volunteers who maintain "
            "the site and library, we cannot guarantee that new music will be "
            "added."
        ],
        htpy.p[
            "You can also use this form to suggest metadata updates or the "
            "removal of music from the library."
        ],
    ]


def _suggestion_wizard_hidden_request_fields(
    description: str,
    links: tuple[tuple[str, str], ...],
) -> htpy.Node:
    return htpy.fragment[
        htpy.input(name="description", type="hidden", value=description),
        [
            htpy.fragment[
                htpy.input(name="link-url", type="hidden", value=url),
                htpy.input(name="link-label", type="hidden", value=label),
            ]
            for url, label in links
        ],
    ]


def _suggestion_wizard_step1(
    channel_id: int | None = None,
    kind: str | None = None,
    result: tuple[str, str] | None = None,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
) -> htpy.Element:
    url = flask.url_for("suggestion_wizard")
    rainwave_channels = sorted(
        (
            (value, label)
            for value, label in channels.items()
            if isinstance(value, int) and value in {1, 2, 3, 4, 6}
        ),
        key=lambda item: item[1].casefold(),
    )
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="innerHTML",
        hx_target="#new-suggestion-modal-body",
    )[
        htpy.input(name="title", type="hidden", value=title),
        _suggestion_wizard_hidden_request_fields(description, links),
        result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
        htpy.p[
            "Choose the channel and suggestion type that best match what you "
            "want to submit."
        ],
        htpy.div(".g-2.row")[
            htpy.div(".col-12.col-sm-6")[
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
                        htpy.option(selected=value == channel_id, value=value)[label]
                        for value, label in rainwave_channels
                    ],
                ],
            ],
            htpy.div(".col-12.col-sm-6")[
                htpy.label(".form-label", for_="new-suggestion-kind")[
                    "Suggestion type"
                ],
                htpy.select(
                    "#new-suggestion-kind.form-select",
                    name="kind",
                    required=True,
                )[
                    htpy.option(
                        disabled=True,
                        selected=kind is None,
                        value="",
                    )["Choose a type"],
                    [
                        htpy.option(selected=value == kind, value=value)[label]
                        for value, label in Suggestion.kind_labels.items()
                    ],
                ],
            ],
        ],
        htpy.div(".d-flex.justify-content-end.mt-3")[
            htpy.button(
                ".btn.btn-primary",
                name="step",
                type="submit",
                value="2",
            )["Next ", htpy.i(".bi-caret-right-fill")],
        ],
    ]


def _suggestion_wizard_step2(
    channel_id: int | None = None,
    kind: str | None = None,
    open_count: int = 0,
    limits_apply: bool = True,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
) -> htpy.Element:
    url = flask.url_for("suggestion_wizard")
    channel_label = channels.get(channel_id, "—") if channel_id else "—"
    kind_label = Suggestion.kind_labels.get(kind or "", "—")
    over_limit = limits_apply and open_count >= 5
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="innerHTML",
        hx_target="#new-suggestion-modal-body",
    )[
        htpy.input(name="channel", type="hidden", value=channel_id or ""),
        htpy.input(name="kind", type="hidden", value=kind or ""),
        htpy.input(name="title", type="hidden", value=title),
        _suggestion_wizard_hidden_request_fields(description, links),
        htpy.div(".alert.alert-secondary", role="alert")[
            htpy.p(".mb-1")[
                "You are suggesting: ",
                htpy.strong[kind_label],
                " on the ",
                htpy.strong[channel_label],
                " channel.",
            ],
            kind in Suggestion.limited_kinds
            and htpy.p(".mb-0")[
                "You currently have ",
                htpy.strong[str(open_count)],
                f" open suggestion{'' if open_count == 1 else 's'} for the ",
                htpy.strong[channel_label],
                " channel.",
            ],
            not limits_apply
            and kind in Suggestion.limited_kinds
            and htpy.p(".mb-0.mt-1")["Suggestion limits do not apply to staff."],
        ],
        over_limit
        and htpy.div(".alert.alert-warning", role="alert")[
            "The ",
            htpy.strong[channel_label],
            (
                " channel allows up to 5 open suggestions at a time. Please wait "
                "until one of your suggestions is resolved before adding another."
            ),
        ],
        not over_limit and channel_id == 1 and _suggestion_game_rules(),
        not over_limit and channel_id == 2 and _suggestion_oc_remix_rules(),
        not over_limit and channel_id == 3 and _suggestion_covers_rules(),
        not over_limit and channel_id == 4 and _suggestion_chiptune_rules(),
        not over_limit and channel_id == 6 and _suggestion_chill_rules(),
        not over_limit
        and htpy.div(".alert.alert-info", role="alert")[
            "If your suggestion complies with these guidelines, continue to "
            "the next step."
        ],
        htpy.div(".d-flex.justify-content-between.mt-3")[
            htpy.button(".btn.btn-secondary", name="step", type="submit", value="1")[
                htpy.i(".bi-caret-left-fill"), " Back"
            ],
            htpy.button(
                ".btn.btn-primary",
                disabled=over_limit,
                name="step",
                type="submit",
                value="3",
            )["Next ", htpy.i(".bi-caret-right-fill")],
        ],
    ]


def _suggestion_wizard_step3(
    channel_id: int | None = None,
    kind: str | None = None,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
    result: tuple[str, str] | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_wizard")
    channel_label = channels.get(channel_id, "—") if channel_id else "—"
    kind_label = Suggestion.kind_labels.get(kind or "", "—")
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="innerHTML",
        hx_target="#new-suggestion-modal-body",
    )[
        htpy.input(name="channel", type="hidden", value=channel_id or ""),
        htpy.input(name="kind", type="hidden", value=kind or ""),
        _suggestion_wizard_hidden_request_fields(description, links),
        result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
        htpy.div(".alert.alert-secondary", role="alert")[
            "You are suggesting: ",
            htpy.strong[kind_label],
            " on the ",
            htpy.strong[channel_label],
            " channel.",
        ],
        htpy.h5["Suggestion title"],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="new-suggestion-title")[
                "Enter the suggestion title"
            ],
            htpy.input(
                "#new-suggestion-title.form-control",
                aria_describedby="new-suggestion-title-help",
                autofocus=True,
                name="title",
                required=True,
                value=title,
            ),
            htpy.div("#new-suggestion-title-help.form-text")[
                htpy.ul(".mb-0.mt-2")[
                    kind == "new-album"
                    and htpy.li["For a game soundtrack, use the name of the game."],
                    kind == "new-album"
                    and htpy.li[
                        "If the game has different names in different regions, "
                        "use the name of the North American release."
                    ],
                    kind == "new-album"
                    and htpy.li[
                        "For a cover or remix album, use the official album title."
                    ],
                    kind != "new-album"
                    and htpy.li[
                        "For an existing album, use the album name "
                        "exactly as it currently appears on Rainwave."
                    ],
                ]
            ],
        ],
        htpy.div(".d-flex.justify-content-between.mt-3")[
            htpy.button(
                ".btn.btn-secondary",
                formnovalidate=True,
                name="step",
                type="submit",
                value="2",
            )[htpy.i(".bi-caret-left-fill"), " Back"],
            htpy.button(".btn.btn-primary", name="step", type="submit", value="4")[
                "Next ", htpy.i(".bi-caret-right-fill")
            ],
        ],
    ]


def _suggestion_wizard_step4(
    channel_id: int | None = None,
    kind: str | None = None,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
    title_matches: tuple[str, ...] = (),
    result: tuple[str, str] | None = None,
) -> htpy.Element:
    url = flask.url_for("suggestion_wizard")
    channel_label = channels.get(channel_id, "—") if channel_id else "—"
    kind_label = Suggestion.kind_labels.get(kind or "", "—")
    return htpy.form(
        hx_disabled_elt="button",
        hx_post=url,
        hx_swap="innerHTML",
        hx_target="#new-suggestion-modal-body",
    )[
        htpy.input(name="channel", type="hidden", value=channel_id or ""),
        htpy.input(name="kind", type="hidden", value=kind or ""),
        htpy.input(name="title", type="hidden", value=title),
        result and htpy.div(f".alert.{result[0]}.py-2", role="alert")[result[1]],
        htpy.div(".alert.alert-secondary", role="alert")[
            htpy.p(".mb-1")[
                "You are suggesting: ",
                htpy.strong[kind_label],
                " on the ",
                htpy.strong[channel_label],
                " channel.",
            ],
            htpy.p(".mb-0")["Suggestion title: ", htpy.strong[title]],
        ],
        title_matches
        and htpy.div(".alert.alert-warning", role="alert")[
            htpy.p(".fw-semibold.mb-1")[
                "This title may already be in use. Review these matches before "
                "continuing:"
            ],
            htpy.ul(".mb-0")[
                "open-suggestion" in title_matches
                and htpy.li["An open suggestion already uses this title."],
                "declined-suggestion" in title_matches
                and htpy.li["A declined suggestion already uses this title."],
                "album" in title_matches
                and htpy.li[
                    "An album with this name already exists in the Rainwave library."
                ],
            ],
        ],
        htpy.h5["Suggestion details"],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="new-suggestion-description")[
                "Describe your suggestion"
            ],
            htpy.div("#new-suggestion-description-help.form-text.mb-2.mt-0")[
                "Include enough information for the staff to understand and "
                "complete your suggestion."
            ],
            htpy.textarea(
                "#new-suggestion-description.form-control",
                aria_describedby="new-suggestion-description-help",
                autofocus=True,
                name="description",
                required=True,
                rows=5,
            )[description],
        ],
        htpy.h5["Links"],
        htpy.p(".form-text")[
            (
                "Add any relevant download, artist, album, source, cover art, "
                "or evidence links."
            )
        ],
        htpy.div("#new-suggestion-links.d-flex.flex-column.gap-2")[
            [
                _suggestion_link_fields(link_url, label, required=True)
                for link_url, label in links
            ]
        ],
        htpy.button(
            ".btn.btn-info.btn-sm.mt-2",
            hx_get=flask.url_for("suggestion_link_row", required=1),
            hx_swap="beforeend",
            hx_target="#new-suggestion-links",
            type="button",
        )[htpy.i(".bi-plus-lg"), " Add link"],
        htpy.div(".d-flex.justify-content-between.mt-3")[
            htpy.button(
                ".btn.btn-secondary",
                formnovalidate=True,
                name="step",
                type="submit",
                value="3",
            )[htpy.i(".bi-caret-left-fill"), " Back"],
            htpy.button(
                ".btn.btn-primary",
                name="step",
                type="submit",
                value="5",
            )["Next ", htpy.i(".bi-caret-right-fill")],
        ],
    ]


def _suggestion_wizard_step5(
    channel_id: int | None = None,
    kind: str | None = None,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
) -> htpy.Element:
    wizard_url = flask.url_for("suggestion_wizard")
    create_url = flask.url_for("suggestion_create")
    channel_label = channels.get(channel_id, "—") if channel_id else "—"
    kind_label = Suggestion.kind_labels.get(kind or "", "—")
    description_display = (
        htpy.div(style="white-space: pre-wrap")[description]
        if description
        else _suggestion_value(None)
    )
    links_display = (
        htpy.ul(".mb-0.ps-3")[
            [
                htpy.li[
                    label and htpy.strong[label],
                    label and ": ",
                    url or htpy.span(".text-secondary")["No URL provided"],
                ]
                for url, label in links
            ]
        ]
        if links
        else _suggestion_value(None)
    )
    return htpy.form(
        action=create_url,
        hx_disabled_elt="button",
        hx_swap="innerHTML",
        hx_target="#new-suggestion-modal-body",
        method="post",
    )[
        htpy.input(name="channel", type="hidden", value=channel_id or ""),
        htpy.input(name="kind", type="hidden", value=kind or ""),
        htpy.input(name="title", type="hidden", value=title),
        _suggestion_wizard_hidden_request_fields(description, links),
        htpy.h5["Confirm suggestion"],
        htpy.p["Review your suggestion before submitting it."],
        _suggestion_detail_table(
            [
                ("Channel", channel_label),
                ("Suggestion type", kind_label),
                ("Suggestion title", title),
                ("Suggestion details", description_display),
                ("Links", links_display),
            ]
        ),
        htpy.div(".d-flex.justify-content-between.mt-3")[
            htpy.button(
                ".btn.btn-secondary",
                formaction=wizard_url,
                formnovalidate=True,
                hx_post=wizard_url,
                name="step",
                type="submit",
                value="4",
            )[htpy.i(".bi-caret-left-fill"), " Back"],
            htpy.button(
                ".btn.btn-success",
                hx_post=create_url,
                type="submit",
            )[htpy.i(".bi-check-lg"), " Submit suggestion"],
        ],
    ]


def _suggestion_wizard_body(
    step: int,
    channel_id: int | None = None,
    kind: str | None = None,
    result: tuple[str, str] | None = None,
    song_count: int = 0,
    song_count_as_of: str = "",
    open_count: int = 0,
    limits_apply: bool = True,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
    title_matches: tuple[str, ...] = (),
) -> htpy.Node:
    if step == 5:
        return _suggestion_wizard_step5(channel_id, kind, title, description, links)
    if step == 4:
        return _suggestion_wizard_step4(
            channel_id, kind, title, description, links, title_matches, result
        )
    if step == 3:
        return _suggestion_wizard_step3(
            channel_id, kind, title, description, links, result
        )
    if step == 2:
        return _suggestion_wizard_step2(
            channel_id,
            kind,
            open_count,
            limits_apply,
            title,
            description,
            links,
        )
    return htpy.fragment[
        _suggestion_create_notice(song_count, song_count_as_of),
        _suggestion_wizard_step1(channel_id, kind, result, title, description, links),
    ]


def suggestion_wizard_body(
    step: int,
    channel_id: int | None = None,
    kind: str | None = None,
    result: tuple[str, str] | None = None,
    song_count: int = 0,
    song_count_as_of: str = "",
    open_count: int = 0,
    limits_apply: bool = True,
    title: str = "",
    description: str = "",
    links: tuple[tuple[str, str], ...] = (),
    title_matches: tuple[str, ...] = (),
) -> str:
    return str(
        _suggestion_wizard_body(
            step,
            channel_id,
            kind,
            result,
            song_count,
            song_count_as_of,
            open_count,
            limits_apply,
            title,
            description,
            links,
            title_matches,
        )
    )
