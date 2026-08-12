import htpy


def _suggestion_safe_for_work_guidelines() -> htpy.Element:
    return htpy.div[
        htpy.h5["Safe-for-work guidelines"],
        htpy.p[
            "Rainwave is strictly safe-for-work. Songs must not contain NSFW "
            "lyrics, although titles may be masked with stars. Any associated "
            "game must also meet all of these criteria:"
        ],
        htpy.ul[
            htpy.li[
                "You can explain the game to an office co-worker who does not "
                "play video games."
            ],
            htpy.li[
                "You can discuss the game with an office co-worker who knows "
                "what the game is."
            ],
            htpy.li[
                "You can read the game's Wikipedia page or perform a Google "
                "Images search without encountering any red-flag words or images."
            ],
        ],
    ]


def _suggestion_game_rules() -> htpy.Element:
    return htpy.div[
        htpy.p["The Game channel plays video game OSTs from the 16-bit era onward."],
        htpy.h5["Submission requirements"],
        htpy.ul[
            htpy.li["The music must be from a video game."],
            htpy.li[
                "A new album must contain at least four tracks eligible for "
                "the Game channel."
            ],
            htpy.li[
                'Tracks must have distinct names (not "Track 01," "Track 02," '
                'etc.) and an identifiable artist (not "Unknown Artist").'
            ],
            htpy.li[
                "Provide an MP3 download link for the album using Dropbox, "
                "MediaFire, or any other reliable service. Whenever possible, "
                "include the entire album rather than only your favorite tracks."
            ],
            htpy.li[
                "Provide a condensed list of your favorite tracks. This saves "
                "review time and makes those tracks more likely to get on the air."
            ],
        ],
        htpy.h5["Quality guidelines"],
        htpy.ul[
            htpy.li[
                "Tracks should be recognizable and up-tempo, generally between "
                "1 and 5 minutes long, with little to no silence. Generic "
                "orchestral or movie-like soundtracks generally do not fit "
                "the channel."
            ],
            htpy.li[
                "The channel has an easy-listening format, so rap, hip-hop, "
                "hardcore techno, and similar styles generally do not fit."
            ],
            htpy.li["Lyrical tracks are not accepted, with few exceptions."],
            htpy.li[
                "Chip-based music from the NES, Game Boy, Game Boy Color, and "
                "older systems generally belongs on the Chiptune channel."
            ],
        ],
        _suggestion_safe_for_work_guidelines(),
    ]


def _suggestion_oc_remix_rules() -> htpy.Element:
    return htpy.div[
        htpy.div(".alert.alert-info", role="alert")[
            "Rainwave automatically adds every remix and album published on ",
            htpy.a(href="https://ocremix.org/")["OC ReMix"],
            ". You do not need to suggest new OC ReMix music or ask for it to "
            "be added to an existing album.",
        ],
        htpy.h5["When to make a suggestion"],
        htpy.ul[
            htpy.li[
                htpy.strong["Correct a metadata problem: "],
                "Use a Metadata update suggestion when a title, artist, album, "
                "source game, arrangement credit, or other library information "
                "is missing or incorrect.",
            ],
            htpy.li[
                htpy.strong["Report a Content ID restriction: "],
                "If an OC ReMix track becomes subject to Content ID restrictions, "
                "use a Metadata update suggestion to request that it be moved "
                "to the Covers channel.",
            ],
        ],
        htpy.p[
            "Keeping the OC ReMix channel free of Content ID restrictions makes "
            "it suitable for background music in Twitch streams and other "
            "broadcasts."
        ],
        htpy.h5["What to include"],
        htpy.ul[
            htpy.li[
                "Provide a direct link to the remix or album on ocremix.org and, "
                "when available, the corresponding Rainwave library page."
            ],
            htpy.li[
                "For metadata corrections, identify the current value, the "
                "correct value, and a reliable source for the correction."
            ],
            htpy.li[
                "For Content ID reports, identify the affected track, the "
                "claiming party, the platform where the restriction occurred, "
                "and any available evidence of the claim."
            ],
        ],
        htpy.p[
            "Music that has not been published on ocremix.org should not be "
            "suggested for the OC ReMix channel. Suggest eligible remixes and "
            "arrangements for the Covers channel instead."
        ],
    ]


