import notch
import os
import signal
import sys
import rainwave_library.app

log = notch.make_log("rainwave-library-entrypoint")


def handle_sigterm(_signal, _frame):
    sys.exit()


port = int(os.getenv("PORT", 8080))

signal.signal(signal.SIGTERM, handle_sigterm)
rainwave_library.app.main(port=port)
