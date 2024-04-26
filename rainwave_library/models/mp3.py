import logging
import mutagen.id3

log = logging.getLogger(__name__)


def set_tags(filename: str, **kwargs):
    """Takes a filename and the following possible kwargs: album, artist, categories, link_text, title, url"""
    log.info(f'Attempting to update tags for {filename}')
    try:
        md = mutagen.id3.ID3(filename)
    except mutagen.id3.ID3NoHeaderError:
        md = mutagen.id3.ID3()
    for tag_name, tag_value in kwargs.items():
        if tag_name == 'album':
            md.delall('TALB')
            md.add(mutagen.id3.TALB(encoding=3, text=[tag_value]))
        elif tag_name == 'artist':
            md.delall('TPE1')
            md.add(mutagen.id3.TPE1(encoding=3, text=[tag_value]))
        elif tag_name == 'categories':
            md.delall('TCON')
            if tag_value:
                md.add(mutagen.id3.TCON(encoding=3, text=[tag_value]))
        elif tag_name == 'link_text':
            md.delall('COMM')
            if tag_value:
                md.add(mutagen.id3.COMM(encoding=3, text=[tag_value]))
        elif tag_name == 'title':
            md.delall('TIT2')
            md.add(mutagen.id3.TIT2(encoding=3, text=[tag_value]))
        elif tag_name == 'url':
            md.delall('WXXX')
            if tag_value:
                md.add(mutagen.id3.WXXX(encoding=0, url=tag_value))
    md.save(filename)
    log.info(f'Updated tags for {filename}')
