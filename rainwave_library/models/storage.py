import dataclasses
import datetime
import enum
import json
import logging
import os
import pathlib
import secrets
import shutil
import sqlite3
import typing

import mutagen
import mutagen.mp3

from rainwave_library.models.rainwave import ChannelRootFolder

log = logging.getLogger(__name__)

USER_COLOR_MODE_SETTING_KEY = "color-mode"
USER_COLOR_MODES = ("light", "dark")
USER_COLOR_MODE_DEFAULT = "light"
USER_SUGGESTION_FILTERS_SETTING_KEY = "suggestion-filters"
LIBRARY_BROWSER_TEXT_PREVIEW_MAX_BYTES = 512 * 1024
_LIBRARY_BROWSER_AUDIO_TYPES = {".mp3": "audio/mpeg"}
_LIBRARY_BROWSER_IMAGE_TYPES = {
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_LIBRARY_BROWSER_TEXT_SUFFIXES = frozenset(
    {
        ".asc",
        ".bat",
        ".cfg",
        ".conf",
        ".css",
        ".csv",
        ".cue",
        ".env",
        ".htm",
        ".html",
        ".ini",
        ".js",
        ".json",
        ".log",
        ".m3u",
        ".m3u8",
        ".md",
        ".nfo",
        ".pls",
        ".ps1",
        ".py",
        ".rst",
        ".sh",
        ".sql",
        ".srt",
        ".text",
        ".toml",
        ".tsv",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)


@dataclasses.dataclass(frozen=True)
class User:
    discord_id: str
    username: str | None
    display_name: str | None
    avatar_url: str | None
    role: str
    created_at: str
    updated_at: str


class LibraryBrowserRoot(enum.StrEnum):
    UPCOMING = "upcoming"
    REMOVED = "removed"

    @property
    def allow_empty_directory_delete(self) -> bool:
        return self is self.UPCOMING

    @property
    def calculate_mp3_duration(self) -> bool:
        return self is self.UPCOMING

    @property
    def directory_name(self) -> str:
        return "~upcoming" if self is self.UPCOMING else "removed"

    @property
    def label(self) -> str:
        return "Upcoming music" if self is self.UPCOMING else "Removed music"


@dataclasses.dataclass(frozen=True)
class LibraryBrowserEntry:
    name: str
    relative_path: str
    is_directory: bool
    is_audio: bool
    is_image: bool
    is_text: bool
    size: int | None
    duration_seconds: float | None


@dataclasses.dataclass(frozen=True)
class LibraryBrowserDirectory:
    root: LibraryBrowserRoot
    path: pathlib.Path
    relative_path: str
    exists: bool
    entries: tuple[LibraryBrowserEntry, ...]


def _library_browser_path_parts(relative_path: str) -> tuple[str, ...]:
    normalized_path = relative_path.replace("\\", "/").strip()
    path = pathlib.PurePosixPath(normalized_path)
    if (
        path.is_absolute()
        or ".." in path.parts
        or pathlib.PureWindowsPath(normalized_path).drive
        or any(ord(character) < 32 for character in normalized_path)
    ):
        msg = "Invalid library browser path."
        raise ValueError(msg)
    return path.parts if normalized_path else ()


def _library_browser_file_is_text(path: pathlib.PurePath) -> bool:
    return path.suffix.casefold() in _LIBRARY_BROWSER_TEXT_SUFFIXES


def _library_browser_audio_mimetype_get(path: pathlib.PurePath) -> str | None:
    return _LIBRARY_BROWSER_AUDIO_TYPES.get(path.suffix.casefold())


def _library_browser_image_mimetype_get(path: pathlib.PurePath) -> str | None:
    return _LIBRARY_BROWSER_IMAGE_TYPES.get(path.suffix.casefold())


def _library_browser_root_get(
    library_root: pathlib.Path,
    browser_root: LibraryBrowserRoot,
) -> pathlib.Path:
    return (library_root / browser_root.directory_name).resolve()


def _upcoming_music_root_get(library_root: pathlib.Path) -> pathlib.Path:
    return _library_browser_root_get(library_root, LibraryBrowserRoot.UPCOMING)


def _library_browser_path_get(
    library_root: pathlib.Path,
    browser_root: LibraryBrowserRoot,
    relative_path: str,
) -> tuple[pathlib.Path, pathlib.Path, tuple[str, ...]]:
    root = _library_browser_root_get(library_root, browser_root)
    parts = _library_browser_path_parts(relative_path)
    candidate = root.joinpath(*parts)
    try:
        resolved_candidate = candidate.resolve(strict=True)
    except FileNotFoundError:
        msg = "That library browser path no longer exists."
        raise ValueError(msg) from None
    if not resolved_candidate.is_relative_to(root):
        msg = "Invalid library browser path."
        raise ValueError(msg)
    return root, resolved_candidate, parts


def _mp3_duration_get(
    directory: pathlib.Path,
    root: pathlib.Path,
) -> float:
    duration_seconds = 0.0
    pending_directories = [directory]
    while pending_directories:
        current_directory = pending_directories.pop()
        try:
            children = current_directory.iterdir()
            for child in children:
                try:
                    if child.is_symlink():
                        continue
                    resolved_child = child.resolve(strict=True)
                    if not resolved_child.is_relative_to(root):
                        continue
                    if resolved_child.is_dir():
                        pending_directories.append(resolved_child)
                    elif (
                        resolved_child.is_file()
                        and resolved_child.suffix.casefold() == ".mp3"
                    ):
                        mp3 = mutagen.mp3.MP3(resolved_child)
                        if mp3.info is not None:
                            duration_seconds += mp3.info.length
                except (mutagen.MutagenError, OSError) as error:
                    log.warning(
                        "Unable to read MP3 file %s: %s",
                        child,
                        error,
                    )
        except OSError as error:
            log.warning(
                "Unable to read folder %s while calculating MP3 duration: %s",
                current_directory,
                error,
            )
    return duration_seconds


def upcoming_music_date_mp3_duration_get(
    library_root: pathlib.Path,
    release_date: str,
) -> float:
    try:
        parsed_release_date = datetime.date.fromisoformat(release_date)
    except ValueError:
        msg = "Choose a valid release date."
        raise ValueError(msg) from None

    root = _upcoming_music_root_get(library_root)
    date_directory = root / parsed_release_date.isoformat()
    if not date_directory.exists():
        return 0.0
    try:
        resolved_date_directory = date_directory.resolve(strict=True)
    except OSError as error:
        msg = "The upcoming music date folder could not be read."
        raise ValueError(msg) from error
    if (
        not resolved_date_directory.is_relative_to(root)
        or not resolved_date_directory.is_dir()
    ):
        msg = "The upcoming music date path is not a folder."
        raise ValueError(msg)
    return _mp3_duration_get(resolved_date_directory, root)


def library_browser_directory_get(
    library_root: pathlib.Path,
    browser_root: LibraryBrowserRoot,
    relative_path: str = "",
) -> LibraryBrowserDirectory:
    root = _library_browser_root_get(library_root, browser_root)
    parts = _library_browser_path_parts(relative_path)
    normalized_path = pathlib.PurePosixPath(*parts).as_posix() if parts else ""
    if not root.exists() and not parts:
        return LibraryBrowserDirectory(browser_root, root, "", False, ())

    _, directory, _ = _library_browser_path_get(
        library_root,
        browser_root,
        relative_path,
    )
    if not directory.is_dir():
        msg = "That library browser path is not a folder."
        raise ValueError(msg)

    entries = []
    try:
        children = tuple(directory.iterdir())
    except OSError as error:
        msg = "The library browser folder could not be read."
        raise ValueError(msg) from error
    for child in children:
        try:
            resolved_child = child.resolve(strict=True)
            if not resolved_child.is_relative_to(root):
                continue
            is_directory = resolved_child.is_dir()
            if not is_directory and not resolved_child.is_file():
                continue
            child_parts = (*parts, child.name)
            entries.append(
                LibraryBrowserEntry(
                    name=child.name,
                    relative_path=pathlib.PurePosixPath(*child_parts).as_posix(),
                    is_directory=is_directory,
                    is_audio=(
                        not is_directory
                        and _library_browser_audio_mimetype_get(child) is not None
                    ),
                    is_image=(
                        not is_directory
                        and _library_browser_image_mimetype_get(child) is not None
                    ),
                    is_text=(not is_directory and _library_browser_file_is_text(child)),
                    size=None if is_directory else resolved_child.stat().st_size,
                    duration_seconds=(
                        _mp3_duration_get(resolved_child, root)
                        if is_directory and browser_root.calculate_mp3_duration
                        else None
                    ),
                )
            )
        except OSError:
            continue
    entries.sort(key=lambda entry: (not entry.is_directory, entry.name.casefold()))
    return LibraryBrowserDirectory(
        browser_root,
        directory,
        normalized_path,
        True,
        tuple(entries),
    )


def library_browser_file_get(
    library_root: pathlib.Path,
    browser_root: LibraryBrowserRoot,
    relative_path: str,
) -> pathlib.Path:
    _, path, _ = _library_browser_path_get(
        library_root,
        browser_root,
        relative_path,
    )
    if not path.is_file():
        msg = "That library browser path is not a file."
        raise ValueError(msg)
    return path


def library_browser_text_file_get(
    library_root: pathlib.Path,
    browser_root: LibraryBrowserRoot,
    relative_path: str,
) -> tuple[pathlib.Path, str, bool]:
    path = library_browser_file_get(library_root, browser_root, relative_path)
    if not _library_browser_file_is_text(path):
        msg = "That file is not a recognized text file."
        raise ValueError(msg)

    try:
        with path.open("rb") as file:
            content_bytes = file.read(LIBRARY_BROWSER_TEXT_PREVIEW_MAX_BYTES + 1)
    except OSError as error:
        msg = "The text file could not be read."
        raise ValueError(msg) from error

    truncated = len(content_bytes) > LIBRARY_BROWSER_TEXT_PREVIEW_MAX_BYTES
    if truncated:
        content_bytes = content_bytes[:LIBRARY_BROWSER_TEXT_PREVIEW_MAX_BYTES]
    content = content_bytes.decode("utf-8-sig", errors="replace")
    return path, content, truncated


def library_browser_image_file_get(
    library_root: pathlib.Path,
    browser_root: LibraryBrowserRoot,
    relative_path: str,
) -> tuple[pathlib.Path, str]:
    path = library_browser_file_get(library_root, browser_root, relative_path)
    mimetype = _library_browser_image_mimetype_get(path)
    if mimetype is None:
        msg = "That file is not a recognized image file."
        raise ValueError(msg)
    return path, mimetype


def library_browser_audio_file_get(
    library_root: pathlib.Path,
    browser_root: LibraryBrowserRoot,
    relative_path: str,
) -> tuple[pathlib.Path, str]:
    path = library_browser_file_get(library_root, browser_root, relative_path)
    mimetype = _library_browser_audio_mimetype_get(path)
    if mimetype is None:
        msg = "That file is not a recognized audio file."
        raise ValueError(msg)
    return path, mimetype


def library_browser_directory_delete(
    library_root: pathlib.Path,
    browser_root: LibraryBrowserRoot,
    relative_path: str,
) -> str:
    if not browser_root.allow_empty_directory_delete:
        msg = f"Folders cannot be deleted from {browser_root.label}."
        raise ValueError(msg)

    parts = _library_browser_path_parts(relative_path)
    if not parts:
        msg = f"The {browser_root.label} root folder cannot be deleted."
        raise ValueError(msg)

    root, directory, _ = _library_browser_path_get(
        library_root,
        browser_root,
        relative_path,
    )
    candidate = root
    for part in parts:
        candidate /= part
        if candidate.is_symlink():
            msg = "Linked library browser folders cannot be deleted."
            raise ValueError(msg)
    if not directory.is_dir():
        msg = "That library browser path is not a folder."
        raise ValueError(msg)
    try:
        candidate.rmdir()
    except OSError as error:
        msg = "Only an empty library browser folder can be deleted."
        raise ValueError(msg) from error
    return pathlib.PurePosixPath(*parts[:-1]).as_posix() if len(parts) > 1 else ""


def _suggestion_release_path_name_get(name: str, label: str) -> str:
    invalid_characters = '<>:"/\\|?*'
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    }
    if (
        not name
        or name in {".", ".."}
        or name[-1] in {" ", "."}
        or any(character in invalid_characters for character in name)
        or any(ord(character) < 32 for character in name)
        or name.split(".", 1)[0].upper() in reserved_names
    ):
        msg = f"Choose a valid {label}."
        raise ValueError(msg)
    if len(name.encode()) > 255:
        msg = f"The {label} is too long."
        raise ValueError(msg)
    return name


def _suggestion_release_folder_path_get(folder_path: str) -> pathlib.PurePosixPath:
    normalized_path = folder_path.strip()
    parts = normalized_path.split("/")
    if not normalized_path or any(not part for part in parts):
        msg = "Choose a valid folder path."
        raise ValueError(msg)
    return pathlib.PurePosixPath(
        *(
            _suggestion_release_path_name_get(part, "folder path segment")
            for part in parts
        )
    )


def suggestion_release_target_get(
    library_root: pathlib.Path,
    release_date: str,
    channel_folder: str,
    folder_path: str,
    *,
    release_immediately: bool = False,
) -> pathlib.Path:
    parsed_release_date = None
    if not release_immediately:
        try:
            parsed_release_date = datetime.date.fromisoformat(release_date)
        except ValueError:
            msg = "Choose a valid release date."
            raise ValueError(msg) from None
        if parsed_release_date <= datetime.date.today():
            msg = "The release date must be in the future."
            raise ValueError(msg)
    try:
        root_folder = ChannelRootFolder(channel_folder)
    except ValueError:
        msg = "Choose a valid channel folder."
        raise ValueError(msg) from None
    release_folder_path = _suggestion_release_folder_path_get(folder_path)

    destination_root = (
        library_root.resolve()
        if release_immediately
        else _upcoming_music_root_get(library_root)
    )
    destination_parent = destination_root / root_folder.value
    if parsed_release_date is not None:
        destination_parent = (
            destination_root / parsed_release_date.isoformat() / root_folder.value
        )
    destination = destination_parent.joinpath(*release_folder_path.parts).resolve()
    if not destination.is_relative_to(destination_root):
        msg = "Invalid release destination."
        raise ValueError(msg)
    return destination


def suggestion_release_schedule(
    library_root: pathlib.Path,
    suggestion_id: str,
    release_date: str,
    channel_folder: str,
    folder_path: str,
    *,
    release_immediately: bool = False,
) -> str:
    destination_root = (
        library_root.resolve()
        if release_immediately
        else _upcoming_music_root_get(library_root)
    )
    destination = suggestion_release_target_get(
        library_root,
        release_date,
        channel_folder,
        folder_path,
        release_immediately=release_immediately,
    )
    if destination.exists() and not release_immediately:
        msg = "That upcoming music destination already exists."
        raise ValueError(msg)
    if destination.exists() and not destination.is_dir():
        msg = "The library destination is not a folder."
        raise ValueError(msg)

    source = suggestion_staging_folder_get(library_root, suggestion_id)
    if not suggestion_staging_files_get(library_root, suggestion_id):
        msg = "Upload at least one file before releasing the suggestion."
        raise ValueError(msg)

    created_directories = []
    destination_parts = destination.parent.relative_to(destination_root).parts
    for directory in (
        destination_root,
        *(
            destination_root.joinpath(*destination_parts[:index])
            for index in range(1, len(destination_parts) + 1)
        ),
    ):
        if directory.exists():
            if not directory.is_dir():
                msg = "The release destination is not a folder."
                raise ValueError(msg)
            continue
        directory.mkdir()
        created_directories.append(directory)
    immediate_destination_created = False
    try:
        if release_immediately:
            if not destination.exists():
                try:
                    destination.mkdir()
                except FileExistsError:
                    if not destination.is_dir():
                        raise
                else:
                    immediate_destination_created = True
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            source.rename(destination)
    except OSError:
        if immediate_destination_created:
            shutil.rmtree(destination, ignore_errors=True)
        for directory in reversed(created_directories):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    return destination.relative_to(destination_root).as_posix()


def suggestion_staging_folder_get(
    library_root: pathlib.Path,
    suggestion_id: str,
) -> pathlib.Path:
    staging_root = (library_root / "staging").resolve()
    suggestion_root = (staging_root / suggestion_id).resolve()
    if suggestion_root == staging_root or not suggestion_root.is_relative_to(
        staging_root
    ):
        msg = "Invalid suggestion staging directory."
        raise ValueError(msg)
    return suggestion_root


def suggestion_staging_mp3_duration_get(
    library_root: pathlib.Path,
    suggestion_id: str,
) -> float:
    suggestion_root = suggestion_staging_folder_get(library_root, suggestion_id)
    if not suggestion_root.is_dir():
        return 0.0
    return _mp3_duration_get(suggestion_root, suggestion_root)


def suggestion_staging_files_get(
    library_root: pathlib.Path,
    suggestion_id: str,
) -> tuple[tuple[str, int], ...]:
    suggestion_root = suggestion_staging_folder_get(library_root, suggestion_id)
    if not suggestion_root.is_dir():
        return ()

    files = []
    for path in suggestion_root.rglob("*"):
        try:
            if not path.is_file():
                continue
            files.append(
                (
                    path.relative_to(suggestion_root).as_posix(),
                    path.stat().st_size,
                )
            )
        except OSError:
            continue
    return tuple(sorted(files, key=lambda file: file[0].casefold()))


def suggestion_staging_files_upload(
    library_root: pathlib.Path,
    suggestion_id: str,
    uploads: typing.Iterable[tuple[str, typing.IO[bytes]]],
) -> tuple[str, ...]:
    normalized_uploads = []
    for original_name, stream in uploads:
        filename = pathlib.PurePosixPath(original_name.replace("\\", "/")).name.strip()
        if (
            not filename
            or filename in {".", ".."}
            or any(ord(character) < 32 for character in filename)
        ):
            msg = "Every uploaded file must have a valid filename."
            raise ValueError(msg)
        if len(filename.encode()) > 255:
            msg = f"The filename {filename!r} is too long."
            raise ValueError(msg)
        normalized_uploads.append((filename, stream))
    if not normalized_uploads:
        msg = "Choose at least one file to upload."
        raise ValueError(msg)

    normalized_names = [filename.casefold() for filename, _ in normalized_uploads]
    if len(normalized_names) != len(set(normalized_names)):
        msg = "The upload contains duplicate filenames."
        raise ValueError(msg)

    suggestion_root = suggestion_staging_folder_get(library_root, suggestion_id)
    suggestion_root.mkdir(parents=True, exist_ok=True)

    destinations = [suggestion_root / filename for filename, _ in normalized_uploads]
    existing_names = {path.name.casefold() for path in suggestion_root.iterdir()}
    if any(
        destination.name.casefold() in existing_names for destination in destinations
    ):
        msg = "A file with that name already exists in the suggestion folder."
        raise ValueError(msg)

    created: list[pathlib.Path] = []
    try:
        for destination, (_, stream) in zip(
            destinations, normalized_uploads, strict=True
        ):
            with destination.open("xb") as target:
                created.append(destination)
                shutil.copyfileobj(stream, target)
    except Exception:
        for destination in created:
            destination.unlink(missing_ok=True)
        raise
    return tuple(destination.name for destination in destinations)


def _suggestion_staging_file_get(
    library_root: pathlib.Path,
    suggestion_id: str,
    relative_path: str,
) -> tuple[pathlib.Path, pathlib.PurePosixPath]:
    normalized_path = relative_path.replace("\\", "/").strip()
    path = pathlib.PurePosixPath(normalized_path)
    if (
        not normalized_path
        or path.is_absolute()
        or path == pathlib.PurePosixPath(".")
        or ".." in path.parts
        or pathlib.PureWindowsPath(normalized_path).drive
        or any(ord(character) < 32 for character in normalized_path)
    ):
        msg = "Invalid suggestion file path."
        raise ValueError(msg)

    suggestion_root = suggestion_staging_folder_get(library_root, suggestion_id)
    candidate = suggestion_root.joinpath(*path.parts)
    try:
        resolved_candidate = candidate.resolve(strict=True)
    except FileNotFoundError:
        msg = "That file no longer exists in the suggestion folder."
        raise ValueError(msg) from None
    if (
        not resolved_candidate.is_relative_to(suggestion_root)
        or not candidate.is_file()
    ):
        msg = "Invalid suggestion file path."
        raise ValueError(msg)
    return candidate, path


def suggestion_staging_file_get(
    library_root: pathlib.Path,
    suggestion_id: str,
    relative_path: str,
) -> pathlib.Path:
    candidate, _ = _suggestion_staging_file_get(
        library_root,
        suggestion_id,
        relative_path,
    )
    return candidate


def suggestion_staging_file_delete(
    library_root: pathlib.Path,
    suggestion_id: str,
    relative_path: str,
) -> str:
    candidate, path = _suggestion_staging_file_get(
        library_root,
        suggestion_id,
        relative_path,
    )

    try:
        candidate.unlink()
    except FileNotFoundError:
        msg = "That file no longer exists in the suggestion folder."
        raise ValueError(msg) from None

    suggestion_root = suggestion_staging_folder_get(library_root, suggestion_id)
    parent = candidate.parent
    while parent != suggestion_root:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent
    return path.as_posix()


def suggestion_staging_files_rename(
    library_root: pathlib.Path,
    suggestion_id: str,
    renames: typing.Mapping[str, str],
) -> tuple[tuple[str, str], ...]:
    if not renames:
        return ()

    suggestion_root = suggestion_staging_folder_get(library_root, suggestion_id)
    rename_paths = []
    source_keys = set()
    target_keys = set()
    for source_path, target_path in renames.items():
        source, normalized_source = _suggestion_staging_file_get(
            library_root,
            suggestion_id,
            source_path,
        )
        normalized_target = pathlib.PurePosixPath(target_path.replace("\\", "/"))
        if (
            normalized_source.suffix.casefold() != ".mp3"
            or normalized_target.is_absolute()
            or normalized_target == pathlib.PurePosixPath(".")
            or ".." in normalized_target.parts
            or pathlib.PureWindowsPath(target_path).drive
            or any(ord(character) < 32 for character in target_path)
            or normalized_target.suffix.casefold() != ".mp3"
            or normalized_target.parent != normalized_source.parent
        ):
            msg = "Invalid normalized MP3 filename."
            raise ValueError(msg)

        destination = source.with_name(normalized_target.name)
        source_key = normalized_source.as_posix().casefold()
        target_key = normalized_target.as_posix().casefold()
        if source_key in source_keys or target_key in target_keys:
            msg = "The normalized MP3 filenames are not unique."
            raise ValueError(msg)
        source_keys.add(source_key)
        target_keys.add(target_key)
        rename_paths.append((source, destination, normalized_source, normalized_target))

    existing_paths = {
        path.relative_to(suggestion_root).as_posix().casefold()
        for path in suggestion_root.rglob("*")
        if path.is_file()
    }
    if any(
        normalized_target.as_posix().casefold() in existing_paths - source_keys
        for _, _, _, normalized_target in rename_paths
    ):
        msg = "A normalized MP3 filename already exists."
        raise ValueError(msg)

    staged_renames: list[tuple[pathlib.Path, pathlib.Path, pathlib.Path]] = []
    try:
        for source, destination, _, _ in rename_paths:
            temporary = source.with_name(
                f".{source.name}.{secrets.token_hex(8)}.normalizing"
            )
            while temporary.exists():
                temporary = source.with_name(
                    f".{source.name}.{secrets.token_hex(8)}.normalizing"
                )
            source.rename(temporary)
            staged_renames.append((source, temporary, destination))
    except OSError:
        for source, temporary, _ in reversed(staged_renames):
            temporary.rename(source)
        raise

    completed: list[tuple[pathlib.Path, pathlib.Path, pathlib.Path]] = []
    try:
        for source, temporary, destination in staged_renames:
            temporary.rename(destination)
            completed.append((source, temporary, destination))
    except OSError:
        for _, temporary, destination in reversed(completed):
            destination.rename(temporary)
        for source, temporary, _ in reversed(staged_renames):
            temporary.rename(source)
        raise

    return tuple(
        (normalized_source.as_posix(), normalized_target.as_posix())
        for _, _, normalized_source, normalized_target in rename_paths
    )


def connection_init(path: str) -> None:
    con = sqlite3.connect(path)
    con.execute("pragma journal_mode=wal")
    con.close()


def connection_get(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path, autocommit=True)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=5000")
    con.execute("pragma foreign_keys=on")
    con.autocommit = False
    return con


def setting_get(con: sqlite3.Connection, key: str) -> str | None:
    row = con.execute(
        "select value from settings where key = :key",
        {"key": key},
    ).fetchone()
    if row is None:
        return None
    return row["value"]


def setting_set(
    con: sqlite3.Connection,
    key: str,
    value: str,
    *,
    protected: bool = False,
) -> bool:
    key = key.strip()
    if not key:
        msg = "Setting key is required."
        raise ValueError(msg)
    if not value:
        msg = "Setting value is required."
        raise ValueError(msg)

    created = setting_get(con, key) is None
    try:
        con.execute(
            """
            insert into settings (key, value, protected)
            values (:key, :value, :protected)
            on conflict (key) do update set
                value = excluded.value,
                protected = max(settings.protected, excluded.protected)
            """,
            {
                "key": key,
                "value": value,
                "protected": int(protected),
            },
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    return created


def settings_get(con: sqlite3.Connection) -> list[tuple[str, str, bool]]:
    rows = con.execute(
        "select key, value, protected from settings order by key"
    ).fetchall()
    return [(row["key"], row["value"], bool(row["protected"])) for row in rows]


def _user_from_row(row: sqlite3.Row) -> User:
    return User(
        discord_id=row["discord_id"],
        username=row["username"],
        display_name=row["display_name"],
        avatar_url=row["avatar_url"],
        role=row["role"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def user_get(con: sqlite3.Connection, discord_id: str) -> User | None:
    row = con.execute(
        "select * from users where discord_id = ?",
        (discord_id.strip(),),
    ).fetchone()
    return _user_from_row(row) if row is not None else None


def staff_users_get(
    con: sqlite3.Connection,
    *,
    exclude_discord_id: str | None = None,
) -> list[User]:
    rows = con.execute(
        """
        select *
        from users
        where role = 'staff'
            and (
                :exclude_discord_id is null
                or discord_id != :exclude_discord_id
            )
        order by
            coalesce(
                nullif(trim(display_name), ''),
                nullif(trim(username), ''),
                discord_id
            ) collate nocase,
            discord_id
        """,
        {"exclude_discord_id": exclude_discord_id},
    ).fetchall()
    return [_user_from_row(row) for row in rows]


def user_upsert(
    con: sqlite3.Connection,
    discord_id: str,
    *,
    username: str | None,
    display_name: str | None,
    avatar_url: str | None,
    role: str,
) -> None:
    discord_id = discord_id.strip()
    if not discord_id:
        msg = "A Discord user ID is required."
        raise ValueError(msg)
    if role not in {"member", "staff"}:
        msg = "Invalid user role."
        raise ValueError(msg)

    try:
        con.execute(
            """
            insert into users (
                discord_id,
                username,
                display_name,
                avatar_url,
                role
            ) values (
                :discord_id,
                :username,
                :display_name,
                :avatar_url,
                :role
            )
            on conflict (discord_id) do update set
                username = excluded.username,
                display_name = excluded.display_name,
                avatar_url = excluded.avatar_url,
                role = excluded.role,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            {
                "discord_id": discord_id,
                "username": username,
                "display_name": display_name,
                "avatar_url": avatar_url,
                "role": role,
            },
        )
        con.commit()
    except Exception:
        con.rollback()
        raise


def user_setting_get(
    con: sqlite3.Connection,
    discord_id: str,
    key: str,
) -> str | None:
    row = con.execute(
        """
        select value
        from user_settings
        where discord_id = :discord_id
            and key = :key
        """,
        {
            "discord_id": discord_id.strip(),
            "key": key.strip(),
        },
    ).fetchone()
    return str(row["value"]) if row is not None else None


def user_setting_set(
    con: sqlite3.Connection,
    discord_id: str,
    key: str,
    value: str,
) -> bool:
    discord_id = discord_id.strip()
    key = key.strip()
    if not discord_id:
        msg = "A Discord user ID is required."
        raise ValueError(msg)
    if not key:
        msg = "Setting key is required."
        raise ValueError(msg)
    if not value:
        msg = "Setting value is required."
        raise ValueError(msg)
    if key == USER_COLOR_MODE_SETTING_KEY and value not in USER_COLOR_MODES:
        msg = "Color mode must be light or dark."
        raise ValueError(msg)

    created = user_setting_get(con, discord_id, key) is None
    try:
        con.execute(
            """
            insert into user_settings (discord_id, key, value)
            values (:discord_id, :key, :value)
            on conflict (discord_id, key) do update set
                value = excluded.value
            """,
            {
                "discord_id": discord_id,
                "key": key,
                "value": value,
            },
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    return created


def user_setting_delete(
    con: sqlite3.Connection,
    discord_id: str,
    key: str,
) -> bool:
    discord_id = discord_id.strip()
    key = key.strip()
    if not discord_id:
        msg = "A Discord user ID is required."
        raise ValueError(msg)
    if not key:
        msg = "Setting key is required."
        raise ValueError(msg)

    try:
        cursor = con.execute(
            """
            delete from user_settings
            where discord_id = :discord_id
                and key = :key
            """,
            {
                "discord_id": discord_id,
                "key": key,
            },
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    return cursor.rowcount > 0


def user_color_mode_get(
    con: sqlite3.Connection,
    discord_id: str,
) -> str:
    value = user_setting_get(con, discord_id, USER_COLOR_MODE_SETTING_KEY)
    return value if value in USER_COLOR_MODES else USER_COLOR_MODE_DEFAULT


def user_settings_get(
    con: sqlite3.Connection,
    discord_id: str,
) -> list[tuple[str, str]]:
    rows = con.execute(
        """
        select key, value
        from user_settings
        where discord_id = ?
        order by key
        """,
        (discord_id.strip(),),
    ).fetchall()
    return [(str(row["key"]), str(row["value"])) for row in rows]


def user_version_get(con: sqlite3.Connection) -> int:
    return con.execute("pragma user_version").fetchone()[0]


def user_version_set(con: sqlite3.Connection, version: int) -> None:
    if not 0 <= version <= 2_147_483_647:
        msg = "SQLite user_version must be a nonnegative 32-bit signed integer"
        raise ValueError(msg)
    con.execute(f"pragma user_version={version}")


def _migration_1(con: sqlite3.Connection) -> None:
    con.execute(
        """
        create table settings (
            key text primary key not null,
            value text not null
        )
        """
    )


def _migration_2(con: sqlite3.Connection) -> None:
    environment_settings = {
        "BSKY_HANDLE": "bluesky/handle",
        "BSKY_PASSWORD": "bluesky/password",
        "DISCORD_GUILD_ID": "discord/guild-id",
        "DISCORD_ROLE_ID_STAFF": "discord/staff-role-id",
        "LIBRARY_ROOT": "library/root",
        "OPENID_CLIENT_ID": "openid/client-id",
        "OPENID_CLIENT_SECRET": "openid/client-secret",
        "RW_CNX": "rainwave/connection",
        "SCHEME": "app/url-scheme",
        "SECRET_KEY": "app/secret-key",
    }
    settings = [
        {"key": key, "value": value}
        for environment_name, key in environment_settings.items()
        if (value := os.getenv(environment_name)) is not None
    ]
    con.executemany(
        """
        insert into settings (key, value)
        values (:key, :value)
        on conflict (key) do nothing
        """,
        settings,
    )


def _migration_3(con: sqlite3.Connection) -> None:
    con.execute(
        """
        alter table settings
        add column protected integer not null default 0
            check (protected in (0, 1))
        """
    )
    con.execute(
        """
        update settings
        set protected = 1
        where key in (
            'app/secret-key',
            'bluesky/password',
            'openid/client-secret',
            'rainwave/connection'
        )
        """
    )


def _migration_4(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create table suggestions (
            suggestion_id text primary key not null,
            title text not null,
            kind text not null default 'addition'
                check (kind in ('addition', 'removal', 'cleanup')),
            status text not null default 'new'
                check (
                    status in (
                        'new', 'claimed', 'fulfilled', 'declined', 'processed'
                    )
                ),
            archived integer not null default 0
                check (archived in (0, 1)),
            description text not null default '',
            requester_name text,
            requester_discord_id text,
            requested_at text,
            claimed_by_name text,
            claimed_by_discord_id text,
            claimed_at text,
            resolved_at text,
            resolution_notes text,
            sort_order real not null default 0,
            created_at text not null,
            updated_at text not null,
            trello_card_id text unique,
            trello_url text
        ) without rowid;

        create index suggestions_status_idx
            on suggestions (archived, status, sort_order);
        create index suggestions_claimed_by_idx
            on suggestions (claimed_by_discord_id, claimed_by_name);

        create table suggestion_channels (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            channel_id integer not null,
            is_primary integer not null default 0
                check (is_primary in (0, 1)),
            primary key (suggestion_id, channel_id)
        ) without rowid;

        create table suggestion_links (
            link_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            link_type text not null,
            url text not null,
            label text,
            sort_order real not null default 0,
            trello_attachment_id text unique,
            unique (suggestion_id, url)
        ) without rowid;

        create index suggestion_links_suggestion_idx
            on suggestion_links (suggestion_id, sort_order);

        create table suggestion_tags (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            tag text not null,
            primary key (suggestion_id, tag)
        ) without rowid;

        create table suggestion_activity (
            activity_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            activity_type text not null,
            actor_name text,
            actor_discord_id text,
            body text,
            old_value text,
            new_value text,
            created_at text not null,
            trello_action_id text unique,
            trello_member_id text
        ) without rowid;

        create index suggestion_activity_suggestion_idx
            on suggestion_activity (suggestion_id, created_at);
        """
    )


def _migration_5(con: sqlite3.Connection) -> None:
    con.execute(
        """
        update suggestions
        set status = 'fulfilled'
        where status = 'processed'
        """
    )


def _migration_6(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create temp table _migration_6_suggestions as
            select * from suggestions;
        create temp table _migration_6_suggestion_channels as
            select * from suggestion_channels;
        create temp table _migration_6_suggestion_links as
            select * from suggestion_links;
        create temp table _migration_6_suggestion_tags as
            select * from suggestion_tags;
        create temp table _migration_6_suggestion_activity as
            select * from suggestion_activity;

        drop table suggestion_activity;
        drop table suggestion_tags;
        drop table suggestion_links;
        drop table suggestion_channels;
        drop table suggestions;

        create table suggestions (
            suggestion_id text primary key not null,
            title text not null,
            kind text not null default 'addition'
                check (kind in ('addition', 'removal', 'cleanup')),
            status text not null default 'new'
                check (
                    status in (
                        'new', 'claimed', 'accepted', 'uploaded', 'declined'
                    )
                ),
            archived integer not null default 0
                check (archived in (0, 1)),
            description text not null default '',
            requester_name text,
            requester_discord_id text,
            requested_at text,
            claimed_by_name text,
            claimed_by_discord_id text,
            claimed_at text,
            resolved_at text,
            resolution_notes text,
            sort_order real not null default 0,
            created_at text not null,
            updated_at text not null,
            trello_card_id text unique,
            trello_url text
        ) without rowid;

        create index suggestions_status_idx
            on suggestions (archived, status, sort_order);
        create index suggestions_claimed_by_idx
            on suggestions (claimed_by_discord_id, claimed_by_name);

        insert into suggestions (
            suggestion_id,
            title,
            kind,
            status,
            archived,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            resolution_notes,
            sort_order,
            created_at,
            updated_at,
            trello_card_id,
            trello_url
        )
        select
            suggestion_id,
            title,
            kind,
            case
                when status in ('fulfilled', 'processed') then 'uploaded'
                else status
            end,
            archived,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            resolution_notes,
            sort_order,
            created_at,
            updated_at,
            trello_card_id,
            trello_url
        from _migration_6_suggestions;

        create table suggestion_channels (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            channel_id integer not null,
            is_primary integer not null default 0
                check (is_primary in (0, 1)),
            primary key (suggestion_id, channel_id)
        ) without rowid;

        insert into suggestion_channels (suggestion_id, channel_id, is_primary)
        select suggestion_id, channel_id, is_primary
        from _migration_6_suggestion_channels;

        create table suggestion_links (
            link_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            link_type text not null,
            url text not null,
            label text,
            sort_order real not null default 0,
            trello_attachment_id text unique,
            unique (suggestion_id, url)
        ) without rowid;

        create index suggestion_links_suggestion_idx
            on suggestion_links (suggestion_id, sort_order);

        insert into suggestion_links (
            link_id,
            suggestion_id,
            link_type,
            url,
            label,
            sort_order,
            trello_attachment_id
        )
        select
            link_id,
            suggestion_id,
            link_type,
            url,
            label,
            sort_order,
            trello_attachment_id
        from _migration_6_suggestion_links;

        create table suggestion_tags (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            tag text not null,
            primary key (suggestion_id, tag)
        ) without rowid;

        insert into suggestion_tags (suggestion_id, tag)
        select suggestion_id, tag
        from _migration_6_suggestion_tags;

        create table suggestion_activity (
            activity_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            activity_type text not null,
            actor_name text,
            actor_discord_id text,
            body text,
            old_value text,
            new_value text,
            created_at text not null,
            trello_action_id text unique,
            trello_member_id text
        ) without rowid;

        create index suggestion_activity_suggestion_idx
            on suggestion_activity (suggestion_id, created_at);

        insert into suggestion_activity (
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_action_id,
            trello_member_id
        )
        select
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_action_id,
            trello_member_id
        from _migration_6_suggestion_activity;

        drop table _migration_6_suggestion_activity;
        drop table _migration_6_suggestion_tags;
        drop table _migration_6_suggestion_links;
        drop table _migration_6_suggestion_channels;
        drop table _migration_6_suggestions;
        """
    )


def _migration_7(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        update suggestion_activity
        set activity_type = 'updated-suggested-by-name'
        where activity_type = 'updated-requester-name';

        update suggestion_activity
        set activity_type = 'updated-suggested-by-discord-id'
        where activity_type = 'updated-requester-discord-id';

        update suggestion_activity
        set activity_type = 'updated-suggested-at'
        where activity_type = 'updated-requested-at';
        """
    )


def _migration_8(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create temp table _migration_8_suggestions as
            select * from suggestions;
        create temp table _migration_8_suggestion_channels as
            select * from suggestion_channels;
        create temp table _migration_8_suggestion_links as
            select * from suggestion_links;
        create temp table _migration_8_suggestion_tags as
            select * from suggestion_tags;
        create temp table _migration_8_suggestion_activity as
            select * from suggestion_activity;

        drop table suggestion_activity;
        drop table suggestion_tags;
        drop table suggestion_links;
        drop table suggestion_channels;
        drop table suggestions;

        create table suggestions (
            suggestion_id text primary key not null,
            title text not null,
            kind text not null default 'new-album'
                check (
                    kind in (
                        'new-album',
                        'add-to-existing-album',
                        'metadata-update',
                        'removal'
                    )
                ),
            status text not null default 'new'
                check (
                    status in (
                        'new', 'claimed', 'accepted', 'uploaded', 'declined'
                    )
                ),
            archived integer not null default 0
                check (archived in (0, 1)),
            description text not null default '',
            requester_name text,
            requester_discord_id text,
            requested_at text,
            claimed_by_name text,
            claimed_by_discord_id text,
            claimed_at text,
            resolved_at text,
            resolution_notes text,
            sort_order real not null default 0,
            created_at text not null,
            updated_at text not null,
            trello_card_id text unique,
            trello_url text
        ) without rowid;

        create index suggestions_status_idx
            on suggestions (archived, status, sort_order);
        create index suggestions_claimed_by_idx
            on suggestions (claimed_by_discord_id, claimed_by_name);

        insert into suggestions (
            suggestion_id,
            title,
            kind,
            status,
            archived,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            resolution_notes,
            sort_order,
            created_at,
            updated_at,
            trello_card_id,
            trello_url
        )
        select
            suggestion_id,
            title,
            case kind
                when 'addition' then 'new-album'
                when 'cleanup' then 'metadata-update'
                when 'removal' then 'removal'
                else 'new-album'
            end,
            status,
            archived,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            resolution_notes,
            sort_order,
            created_at,
            updated_at,
            trello_card_id,
            trello_url
        from _migration_8_suggestions;

        create table suggestion_channels (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            channel_id integer not null,
            is_primary integer not null default 0
                check (is_primary in (0, 1)),
            primary key (suggestion_id, channel_id)
        ) without rowid;

        insert into suggestion_channels (suggestion_id, channel_id, is_primary)
        select suggestion_id, channel_id, is_primary
        from _migration_8_suggestion_channels;

        create table suggestion_links (
            link_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            link_type text not null,
            url text not null,
            label text,
            sort_order real not null default 0,
            trello_attachment_id text unique,
            unique (suggestion_id, url)
        ) without rowid;

        create index suggestion_links_suggestion_idx
            on suggestion_links (suggestion_id, sort_order);

        insert into suggestion_links (
            link_id,
            suggestion_id,
            link_type,
            url,
            label,
            sort_order,
            trello_attachment_id
        )
        select
            link_id,
            suggestion_id,
            link_type,
            url,
            label,
            sort_order,
            trello_attachment_id
        from _migration_8_suggestion_links;

        create table suggestion_tags (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            tag text not null,
            primary key (suggestion_id, tag)
        ) without rowid;

        insert into suggestion_tags (suggestion_id, tag)
        select suggestion_id, tag
        from _migration_8_suggestion_tags;

        create table suggestion_activity (
            activity_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            activity_type text not null,
            actor_name text,
            actor_discord_id text,
            body text,
            old_value text,
            new_value text,
            created_at text not null,
            trello_action_id text unique,
            trello_member_id text
        ) without rowid;

        create index suggestion_activity_suggestion_idx
            on suggestion_activity (suggestion_id, created_at);

        insert into suggestion_activity (
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_action_id,
            trello_member_id
        )
        select
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_action_id,
            trello_member_id
        from _migration_8_suggestion_activity;

        drop table _migration_8_suggestion_activity;
        drop table _migration_8_suggestion_tags;
        drop table _migration_8_suggestion_links;
        drop table _migration_8_suggestion_channels;
        drop table _migration_8_suggestions;
        """
    )


def _migration_9(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        update suggestion_activity
        set
            old_value = case old_value
                when 'addition' then 'new-album'
                when 'cleanup' then 'metadata-update'
                else old_value
            end,
            new_value = case new_value
                when 'addition' then 'new-album'
                when 'cleanup' then 'metadata-update'
                else new_value
            end
        where activity_type = 'updated-kind';
        """
    )


def _migration_10(con: sqlite3.Connection) -> None:
    con.execute("drop table if exists suggestion_tags")


def _migration_11(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create table _migration_11_suggestion_links (
            link_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            link_type text not null,
            url text not null,
            label text,
            sort_order real not null default 0,
            unique (suggestion_id, url)
        ) without rowid;

        insert into _migration_11_suggestion_links (
            link_id,
            suggestion_id,
            link_type,
            url,
            label,
            sort_order
        )
        select
            link_id,
            suggestion_id,
            link_type,
            url,
            label,
            sort_order
        from suggestion_links;

        drop table suggestion_links;
        alter table _migration_11_suggestion_links rename to suggestion_links;

        create index suggestion_links_suggestion_idx
            on suggestion_links (suggestion_id, sort_order);
        """
    )


def _migration_12(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create table _migration_12_suggestion_links (
            link_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            link_type text not null,
            url text not null,
            label text,
            unique (suggestion_id, url)
        ) without rowid;

        insert into _migration_12_suggestion_links (
            link_id,
            suggestion_id,
            link_type,
            url,
            label
        )
        select
            link_id,
            suggestion_id,
            link_type,
            url,
            label
        from suggestion_links;

        drop table suggestion_links;
        alter table _migration_12_suggestion_links rename to suggestion_links;
        """
    )


def _migration_13(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create table _migration_13_suggestion_links (
            link_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            url text not null,
            label text,
            unique (suggestion_id, url)
        ) without rowid;

        insert into _migration_13_suggestion_links (
            link_id,
            suggestion_id,
            url,
            label
        )
        select
            link_id,
            suggestion_id,
            url,
            label
        from suggestion_links;

        drop table suggestion_links;
        alter table _migration_13_suggestion_links rename to suggestion_links;
        """
    )


def _migration_14(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create table _migration_14_suggestion_activity (
            activity_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            activity_type text not null,
            actor_name text,
            actor_discord_id text,
            body text,
            old_value text,
            new_value text,
            created_at text not null,
            trello_member_id text
        ) without rowid;

        insert into _migration_14_suggestion_activity (
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_member_id
        )
        select
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_member_id
        from suggestion_activity;

        drop table suggestion_activity;
        alter table _migration_14_suggestion_activity rename to suggestion_activity;

        create index suggestion_activity_suggestion_idx
            on suggestion_activity (suggestion_id, created_at);
        """
    )


def _migration_15(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create temp table _migration_15_suggestions as
            select * from suggestions;
        create temp table _migration_15_suggestion_channels as
            select * from suggestion_channels;
        create temp table _migration_15_suggestion_links as
            select * from suggestion_links;
        create temp table _migration_15_suggestion_activity as
            select * from suggestion_activity;

        drop table suggestion_activity;
        drop table suggestion_links;
        drop table suggestion_channels;
        drop table suggestions;

        create table suggestions (
            suggestion_id text primary key not null,
            title text not null,
            kind text not null default 'new-album'
                check (
                    kind in (
                        'new-album',
                        'add-to-existing-album',
                        'metadata-update',
                        'removal'
                    )
                ),
            status text not null default 'new'
                check (
                    status in (
                        'new', 'claimed', 'accepted', 'uploaded', 'declined'
                    )
                ),
            description text not null default '',
            requester_name text,
            requester_discord_id text,
            requested_at text,
            claimed_by_name text,
            claimed_by_discord_id text,
            claimed_at text,
            resolved_at text,
            created_at text not null,
            updated_at text not null
        ) without rowid;

        create index suggestions_status_idx
            on suggestions (status, requested_at);
        create index suggestions_claimed_by_idx
            on suggestions (claimed_by_discord_id, claimed_by_name);

        insert into suggestions (
            suggestion_id,
            title,
            kind,
            status,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            created_at,
            updated_at
        )
        select
            suggestion_id,
            title,
            kind,
            status,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            created_at,
            updated_at
        from _migration_15_suggestions;

        create table suggestion_channels (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            channel_id integer not null,
            is_primary integer not null default 0
                check (is_primary in (0, 1)),
            primary key (suggestion_id, channel_id)
        ) without rowid;

        insert into suggestion_channels (suggestion_id, channel_id, is_primary)
        select suggestion_id, channel_id, is_primary
        from _migration_15_suggestion_channels;

        create table suggestion_links (
            link_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            url text not null,
            label text,
            unique (suggestion_id, url)
        ) without rowid;

        insert into suggestion_links (
            link_id,
            suggestion_id,
            url,
            label
        )
        select
            link_id,
            suggestion_id,
            url,
            label
        from _migration_15_suggestion_links;

        create table suggestion_activity (
            activity_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            activity_type text not null,
            actor_name text,
            actor_discord_id text,
            body text,
            old_value text,
            new_value text,
            created_at text not null,
            trello_member_id text
        ) without rowid;

        create index suggestion_activity_suggestion_idx
            on suggestion_activity (suggestion_id, created_at);

        insert into suggestion_activity (
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_member_id
        )
        select
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_member_id
        from _migration_15_suggestion_activity;

        drop table _migration_15_suggestion_activity;
        drop table _migration_15_suggestion_links;
        drop table _migration_15_suggestion_channels;
        drop table _migration_15_suggestions;
        """
    )


def _migration_16(con: sqlite3.Connection) -> None:
    con.execute(
        """
        create table users (
            discord_id text primary key not null,
            username text,
            display_name text,
            avatar_url text,
            role text not null default 'member'
                check (role in ('member', 'staff')),
            created_at text not null
                default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at text not null
                default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        ) without rowid
        """
    )


def _migration_17(con: sqlite3.Connection) -> None:
    con.execute(
        """
        create table user_settings (
            discord_id text not null
                references users (discord_id) on delete cascade,
            key text not null,
            value text not null,
            primary key (discord_id, key)
        ) without rowid
        """
    )


def _migration_18(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create temp table _migration_18_suggestions as
            select * from suggestions;
        create temp table _migration_18_suggestion_channels as
            select * from suggestion_channels;
        create temp table _migration_18_suggestion_links as
            select * from suggestion_links;
        create temp table _migration_18_suggestion_activity as
            select * from suggestion_activity;

        drop table suggestion_activity;
        drop table suggestion_links;
        drop table suggestion_channels;
        drop table suggestions;

        create table suggestions (
            suggestion_id text primary key not null,
            title text not null,
            kind text not null default 'new-album'
                check (
                    kind in (
                        'new-album',
                        'add-to-existing-album',
                        'metadata-update',
                        'removal'
                    )
                ),
            status text not null default 'new'
                check (
                    status in (
                        'new', 'claimed', 'accepted', 'completed', 'declined'
                    )
                ),
            description text not null default '',
            requester_name text,
            requester_discord_id text,
            requested_at text,
            claimed_by_name text,
            claimed_by_discord_id text,
            claimed_at text,
            resolved_at text,
            created_at text not null,
            updated_at text not null
        ) without rowid;

        create index suggestions_status_idx
            on suggestions (status, requested_at);
        create index suggestions_claimed_by_idx
            on suggestions (claimed_by_discord_id, claimed_by_name);

        insert into suggestions (
            suggestion_id,
            title,
            kind,
            status,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            created_at,
            updated_at
        )
        select
            suggestion_id,
            title,
            kind,
            case status
                when 'uploaded' then 'completed'
                else status
            end,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            created_at,
            updated_at
        from _migration_18_suggestions;

        create table suggestion_channels (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            channel_id integer not null,
            is_primary integer not null default 0
                check (is_primary in (0, 1)),
            primary key (suggestion_id, channel_id)
        ) without rowid;

        insert into suggestion_channels (suggestion_id, channel_id, is_primary)
        select suggestion_id, channel_id, is_primary
        from _migration_18_suggestion_channels;

        create table suggestion_links (
            link_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            url text not null,
            label text,
            unique (suggestion_id, url)
        ) without rowid;

        insert into suggestion_links (
            link_id,
            suggestion_id,
            url,
            label
        )
        select
            link_id,
            suggestion_id,
            url,
            label
        from _migration_18_suggestion_links;

        create table suggestion_activity (
            activity_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            activity_type text not null,
            actor_name text,
            actor_discord_id text,
            body text,
            old_value text,
            new_value text,
            created_at text not null,
            trello_member_id text
        ) without rowid;

        create index suggestion_activity_suggestion_idx
            on suggestion_activity (suggestion_id, created_at);

        insert into suggestion_activity (
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_member_id
        )
        select
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            case
                when activity_type = 'updated-status' and old_value = 'uploaded'
                then 'completed'
                else old_value
            end,
            case
                when activity_type = 'updated-status' and new_value = 'uploaded'
                then 'completed'
                else new_value
            end,
            created_at,
            trello_member_id
        from _migration_18_suggestion_activity;

        drop table _migration_18_suggestion_activity;
        drop table _migration_18_suggestion_links;
        drop table _migration_18_suggestion_channels;
        drop table _migration_18_suggestions;
        """
    )

    rows = con.execute(
        """
        select discord_id, value
        from user_settings
        where key = :key
        """,
        {"key": USER_SUGGESTION_FILTERS_SETTING_KEY},
    ).fetchall()
    for row in rows:
        try:
            filters = json.loads(str(row["value"]))
        except json.JSONDecodeError:
            continue
        if not isinstance(filters, dict) or not isinstance(filters.get("status"), list):
            continue
        statuses = filters["status"]
        migrated_statuses = [
            "completed" if status == "uploaded" else status for status in statuses
        ]
        if migrated_statuses == statuses:
            continue
        filters["status"] = migrated_statuses
        con.execute(
            """
            update user_settings
            set value = :value
            where discord_id = :discord_id
                and key = :key
            """,
            {
                "discord_id": row["discord_id"],
                "key": USER_SUGGESTION_FILTERS_SETTING_KEY,
                "value": json.dumps(filters),
            },
        )


def _migration_19(con: sqlite3.Connection) -> None:
    con.execute(
        """
        create table suggestion_file_reviews (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            relative_path text not null,
            decision text not null
                check (decision in ('keep', 'pass')),
            reviewed_by_discord_id text,
            reviewed_at text not null
                default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            primary key (suggestion_id, relative_path)
        ) without rowid
        """
    )


MIGRATIONS = (
    _migration_1,
    _migration_2,
    _migration_3,
    _migration_4,
    _migration_5,
    _migration_6,
    _migration_7,
    _migration_8,
    _migration_9,
    _migration_10,
    _migration_11,
    _migration_12,
    _migration_13,
    _migration_14,
    _migration_15,
    _migration_16,
    _migration_17,
    _migration_18,
    _migration_19,
)


def migrate(con: sqlite3.Connection) -> None:
    current_version = user_version_get(con)
    latest_version = len(MIGRATIONS)
    if not 0 <= current_version <= latest_version:
        msg = (
            f"Unsupported database version {current_version}; "
            f"latest supported version is {latest_version}"
        )
        raise RuntimeError(msg)

    try:
        for version, migration in enumerate(MIGRATIONS, start=1):
            if version <= current_version:
                continue
            log.info("Running database migration %d", version)
            migration(con)
            user_version_set(con, version)
        con.commit()
    except Exception:
        con.rollback()
        raise
