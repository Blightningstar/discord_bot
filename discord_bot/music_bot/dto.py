from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SongInfoDTO:
    """
    Data Transfer Object representing a song entry in the music queue.
    Used across MusicService, YouTubeExtractorService and MusicCog
    to avoid raw dict access and key-typo bugs.
    """

    author: str
    url: str
    title: str = ""
    duration: float = 0.0
    source: str = ""
    thumbnail: Optional[str] = None
    format_id: Optional[str] = None
