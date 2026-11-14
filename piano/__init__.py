"""PianoCapture - turn a YouTube fragment into an 88-key piano view.

A separate, thin app next to AI TabTool in the same repository. It reuses the
proven audio plumbing (yt-dlp download, ffmpeg) from ``app.pipeline`` but keeps
its own data, UI and playback, so TabTool's frozen playback chain is untouched.
"""

__version__ = "0.6.0"
