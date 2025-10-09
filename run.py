import os
import signal
import sys
import types

import notch

import rainwave_library.app

notch.configure()


def handle_sigterm(_signal: int, _frame: types.FrameType) -> None:
    sys.exit()


port = int(os.getenv("PORT", 8080))

signal.signal(signal.SIGTERM, handle_sigterm)
rainwave_library.app.main(port=port)
