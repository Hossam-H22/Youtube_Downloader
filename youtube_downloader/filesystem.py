"""Filesystem and OS-level side effects (creating files, opening/clearing the console)."""

import os
import subprocess
import sys


def ensure_dir(path: str) -> None:
    """Create ``path`` (and parents) if it does not already exist."""
    os.makedirs(path, exist_ok=True)


def create_text_file(lines: list[str], path: str) -> None:
    """Write ``lines`` to ``Link.txt`` inside ``path`` (creating the folder)."""
    ensure_dir(path)  # Ensure the directory exists
    file_path = os.path.join(path, 'Link.txt')  # Define the file path

    # Write the description to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        for line in lines:
            file.write(line)


def clear_console() -> None:
    """Clear the terminal, cross-platform."""
    # Clear command for Windows
    if os.name == 'nt':
        os.system('cls')
    # Clear command for Unix/Linux/Mac
    else:
        os.system('clear')


def open_folder(path: str) -> None:
    """Open ``path`` in the system file explorer, cross-platform."""
    try:
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', path])
        else:
            subprocess.run(['xdg-open', path])
    except Exception as e:
        print(f"Could not open folder: {e}")
