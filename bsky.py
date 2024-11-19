# https://docs.bsky.app/docs/get-started

import dataclasses
import httpx
import logging
import notch
import os

log = logging.getLogger(__name__)


@dataclasses.dataclass
class BlueskyClient:
    handle: str
    password: str
    pds_host: str = "https://bsky.social"

    def create_session(self):
        url = f"{self.pds_host}/xrpc/com.atproto.server.createSession"
        j = {
            "identifier": self.handle,
            "password": self.password,
        }
        response = httpx.post(url, json=j)
        log.info(response.json())


def main():
    notch.make_log("bsky")
    b = BlueskyClient(os.getenv("BSKY_HANDLE"), os.getenv("BSKY_PASSWORD"))
    b.create_session()


if __name__ == "__main__":
    main()
