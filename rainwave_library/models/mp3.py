import logging
import mutagen.id3

log = logging.getLogger(__name__)


# Special characters sorted by results of ord()
# {
#  '²': 178
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
#  'ş': 351,
#  'К': 1050,
#  'С': 1057,
#  'а': 1072,
#  'в': 1074,
#  'е': 1077,
#  'и': 1080,
#  'й': 1081,
#  'к': 1082,
#  'м': 1084,
#  'н': 1085,
#  'о': 1086,
#  'с': 1089,
#  'т': 1090
# }

def make_safe(s: str) -> str:
    """Converts a string to a safe string, with no spaces or special characters"""
    translate_table = {ord(char): None for char in ' !"#%&\'()*+,-./:;<=>?@[\\]^_`{|}~–—あいごま고말싶은하'}
    special = dict(zip(map(ord, '²ÉÜàáâãäçèéêíðñóöúüşКСавеийкмност'), '2EUaaaaaceeeidnoouusKSaveijkmnost'))
    translate_table.update(special)
    return s.translate(translate_table)


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
