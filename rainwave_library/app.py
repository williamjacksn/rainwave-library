import datetime
import functools
import io
import itertools
import json
import os
import pathlib
import secrets
import string
import textwrap
import time
import typing
import urllib.parse

import flask
import httpx
import mutagen.id3
import waitress
import werkzeug.middleware.proxy_fix
import xlsxwriter

import rainwave_library.components
import rainwave_library.models

app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(  # ty:ignore[invalid-assignment]
    app.wsgi_app, x_for=1, x_proto=1, x_port=1
)

_IDENTITY_SESSION_KEYS = (
    "discord_id",
    "discord_username",
    "discord_display_name",
    "discord_avatar_url",
    "role",
)

storage_dir = pathlib.Path(os.getenv("STATE_DIRECTORY") or ".local")
app.config["STORAGE_CNX"] = os.getenv(
    "STORAGE_CNX", str(storage_dir / "rainwave-library.db")
)

rainwave_library.models.storage.connection_init(app.config["STORAGE_CNX"])
storage_cnx = rainwave_library.models.storage.connection_get(app.config["STORAGE_CNX"])
try:
    rainwave_library.models.storage.migrate(storage_cnx)
    app.secret_key = rainwave_library.models.storage.setting_get(
        storage_cnx, "app/secret-key"
    )
    app.config["PREFERRED_URL_SCHEME"] = (
        rainwave_library.models.storage.setting_get(storage_cnx, "app/url-scheme")
        or "https"
    )
    app.config["DISCORD_GUILD_ID"] = rainwave_library.models.storage.setting_get(
        storage_cnx, "discord/guild-id"
    )
    app.config["DISCORD_STAFF_ROLE_ID"] = rainwave_library.models.storage.setting_get(
        storage_cnx, "discord/staff-role-id"
    )
    app.config["LIBRARY_ROOT"] = pathlib.Path(
        rainwave_library.models.storage.setting_get(storage_cnx, "library/root")
        or "/icecast"
    )
    app.config["OPENID_CLIENT_ID"] = rainwave_library.models.storage.setting_get(
        storage_cnx, "openid/client-id"
    )
    app.config["OPENID_CLIENT_SECRET"] = rainwave_library.models.storage.setting_get(
        storage_cnx, "openid/client-secret"
    )
    rainwave_connection = rainwave_library.models.storage.setting_get(
        storage_cnx, "rainwave/connection"
    )
finally:
    storage_cnx.close()

app.config["RAINWAVE_DATABASE"] = rainwave_library.models.rainwave.connection_get(
    rainwave_connection or ""
)


def external_url_for(endpoint: str, *args, **kwargs) -> str:  # noqa: ANN002, ANN003
    return flask.url_for(
        endpoint,
        _scheme=app.config["PREFERRED_URL_SCHEME"],
        _external=True,
        *args,
        **kwargs,
    )


def _suggestion_discord_message_send(
    suggestion_id: str,
    content: str,
    mentioned_user_ids: tuple[str, ...] = (),
) -> None:
    try:
        storage_cnx = rainwave_library.models.storage.connection_get(
            app.config["STORAGE_CNX"]
        )
        try:
            bot_token = rainwave_library.models.storage.setting_get(
                storage_cnx, "discord/bot-token"
            )
            discord_channel_id = rainwave_library.models.storage.setting_get(
                storage_cnx, "discord/music-suggestion-channel-id"
            )
        finally:
            storage_cnx.close()

        if not bot_token or not discord_channel_id:
            app.logger.warning(
                "Could not announce suggestion %s because the Discord settings "
                "are incomplete",
                suggestion_id,
            )
            return

        rainwave_library.models.discord.send_message(
            bot_token,
            discord_channel_id,
            content,
            mentioned_user_ids=mentioned_user_ids,
        )
    except Exception:
        app.logger.exception(
            "Could not send a Discord message for suggestion %s",
            suggestion_id,
        )


def _suggestion_created_announce(
    suggestion_id: str,
    *,
    title: str,
    channel_id: int,
    kind: str,
    requester_name: str | None,
    requester_discord_id: str | None,
) -> None:
    channel_name = rainwave_library.models.rainwave.channels.get(channel_id, "Unknown")
    kind_name = rainwave_library.models.suggestions.Suggestion.kind_labels.get(
        kind, kind
    )
    suggested_by = (
        f"<@{requester_discord_id}>"
        if requester_discord_id
        else requester_name or "Unknown"
    )
    suggestions_url = external_url_for("suggestions")
    content = "\n".join(
        (
            "**New music suggestion**",
            f"**Title:** {title.strip()}",
            f"**Channel:** {channel_name}",
            f"**Type:** {kind_name}",
            f"**Suggested by:** {suggested_by}",
            f"-# [See all suggestions]({suggestions_url})",
        )
    )
    _suggestion_discord_message_send(
        suggestion_id,
        content,
        (requester_discord_id,) if requester_discord_id else (),
    )


def _suggestion_comment_announce(
    suggestion: rainwave_library.models.suggestions.SuggestionDetail,
    *,
    commenter_name: str | None,
    commenter_discord_id: str | None,
    body: str,
) -> None:
    if not suggestion.requester_discord_id:
        app.logger.warning(
            "Could not announce a comment on suggestion %s because the requester "
            "does not have a Discord ID",
            suggestion.id,
        )
        return

    commenter = (
        f"<@{commenter_discord_id}>"
        if commenter_discord_id
        else commenter_name or "Unknown commenter"
    )
    channel_name = _suggestion_channel_name(suggestion)
    content = "\n".join(
        (
            f"<@{suggestion.requester_discord_id}> there is a new comment on your "
            f"suggestion **{suggestion.title}** for the {channel_name} channel.",
            f"{commenter} said: {body.strip()}",
        )
    )
    mentioned_user_ids = tuple(
        dict.fromkeys(
            (
                suggestion.requester_discord_id,
                *([commenter_discord_id] if commenter_discord_id else []),
            )
        )
    )
    _suggestion_discord_message_send(
        suggestion.id,
        content,
        mentioned_user_ids,
    )


def _suggestion_claim_announce(
    suggestion: rainwave_library.models.suggestions.SuggestionDetail,
) -> None:
    if not suggestion.requester_discord_id or not suggestion.claimed_by_discord_id:
        app.logger.warning(
            "Could not announce the claim on suggestion %s because a Discord ID "
            "is missing",
            suggestion.id,
        )
        return

    content = (
        f"<@{suggestion.requester_discord_id}> your suggestion "
        f"**{suggestion.title}** was claimed by "
        f"<@{suggestion.claimed_by_discord_id}>."
    )
    mentioned_user_ids = (suggestion.requester_discord_id,)
    if suggestion.claimed_by_discord_id != suggestion.requester_discord_id:
        mentioned_user_ids += (suggestion.claimed_by_discord_id,)
    _suggestion_discord_message_send(
        suggestion.id,
        content,
        mentioned_user_ids,
    )


def _suggestion_channel_name(
    suggestion: rainwave_library.models.suggestions.SuggestionDetail,
) -> str:
    channel_id = suggestion.primary_channel_id
    if channel_id is None and suggestion.channel_ids:
        channel_id = suggestion.channel_ids[0]
    return rainwave_library.models.rainwave.channels.get(channel_id, "Unknown")


def _suggestion_accepted_announce(
    suggestion: rainwave_library.models.suggestions.SuggestionDetail,
) -> None:
    channel_name = _suggestion_channel_name(suggestion)
    if suggestion.requester_discord_id:
        content = (
            f"<@{suggestion.requester_discord_id}> your suggestion "
            f"**{suggestion.title}** for the {channel_name} channel was accepted."
        )
        mentioned_user_ids = (suggestion.requester_discord_id,)
    else:
        content = (
            f"The suggestion **{suggestion.title}** for the {channel_name} channel "
            "was accepted."
        )
        mentioned_user_ids = ()

    if suggestion.kind in {"new-album", "add-to-existing-album"}:
        content += " New music will be added to Rainwave in a future update."

    _suggestion_discord_message_send(
        suggestion.id,
        content,
        mentioned_user_ids,
    )


def _suggestion_declined_announce(
    suggestion: rainwave_library.models.suggestions.SuggestionDetail,
) -> None:
    channel_name = _suggestion_channel_name(suggestion)
    if suggestion.requester_discord_id:
        content = (
            f"<@{suggestion.requester_discord_id}> your suggestion "
            f"**{suggestion.title}** for the {channel_name} channel was declined."
        )
        mentioned_user_ids = (suggestion.requester_discord_id,)
    else:
        content = (
            f"The suggestion **{suggestion.title}** for the {channel_name} channel "
            "was declined."
        )
        mentioned_user_ids = ()

    _suggestion_discord_message_send(
        suggestion.id,
        content,
        mentioned_user_ids,
    )


