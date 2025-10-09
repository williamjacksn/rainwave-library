# https://docs.bsky.app/docs/get-started

import dataclasses
import datetime
import logging
import os

import httpx
import notch

log = logging.getLogger(__name__)


@dataclasses.dataclass
class BlueskyClient:
    handle: str
    password: str
    pds_host: str = "https://bsky.social"

    _access_token: str = dataclasses.field(default=None, init=False, repr=False)

    @property
    def access_token(self) -> str:
        if self._access_token is None:
            session = self.create_session()
            self._access_token = session.get("accessJwt")
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


def get_client_from_env() -> BlueskyClient:
    return BlueskyClient(os.getenv("BSKY_HANDLE"), os.getenv("BSKY_PASSWORD"))


def main() -> None:
    notch.make_log("bsky")
    b = get_client_from_env()
    print(b.post("Test post"))


if __name__ == "__main__":
    main()
