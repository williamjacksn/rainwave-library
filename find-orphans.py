import pathlib

import rainwave_library.app
import rainwave_library.models

cnx = rainwave_library.app.app.config["RAINWAVE_DATABASE"]
library_root = pathlib.Path(rainwave_library.app.app.config["LIBRARY_ROOT"])

known_filenames = rainwave_library.models.rainwave.get_song_filenames(cnx)
print(f"{len(known_filenames)} known filenames")

for f in rainwave_library.models.mp3.yield_all(library_root):
    sf = str(f)
    if (
        sf in known_filenames
        or sf.startswith(str(library_root / "xmas"))
        or sf.startswith(str(library_root / "podcast"))
        or sf.startswith(str(library_root / "~autoremoved"))
        or sf.startswith(str(library_root / "removed"))
        or sf.startswith(str(library_root / "~upcoming"))
        or sf.startswith(str(library_root / "metalgear"))
        or sf.startswith(str(library_root / "V-Wave Theme"))
        or sf.startswith(str(library_root / "staging"))
        or sf.startswith(str(library_root / "~misc"))
        or sf.startswith(str(library_root / "silence"))
    ):
        continue
    print(str(f))
