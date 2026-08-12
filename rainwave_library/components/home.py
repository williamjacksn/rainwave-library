import pathlib

import flask
import htpy

from rainwave_library.models.storage import (
    LibraryBrowserDirectory,
    LibraryBrowserEntry,
    LibraryBrowserRoot,
)

from .common import _back_button, _base, _duration_hms, _user_menu


def _library_browser_entry(
    entry: LibraryBrowserEntry,
    browser_root: LibraryBrowserRoot,
) -> htpy.Element:
    content = htpy.fragment[
        htpy.i(
            ".bi-folder-fill.fs-4.text-warning"
            if entry.is_directory
            else (
                ".bi-file-earmark-text.fs-4.text-secondary"
                if entry.is_text
                else ".bi-file-earmark.fs-4.text-secondary"
            )
        ),
        htpy.div(".flex-grow-1.text-break")[entry.name],
        (
            htpy.span(".small.text-nowrap.text-secondary")[
                f"{_duration_hms(entry.duration_seconds)} MP3"
            ]
            if entry.duration_seconds is not None
            else (
                htpy.span(".small.text-nowrap.text-secondary")[
                    f"{entry.size or 0:,} bytes"
                ]
                if not entry.is_directory
                else None
            )
        ),
    ]
    if entry.is_text:
        return htpy.button(
            ".align-items-center.d-flex.gap-3.list-group-item."
            "list-group-item-action.text-start",
            aria_label=f"Preview {entry.name}",
            data_bs_target="#modal-lg",
            data_bs_toggle="modal",
            hx_get=flask.url_for(
                "library_browser_text_preview",
                browser_root=browser_root.value,
                path=entry.relative_path,
            ),
            hx_swap="outerHTML",
            hx_target="#modal-lg-content",
            type="button",
        )[content]

    href = (
        flask.url_for(
            "library_browser",
            browser_root=browser_root.value,
            path=entry.relative_path,
        )
        if entry.is_directory
        else flask.url_for(
            "library_browser_file",
            browser_root=browser_root.value,
            path=entry.relative_path,
        )
    )
    return htpy.a(
        ".align-items-center.d-flex.gap-3.list-group-item.list-group-item-action",
        download=None if entry.is_directory else entry.name,
        href=href,
    )[content]


def library_browser_text_preview(
    browser_root: LibraryBrowserRoot,
    path: str,
    content: str,
    *,
    truncated: bool,
) -> str:
    download_url = flask.url_for(
        "library_browser_file",
        browser_root=browser_root.value,
        path=path,
    )
    return str(
        htpy.div("#modal-lg-content.modal-content")[
            htpy.div(".modal-header")[
                htpy.h5(".mb-0.modal-title.text-break")[path],
                htpy.button(
                    ".btn-close",
                    aria_label="Close",
                    data_bs_dismiss="modal",
                    type="button",
                ),
            ],
            htpy.div(".modal-body")[
                (
                    htpy.div(".alert.alert-warning", role="alert")[
                        "This preview is limited to the first 512 KiB of the file."
                    ]
                    if truncated
                    else None
                ),
                htpy.pre(".bg-body-tertiary.border.mb-0.p-3.rounded.text-file-preview")[
                    content
                ],
            ],
            htpy.div(".modal-footer")[
                htpy.a(
                    ".btn.btn-primary",
                    download=pathlib.PurePosixPath(path).name,
                    href=download_url,
                )[htpy.i(".bi-download"), " Download"],
                htpy.button(
                    ".btn.btn-secondary",
                    data_bs_dismiss="modal",
                    type="button",
                )["Close"],
            ],
        ]
    )


def _library_browser_breadcrumbs(
    directory: LibraryBrowserDirectory,
) -> htpy.Element:
    parts = (
        pathlib.PurePosixPath(directory.relative_path).parts
        if directory.relative_path
        else ()
    )
    breadcrumbs = [
        htpy.li(
            ".active.breadcrumb-item" if not parts else ".breadcrumb-item",
            aria_current="page" if not parts else None,
        )[
            directory.root.label
            if not parts
            else htpy.a(
                href=flask.url_for(
                    "library_browser",
                    browser_root=directory.root.value,
                )
            )[directory.root.label]
        ]
    ]
    for index, part in enumerate(parts):
        is_current = index == len(parts) - 1
        path = pathlib.PurePosixPath(*parts[: index + 1]).as_posix()
        breadcrumbs.append(
            htpy.li(
                ".active.breadcrumb-item" if is_current else ".breadcrumb-item",
                aria_current="page" if is_current else None,
            )[
                part
                if is_current
                else htpy.a(
                    href=flask.url_for(
                        "library_browser",
                        browser_root=directory.root.value,
                        path=path,
                    )
                )[part]
            ]
        )
    return htpy.nav(aria_label=f"{directory.root.label} folders")[
        htpy.ol(".breadcrumb")[breadcrumbs]
    ]


