"""Flask-based web GUI for the YouTube Downloader.

A second front-end (alongside the console ``ConsoleApp``) that reuses the same
services and the shared :class:`~youtube_downloader.workflows.DownloadWorkflows`.
Launched by ``main.py`` when no ``--console-view`` flag is passed.
"""
