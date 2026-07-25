import httpx

_API_ROOT = "https://discord.com/api/v10"


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