def _library_browser_empty_folder(
    directory: LibraryBrowserDirectory,
) -> htpy.Element:
    folder_name = pathlib.PurePosixPath(directory.relative_path).name
    delete_url = flask.url_for(
        "library_browser_folder_delete",
        browser_root=directory.root.value,
    )
    return htpy.div[
        htpy.p(".text-secondary")["This folder is empty."],
        directory.relative_path
        and directory.root.allow_empty_directory_delete
        and htpy.form(
            action=delete_url,
            hx_confirm=f'Delete the empty folder "{folder_name}"?',
            hx_disabled_elt="button",
            hx_post=delete_url,
            hx_swap="none",
            method="post",
        )[
            htpy.input(
                name="path",
                type="hidden",
                value=directory.relative_path,
            ),
            htpy.button(".btn.btn-danger", type="submit")[
                htpy.i(".bi-trash"), " Delete empty folder"
            ],
        ],
    ]


def library_browser(directory: LibraryBrowserDirectory) -> str:
    content = [
        htpy.div(".g-1.pt-3.row")[
            _back_button(flask.url_for("index"), "Home"),
            _user_menu(),
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.h1["Library files"],
                htpy.code(".d-block.small.text-break.user-select-all")[
                    str(directory.path)
                ],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.nav(aria_label="Library folder selection")[
                    htpy.div(".nav.nav-tabs.mb-3")[
                        [
                            htpy.a(
                                class_=[
                                    "nav-link",
                                    {"active": browser_root is directory.root},
                                ],
                                aria_current=(
                                    "page" if browser_root is directory.root else None
                                ),
                                href=flask.url_for(
                                    "library_browser",
                                    browser_root=browser_root.value,
                                ),
                            )[browser_root.label]
                            for browser_root in LibraryBrowserRoot
                        ]
                    ]
                ],
                _library_browser_breadcrumbs(directory),
                (
                    htpy.div(".list-group")[
                        [
                            _library_browser_entry(entry, directory.root)
                            for entry in directory.entries
                        ]
                    ]
                    if directory.entries
                    else (
                        _library_browser_empty_folder(directory)
                        if directory.exists
                        else htpy.div(".alert.alert-warning", role="alert")[
                            f"The {directory.root.label.lower()} folder does not exist."
                        ]
                    )
                ),
            ]
        ],
    ]
    return str(_base(content))


def welcome(role: str) -> str:
    tools: list[tuple[str, str, str]] = [
        (
            "suggestions",
            "Music suggestions",
            "Browse music suggested for the Rainwave library",
        )
    ]
    if role == "staff":
        tools.extend(
            [
                ("songs", "Songs", "Browse and manage songs in the Rainwave library"),
                ("albums", "Albums", "Browse albums and check for missing art"),
                ("artists", "Artists", "Browse artists and their song counts"),
                (
                    "listeners",
                    "Listeners",
                    "Browse and manage Rainwave listener accounts",
                ),
                (
                    "get_ocremix",
                    "OC ReMix",
                    "Download and tag remixes from ocremix.org",
                ),
                (
                    "library_browser_index",
                    "Library files",
                    "Browse upcoming and removed music files",
                ),
                (
                    "bluesky",
                    "Post to Bluesky",
                    "Post an update to the Rainwave Bluesky account",
                ),
                (
                    "settings",
                    "Application settings",
                    "View application configuration",
                ),
            ]
        )
    content = [
        htpy.div(".g-1.pt-3.row")[
            htpy.div(".col-auto.me-auto")[
                htpy.a(".btn.btn-secondary", href="#")[
                    htpy.i(".bi-boombox-fill", style="color: #f73"), " Rainwave Library"
                ]
            ],
            _user_menu(),
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.div(".list-group")[
                    [
                        htpy.a(
                            ".list-group-item.list-group-item-action",
                            href=flask.url_for(endpoint),
                        )[
                            htpy.div(".fw-semibold")[label],
                            htpy.div(".small.text-secondary")[description],
                        ]
                        for endpoint, label, description in tools
                    ]
                    if tools
                    else htpy.p["No tools are available for your account yet."]
                ]
            ]
        ],
    ]
    return str(_base(content))