def signed_in(f: typing.Callable) -> typing.Callable:
    @functools.wraps(f)
    def decorated_function(*args, **kwargs) -> werkzeug.Response:  # noqa: ANN002, ANN003
        if "role" not in flask.session:
            return flask.redirect(flask.url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def secure(f: typing.Callable) -> typing.Callable:
    @functools.wraps(f)
    def decorated_function(*args, **kwargs) -> werkzeug.Response:  # noqa: ANN002, ANN003
        if "role" not in flask.session or flask.session.get("role") == "member":
            return flask.redirect(flask.url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def before_request() -> None:
    app.logger.debug(f"{flask.request.method} {flask.request.path}")
    for k, v in flask.request.values.lists():
        app.logger.debug(f"{k}: {v}")
    flask.session.permanent = True
    flask.g.discord_id = flask.session.get("discord_id")
    flask.g.discord_username = flask.session.get("discord_username")
    flask.g.discord_display_name = flask.session.get("discord_display_name")
    flask.g.discord_avatar_url = flask.session.get("discord_avatar_url")


@app.route("/", methods=["GET"])
def index() -> werkzeug.Response | str:
    if "role" not in flask.session:
        return rainwave_library.components.sign_in()
    return rainwave_library.components.welcome(flask.session.get("role", "member"))


@app.route("/upcoming", methods=["GET"])
@secure
def upcoming_music() -> str:
    try:
        directory = rainwave_library.models.storage.upcoming_music_directory_get(
            app.config["LIBRARY_ROOT"],
            flask.request.args.get("path", ""),
        )
    except ValueError:
        flask.abort(404)
    return rainwave_library.components.upcoming_music(directory)


@app.route("/upcoming/file", methods=["GET"])
@secure
def upcoming_music_file() -> flask.Response:
    try:
        path = rainwave_library.models.storage.upcoming_music_file_get(
            app.config["LIBRARY_ROOT"],
            flask.request.args.get("path", ""),
        )
    except ValueError:
        flask.abort(404)
    response = flask.send_file(
        path,
        as_attachment=True,
        conditional=True,
        download_name=path.name,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/upcoming/folder", methods=["POST"])
@secure
def upcoming_music_folder_delete() -> werkzeug.Response:
    try:
        parent_path = rainwave_library.models.storage.upcoming_music_directory_delete(
            app.config["LIBRARY_ROOT"],
            flask.request.form.get("path", ""),
        )
    except ValueError as error:
        flask.abort(409, str(error))
    redirect_url = flask.url_for(
        "upcoming_music",
        **({"path": parent_path} if parent_path else {}),
    )
    if flask.request.headers.get("HX-Request") == "true":
        response = flask.make_response()
        response.headers["HX-Redirect"] = redirect_url
        return response
    return flask.redirect(redirect_url)


@app.route("/albums", methods=["GET"])
@secure
def albums() -> str:
    return rainwave_library.components.albums_index()


@app.route("/albums/<int:album_id>", methods=["GET"])
@secure
def albums_detail(album_id: int) -> str:
    db = app.config["RAINWAVE_DATABASE"]
    album = rainwave_library.models.rainwave.get_album(db, album_id)
    songs_ = rainwave_library.models.rainwave.get_album_songs(db, album_id)
    return rainwave_library.components.albums_detail(album, songs_)


@app.route("/albums/missing-art", methods=["GET"])
@secure
def albums_missing_art() -> str:
    db = app.config["RAINWAVE_DATABASE"]
    albums_ = rainwave_library.models.rainwave.get_albums_missing_art(db)
    return rainwave_library.components.albums_missing_art(albums_)


@app.route("/albums/rows", methods=["POST"])
@secure
def albums_rows() -> str:
    db = app.config["RAINWAVE_DATABASE"]
    q = flask.request.values.get("q")
    page = int(flask.request.values.get("page", 1))
    sort_col = flask.request.values.get("sort-col", "album_id")
    sort_dir = flask.request.values.get("sort-dir", "asc")
    albums_ = rainwave_library.models.rainwave.get_albums(
        db, q, page, sort_col, sort_dir
    )
    return rainwave_library.components.albums_rows(albums_, page)


@app.route("/artists", methods=["GET"])
@secure
def artists() -> str:
    return rainwave_library.components.artists_index()


@app.route("/artists/<int:artist_id>", methods=["GET", "POST"])
@secure
def artists_detail(artist_id: int) -> werkzeug.Response | str:
    db = app.config["RAINWAVE_DATABASE"]
    artist = rainwave_library.models.rainwave.get_artist(db, artist_id)
    if artist is None:
        flask.abort(404)
    songs_ = rainwave_library.models.rainwave.get_artist_songs(db, artist_id)
    rename_result = None
    if flask.request.method == "POST":
        new_name = flask.request.values.get("artist-name", "").strip()
        if not new_name:
            rename_result = ("alert-danger", "Artist name is required.")
        elif new_name == artist.name:
            rename_result = ("alert-info", "The artist name is unchanged.")
        else:
            errors = rainwave_library.models.mp3.rename_artist(
                [song.filename for song in songs_], artist.name, new_name
            )
            if errors:
                rename_result = (
                    "alert-danger",
                    f"Processed {len(songs_)} song files, but {len(errors)} failed. "
                    "See the application log for details.",
                )
            else:
                renamed_artist = rainwave_library.models.rainwave.get_artist_by_name(
                    db, new_name
                )
                if renamed_artist is None:
                    time.sleep(1)
                    renamed_artist = (
                        rainwave_library.models.rainwave.get_artist_by_name(
                            db, new_name
                        )
                    )
                if renamed_artist is not None:
                    return flask.redirect(
                        flask.url_for("artists_detail", artist_id=renamed_artist.id)
                    )
                rename_result = (
                    "alert-warning",
                    f"Processed {len(songs_)} song files, but Rainwave has not yet "
                    f"created the artist {new_name!r}. Try reloading this page.",
                )
    return rainwave_library.components.artists_detail(
        artist, songs_, rename_result=rename_result
    )


@app.route("/artists/rows", methods=["POST"])
@secure
def artists_rows() -> str:
    db = app.config["RAINWAVE_DATABASE"]
    q = flask.request.values.get("q")
    page = int(flask.request.values.get("page", 1))
    sort_col = flask.request.values.get("sort-col", "artist_id")
    sort_dir = flask.request.values.get("sort-dir", "asc")
    artists_ = rainwave_library.models.rainwave.get_artists(
        db, q, page, sort_col, sort_dir
    )
    return rainwave_library.components.artists_rows(artists_, page)


@app.route("/api/elections")
def api_elections() -> flask.Response:
    db = app.config["RAINWAVE_DATABASE"]
    sid = int(flask.request.values.get("sid", 1))
    day = datetime.date.fromisoformat(flask.request.values.get("day", "2024-01-01"))
    return flask.jsonify(
        {
            "sid": sid,
            "day": day.isoformat(),
            "sched_history": [
                {
                    "id": e.get("elec_id"),
                    "start_actual": e.get("elec_start_actual"),
                    "songs": e.get("songs"),
                }
                for e in rainwave_library.models.rainwave.get_elections(db, sid, day)
            ],
        }
    )


@app.route("/assume-member", methods=["GET"])
@secure
def assume_member() -> werkzeug.Response:
    return flask.redirect(flask.url_for("impersonate_user"))


@app.route("/impersonate", methods=["GET", "POST"])
@secure
def impersonate_user() -> werkzeug.Response | str:
    if flask.session.get("impersonator"):
        flask.abort(409, "Stop impersonating the current user before starting again.")
    if flask.request.method == "GET":
        return rainwave_library.components.impersonate_user()

    discord_user_id = flask.request.form.get("discord-user-id", "").strip()
    if not discord_user_id.isdigit() or not 0 < int(discord_user_id) < 2**64:
        return rainwave_library.components.impersonate_user(
            discord_user_id=discord_user_id,
            error="Enter a valid Discord user ID.",
        )

    storage_cnx_ = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        stored_user = rainwave_library.models.storage.user_get(
            storage_cnx_,
            discord_user_id,
        )
        use_stored_user = bool(
            stored_user
            and stored_user.username
            and stored_user.display_name
            and stored_user.role in {"member", "staff"}
        )
        bot_token = (
            None
            if use_stored_user
            else rainwave_library.models.storage.setting_get(
                storage_cnx_,
                "discord/bot-token",
            )
        )
        guild_id = (
            None
            if use_stored_user
            else rainwave_library.models.storage.setting_get(
                storage_cnx_,
                "discord/guild-id",
            )
        )
        staff_role_id = (
            None
            if use_stored_user
            else rainwave_library.models.storage.setting_get(
                storage_cnx_,
                "discord/staff-role-id",
            )
        )
    finally:
        storage_cnx_.close()

    if use_stored_user and stored_user is not None:
        username = stored_user.username
        display_name = stored_user.display_name
        avatar_url = stored_user.avatar_url
        role = stored_user.role
    else:
        if not bot_token or not guild_id:
            return rainwave_library.components.impersonate_user(
                discord_user_id=discord_user_id,
                error="Discord impersonation is not configured.",
            )
        try:
            member = rainwave_library.models.discord.get_guild_member(
                bot_token,
                guild_id,
                discord_user_id,
            )
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                try:
                    user = rainwave_library.models.discord.get_user(
                        bot_token,
                        discord_user_id,
                    )
                except httpx.HTTPStatusError as user_error:
                    if user_error.response.status_code == 404:
                        message = "That Discord user could not be found."
                    else:
                        app.logger.exception(
                            "Could not look up Discord user %s",
                            discord_user_id,
                        )
                        message = "Discord could not look up that user."
                    return rainwave_library.components.impersonate_user(
                        discord_user_id=discord_user_id,
                        error=message,
                    )
                except (httpx.HTTPError, ValueError):
                    app.logger.exception(
                        "Could not look up Discord user %s",
                        discord_user_id,
                    )
                    return rainwave_library.components.impersonate_user(
                        discord_user_id=discord_user_id,
                        error="Discord could not look up that user.",
                    )
                member = {"user": user, "roles": []}
            else:
                app.logger.exception(
                    "Could not look up Discord guild member %s",
                    discord_user_id,
                )
                return rainwave_library.components.impersonate_user(
                    discord_user_id=discord_user_id,
                    error="Discord could not look up that guild member.",
                )
        except (httpx.HTTPError, ValueError):
            app.logger.exception(
                "Could not look up Discord guild member %s",
                discord_user_id,
            )
            return rainwave_library.components.impersonate_user(
                discord_user_id=discord_user_id,
                error="Discord could not look up that guild member.",
            )

        user = member.get("user")
        roles = member.get("roles")
        if (
            not isinstance(user, dict)
            or str(user.get("id") or "") != discord_user_id
            or not isinstance(roles, list)
        ):
            app.logger.error(
                "Discord returned incomplete user data for user %s",
                discord_user_id,
            )
            return rainwave_library.components.impersonate_user(
                discord_user_id=discord_user_id,
                error="Discord returned incomplete user information.",
            )

        username_value = user.get("username")
        username = (
            username_value
            if isinstance(username_value, str) and username_value
            else None
        )
        display_name = next(
            (
                value
                for value in (
                    member.get("nick"),
                    user.get("global_name"),
                    username,
                )
                if isinstance(value, str) and value
            ),
            None,
        )
        if username is None or display_name is None:
            app.logger.error(
                "Discord returned incomplete user data for user %s",
                discord_user_id,
            )
            return rainwave_library.components.impersonate_user(
                discord_user_id=discord_user_id,
                error="Discord returned incomplete user information.",
            )
        guild_avatar = member.get("avatar")
        user_avatar = user.get("avatar")
        if isinstance(guild_avatar, str) and guild_avatar:
            avatar_url = (
                f"https://cdn.discordapp.com/guilds/{guild_id}/users/"
                f"{discord_user_id}/avatars/{guild_avatar}.png"
            )
        elif isinstance(user_avatar, str) and user_avatar:
            avatar_url = (
                f"https://cdn.discordapp.com/avatars/{discord_user_id}/"
                f"{user_avatar}.png"
            )
        else:
            avatar_url = None
        role = "staff" if staff_role_id in roles else "member"
        storage_cnx_ = rainwave_library.models.storage.connection_get(
            app.config["STORAGE_CNX"]
        )
        try:
            rainwave_library.models.storage.user_upsert(
                storage_cnx_,
                discord_user_id,
                username=username,
                display_name=display_name,
                avatar_url=avatar_url,
                role=role,
            )
        finally:
            storage_cnx_.close()

    impersonator = {key: flask.session.get(key) for key in _IDENTITY_SESSION_KEYS}
    flask.session["impersonator"] = impersonator
    flask.session.update(
        {
            "discord_id": discord_user_id,
            "discord_username": username,
            "discord_display_name": display_name,
            "discord_avatar_url": avatar_url,
            "role": role,
        }
    )
    app.logger.info(
        "Staff Discord user %s is impersonating Discord user %s",
        impersonator["discord_id"],
        discord_user_id,
    )
    return flask.redirect(flask.url_for("index"))


@app.route("/impersonate/stop", methods=["POST"])
@signed_in
def impersonate_stop() -> werkzeug.Response:
    impersonator = flask.session.get("impersonator")
    if not isinstance(impersonator, dict) or impersonator.get("role") != "staff":
        flask.abort(403)

    impersonated_discord_id = flask.session.get("discord_id")
    flask.session.pop("impersonator", None)
    for key in _IDENTITY_SESSION_KEYS:
        value = impersonator.get(key)
        if value is None:
            flask.session.pop(key, None)
        else:
            flask.session[key] = value
    app.logger.info(
        "Staff Discord user %s stopped impersonating Discord user %s",
        flask.session.get("discord_id"),
        impersonated_discord_id,
    )
    return flask.redirect(flask.url_for("index"))


@app.route("/authorize", methods=["GET"])
def authorize() -> werkzeug.Response:
    if flask.session.get("state") != flask.request.values.get("state"):
        return flask.Response("State mismatch", 401)
    flask.session.pop("impersonator", None)
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        client_id = (
            rainwave_library.models.storage.setting_get(
                storage_cnx,
                "openid/client-id",
            )
            or ""
        )
        client_secret = (
            rainwave_library.models.storage.setting_get(
                storage_cnx,
                "openid/client-secret",
            )
            or ""
        )
        guild_id = (
            rainwave_library.models.storage.setting_get(
                storage_cnx,
                "discord/guild-id",
            )
            or ""
        )
        staff_role = (
            rainwave_library.models.storage.setting_get(
                storage_cnx,
                "discord/staff-role-id",
            )
            or ""
        )
    finally:
        storage_cnx.close()
    resp = rainwave_library.models.discord.exchange_authorization_code(
        client_id,
        client_secret,
        flask.request.values.get("code", ""),
        external_url_for("authorize"),
    )
    access_token = resp.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        return flask.redirect(flask.url_for("index"))
    resp = rainwave_library.models.discord.get_current_user_guild_member(
        access_token,
        guild_id,
    )
    user_roles = resp.get("roles")
    if not isinstance(user_roles, list):
        return flask.redirect(flask.url_for("index"))
    user = resp.get("user")
    if not isinstance(user, dict):
        return flask.redirect(flask.url_for("index"))
    user_id = user.get("id")
    if not isinstance(user_id, str) or not user_id:
        return flask.redirect(flask.url_for("index"))
    username_value = user.get("username")
    username = username_value if isinstance(username_value, str) else None
    display_name = next(
        (
            value
            for value in (resp.get("nick"), user.get("global_name"), username)
            if isinstance(value, str) and value
        ),
        None,
    )
    guild_avatar = resp.get("avatar")
    user_avatar = user.get("avatar")
    if isinstance(guild_avatar, str) and guild_avatar:
        avatar_url = f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/{guild_avatar}.png"
    elif isinstance(user_avatar, str) and user_avatar:
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.png"
    else:
        avatar_url = None
    app.logger.debug(f"Sign in attempt from {username} with roles {user_roles}")
    app.logger.debug(f"Staff role is {staff_role}")
    if staff_role in user_roles:
        app.logger.debug(f"{username} is staff")
        role = "staff"
    else:
        app.logger.debug(f"{username} is member")
        role = "member"
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        rainwave_library.models.storage.user_upsert(
            storage_cnx,
            user_id,
            username=username,
            display_name=display_name,
            avatar_url=avatar_url,
            role=role,
        )
    finally:
        storage_cnx.close()
    flask.session.update(
        {
            "discord_id": user_id,
            "discord_username": username,
            "discord_display_name": display_name,
            "discord_avatar_url": avatar_url,
            "role": role,
        }
    )
    return flask.redirect(flask.url_for("index"))


@app.route("/bluesky", methods=["GET", "POST"])
@secure
def bluesky() -> werkzeug.Response | str:
    if flask.request.method == "GET":
        return rainwave_library.components.bluesky_post()
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
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
    b = rainwave_library.models.bsky.get_client(handle, password)
    b.post(flask.request.values["body"])
    return flask.redirect(flask.url_for("index"))


@app.route("/favicon.svg")
def favicon() -> flask.Response:
    return flask.Response(
        rainwave_library.components.favicon(), mimetype="image/svg+xml"
    )


@app.route("/get-ocremix", methods=["GET"])
@secure
def get_ocremix() -> str:
    db = app.config["RAINWAVE_DATABASE"]
    max_ocr_num = rainwave_library.models.rainwave.get_max_ocr_num(db)
    return rainwave_library.components.get_ocremix_start(max_ocr_num)


@app.route("/get-ocremix/download", methods=["POST"])
@secure
def get_ocremix_download() -> str:
    r = httpx.get(flask.request.values["download-from"])
    mp3_data = io.BytesIO(r.content)
    tags = mutagen.id3.ID3(mp3_data)
    tags.delall("TALB")
    tags.add(mutagen.id3.TALB(encoding=3, text=[flask.request.values.get("album")]))
    tags.delall("TIT2")
    tags.add(mutagen.id3.TIT2(encoding=3, text=[flask.request.values.get("title")]))
    tags.delall("TPE1")
    tags.add(mutagen.id3.TPE1(encoding=3, text=[flask.request.values.get("artist")]))
    tags.delall("WXXX")
    tags.add(mutagen.id3.WXXX(encoding=0, url=flask.request.values.get("url")))
    tags.delall("COMM")
    tags.add(mutagen.id3.COMM(encoding=3, text=[flask.request.values.get("link-text")]))
    tags.delall("TCON")
    tags.add(
        mutagen.id3.TCON(encoding=3, text=[flask.request.values.get("categories")])
    )
    for tag in [
        "APIC",
        "TCMP",
        "TCOM",
        "TCOP",
        "TDRC",
        "TENC",
        "TIT1",
        "TIT3",
        "TOAL",
        "TOPE",
        "TPE2",
        "TPUB",
        "TRCK",
        "TSSE",
        "TXXX",
        "USLT",
        "WOAR",
    ]:
        tags.delall(tag)
    tags.save(mp3_data)
    target_file = pathlib.Path(get_ocremix_target_file())
    target_file.parent.mkdir(parents=True, exist_ok=True)
    app.logger.debug(f"Saving file to {target_file}")
    target_file.write_bytes(mp3_data.getvalue())
    return rainwave_library.components.get_ocremix_download()


@app.route("/get-ocremix/fetch", methods=["POST"])
@secure
def get_ocremix_fetch() -> flask.Response | str:
    db = app.config["RAINWAVE_DATABASE"]
    ocr_id = int(flask.request.values["ocr-id"])
    url = f"https://williamjacksn.github.io/ocremix-data/remix/OCR{ocr_id:05}.json"
    try:
        ocr_info = httpx.get(url).json()
        app.logger.debug(ocr_info)
    except json.decoder.JSONDecodeError:
        return flask.make_response("", 204)
    album_name = ocr_info.get("primary_game")
    default_category = rainwave_library.models.rainwave.get_category_for_album(
        db, album_name
    )
    if default_category:
        categories = [default_category]
    else:
        categories = [album_name]
    if ocr_info.get("has_lyrics"):
        categories.append("Vocal")
    return rainwave_library.components.get_ocremix_fetch(ocr_info, categories)


@app.route("/get-ocremix/target-file", methods=["POST"])
@secure
def get_ocremix_target_file() -> str:
    album = rainwave_library.models.mp3.make_safe(flask.request.values["album"])
    album_bad_chars = set(album) - (set(string.ascii_letters) | set(string.digits))
    if album_bad_chars:
        bad_char = min(album_bad_chars)
        return f"Unsupported character in album: {bad_char!r} [{ord(bad_char)}]"
    title = rainwave_library.models.mp3.make_safe(flask.request.values["title"])
    title_bad_chars = set(title) - (set(string.ascii_letters) | set(string.digits))
    if title_bad_chars:
        bad_char = min(title_bad_chars)
        return f"Unsupported character in title: {bad_char!r} [{ord(bad_char)}]"
    first_letter = album[0].lower()
    if first_letter not in string.ascii_lowercase:
        first_letter = "0"
    library_root = app.config["LIBRARY_ROOT"]
    return str(library_root / "ocr-all" / first_letter / album / f"{title}.mp3")


@app.route("/listeners", methods=["GET"])
@secure
def listeners() -> str:
    db = app.config["RAINWAVE_DATABASE"]
    ranks = rainwave_library.models.rainwave.get_ranks(db)
    return rainwave_library.components.listeners_index(ranks)


@app.route("/listeners/<int:listener_id>", methods=["GET"])
@secure
def listeners_detail(listener_id: int) -> str:
    db = app.config["RAINWAVE_DATABASE"]
    listener = rainwave_library.models.rainwave.get_listener(db, listener_id)
    return rainwave_library.components.listeners_detail(listener)


@app.route("/listeners/<int:listener_id>/edit", methods=["GET", "POST"])
@secure
def listeners_edit(listener_id: int) -> werkzeug.Response | str:
    db = app.config["RAINWAVE_DATABASE"]
    listener = rainwave_library.models.rainwave.get_listener(db, listener_id)
    if flask.request.method == "GET":
        return rainwave_library.components.listeners_edit(listener)

    discord_user_id = flask.request.values.get("discord_user_id")
    if not discord_user_id:
        discord_user_id = None
    rainwave_library.models.rainwave.set_discord_user_id(
        db, listener_id, discord_user_id
    )
    return flask.redirect(flask.url_for("listeners_detail", listener_id=listener_id))


@app.route("/listeners/rows", methods=["POST"])
@secure
def listeners_rows() -> str:
    db = app.config["RAINWAVE_DATABASE"]
    q = flask.request.values.get("q")
    page = int(flask.request.values.get("page", 1))
    ranks = list(map(int, flask.request.values.getlist("ranks")))
    sort_col = flask.request.values.get("sort-col", "user_id")
    sort_dir = flask.request.values.get("sort-dir", "asc")
    listeners_ = rainwave_library.models.rainwave.get_listeners(
        db, q, page, ranks, sort_col, sort_dir
    )
    return rainwave_library.components.listeners_rows(listeners_, page)


@app.route("/nothing", methods=["GET"])
@secure
def nothing() -> str:
    return ""


@app.route("/settings", methods=["GET", "POST"])
@secure
def settings() -> str:
    key = ""
    value = ""
    protected = False
    result: tuple[str, str] | None = None
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        if flask.request.method == "POST":
            key = flask.request.form.get("key", "")
            value = flask.request.form.get("value", "")
            protected = "protected" in flask.request.form
            try:
                created = rainwave_library.models.storage.setting_set(
                    storage_cnx,
                    key,
                    value,
                    protected=protected,
                )
            except ValueError as error:
                result = ("alert-danger", str(error))
            else:
                result = (
                    "alert-success",
                    f"Setting {'created' if created else 'replaced'}.",
                )
                key = ""
                value = ""
                protected = False
        settings_ = rainwave_library.models.storage.settings_get(storage_cnx)
    finally:
        storage_cnx.close()
    return rainwave_library.components.settings_index(
        settings_,
        key=key,
        value=value,
        protected=protected,
        result=result,
    )


@app.route("/suggestions", methods=["GET"])
@signed_in
def suggestions() -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        your_suggestions_active_count, your_suggestions_complete_count = (
            rainwave_library.models.suggestions.suggestion_counts_by_requester(
                storage_cnx,
                str(flask.g.discord_id) if flask.g.discord_id else None,
            )
        )
        claimants = rainwave_library.models.suggestions.suggestion_claimants_get(
            storage_cnx
        )
    finally:
        storage_cnx.close()
    return rainwave_library.components.suggestions_index(
        is_staff=flask.session.get("role") == "staff",
        claimants=claimants,
        your_suggestions_active_count=your_suggestions_active_count,
        your_suggestions_complete_count=your_suggestions_complete_count,
        **_suggestion_notice(),
    )


class _SuggestionNotice(typing.TypedDict):
    song_count: int
    song_count_as_of: str


def _suggestion_notice() -> _SuggestionNotice:
    db = app.config["RAINWAVE_DATABASE"]
    count = rainwave_library.models.rainwave.song_count(db)
    return {
        "song_count": count // 1000 * 1000,
        "song_count_as_of": datetime.date.today().strftime("%B %Y"),
    }


@app.route("/suggestions/wizard", methods=["POST"])
@signed_in
def suggestion_wizard() -> str:
    limits_apply = flask.session.get("role") != "staff"
    step = flask.request.form.get("step", "1")
    channel = flask.request.form.get("channel", "")
    channel_id = (
        int(channel) if channel.isdigit() and int(channel) in {1, 2, 3, 4, 6} else None
    )
    kind = flask.request.form.get("kind", "")
    if kind not in rainwave_library.models.suggestions.Suggestion.kinds:
        kind = None
    title = flask.request.form.get("title", "")
    description = flask.request.form.get("description", "")
    link_pairs = tuple(
        (url.strip(), label.strip())
        for url, label in itertools.zip_longest(
            flask.request.form.getlist("link-url"),
            flask.request.form.getlist("link-label"),
            fillvalue="",
        )
    )
    links = tuple(pair for pair in link_pairs if pair[0] or pair[1])
    links_complete = all(url and label for url, label in link_pairs)
    if step in {"2", "3", "4", "5"}:
        if channel_id is None or kind is None:
            return rainwave_library.components.suggestion_wizard_body(
                1,
                channel_id=channel_id,
                kind=kind,
                result=("alert-danger", "Choose a channel and a suggestion type."),
                title=title,
                description=description,
                links=links,
                **_suggestion_notice(),
            )
        storage_cnx = rainwave_library.models.storage.connection_get(
            app.config["STORAGE_CNX"]
        )
        title_matches: tuple[str, ...] = ()
        try:
            open_count = (
                rainwave_library.models.suggestions.suggestion_open_count_for_channel(
                    storage_cnx,
                    str(flask.g.discord_id) if flask.g.discord_id else None,
                    channel_id,
                )
            )
            if step in {"4", "5"} and kind == "new-album" and title.strip():
                title_matches = (
                    rainwave_library.models.suggestions.suggestion_title_match_statuses(
                        storage_cnx,
                        title,
                    )
                )
        finally:
            storage_cnx.close()
        if limits_apply and open_count > 5:
            return rainwave_library.components.suggestion_wizard_body(
                2,
                channel_id=channel_id,
                kind=kind,
                open_count=open_count,
                limits_apply=limits_apply,
                title=title,
                description=description,
                links=links,
            )
        if step in {"4", "5"} and not title.strip():
            return rainwave_library.components.suggestion_wizard_body(
                3,
                channel_id=channel_id,
                kind=kind,
                title=title,
                description=description,
                links=links,
                result=("alert-danger", "Enter a suggestion title."),
            )
        if (
            step in {"4", "5"}
            and kind == "new-album"
            and rainwave_library.models.rainwave.album_name_exists(
                app.config["RAINWAVE_DATABASE"], title, channel_id
            )
        ):
            title_matches = (*title_matches, "album")
        if step == "5":
            if not description.strip():
                return rainwave_library.components.suggestion_wizard_body(
                    4,
                    channel_id=channel_id,
                    kind=kind,
                    title=title,
                    description=description,
                    links=links,
                    title_matches=title_matches,
                    result=("alert-danger", "Enter suggestion details."),
                )
            if not links_complete:
                return rainwave_library.components.suggestion_wizard_body(
                    4,
                    channel_id=channel_id,
                    kind=kind,
                    title=title,
                    description=description,
                    links=links,
                    title_matches=title_matches,
                    result=(
                        "alert-danger",
                        "Every added link requires both a URL and a label.",
                    ),
                )
            return rainwave_library.components.suggestion_wizard_body(
                5,
                channel_id=channel_id,
                kind=kind,
                title=title,
                description=description,
                links=links,
            )
        if step == "4":
            return rainwave_library.components.suggestion_wizard_body(
                4,
                channel_id=channel_id,
                kind=kind,
                title=title,
                description=description,
                links=links,
                title_matches=title_matches,
            )
        if step == "3":
            return rainwave_library.components.suggestion_wizard_body(
                3,
                channel_id=channel_id,
                kind=kind,
                title=title,
                description=description,
                links=links,
            )
        return rainwave_library.components.suggestion_wizard_body(
            2,
            channel_id=channel_id,
            kind=kind,
            open_count=open_count,
            limits_apply=limits_apply,
            title=title,
            description=description,
            links=links,
        )
    return rainwave_library.components.suggestion_wizard_body(
        1,
        channel_id=channel_id,
        kind=kind,
        title=title,
        description=description,
        links=links,
        **_suggestion_notice(),
    )


@app.route("/suggestions/create", methods=["POST"])
@signed_in
def suggestion_create() -> werkzeug.Response | str:
    title = flask.request.form.get("title", "")
    description = flask.request.form.get("description", "")
    kind = flask.request.form.get(
        "kind", rainwave_library.models.suggestions.Suggestion.default_kind
    )
    channel = flask.request.form.get("channel", "")
    channel_id = int(channel) if channel.isdigit() else 0
    link_pairs = [
        (url.strip(), label.strip())
        for url, label in itertools.zip_longest(
            flask.request.form.getlist("link-url"),
            flask.request.form.getlist("link-label"),
            fillvalue="",
        )
    ]
    entered_links = tuple(pair for pair in link_pairs if pair[0] or pair[1])
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        try:
            suggestion_id = rainwave_library.models.suggestions.suggestion_create(
                storage_cnx,
                title=title,
                description=description,
                channel_id=channel_id,
                kind=kind,
                requester_name=flask.g.discord_display_name,
                requester_discord_id=(
                    str(flask.g.discord_id) if flask.g.discord_id else None
                ),
                links=entered_links,
            )
        except ValueError as error:
            return rainwave_library.components.suggestion_create_form(
                title=title,
                description=description,
                channel_id=channel_id or None,
                links=entered_links,
                result=("alert-danger", str(error)),
            )
    finally:
        storage_cnx.close()

    _suggestion_created_announce(
        suggestion_id,
        title=title,
        channel_id=channel_id,
        kind=kind,
        requester_name=flask.g.discord_display_name,
        requester_discord_id=(str(flask.g.discord_id) if flask.g.discord_id else None),
    )

    redirect_url = flask.url_for("suggestions")
    if flask.request.headers.get("HX-Request") == "true":
        response = flask.make_response()
        response.headers["HX-Redirect"] = redirect_url
        return response
    return flask.redirect(redirect_url)


@app.route("/suggestions/staff-create", methods=["POST"])
@secure
def suggestion_staff_create() -> werkzeug.Response | str:
    title = flask.request.form.get("title", "")
    description = flask.request.form.get("description", "")
    kind = flask.request.form.get(
        "kind", rainwave_library.models.suggestions.Suggestion.default_kind
    )
    channel = flask.request.form.get("channel", "")
    channel_id = int(channel) if channel.isdigit() else 0
    requester_name_input = flask.request.form.get("requester-name", "").strip()
    requester_discord_id_input = flask.request.form.get(
        "requester-discord-id", ""
    ).strip()
    requester_name = requester_name_input or None
    requester_discord_id = requester_discord_id_input or None
    if not requester_name_input and not requester_discord_id_input:
        requester_name = flask.g.discord_display_name
        requester_discord_id = str(flask.g.discord_id) if flask.g.discord_id else None
    link_pairs = tuple(
        (url.strip(), label.strip())
        for url, label in itertools.zip_longest(
            flask.request.form.getlist("link-url"),
            flask.request.form.getlist("link-label"),
            fillvalue="",
        )
    )
    entered_links = tuple(pair for pair in link_pairs if pair[0] or pair[1])

    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        try:
            suggestion_id = rainwave_library.models.suggestions.suggestion_create(
                storage_cnx,
                title=title,
                description=description,
                channel_id=channel_id,
                kind=kind,
                requester_name=requester_name,
                requester_discord_id=requester_discord_id,
                links=entered_links,
            )
        except ValueError as error:
            return rainwave_library.components.staff_suggestion_create_form(
                title=title,
                description=description,
                channel_id=channel_id or None,
                kind=kind,
                requester_name=requester_name_input,
                requester_discord_id=requester_discord_id_input,
                links=entered_links,
                result=("alert-danger", str(error)),
            )
    finally:
        storage_cnx.close()

    _suggestion_created_announce(
        suggestion_id,
        title=title,
        channel_id=channel_id,
        kind=kind,
        requester_name=requester_name,
        requester_discord_id=requester_discord_id,
    )

    redirect_url = flask.url_for("suggestions")
    if flask.request.headers.get("HX-Request") == "true":
        response = flask.make_response()
        response.headers["HX-Redirect"] = redirect_url
        return response
    return flask.redirect(redirect_url)


@app.route("/suggestions/staff-requester-discord-id", methods=["GET"])
@secure
def suggestion_staff_requester_discord_id() -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        requester_discord_id = (
            rainwave_library.models.suggestions.suggestion_requester_discord_id_get(
                storage_cnx,
                flask.request.args.get("requester-name", ""),
            )
        )
    finally:
        storage_cnx.close()
    if flask.request.args.get("target") == "edit":
        return rainwave_library.components.suggestion_edit_requester_discord_id_field(
            requester_discord_id or ""
        )
    return rainwave_library.components.staff_suggestion_requester_discord_id_field(
        requester_discord_id or ""
    )


@app.route("/suggestions/link-row", methods=["GET"])
@signed_in
def suggestion_link_row() -> str:
    if "close" in flask.request.args:
        return ""
    return rainwave_library.components.suggestion_link_fields(
        required=flask.request.args.get("required") == "1"
    )


@app.route("/suggestions/rows", methods=["POST"])
@signed_in
def suggestions_rows() -> str:
    query = flask.request.values.get("q")
    statuses = flask.request.values.getlist("status")
    page = max(int(flask.request.values.get("page", 1)), 1)
    sort_col = flask.request.values.get("sort-col", "requested_at")
    sort_dir = flask.request.values.get("sort-dir", "desc")
    claimed_by_names = flask.request.values.getlist("claimed-by")
    kinds = flask.request.values.getlist("kinds")
    input_channels = flask.request.values.getlist("channels")
    include_unassigned_channel = "unassigned" in input_channels
    channel_ids = [
        int(channel_id)
        for channel_id in input_channels
        if channel_id.isdigit() and int(channel_id) in {1, 2, 3, 4, 6}
    ]
    is_staff = flask.session.get("role") == "staff"
    requester_discord_id = (
        str(flask.g.discord_id or "")
        if "your-suggestions" in flask.request.values
        else None
    )
    claimed_by_discord_id = (
        str(flask.g.discord_id or "")
        if is_staff and "your-claims" in flask.request.values
        else None
    )
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestions_ = rainwave_library.models.suggestions.suggestions_get(
            storage_cnx,
            query,
            statuses,
            page,
            requester_discord_id,
            claimed_by_discord_id,
            sort_col,
            sort_dir,
            claimed_by_names,
            channel_ids,
            kinds,
            include_unassigned_channel,
        )
    finally:
        storage_cnx.close()
    return rainwave_library.components.suggestions_rows(suggestions_, page)


def _suggestion_staged_files_get(
    suggestion_id: str,
) -> tuple[
    tuple[tuple[str, int], ...],
    pathlib.Path,
    dict[str, rainwave_library.models.mp3.Mp3TagValues],
]:
    library_root = app.config["LIBRARY_ROOT"]
    staged_files = rainwave_library.models.storage.suggestion_staging_files_get(
        library_root,
        suggestion_id,
    )
    folder_path = rainwave_library.models.storage.suggestion_staging_folder_get(
        library_root,
        suggestion_id,
    )
    music_tags = {}
    for path, _ in staged_files:
        if not path.casefold().endswith(".mp3"):
            continue
        try:
            file_path = rainwave_library.models.storage.suggestion_staging_file_get(
                library_root,
                suggestion_id,
                path,
            )
        except (OSError, ValueError):
            music_tags[path] = rainwave_library.models.mp3.Mp3TagValues(
                error="Could not read ID3 tags."
            )
            continue
        music_tags[path] = rainwave_library.models.mp3.id3_tag_values_get(file_path)
    return staged_files, folder_path, music_tags


@app.route("/suggestions/<suggestion_id>", methods=["GET"])
@secure
def suggestion_page(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()
    if suggestion is None:
        flask.abort(404)
    staged_files, folder_path, music_tags = _suggestion_staged_files_get(suggestion_id)
    staged_mp3_duration_seconds = (
        rainwave_library.models.storage.suggestion_staging_mp3_duration_get(
            app.config["LIBRARY_ROOT"],
            suggestion_id,
        )
    )
    staged_genre = rainwave_library.models.mp3.most_common_genre_get(
        music_tags.values()
    )
    return rainwave_library.components.suggestion_page(
        suggestion,
        staged_files,
        folder_path=str(folder_path),
        music_tags=music_tags,
        staged_mp3_duration_seconds=staged_mp3_duration_seconds,
        staged_genre=staged_genre,
    )


@app.route(
    "/suggestions/<suggestion_id>/schedule-release/duration",
    methods=["GET"],
)
@secure
def suggestion_schedule_release_duration(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx,
            suggestion_id,
        )
    finally:
        storage_cnx.close()
    if suggestion is None:
        flask.abort(404)

    release_date = flask.request.args.get("release-date", "")
    staged_duration_seconds = (
        rainwave_library.models.storage.suggestion_staging_mp3_duration_get(
            app.config["LIBRARY_ROOT"],
            suggestion_id,
        )
    )
    upcoming_duration_seconds = None
    if release_date:
        try:
            upcoming_duration_seconds = (
                rainwave_library.models.storage.upcoming_music_date_mp3_duration_get(
                    app.config["LIBRARY_ROOT"],
                    release_date,
                )
            )
        except ValueError:
            pass
    return rainwave_library.components.suggestion_schedule_release_duration(
        staged_duration_seconds,
        release_date=release_date,
        upcoming_duration_seconds=upcoming_duration_seconds,
    )


@app.route(
    "/suggestions/<suggestion_id>/schedule-release/target",
    methods=["GET"],
)
@secure
def suggestion_schedule_release_target(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx,
            suggestion_id,
        )
    finally:
        storage_cnx.close()
    if suggestion is None:
        flask.abort(404)

    release_date = flask.request.args.get("release-date", "")
    if not release_date:
        return rainwave_library.components.suggestion_schedule_release_target(
            suggestion_id
        )

    try:
        target = rainwave_library.models.storage.suggestion_release_target_get(
            app.config["LIBRARY_ROOT"],
            release_date,
            flask.request.args.get("channel-folder", ""),
            flask.request.args.get("folder-name", ""),
            include_genre=flask.request.args.get("include-genre") == "1",
            genre=flask.request.args.get("genre", ""),
        )
    except ValueError as error:
        return rainwave_library.components.suggestion_schedule_release_target(
            suggestion_id,
            message=str(error),
            error=True,
        )
    return rainwave_library.components.suggestion_schedule_release_target(
        suggestion_id,
        target_path=str(target),
    )


@app.route("/suggestions/<suggestion_id>/schedule-release", methods=["POST"])
@secure
def suggestion_schedule_release(suggestion_id: str) -> werkzeug.Response | str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx,
            suggestion_id,
        )
    finally:
        storage_cnx.close()
    if suggestion is None:
        flask.abort(404)

    release_date = flask.request.form.get("release-date", "")
    channel_folder = flask.request.form.get("channel-folder", "")
    folder_name = flask.request.form.get("folder-name", "")
    include_genre = flask.request.form.get("include-genre") == "1"
    genre = flask.request.form.get("genre", "")
    staged_duration_seconds = (
        rainwave_library.models.storage.suggestion_staging_mp3_duration_get(
            app.config["LIBRARY_ROOT"],
            suggestion_id,
        )
    )
    upcoming_duration_seconds = None
    if release_date:
        try:
            upcoming_duration_seconds = (
                rainwave_library.models.storage.upcoming_music_date_mp3_duration_get(
                    app.config["LIBRARY_ROOT"],
                    release_date,
                )
            )
        except ValueError:
            pass
    try:
        destination = rainwave_library.models.storage.suggestion_release_schedule(
            app.config["LIBRARY_ROOT"],
            suggestion_id,
            release_date,
            channel_folder,
            folder_name,
            include_genre=include_genre,
            genre=genre,
        )
    except ValueError as error:
        return rainwave_library.components.suggestion_schedule_release_form(
            suggestion,
            release_date=release_date,
            channel_folder=channel_folder,
            folder_name=folder_name,
            include_genre=include_genre,
            genre=genre,
            staged_duration_seconds=staged_duration_seconds,
            upcoming_duration_seconds=upcoming_duration_seconds,
            error=str(error),
        )
    except OSError:
        app.logger.exception(
            "Could not schedule release for suggestion %s",
            suggestion_id,
        )
        return rainwave_library.components.suggestion_schedule_release_form(
            suggestion,
            release_date=release_date,
            channel_folder=channel_folder,
            folder_name=folder_name,
            include_genre=include_genre,
            genre=genre,
            staged_duration_seconds=staged_duration_seconds,
            upcoming_duration_seconds=upcoming_duration_seconds,
            error="The suggestion files could not be moved.",
        )

    app.logger.info(
        "Scheduled suggestion %s for release at %s",
        suggestion_id,
        destination,
    )
    redirect_url = flask.url_for("upcoming_music", path=destination)
    if flask.request.headers.get("HX-Request") == "true":
        response = flask.make_response()
        response.headers["HX-Redirect"] = redirect_url
        return response
    return flask.redirect(redirect_url)


@app.route("/suggestions/<suggestion_id>/files", methods=["POST"])
@secure
def suggestion_files_upload(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()
    if suggestion is None:
        flask.abort(404)

    uploads = [
        (upload.filename or "", upload.stream)
        for upload in flask.request.files.getlist("files")
    ]
    try:
        uploaded_names = (
            rainwave_library.models.storage.suggestion_staging_files_upload(
                app.config["LIBRARY_ROOT"],
                suggestion_id,
                uploads,
            )
        )
        result = (
            "alert-success",
            f"Uploaded {len(uploaded_names)} "
            f"file{'' if len(uploaded_names) == 1 else 's'}.",
        )
        app.logger.info(
            "Uploaded %d files for suggestion %s",
            len(uploaded_names),
            suggestion_id,
        )
    except ValueError as error:
        result = ("alert-danger", str(error))
    except OSError:
        app.logger.exception("Could not upload files for suggestion %s", suggestion_id)
        result = ("alert-danger", "The files could not be uploaded.")

    staged_files, folder_path, music_tags = _suggestion_staged_files_get(suggestion_id)
    return rainwave_library.components.suggestion_files_card(
        suggestion_id,
        staged_files,
        result,
        folder_path=str(folder_path),
        music_tags=music_tags,
    )


@app.route("/suggestions/<suggestion_id>/files", methods=["DELETE"])
@secure
def suggestion_file_delete(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()
    if suggestion is None:
        flask.abort(404)

    relative_path = flask.request.args.get("path", "")
    try:
        deleted_path = rainwave_library.models.storage.suggestion_staging_file_delete(
            app.config["LIBRARY_ROOT"],
            suggestion_id,
            relative_path,
        )
        result = ("alert-success", f"Deleted {deleted_path}.")
        app.logger.info(
            "Deleted file %s for suggestion %s",
            deleted_path,
            suggestion_id,
        )
    except ValueError as error:
        result = ("alert-danger", str(error))
    except OSError:
        app.logger.exception(
            "Could not delete file %s for suggestion %s",
            relative_path,
            suggestion_id,
        )
        result = ("alert-danger", "The file could not be deleted.")

    staged_files, folder_path, music_tags = _suggestion_staged_files_get(suggestion_id)
    return rainwave_library.components.suggestion_files_card(
        suggestion_id,
        staged_files,
        result,
        folder_path=str(folder_path),
        music_tags=music_tags,
    )


@app.route("/suggestions/<suggestion_id>/files/tags", methods=["POST"])
@secure
def suggestion_file_tags_update(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()
    if suggestion is None:
        flask.abort(404)

    scope = flask.request.form.get("scope")
    if scope == "file":
        relative_path = flask.request.form.get("path", "")
        if not relative_path.casefold().endswith(".mp3"):
            result = ("alert-danger", "Choose an MP3 file.")
        else:
            tag_values = {
                tag_name: flask.request.form.get(tag_name, "")
                for tag_name in rainwave_library.models.mp3.ID3_TAG_LABELS
            }
            try:
                file_path = rainwave_library.models.storage.suggestion_staging_file_get(
                    app.config["LIBRARY_ROOT"],
                    suggestion_id,
                    relative_path,
                )
                rainwave_library.models.mp3.id3_tag_values_set_all(
                    file_path,
                    tag_values,
                )
                result = (
                    "alert-success",
                    f"Updated tags for {relative_path}.",
                )
            except (OSError, ValueError) as error:
                result = ("alert-danger", str(error))
    else:
        tag_name = flask.request.form.get("tag", "")
        value = flask.request.form.get("value", "")
        tag_label = rainwave_library.models.mp3.ID3_TAG_LABELS.get(tag_name)
        if tag_label is None:
            result = ("alert-danger", "Choose a valid ID3 tag.")
        elif scope == "all":
            staged_files = rainwave_library.models.storage.suggestion_staging_files_get(
                app.config["LIBRARY_ROOT"],
                suggestion_id,
            )
            music_paths = [
                path for path, _ in staged_files if path.casefold().endswith(".mp3")
            ]
            updated_count = 0
            failed_count = 0
            for path in music_paths:
                try:
                    file_path = (
                        rainwave_library.models.storage.suggestion_staging_file_get(
                            app.config["LIBRARY_ROOT"],
                            suggestion_id,
                            path,
                        )
                    )
                    rainwave_library.models.mp3.id3_tag_values_set(
                        file_path,
                        tag_name,
                        value,
                    )
                    updated_count += 1
                except (OSError, ValueError):
                    failed_count += 1
                    app.logger.exception(
                        "Could not update %s for suggestion file %s",
                        tag_name,
                        path,
                    )
            if not music_paths:
                result = ("alert-danger", "There are no MP3 files to update.")
            elif failed_count:
                result = (
                    "alert-warning",
                    f"Updated {tag_label} for {updated_count} MP3 "
                    f"file{'' if updated_count == 1 else 's'}; "
                    f"{failed_count} could not be updated.",
                )
            else:
                result = (
                    "alert-success",
                    f"Updated {tag_label} for {updated_count} MP3 "
                    f"file{'' if updated_count == 1 else 's'}.",
                )
        else:
            relative_path = flask.request.form.get("path", "")
            if not relative_path.casefold().endswith(".mp3"):
                result = ("alert-danger", "Choose an MP3 file.")
            else:
                try:
                    file_path = (
                        rainwave_library.models.storage.suggestion_staging_file_get(
                            app.config["LIBRARY_ROOT"],
                            suggestion_id,
                            relative_path,
                        )
                    )
                    rainwave_library.models.mp3.id3_tag_values_set(
                        file_path,
                        tag_name,
                        value,
                    )
                    result = (
                        "alert-success",
                        f"Updated {tag_label} for {relative_path}.",
                    )
                except (OSError, ValueError) as error:
                    result = ("alert-danger", str(error))

    staged_files, folder_path, music_tags = _suggestion_staged_files_get(suggestion_id)
    return rainwave_library.components.suggestion_files_card(
        suggestion_id,
        staged_files,
        result,
        folder_path=str(folder_path),
        music_tags=music_tags,
    )


def _suggestion_staged_file_get(
    suggestion_id: str,
    allowed_extensions: set[str],
) -> tuple[str, pathlib.Path]:
    relative_path = flask.request.args.get("path", "")
    extension = pathlib.PurePosixPath(
        relative_path.replace("\\", "/")
    ).suffix.casefold()
    if extension not in allowed_extensions:
        flask.abort(404)

    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()
    if suggestion is None:
        flask.abort(404)

    try:
        file_path = rainwave_library.models.storage.suggestion_staging_file_get(
            app.config["LIBRARY_ROOT"],
            suggestion_id,
            relative_path,
        )
    except (OSError, ValueError):
        flask.abort(404)
    return relative_path, file_path


@app.route("/suggestions/<suggestion_id>/files/preview", methods=["GET"])
@secure
def suggestion_file_preview(suggestion_id: str) -> flask.Response:
    image_types = {
        ".jpg": "image/jpeg",
        ".png": "image/png",
    }
    relative_path, image_path = _suggestion_staged_file_get(
        suggestion_id,
        set(image_types),
    )
    extension = pathlib.PurePosixPath(
        relative_path.replace("\\", "/")
    ).suffix.casefold()

    response = flask.send_file(
        image_path,
        conditional=True,
        mimetype=image_types[extension],
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/suggestions/<suggestion_id>/files/play", methods=["GET"])
@secure
def suggestion_file_play(suggestion_id: str) -> str:
    relative_path, _ = _suggestion_staged_file_get(suggestion_id, {".mp3"})
    return rainwave_library.components.suggestion_file_player(
        suggestion_id,
        relative_path,
    )


@app.route("/suggestions/<suggestion_id>/files/stream", methods=["GET"])
@secure
def suggestion_file_stream(suggestion_id: str) -> flask.Response:
    _, audio_path = _suggestion_staged_file_get(suggestion_id, {".mp3"})
    response = flask.send_file(
        audio_path,
        conditional=True,
        mimetype="audio/mpeg",
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/suggestions/<suggestion_id>/details", methods=["GET"])
@signed_in
def suggestion_details(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()
    if suggestion is None:
        flask.abort(404)
    return rainwave_library.components.suggestion_detail_row(
        suggestion, editable=flask.session.get("role") == "staff"
    )


@app.route("/suggestions/<suggestion_id>/description", methods=["GET", "POST"])
@signed_in
def suggestion_description(suggestion_id: str) -> str:
    requester_discord_id = str(flask.g.discord_id or "")
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
        if suggestion is None:
            flask.abort(404)
        if (
            not requester_discord_id
            or suggestion.requester_discord_id != requester_discord_id
        ):
            flask.abort(403)
        if suggestion.status not in (
            rainwave_library.models.suggestions.Suggestion.owner_editable_statuses
        ):
            flask.abort(
                409,
                "Only new or claimed suggestions can be edited by their owner.",
            )

        if flask.request.method == "GET":
            if "close" in flask.request.args:
                return rainwave_library.components.suggestion_description_block(
                    suggestion, editable=True
                )
            return rainwave_library.components.suggestion_description_form(suggestion)

        description = flask.request.form.get("description", "")
        try:
            updated = rainwave_library.models.suggestions.suggestion_description_update(
                storage_cnx,
                suggestion_id,
                requester_discord_id=requester_discord_id,
                description=description,
                actor_name=flask.g.discord_display_name,
            )
        except ValueError as error:
            return rainwave_library.components.suggestion_description_form(
                suggestion,
                description=description,
                error=str(error),
            )
        if not updated:
            flask.abort(403)
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()

    if suggestion is None:
        flask.abort(404)
    return rainwave_library.components.suggestion_description_block(
        suggestion, editable=True
    )


@app.route("/suggestions/<suggestion_id>/activity", methods=["GET"])
@signed_in
def suggestion_activity(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()

    if suggestion is None:
        flask.abort(404)
    return rainwave_library.components.suggestion_activity_block(
        suggestion,
        comments_only=flask.request.args.get("comments_only") == "1",
    )


@app.route("/suggestions/<suggestion_id>/comment", methods=["GET", "POST"])
@signed_in
def suggestion_comment(suggestion_id: str) -> werkzeug.Response | str:
    if flask.request.method == "GET":
        if "close" in flask.request.args:
            return rainwave_library.components.suggestion_comment_button(suggestion_id)
        return rainwave_library.components.suggestion_comment_form(suggestion_id)

    body = flask.request.form.get("body", "")
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        try:
            added = rainwave_library.models.suggestions.suggestion_comment_add(
                storage_cnx,
                suggestion_id,
                actor_name=flask.g.discord_display_name,
                actor_discord_id=(
                    str(flask.g.discord_id) if flask.g.discord_id else None
                ),
                body=body,
            )
        except ValueError as error:
            response = flask.make_response(
                rainwave_library.components.suggestion_comment_form(
                    suggestion_id, body=body, error=str(error)
                )
            )
            response.headers["HX-Retarget"] = f"#suggestion-comment-{suggestion_id}"
            response.headers["HX-Reswap"] = "innerHTML"
            return response
        if not added:
            flask.abort(404)
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()

    if suggestion is None:
        flask.abort(404)
    _suggestion_comment_announce(
        suggestion,
        commenter_name=flask.g.discord_display_name,
        commenter_discord_id=(str(flask.g.discord_id) if flask.g.discord_id else None),
        body=body,
    )
    return rainwave_library.components.suggestion_activity_block(suggestion)


@app.route("/suggestions/<suggestion_id>/link", methods=["GET", "POST"])
@signed_in
def suggestion_link(suggestion_id: str) -> werkzeug.Response | str:
    requester_discord_id = str(flask.g.discord_id or "")
    is_staff = flask.session.get("role") == "staff"
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
        if suggestion is None:
            flask.abort(404)
        if not is_staff and (
            not requester_discord_id
            or suggestion.requester_discord_id != requester_discord_id
        ):
            flask.abort(403)
        if not is_staff and suggestion.status not in (
            rainwave_library.models.suggestions.Suggestion.owner_editable_statuses
        ):
            flask.abort(
                409,
                "Links can only be added while a suggestion is new or claimed.",
            )

        if flask.request.method == "GET":
            if "close" in flask.request.args:
                return rainwave_library.components.suggestion_link_button(suggestion_id)
            return rainwave_library.components.suggestion_link_form(suggestion_id)

        url = flask.request.form.get("url", "")
        label = flask.request.form.get("label", "")
        try:
            added = rainwave_library.models.suggestions.suggestion_link_add(
                storage_cnx,
                suggestion_id,
                url=url,
                label=label,
                actor_name=flask.g.discord_display_name,
                actor_discord_id=requester_discord_id,
                is_staff=is_staff,
            )
        except ValueError as error:
            response = flask.make_response(
                rainwave_library.components.suggestion_link_form(
                    suggestion_id, url=url, label=label, error=str(error)
                )
            )
            response.headers["HX-Retarget"] = f"#suggestion-add-link-{suggestion_id}"
            response.headers["HX-Reswap"] = "innerHTML"
            return response
        if not added:
            flask.abort(403)
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()

    if suggestion is None:
        flask.abort(404)
    return rainwave_library.components.suggestion_links_block(suggestion)


@app.route(
    "/suggestions/<suggestion_id>/link/<link_id>",
    methods=["DELETE"],
)
@signed_in
def suggestion_link_delete(suggestion_id: str, link_id: str) -> str:
    actor_discord_id = str(flask.g.discord_id or "")
    is_staff = flask.session.get("role") == "staff"
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
        if suggestion is None:
            flask.abort(404)
        is_owner = bool(actor_discord_id) and (
            suggestion.requester_discord_id == actor_discord_id
        )
        if not is_owner and not is_staff:
            flask.abort(403)
        if not is_staff and suggestion.status not in (
            rainwave_library.models.suggestions.Suggestion.owner_editable_statuses
        ):
            flask.abort(
                409,
                "Links can only be deleted while a suggestion is new or claimed.",
            )
        if not any(link.id == link_id for link in suggestion.links):
            flask.abort(404)

        deleted = rainwave_library.models.suggestions.suggestion_link_delete(
            storage_cnx,
            suggestion_id,
            link_id,
            actor_name=flask.g.discord_display_name,
            actor_discord_id=actor_discord_id,
            is_staff=is_staff,
        )
    finally:
        storage_cnx.close()

    if not deleted:
        flask.abort(404)
    return ""


@app.route("/suggestions/<suggestion_id>/claim", methods=["POST"])
@secure
def suggestion_claim(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        claimed = rainwave_library.models.suggestions.suggestion_claim(
            storage_cnx,
            suggestion_id,
            flask.g.discord_display_name or "",
            str(flask.g.discord_id or ""),
        )
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    except ValueError as error:
        flask.abort(400, str(error))
    finally:
        storage_cnx.close()

    if suggestion is None:
        flask.abort(404)
    if not claimed:
        flask.abort(409, "This suggestion is no longer available to claim.")
    _suggestion_claim_announce(suggestion)
    return rainwave_library.components.suggestion_row(suggestion)


@app.route("/suggestions/<suggestion_id>/release", methods=["POST"])
@signed_in
def suggestion_release(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        released = rainwave_library.models.suggestions.suggestion_release(
            storage_cnx,
            suggestion_id,
            flask.g.discord_display_name or "",
            str(flask.g.discord_id or ""),
        )
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    except ValueError as error:
        flask.abort(400, str(error))
    finally:
        storage_cnx.close()

    if suggestion is None:
        flask.abort(404)
    if not released:
        flask.abort(409, "Only the claimant can release this suggestion claim.")
    return rainwave_library.components.suggestion_row(suggestion)


@app.route("/suggestions/<suggestion_id>", methods=["POST"])
@secure
def suggestion_update(suggestion_id: str) -> str:
    def optional_value(name: str) -> str | None:
        value = flask.request.form.get(name, "").strip()
        return value or None

    result: tuple[str, str]
    accepted = False
    declined = False
    try:
        channel_ids = [
            int(channel_id)
            for channel_id in flask.request.form.getlist("channels")
            if channel_id.isdigit()
        ]
        primary_channel = flask.request.form.get("primary-channel", "")
        primary_channel_id = int(primary_channel) if primary_channel.isdigit() else None
        storage_cnx = rainwave_library.models.storage.connection_get(
            app.config["STORAGE_CNX"]
        )
        try:
            previous_suggestion = rainwave_library.models.suggestions.suggestion_get(
                storage_cnx, suggestion_id
            )
            if previous_suggestion is None:
                flask.abort(404)
            updated = rainwave_library.models.suggestions.suggestion_update(
                storage_cnx,
                suggestion_id,
                title=flask.request.form.get("title", ""),
                kind=flask.request.form.get("kind", ""),
                status=flask.request.form.get("status", ""),
                description=flask.request.form.get("description", ""),
                requester_name=optional_value("requester-name"),
                requester_discord_id=optional_value("requester-discord-id"),
                requested_at=optional_value("requested-at"),
                channel_ids=channel_ids,
                primary_channel_id=primary_channel_id,
                actor_name=flask.g.discord_display_name,
                actor_discord_id=(
                    str(flask.g.discord_id) if flask.g.discord_id else None
                ),
            )
            if not updated:
                flask.abort(404)
            suggestion = rainwave_library.models.suggestions.suggestion_get(
                storage_cnx, suggestion_id
            )
            accepted = (
                suggestion is not None
                and previous_suggestion.status != "accepted"
                and suggestion.status == "accepted"
            )
            declined = (
                suggestion is not None
                and previous_suggestion.status != "declined"
                and suggestion.status == "declined"
            )
        finally:
            storage_cnx.close()
        result = ("alert-success", "Suggestion updated.")
    except ValueError as error:
        result = ("alert-danger", str(error))
        storage_cnx = rainwave_library.models.storage.connection_get(
            app.config["STORAGE_CNX"]
        )
        try:
            suggestion = rainwave_library.models.suggestions.suggestion_get(
                storage_cnx, suggestion_id
            )
        finally:
            storage_cnx.close()

    if suggestion is None:
        flask.abort(404)
    if accepted:
        _suggestion_accepted_announce(suggestion)
    if declined:
        _suggestion_declined_announce(suggestion)
    return rainwave_library.components.suggestion_detail_row(
        suggestion, editable=True, edit_result=result
    )


@app.route("/suggestions/<suggestion_id>", methods=["DELETE"])
@secure
def suggestion_delete(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        deleted = rainwave_library.models.suggestions.suggestion_delete(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()

    if not deleted:
        flask.abort(404)
    return ""


@app.route("/suggestions/<suggestion_id>/row", methods=["GET"])
@signed_in
def suggestion_row(suggestion_id: str) -> str:
    storage_cnx = rainwave_library.models.storage.connection_get(
        app.config["STORAGE_CNX"]
    )
    try:
        suggestion = rainwave_library.models.suggestions.suggestion_get(
            storage_cnx, suggestion_id
        )
    finally:
        storage_cnx.close()
    if suggestion is None:
        flask.abort(404)
    return rainwave_library.components.suggestion_row(suggestion)


@app.route("/sign-in", methods=["GET"])
def sign_in() -> werkzeug.Response:
    state = secrets.token_urlsafe()
    flask.session.update({"state": state})
    redirect_uri = external_url_for("authorize")
    query = {
        "client_id": app.config["OPENID_CLIENT_ID"],
        "prompt": "none",
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "guilds.members.read",
        "state": state,
    }
    auth_endpoint = "https://discord.com/oauth2/authorize"
    auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(query)}"
    return flask.redirect(auth_url, 307)


@app.route("/sign-out", methods=["GET"])
def sign_out() -> werkzeug.Response:
    for key in (*_IDENTITY_SESSION_KEYS, "impersonator"):
        flask.session.pop(key, None)
    return flask.redirect(flask.url_for("index"))


@app.route("/songs", methods=["GET"])
@secure
def songs() -> str:
    return rainwave_library.components.songs_index()


@app.route("/songs/<int:song_id>", methods=["GET"])
@secure
def songs_detail(song_id: int) -> str:
    db = app.config["RAINWAVE_DATABASE"]
    song = rainwave_library.models.rainwave.get_song(db, song_id)
    return rainwave_library.components.songs_detail(song)


@app.route("/songs/<int:song_id>/change-channels/target", methods=["GET"])
@secure
def songs_change_channels_target(song_id: int) -> str:
    db = app.config["RAINWAVE_DATABASE"]
    song = rainwave_library.models.rainwave.get_song(db, song_id)
    try:
        new_filename = rainwave_library.models.rainwave.song_channel_filename_get(
            song.filename,
            app.config["LIBRARY_ROOT"],
            flask.request.args.get("channel-root-folder", ""),
        )
    except ValueError as error:
        return rainwave_library.components.songs_change_channels_target(
            error=str(error)
        )
    return rainwave_library.components.songs_change_channels_target(
        new_filename=str(new_filename)
    )


@app.route("/songs/<int:song_id>/change-channels", methods=["POST"])
@secure
def songs_change_channels(song_id: int) -> werkzeug.Response | str:
    db = app.config["RAINWAVE_DATABASE"]
    song = rainwave_library.models.rainwave.get_song(db, song_id)
    channel_root_folder = flask.request.form.get("channel-root-folder", "")
    new_filename: pathlib.Path | None = None
    try:
        new_filename = rainwave_library.models.rainwave.song_channel_filename_get(
            song.filename,
            app.config["LIBRARY_ROOT"],
            channel_root_folder,
        )
        destination = rainwave_library.models.rainwave.song_channel_change(
            song.filename,
            app.config["LIBRARY_ROOT"],
            channel_root_folder,
        )
    except ValueError as error:
        return rainwave_library.components.songs_change_channels_form(
            song,
            channel_root_folder=channel_root_folder,
            new_filename=str(new_filename) if new_filename is not None else None,
            error=str(error),
        )
    except OSError:
        app.logger.exception("Could not change channels for song %s", song_id)
        return rainwave_library.components.songs_change_channels_form(
            song,
            channel_root_folder=channel_root_folder,
            new_filename=str(new_filename) if new_filename is not None else None,
            error="The song file could not be moved.",
        )

    app.logger.info(
        "Changed channels for song %s by moving it to %s",
        song_id,
        destination,
    )
    # Give the scanner time to update the filename and channel in the database.
    time.sleep(1)
    redirect_url = flask.url_for("songs_detail", song_id=song_id)
    if flask.request.headers.get("HX-Request") == "true":
        response = flask.make_response()
        response.headers["HX-Redirect"] = redirect_url
        return response
    return flask.redirect(redirect_url)


@app.route("/songs/<int:song_id>/download", methods=["GET"])
@secure
def songs_download(song_id: int) -> flask.Response:
    db = app.config["RAINWAVE_DATABASE"]
    song = rainwave_library.models.rainwave.get_song(db, song_id)
    return flask.send_file(song.filename, as_attachment=True)


@app.route("/songs/<int:song_id>/edit", methods=["GET", "POST"])
@secure
def songs_edit(song_id: int) -> str:
    db = app.config["RAINWAVE_DATABASE"]
    song = rainwave_library.models.rainwave.get_song(db, song_id)
    if flask.request.method == "GET":
        return rainwave_library.components.songs_edit(song)

    kwargs = {
        "album": flask.request.values["album"],
        "artist": flask.request.values["artist"],
        "categories": flask.request.values["categories"],
        "link_text": flask.request.values["link-text"],
        "title": flask.request.values["title"],
        "url": flask.request.values["url"],
    }
    result = rainwave_library.models.mp3.set_tags(song.filename, **kwargs)
    if result:
        edit_result = result
        alert_class = "alert-danger"
    else:
        edit_result = "Song tags updated"
        alert_class = "alert-success"
    # give the scanner some time to catch the file changes and update the database
    time.sleep(1)
    return rainwave_library.components.songs_edit_result(alert_class, edit_result)


@app.route("/songs/<int:song_id>/play", methods=["GET"])
@secure
def songs_play(song_id: int) -> str:
    db = app.config["RAINWAVE_DATABASE"]
    song = rainwave_library.models.rainwave.get_song(db, song_id)
    return rainwave_library.components.songs_play(song)


@app.route("/songs/<int:song_id>/remove", methods=["GET", "POST"])
@secure
def songs_remove(song_id: int) -> werkzeug.Response | str:
    db = app.config["RAINWAVE_DATABASE"]
    song = rainwave_library.models.rainwave.get_song(db, song_id)
    song_filename = pathlib.Path(song.filename)
    new_loc = rainwave_library.models.rainwave.calculate_removed_location(
        song_filename,
        app.config["LIBRARY_ROOT"],
    )

    if flask.request.method == "GET":
        return rainwave_library.components.songs_remove(song, str(new_loc))

    reason = flask.request.values.get("reason")
    if new_loc.exists():
        flask.flash(f"Cannot proceed, there is already a file at {new_loc}")
        return flask.redirect(flask.url_for("songs_detail", song_id=song_id))

    new_loc.parent.mkdir(parents=True, exist_ok=True)
    song_filename.rename(new_loc)
    note_text = textwrap.dedent(f"""\
        Song ID: {song_id}
        Original location: {song_filename}
        Removed: {datetime.datetime.now(tz=datetime.UTC)}
        Removed by: {flask.g.discord_username} ({flask.g.discord_id})
        Removal reason: {reason}
        """)
    note_loc = new_loc.with_suffix(".txt")
    note_loc.write_text(note_text)
    return flask.redirect(flask.url_for("index"))


@app.route("/songs/<int:song_id>/stream", methods=["GET"])
@secure
def stream_song(song_id: int) -> flask.Response:
    db = app.config["RAINWAVE_DATABASE"]
    song = rainwave_library.models.rainwave.get_song(db, song_id)
    return flask.send_file(song.filename)


@app.route("/songs/rows", methods=["POST"])
@secure
def songs_rows() -> str:
    db = app.config["RAINWAVE_DATABASE"]
    q = flask.request.values.get("q")
    page = int(flask.request.values.get("page", 1))
    sort_col = flask.request.values.get("sort-col", "song_id")
    sort_dir = flask.request.values.get("sort-dir", "asc")
    input_channels = flask.request.values.getlist("channels")
    valid_channels = [int(c) for c in input_channels if c.isdigit() and 0 < int(c) < 7]
    app.logger.debug(f"{valid_channels=}")
    if not valid_channels:
        valid_channels = None
    include_unrated = "include-unrated" in flask.request.values
    songs_ = rainwave_library.models.rainwave.get_songs(
        db, q, page, sort_col, sort_dir, valid_channels, include_unrated
    )
    return rainwave_library.components.songs_rows(songs_, page)


@app.route("/songs.xlsx", methods=["POST"])
@secure
def songs_xlsx() -> flask.Response:
    db = app.config["RAINWAVE_DATABASE"]
    query = flask.request.values.get("q")
    page = 0
    sort_col = flask.request.values["sort-col"]
    sort_dir = flask.request.values["sort-dir"]
    input_channels = flask.request.values.getlist("channels")
    channels = [
        int(c) for c in input_channels if c.isdigit() and 0 < int(c) < 7
    ] or None
    include_unrated = "include-unrated" in flask.request.values
    data = rainwave_library.models.rainwave.get_songs(
        db, query, page, sort_col, sort_dir, channels, include_unrated
    )
    headers = [
        "song_id",
        "channels",
        "album_name",
        "song_title",
        "song_artist_tag",
        "song_added_on",
        "song_filename",
        "song_groups",
        "song_length",
        "song_rating",
        "song_rating_count",
        "song_url",
        "song_link_text",
    ]
    col_widths = [len(h) for h in headers]
    output = io.BytesIO()
    workbook_options = {
        "default_date_format": "yyyy-mm-dd HH:mm:ss",
        "in_memory": True,
        "remove_timezone": True,
        "strings_to_formulas": False,
    }
    workbook = xlsxwriter.Workbook(output, workbook_options)
    rating_format = workbook.add_format({"num_format": "0.00"})
    worksheet = workbook.add_worksheet()
    for i, row in enumerate(data, start=1):
        for j, col_name in enumerate(headers):
            if col_name == "channels":
                col_data = ", ".join(
                    [rainwave_library.components.channels[c] for c in row.channel_ids]
                )
                col_widths[j] = max(col_widths[j], len(col_data))
                worksheet.write(i, j, col_data)
            elif col_name == "song_groups":
                col_data = ", ".join(row.groups)
                col_widths[j] = max(col_widths[j], len(col_data))
                worksheet.write(i, j, col_data)
            elif col_name == "song_id":
                col_data = str(row.id)
                col_widths[j] = max(10, col_widths[j], len(col_data))
                worksheet.write(i, j, col_data)
            elif col_name == "song_length":
                col_data = rainwave_library.components.length_display(len(row))
                col_widths[j] = max(14, col_widths[j], len(col_data))
                worksheet.write(i, j, col_data)
            elif col_name == "song_rating":
                col_data = row.rating
                col_widths[j] = max(13, col_widths[j], len(str(col_data)))
                worksheet.write(i, j, col_data, rating_format)
            else:
                col_data = row.data.get(col_name)
                col_widths[j] = max(col_widths[j], len(str(col_data)))
                worksheet.write(i, j, col_data)
    for i, width in enumerate(col_widths):
        worksheet.set_column(i, i, width)
    table_options = {"name": "songs", "columns": [{"header": h} for h in headers]}
    worksheet.add_table(0, 0, len(data), len(headers) - 1, table_options)
    workbook.close()
    response = flask.make_response(output.getvalue())
    cd = 'attachment; filename="rainwave-songs.xlsx"'
    ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response.headers.update({"Content-Disposition": cd, "Content-Type": ct})
    return response


def main(port: int) -> None:
    waitress.serve(app, port=port, ident=None)
