import asyncio
import logging
from typing import Any, Dict, Optional

import validators
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

from .dto import SongInfoDTO


class YouTubeExtractorService:
    def __init__(
        self, ydl_options: Optional[Dict[str, Any]] = None, test_mode: bool = False
    ):
        self.ydl_options = ydl_options or {}
        self.test_mode = test_mode

    def _extract_sync(self, url: str, opts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronously extract video information using yt-dlp.
        Params:
            * (String) url: The complete url of a Youtube video or a search query.
            * (Dict) opts: The options to pass to yt-dlp.
        Returns:
            * (Dict) A dictionary with the extracted video information.
        """
        with YoutubeDL(opts) as ydl:
            if validators.url(url):
                return ydl.extract_info(url, download=False)

            result = ydl.extract_info(f"ytsearch:{url}", download=False)
            if isinstance(result, dict) and result.get("entries"):
                return result["entries"][0]
            return result

    def _has_audio_formats(self, formats: list[dict]) -> bool:
        return any(
            f.get("url") and f.get("acodec") and f.get("acodec") != "none"
            for f in formats
        )

    def _select_best_audio_source(
        self, formats: list[dict]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Select the best audio source from a list of formats.
        Params:
            * (List) formats: A list of format dictionaries from yt-dlp.
        Returns:
            * (Tuple) A tuple containing the URL of the best audio source and its format ID.
        """
        audio_formats = [
            f
            for f in formats
            if f.get("url") and f.get("acodec") and f.get("acodec") != "none"
        ]

        if not audio_formats:
            # Last-resort fallback: any URL
            for f in formats:
                if f.get("url"):
                    return f.get("url"), f.get("format_id")
            return None, None

        opus_candidates = [
            f for f in audio_formats if "opus" in (f.get("acodec") or "").lower()
        ]
        candidates = opus_candidates or audio_formats

        def score(f: dict) -> float:
            try:
                return float(f.get("abr") or f.get("tbr") or 0)
            except Exception:
                return 0.0

        best = max(candidates, key=score)
        return best.get("url"), best.get("format_id")

    async def search(self, url: str, author: str) -> Optional[SongInfoDTO]:
        """
        Search for a YouTube video and extract its info and best audio source URL.
        Params:
            * (String) url: The complete url of a Youtube video or a search query.
            * (String) author: The name of the user who requested the song, used for logging and display purposes.
        Returns:
            * (Dict) A dictionary with all the relevant info of a song, such as title, duration, thumbnail and url, this info is used to save the song in the music queue and
        """
        loop = asyncio.get_running_loop()
        options = self.ydl_options.copy()

        try:
            info = await loop.run_in_executor(
                None, lambda: self._extract_sync(url, options)
            )
        except Exception:
            try:
                retry_opts = options.copy()
                retry_opts["js_runtimes"] = {"node": {}}
                info = await loop.run_in_executor(
                    None, lambda: self._extract_sync(url, retry_opts)
                )
            except Exception as e:
                logger.error("yt-dlp extract_info failed: %s", e)
                return None

        formats = info.get("formats") or []
        if not self._has_audio_formats(formats):
            try:
                retry_opts = options.copy()
                retry_opts["js_runtimes"] = {"node": {}}
                info = await loop.run_in_executor(
                    None, lambda: self._extract_sync(url, retry_opts)
                )
                formats = info.get("formats") or []
            except Exception as e:
                logger.warning("yt-dlp retry with js_runtimes failed: %s", e)

        if self.test_mode:
            try:
                logger.debug(
                    "[yt-dlp] formats for %s: %d entries", info.get("id"), len(formats)
                )
                for f in formats:
                    logger.debug(
                        "  %s\t%s\tacodec=%s\tabr=%s\ttbr=%s\t%s",
                        f.get("format_id"),
                        f.get("ext"),
                        f.get("acodec"),
                        f.get("abr"),
                        f.get("tbr"),
                        (f.get("url") or "")[:120],
                    )
            except Exception:
                pass

        source_url, selected_format_id = self._select_best_audio_source(formats)

        return SongInfoDTO(
            author=author,
            url=info.get("webpage_url") or "",
            title=info.get("title") or "",
            duration=float(info.get("duration") or 0.0),
            source=source_url or "",
            thumbnail=info.get("thumbnail"),
            format_id=selected_format_id,
        )
