import httpx

_API_ROOT = "https://discord.com/api/v10"


def send_message(bot_token: str, channel_id: str, content: str) -> dict:
    response = httpx.post(
        f"{_API_ROOT}/channels/{channel_id}/messages",
        headers={"Authorization": f"Bot {bot_token}"},
        json={"content": content},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
