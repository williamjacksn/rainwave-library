from .activity import (
    suggestion_activity_block,
    suggestion_comment_button,
    suggestion_comment_form,
)
from .content import (
    suggestion_description_block,
    suggestion_description_form,
    suggestion_link_button,
    suggestion_link_form,
    suggestion_links_block,
)
from .detail import suggestion_detail_row, suggestion_link_fields, suggestion_page
from .file_controls import (
    suggestion_music_review_controls,
    suggestion_normalize_filenames_form,
)
from .files import (
    suggestion_file_player,
    suggestion_files_card,
    suggestion_image_preview_modal,
)
from .forms import (
    staff_suggestion_create_form,
    staff_suggestion_requester_discord_id_field,
    suggestion_create_form,
)
from .index import (
    suggestion_default_filters_saved,
    suggestions_index,
    suggestions_rows,
)
from .release import (
    suggestion_schedule_release_duration,
    suggestion_schedule_release_form,
    suggestion_schedule_release_target,
)
from .summary import (
    suggestion_accept_form,
    suggestion_decline_form,
    suggestion_edit_requester_discord_id_field,
    suggestion_row,
)
from .wizard import suggestion_wizard_body

__all__ = (
    "staff_suggestion_create_form",
    "staff_suggestion_requester_discord_id_field",
    "suggestion_accept_form",
    "suggestion_activity_block",
    "suggestion_comment_button",
    "suggestion_comment_form",
    "suggestion_create_form",
    "suggestion_decline_form",
    "suggestion_default_filters_saved",
    "suggestion_description_block",
    "suggestion_description_form",
    "suggestion_detail_row",
    "suggestion_edit_requester_discord_id_field",
    "suggestion_file_player",
    "suggestion_files_card",
    "suggestion_image_preview_modal",
    "suggestion_link_button",
    "suggestion_link_fields",
    "suggestion_link_form",
    "suggestion_links_block",
    "suggestion_music_review_controls",
    "suggestion_normalize_filenames_form",
    "suggestion_page",
    "suggestion_row",
    "suggestion_schedule_release_duration",
    "suggestion_schedule_release_form",
    "suggestion_schedule_release_target",
    "suggestion_wizard_body",
    "suggestions_index",
    "suggestions_rows",
)
