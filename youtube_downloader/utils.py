"""Pure, dependency-free helper functions shared across the package."""

import re

from pysrt import SubRipTime


def clean_filename(filename: str) -> str:
    """Strip characters that are illegal in file names on common file systems."""
    pattern = r'[<>:"/\\|?*\x00-\x1F]'
    return re.sub(pattern, '', filename)


def format_video_length(seconds: int) -> str:
    """Render a duration in seconds as a human-readable string.

    Example: ``3661`` -> ``"1 hours and 1 minutes and 1 seconds"``.
    """
    hours = seconds // 3600  # Calculate the number of hours
    minutes = (seconds % 3600) // 60  # Calculate the remaining minutes
    remaining_seconds = seconds % 60  # Calculate the remaining seconds
    msg = ""
    if hours > 0:
        msg += f"{hours} hours"
    if minutes > 0:
        if hours > 0:
            msg += f" and "
        msg += f"{minutes} minutes"
    if remaining_seconds > 0:
        if hours > 0 or minutes > 0:
            msg += f" and "
        msg += f"{remaining_seconds} seconds"
    return msg


def format_counter(counter: int, length: int) -> str:
    """Zero-pad ``counter`` to the width of ``length`` and append ``". "``.

    Example: ``format_counter(2, 100)`` -> ``"002. "``.
    """
    total_digit_len = len(str(abs(length)))
    digit_len = len(str(abs(counter)))
    return f"{'0' * (total_digit_len - digit_len)}{counter}. "


def seconds_to_srt_time(seconds: float) -> SubRipTime:
    """Convert a number of seconds into a :class:`SubRipTime` position."""
    return SubRipTime.from_ordinal(int(seconds * 1000))
