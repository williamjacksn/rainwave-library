# https://docs.bsky.app/docs/get-started

import dataclasses
import datetime
import logging

import httpx
import notch

log = logging.getLogger(__name__)


@dataclasses.dataclass
class BlueskyClient:
    handle: str
    password: str
    pds_host: str = "https://bsky.social"

    _access_token: str = dataclasses.field(default="", init=False, repr=False)

    @property
    def access_token(self) -> str:
        if self._access_token == "":
            session: dict[str, str] = self.create_session()
            self._access_token = session["accessJwt"]
        return self._access_token

    def create_record(self, record: dict) -> dict:
        url = f"{self.pds_host}/xrpc/com.atproto.repo.createRecord"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        response = httpx.post(url, headers=headers, json=record)
        return response.json()

    def create_session(self) -> dict:
        url = f"{self.pds_host}/xrpc/com.atproto.server.createSession"
        j = {
            "identifier": self.handle,
            "password": self.password,
        }
        response = httpx.post(url, json=j)
        return response.json()

    def post(self, text: str) -> dict:
        record = {
            "collection": "app.bsky.feed.post",
            "record": {
                "createdAt": datetime.datetime.now(tz=datetime.UTC).isoformat(),
                "text": text,
            },
            "repo": self.handle,
        }
        return self.create_record(record)


def get_client(handle: str, password: str) -> BlueskyClient:
    return BlueskyClient(handle, password)


def main() -> None:
    import rainwave_library.app
    import rainwave_library.models.storage

    notch.make_log("bsky")
    storage_cnx = rainwave_library.models.storage.connection_get(
        rainwave_library.app.app.config["STORAGE_CNX"]
    )
    try:
        handle = (
            rainwave_library.models.storage.setting_get(
                storage_cnx,
                "bluesky/handle",
            )
            or ""
        )
        password = (
            rainwave_library.models.storage.setting_get(
                storage_cnx,
                "bluesky/password",
            )
            or ""
        )
    finally:
        storage_cnx.close()
    b = get_client(handle, password)
    print(b.post("Test post"))


if __name__ == "__main__":
    main()
