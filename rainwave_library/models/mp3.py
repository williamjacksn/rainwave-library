import dataclasses
import logging
import pathlib
import typing

import mutagen.id3

log = logging.getLogger(__name__)

ID3_TAG_LABELS = {
    "album": "Album",
    "title": "Title",
    "artist": "Artist",
    "genre": "Genre",
    "www": "WWW",
    "comment": "Comment",
}


@dataclasses.dataclass(frozen=True)
class Mp3TagValues:
    album: tuple[str, ...] = ()
    title: tuple[str, ...] = ()
    artist: tuple[str, ...] = ()
    genre: tuple[str, ...] = ()
    www: tuple[str, ...] = ()
    comment: tuple[str, ...] = ()
    error: str | None = None


def _text_frame_values(tags: mutagen.id3.ID3, frame_id: str) -> tuple[str, ...]:
    values = []
    for frame in tags.getall(frame_id):
        for value in getattr(frame, "text", ()):
            normalized_value = str(value).strip()
            if normalized_value:
                values.append(normalized_value)
    return tuple(values)


def id3_tag_values_get(filename: str | pathlib.Path) -> Mp3TagValues:
    try:
        tags = mutagen.id3.ID3(filename)
    except mutagen.id3.ID3NoHeaderError:
        return Mp3TagValues(error="No ID3 tags found.")
    except (mutagen.MutagenError, OSError) as error:
        log.warning("Unable to read ID3 tags from %s: %s", filename, error)
        return Mp3TagValues(error="Could not read ID3 tags.")

    www = tuple(
        url
        for frame in tags.getall("WXXX")
        if (url := str(getattr(frame, "url", "")).strip())
    )
    return Mp3TagValues(
        album=_text_frame_values(tags, "TALB"),
        title=_text_frame_values(tags, "TIT2"),
        artist=_text_frame_values(tags, "TPE1"),
        genre=_text_frame_values(tags, "TCON"),
        www=www,
        comment=_text_frame_values(tags, "COMM"),
    )


def id3_tag_values_set(
    filename: str | pathlib.Path,
    tag_name: str,
    value: str,
) -> None:
    if tag_name not in ID3_TAG_LABELS:
        msg = "Choose a valid ID3 tag."
        raise ValueError(msg)
    values = tuple(line.strip() for line in value.splitlines() if line.strip())
    try:
        try:
            tags = mutagen.id3.ID3(filename)
        except mutagen.id3.ID3NoHeaderError:
            tags = mutagen.id3.ID3()

        if tag_name == "album":
            tags.delall("TALB")
            if values:
                tags.add(mutagen.id3.TALB(encoding=3, text=list(values)))
        elif tag_name == "title":
            tags.delall("TIT2")
            if values:
                tags.add(mutagen.id3.TIT2(encoding=3, text=list(values)))
        elif tag_name == "artist":
            tags.delall("TPE1")
            if values:
                tags.add(mutagen.id3.TPE1(encoding=3, text=list(values)))
        elif tag_name == "genre":
            tags.delall("TCON")
            if values:
                tags.add(mutagen.id3.TCON(encoding=3, text=list(values)))
        elif tag_name == "www":
            tags.delall("WXXX")
            for index, url in enumerate(values):
                tags.add(
                    mutagen.id3.WXXX(
                        encoding=3,
                        desc="" if index == 0 else f"Rainwave {index + 1}",
                        url=url,
                    )
                )
        elif tag_name == "comment":
            tags.delall("COMM")
            if values:
                tags.add(
                    mutagen.id3.COMM(
                        encoding=3,
                        lang="eng",
                        desc="",
                        text=list(values),
                    )
                )
        tags.save(filename)
    except (mutagen.MutagenError, OSError) as error:
        log.error("Unable to update %s in %s: %s", tag_name, filename, error)
        msg = "Could not update the ID3 tag."
        raise ValueError(msg) from error


