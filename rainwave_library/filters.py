def length_display(length: int):
    """Convert number of seconds to mm:ss format"""
    minutes, seconds = divmod(length, 60)
    return f"{minutes}:{seconds:02d}"
