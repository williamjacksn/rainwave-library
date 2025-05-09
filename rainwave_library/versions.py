import json
import pathlib

package_json = pathlib.Path("package.json").resolve()
with package_json.open() as f:
    data = json.load(f)

bi: str = data.get("dependencies").get("bootstrap-icons")
bs: str = data.get("dependencies").get("bootstrap")
hx: str = data.get("dependencies").get("htmx.org")