# Special characters sorted by results of ord()
# {
#  '²': 178,
#  'À': 192,
#  'É': 201,
#  'Ü': 220,
#  'à': 224,
#  'á': 225,
#  'â': 226,
#  'ã': 227,
#  'ä': 228,
#  'ç': 231,
#  'è': 232,
#  'é': 233,
#  'ê': 234,
#  'í': 237,
#  'ð', 240,
#  'ñ': 241,
#  'ó': 243,
#  'ö': 246,
#  'ú': 250,
#  'ü': 252,
#  'ā': 257,
#  'ō': 333,
#  'ş': 351,
#  'ū': 363,
#  'К': 1050,  # noqa: RUF003
#  'С': 1057,  # noqa: RUF003
#  'а': 1072,  # noqa: RUF003
#  'в': 1074,
#  'е': 1077,  # noqa: RUF003
#  'и': 1080,
#  'й': 1081,
#  'к': 1082,
#  'м': 1084,
#  'н': 1085,
#  'о': 1086,  # noqa: RUF003
#  'с': 1089,  # noqa: RUF003
#  'т': 1090,
#  'ṃ': 7747,
# }


def make_safe(s: str) -> str:
    """Converts a string to a safe string, with no spaces or special characters"""
    translate_table = {
        ord(char): None
        for char in " !\"#%&'()*+,-./:;<=>?@[\\]^_`{|}~–—あいごま고말싶은하•"  # noqa: RUF001
    }
    special = dict(
        zip(
            map(ord, "²ÀÉÜàáâãäçèéêíðñóöúüāōşūКСавеийкмностṃ"),
            "2AEUaaaaaceeeidnoouuaosuKSaveijkmnostm",
        )
    )
    translate_table.update(special)
    return s.translate(translate_table)


def rename_artist(
    mp3s: typing.Iterable[str | pathlib.Path], old_name: str, new_name: str
) -> list[Exception]:
    errors: list[Exception] = []
    for mp3 in mp3s:
        try:
            tags = mutagen.id3.ID3(mp3)
            artist_frames = tags.getall("TPE1")
            if not artist_frames or not artist_frames[0].text:
                continue
            artists = [artist.strip() for artist in artist_frames[0].text[0].split(",")]
            changed = False
            for index, artist in enumerate(artists):
                if artist == old_name:
                    artists[index] = new_name
                    changed = True
            if not changed:
                continue
            tags.delall("TPE1")
            tags.add(mutagen.id3.TPE1(encoding=3, text=[", ".join(artists)]))
            tags.save(mp3)
            log.info(f"Renamed artist {old_name!r} to {new_name!r} in {mp3}")
        except (mutagen.MutagenError, OSError) as e:
            log.error(f"Unable to rename artist in {mp3}: {e}")
            errors.append(e)
    return errors


def set_tags(filename: str, **kwargs: str) -> str:
    """Takes a filename and the following possible kwargs:
    album, artist, categories, link_text, title, url"""
    log.info(f"Attempting to update tags for {filename}")
    result = ""
    try:
        md = mutagen.id3.ID3(filename)
    except mutagen.id3.ID3NoHeaderError:
        md = mutagen.id3.ID3()
    except mutagen.MutagenError as e:
        log.error(e)
        return str(e)
    for tag_name, tag_value in kwargs.items():
        if tag_name == "album":
            md.delall("TALB")
            md.add(mutagen.id3.TALB(encoding=3, text=[tag_value]))
        elif tag_name == "artist":
            md.delall("TPE1")
            md.add(mutagen.id3.TPE1(encoding=3, text=[tag_value]))
        elif tag_name == "categories":
            md.delall("TCON")
            if tag_value:
                md.add(mutagen.id3.TCON(encoding=3, text=[tag_value]))
        elif tag_name == "link_text":
            md.delall("COMM")
            if tag_value:
                md.add(mutagen.id3.COMM(encoding=3, text=[tag_value]))
        elif tag_name == "title":
            md.delall("TIT2")
            md.add(mutagen.id3.TIT2(encoding=3, text=[tag_value]))
        elif tag_name == "url":
            md.delall("WXXX")
            if tag_value:
                md.add(mutagen.id3.WXXX(encoding=0, url=tag_value))
    try:
        md.save(filename)
        log.info(f"Updated tags for {filename}")
    except mutagen.MutagenError as e:
        log.error(e)
        result = str(e)
    return result


def yield_all(starting_dir: pathlib.Path) -> typing.Iterator[pathlib.Path]:
    for child in starting_dir.iterdir():
        if child.is_dir():
            yield from yield_all(child)
        elif child.suffix.lower() == ".mp3":
            yield child