def _suggestion_covers_rules() -> htpy.Element:
    return htpy.div[
        htpy.p[
            "The Covers channel plays video game OST covers, remixes not found "
            "on OC ReMix, official arrangements, and video-game-inspired music."
        ],
        htpy.p[
            "Think of it as OC ReMix radio with additional remixes and original "
            "music submitted directly by independent artists. You'll hear "
            "familiar artists alongside groups from around the world, covering "
            "a variety of genres while maintaining a consistent overall sound."
        ],
        htpy.h5["Submission requirements"],
        htpy.ul[
            htpy.li["The music must come from an independent source."],
            htpy.li["Provide a link to the artist's main page or the project page."],
            htpy.li[
                "The page must provide a way to contact the artist. We must be "
                "able to obtain permission before adding the music unless the "
                "site already grants it, such as through a Creative Commons license."
            ],
            htpy.li[
                "If the artist releases only singles, create a best-of "
                "collection, upload it, and provide a download link. If the "
                "artist releases albums, identify the albums you most want added."
            ],
            htpy.li[
                "Suggest one artist at a time. A single suggestion may include "
                "multiple albums, but they must all be by the same artist."
            ],
            htpy.li[
                'Tracks must have distinct names (not "Track 01," "Track 02," etc.).'
            ],
        ],
        htpy.h5["Quality guidelines"],
        htpy.ul[
            htpy.li[
                "The music must be high quality. With the exception of chiptune "
                "remixes, it should sound like something that could be featured "
                "on OC ReMix."
            ],
            htpy.li[
                "Any style is welcome if the music meets the quality standard "
                "and fits the channel's overall sound."
            ],
        ],
        _suggestion_safe_for_work_guidelines(),
    ]


def _suggestion_chiptune_rules() -> htpy.Element:
    return htpy.div[
        htpy.p[
            "The Chiptune channel plays both chiptune video game soundtracks "
            "and modern chiptunes. Modern chiptunes are created entirely with "
            "8-bit sound elements."
        ],
        htpy.h5["Submission requirements"],
        htpy.ul[
            htpy.li["Provide artist and platform information."],
            htpy.li[
                "Provide an MP3 download link for the album using Dropbox, "
                "MediaFire, or any other reliable service. Suggestions with "
                "download links can usually be reviewed much faster."
            ],
            htpy.li[
                "Optionally, provide a list of the tracks you think should go "
                "on the air. Most chiptune albums are short, so this is not "
                "strictly necessary, but it can help ensure that your favorite "
                "tracks make the cut."
            ],
        ],
        htpy.h5["Video game soundtrack guidelines"],
        htpy.ul[
            htpy.li["The music must be from a video game."],
            htpy.li["The music must be chip-based or too lo-fi for the Game channel."],
            htpy.li[
                'Tracks must have distinct English-language titles (not "Track '
                '01," "死なばもろとも," etc.), except in cases of artistic license.'
            ],
            htpy.li["Tracks should be interesting, recognizable in-game music."],
            htpy.li[
                "Tracks should generally be between 1 and 5 minutes long. "
                "There is limited flexibility for exceptional tracks."
            ],
            htpy.li[
                "Eligible soundtracks often come from the following systems, "
                "although exceptions exist:",
                htpy.ul[
                    htpy.li["Nintendo Entertainment System / Famicom"],
                    htpy.li["Game Boy / Game Boy Color"],
                    htpy.li["Sega Master System"],
                    htpy.li["Commodore 64"],
                    htpy.li["Amiga"],
                    htpy.li["MSX"],
                    htpy.li["Virtual Boy"],
                    htpy.li["PC (modern chiptunes)"],
                    htpy.li[
                        "Game Boy Advance (when a suggestion for the Game "
                        "channel is rejected as too lo-fi)"
                    ],
                    htpy.li[
                        "Super Nintendo Entertainment System (when a suggestion "
                        "for the Game channel is rejected as too lo-fi)"
                    ],
                    htpy.li[
                        "Sega Genesis / Mega Drive (when a suggestion for the "
                        "Game channel is rejected as too lo-fi)"
                    ],
                ],
            ],
        ],
        htpy.h5["Original chiptune and arrangement guidelines"],
        htpy.ul[
            htpy.li[
                "The music must be either an original composition or an "
                "arrangement of existing music."
            ],
            htpy.li[
                "The music must be chiptune and should sound as though it was "
                "produced entirely with one of the systems listed above. "
                "Otherwise, it probably belongs on the Covers channel."
            ],
            htpy.li["Tracks should be interesting, upbeat, and high quality."],
            htpy.li[
                "Tracks should generally be between 1 and 5 minutes long. "
                "There is limited flexibility for exceptional tracks."
            ],
            htpy.li[
                "We must be able to obtain the artist's permission before "
                "adding the music. We'll handle the permission request, but "
                "providing contact information will speed up the process."
            ],
        ],
        _suggestion_safe_for_work_guidelines(),
    ]


