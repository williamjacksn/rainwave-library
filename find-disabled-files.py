import pathlib

import rainwave_library.app
import rainwave_library.models

cnx = rainwave_library.app.app.config["RAINWAVE_DATABASE"]
library_root = rainwave_library.app.app.config["LIBRARY_ROOT"]

known_filenames = rainwave_library.models.rainwave.get_song_filenames(cnx)
print(f"{len(known_filenames)} known filenames")

for f in rainwave_library.models.mp3.yield_all(pathlib.Path(library_root)):
    sf = str(f)
    if sf in known_filenames and not known_filenames.get(sf):
        print(str(f))
