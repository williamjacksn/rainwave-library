import httpx

_API_ROOT = "https://discord.com/api/v10"


def exchange_authorization_code(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict:
    response = httpx.post(
        f"{_API_ROOT}/oauth2/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_current_user_guild_member(access_token: str, guild_id: str) -> dict:
    response = httpx.get(
        f"{_API_ROOT}/users/@me/guilds/{guild_id}/member",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_guild_member(bot_token: str, guild_id: str, user_id: str) -> dict:
    response = httpx.get(
        f"{_API_ROOT}/guilds/{guild_id}/members/{user_id}",
        headers={"Authorization": f"Bot {bot_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def send_message(
    bot_token: str,
    channel_id: str,
    content: str,
    *,
    mentioned_user_ids: tuple[str, ...] = (),
) -> dict:
    response = httpx.post(
        f"{_API_ROOT}/channels/{channel_id}/messages",
        headers={"Authorization": f"Bot {bot_token}"},
        json={
            "content": content,
            "allowed_mentions": {
                "parse": [],
                "users": list(mentioned_user_ids),
            },
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
