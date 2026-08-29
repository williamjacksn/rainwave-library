import pathlib

import rainwave_library.app
import rainwave_library.models

cnx = rainwave_library.app.app.config["RAINWAVE_DATABASE"]
library_root = pathlib.Path(rainwave_library.app.app.config["LIBRARY_ROOT"])

known_filenames = rainwave_library.models.rainwave.get_song_filenames(cnx)
print(f"{len(known_filenames)} known filenames")

ignored_prefixes = tuple(
    str(library_root / directory)
    for directory in (
        "xmas",
        "podcast",
        "~autoremoved",
        "removed",
        "~upcoming",
        "metalgear",
        "V-Wave Theme",
        "staging",
        "~misc",
        "silence",
    )
)

for f in rainwave_library.models.mp3.yield_all(library_root):
    sf = str(f)
    if sf in known_filenames or sf.startswith(ignored_prefixes):
        continue
    print(str(f))
