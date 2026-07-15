import logging
import pathlib
import typing

import mutagen.id3

log = logging.getLogger(__name__)


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
