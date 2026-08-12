import flask
import htpy

from .common import _back_button, _base, _user_menu


def settings_index(
    settings: list[tuple[str, str, bool]],
    *,
    key: str = "",
    value: str = "",
    protected: bool = False,
    result: tuple[str, str] | None = None,
) -> str:
    rows = [
        htpy.tr[
            htpy.td[htpy.code(".user-select-all")[key]],
            htpy.td(".text-break")[
                htpy.span(".badge.text-bg-secondary")["protected"]
                if protected
                else htpy.code(".user-select-all")[value]
            ],
        ]
        for key, value, protected in settings
    ]
    if not rows:
        rows.append(
            htpy.tr[htpy.td(".py-3.text-center", colspan=2)["No settings found."]]
        )
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["Application settings"],]],
        htpy.div(".pt-3.row")[
            htpy.div(".col-lg-8")[
                htpy.div(".card")[
                    htpy.div(".card-header")[
                        htpy.h5(".mb-0")["Create or replace a setting"]
                    ],
                    htpy.div(".card-body")[
                        result
                        and htpy.div(f".alert.{result[0]}", role="alert")[result[1]],
                        htpy.p[
                            "Saving a key that already exists replaces its value. "
                            "Application settings are loaded at startup."
                        ],
                        htpy.form(
                            action=flask.url_for("settings"),
                            autocomplete="off",
                            method="post",
                        )[
                            htpy.div(".g-3.row")[
                                htpy.div(".col-md-5")[
                                    htpy.label(".form-label", for_="setting-key")[
                                        "Key"
                                    ],
                                    htpy.input(
                                        "#setting-key.form-control",
                                        name="key",
                                        required=True,
                                        type="text",
                                        value=key,
                                    ),
                                ],
                                htpy.div(".col-md-7")[
                                    htpy.label(".form-label", for_="setting-value")[
                                        "Value"
                                    ],
                                    htpy.input(
                                        "#setting-value.form-control",
                                        name="value",
                                        required=True,
                                        type="text",
                                        value=value,
                                    ),
                                ],
                            ],
                            htpy.div(".form-check.mt-3")[
                                htpy.input(
                                    "#setting-protected.form-check-input",
                                    checked=protected,
                                    name="protected",
                                    type="checkbox",
                                    value="1",
                                ),
                                htpy.label(
                                    ".form-check-label",
                                    for_="setting-protected",
                                )["Protect value"],
                                htpy.div(".form-text")[
                                    "Protected values are hidden on this page. "
                                    "An existing protected setting remains protected."
                                ],
                            ],
                            htpy.button(".btn.btn-primary.mt-3", type="submit")[
                                htpy.i(".bi-floppy"), " Save setting"
                            ],
                        ],
                    ],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(
                    ".align-middle.d-block.table.table-bordered.table-sm.table-striped"
                )[
                    htpy.thead[htpy.tr[htpy.th["Key"], htpy.th["Value"]]],
                    htpy.tbody[rows],
                ]
            ]
        ],
    ]
    return str(_base(content))


def user_settings_index(
    settings: list[tuple[str, str]],
    *,
    color_mode: str = "light",
    color_mode_result: tuple[str, str] | None = None,
    key: str = "",
    value: str = "",
    result: tuple[str, str] | None = None,
) -> str:
    rows = [
        htpy.tr[
            htpy.td[htpy.code(".user-select-all")[key]],
            htpy.td(".text-break")[htpy.code(".user-select-all")[value]],
        ]
        for key, value in settings
    ]
    if not rows:
        rows.append(
            htpy.tr[htpy.td(".py-3.text-center", colspan=2)["No settings found."]]
        )
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"), _user_menu()
        ],
        htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1["User settings"]]],
        htpy.div(".pt-3.row")[
            htpy.div(".col-lg-8")[
                htpy.div(".card")[
                    htpy.div(".card-header")[htpy.h5(".mb-0")["Color mode"]],
                    htpy.div(".card-body")[
                        color_mode_result
                        and htpy.div(
                            f".alert.{color_mode_result[0]}",
                            role="alert",
                        )[color_mode_result[1]],
                        htpy.form(
                            action=flask.url_for("user_settings"),
                            method="post",
                        )[
                            htpy.input(
                                name="form",
                                type="hidden",
                                value="color-mode",
                            ),
                            htpy.label(
                                ".form-label",
                                for_="user-color-mode",
                            )["Color mode"],
                            htpy.select(
                                "#user-color-mode.form-select",
                                name="color-mode",
                                required=True,
                            )[
                                htpy.option(
                                    selected=color_mode == "light",
                                    value="light",
                                )["Light"],
                                htpy.option(
                                    selected=color_mode == "dark",
                                    value="dark",
                                )["Dark"],
                            ],
                            htpy.button(".btn.btn-primary.mt-3", type="submit")[
                                htpy.i(".bi-palette"), " Save color mode"
                            ],
                        ],
                    ],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col-lg-8")[
                htpy.div(".card")[
                    htpy.div(".card-header")[
                        htpy.h5(".mb-0")["Create, replace, or remove a setting"]
                    ],
                    htpy.div(".card-body")[
                        result
                        and htpy.div(f".alert.{result[0]}", role="alert")[result[1]],
                        htpy.p[
                            "Saving a key that already exists replaces its value. "
                            "Leave the value blank to remove the setting. These "
                            "settings are associated with your user account."
                        ],
                        htpy.form(
                            action=flask.url_for("user_settings"),
                            autocomplete="off",
                            method="post",
                        )[
                            htpy.div(".g-3.row")[
                                htpy.div(".col-md-5")[
                                    htpy.label(
                                        ".form-label",
                                        for_="user-setting-key",
                                    )["Key"],
                                    htpy.input(
                                        "#user-setting-key.form-control",
                                        name="key",
                                        required=True,
                                        type="text",
                                        value=key,
                                    ),
                                ],
                                htpy.div(".col-md-7")[
                                    htpy.label(
                                        ".form-label",
                                        for_="user-setting-value",
                                    )["Value"],
                                    htpy.input(
                                        "#user-setting-value.form-control",
                                        name="value",
                                        type="text",
                                        value=value,
                                    ),
                                ],
                            ],
                            htpy.button(".btn.btn-primary.mt-3", type="submit")[
                                htpy.i(".bi-floppy"), " Save setting"
                            ],
                        ],
                    ],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(
                    ".align-middle.d-block.table.table-bordered.table-sm.table-striped"
                )[
                    htpy.thead[htpy.tr[htpy.th["Key"], htpy.th["Value"]]],
                    htpy.tbody[rows],
                ]
            ]
        ],
    ]
    return str(_base(content))
