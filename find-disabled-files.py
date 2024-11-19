import pathlib
import rainwave_library.models

# RW_CNX=postgres://user:pass@server/db python find-disabled.py

cnx = rainwave_library.models.rainwave.cnx

known_filenames = rainwave_library.models.rainwave.get_song_filenames(cnx)
print(f"{len(known_filenames)} known filenames")

for f in rainwave_library.models.mp3.yield_all(pathlib.Path("/icecast")):
    sf = str(f)
    if sf in known_filenames and not known_filenames.get(sf):
        print(str(f))
