import pathlib
import rainwave_library.models

# RW_CNX=postgres://user:pass@server/db python find-orphans.py

cnx = rainwave_library.models.rainwave.cnx

known_filenames = rainwave_library.models.rainwave.get_song_filenames(cnx)
print(f"{len(known_filenames)} known filenames")

for f in rainwave_library.models.mp3.yield_all(pathlib.Path("/icecast")):
    sf = str(f)
    if (
        sf in known_filenames
        or sf.startswith("/icecast/xmas")
        or sf.startswith("/icecast/podcast")
        or sf.startswith("/icecast/~autoremoved")
        or sf.startswith("/icecast/removed")
        or sf.startswith("/icecast/~upcoming")
        or sf.startswith("/icecast/metalgear")
        or sf.startswith("/icecast/V-Wave Theme")
        or sf.startswith("/icecast/staging")
        or sf.startswith("/icecast/~misc")
        or sf.startswith("/icecast/silence")
    ):
        continue
    print(str(f))