def _suggestion_chill_rules() -> htpy.Element:
    return htpy.div[
        htpy.p[
            "The Chill channel plays relaxed, low-intensity video game music, "
            "covers, and remixes. It is intended for background listening, "
            "studying, relaxing, and winding down."
        ],
        htpy.h5["Submission requirements"],
        htpy.ul[
            htpy.li[
                "Identify the source game, album, and artist. For covers and "
                "remixes, also identify the source track."
            ],
            htpy.li[
                'Tracks must have distinct names (not "Track 01," "Track 02," '
                'etc.) and an identifiable artist (not "Unknown Artist").'
            ],
            htpy.li[
                "Provide an MP3 download link for the album using Dropbox, "
                "MediaFire, or any other reliable service. Whenever possible, "
                "include the entire album rather than only the suggested tracks."
            ],
            htpy.li[
                "Provide a focused list of the tracks that best fit the Chill "
                "channel. An album does not need to be uniformly chill, and "
                "tracks that do not fit should be left off the list."
            ],
            htpy.li[
                "For independently released covers and remixes, provide an "
                "artist or project page with contact information. We must be "
                "able to obtain permission before adding the music unless the "
                "site already grants it, such as through a Creative Commons license."
            ],
        ],
        htpy.h5["Quality guidelines"],
        htpy.ul[
            htpy.li[
                "The music must be connected to video games: a video game "
                "soundtrack or a cover or remix of game music."
            ],
            htpy.li[
                "Tracks should maintain a calm, comfortable mood. Ambient, "
                "acoustic, orchestral, jazz, electronic, and lo-fi styles can "
                "all fit when their overall energy remains restrained."
            ],
            htpy.li[
                "Avoid tracks dominated by intense combat energy, aggressive "
                "percussion, abrasive sounds, sudden volume changes, or other "
                "elements that disrupt relaxed listening."
            ],
            htpy.li[
                "Tracks should work as standalone music and should not contain "
                "excessive silence, long non-musical passages, or abrupt endings."
            ],
            htpy.li[
                "Instrumental tracks are preferred. Vocals may be accepted when "
                "they are subdued, complement the music, and do not distract "
                "from the channel's relaxed flow."
            ],
            htpy.li[
                "Audio must be clean and high quality, without clipping, "
                "obvious recording artifacts, or inconsistent mastering."
            ],
        ],
        _suggestion_safe_for_work_guidelines(),
    ]
