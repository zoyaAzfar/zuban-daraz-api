"""Python client for the Zuban Daraz South Asian Proverb API."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterator, List, Optional

import requests

DEFAULT_BASE_URL = "https://zuban-daraz-proverb-api.zoe-azfar.workers.dev"
MAX_PAGE_SIZE = 100


class ZubanDarazError(Exception):
    """Raised when the API can't be reached or returns an error."""


class NotFoundError(ZubanDarazError):
    """Raised when the API returns 404."""


@dataclass(frozen=True)
class Proverb:
    id: int
    proverb: str
    translation: Optional[str]
    language: str
    theme: Optional[str]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Proverb":
        return cls(
            id=d["id"],
            proverb=d["proverb"],
            translation=d.get("translation"),
            language=d["language"],
            theme=d.get("theme"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Client:
    """
    >>> from zubandaraz import Client
    >>> api = Client()
    >>> api.random(theme="Animals")
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", "zubandaraz-python/0.1")

    # -- internals -------------------------------------------------------
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            resp = self.session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ZubanDarazError(f"Could not reach the API: {exc}") from exc
        if resp.status_code == 404:
            raise NotFoundError("Not found")
        if not resp.ok:
            raise ZubanDarazError(f"API returned HTTP {resp.status_code}")
        try:
            return resp.json()
        except ValueError as exc:
            raise ZubanDarazError("API returned invalid JSON") from exc

    # -- public methods --------------------------------------------------
    def proverbs(
        self,
        language: Optional[str] = None,
        theme: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Proverb]:
        """One page of proverbs (max 100 per page). Use `iter_all` for everything."""
        body = self._get(
            "/v1/proverbs",
            {"language": language, "theme": theme, "q": q, "limit": limit, "offset": offset},
        )
        return [Proverb.from_dict(d) for d in body["data"]]

    def iter_all(
        self,
        language: Optional[str] = None,
        theme: Optional[str] = None,
        q: Optional[str] = None,
    ) -> Iterator[Proverb]:
        """Iterate over every matching proverb, fetching pages automatically."""
        offset = 0
        while True:
            body = self._get(
                "/v1/proverbs",
                {"language": language, "theme": theme, "q": q, "limit": MAX_PAGE_SIZE, "offset": offset},
            )
            for d in body["data"]:
                yield Proverb.from_dict(d)
            offset += MAX_PAGE_SIZE
            if offset >= body["meta"]["total"]:
                return

    def get(self, proverb_id: int) -> Optional[Proverb]:
        """A single proverb by id, or None if it doesn't exist."""
        try:
            return Proverb.from_dict(self._get(f"/v1/proverbs/{int(proverb_id)}")["data"])
        except NotFoundError:
            return None

    def random(self, language: Optional[str] = None, theme: Optional[str] = None) -> Optional[Proverb]:
        """A random proverb, optionally filtered. None if nothing matches."""
        try:
            return Proverb.from_dict(self._get("/v1/proverbs/random", {"language": language, "theme": theme})["data"])
        except NotFoundError:
            return None

    def languages(self) -> List[Dict[str, Any]]:
        """[{'name': 'Punjabi', 'count': 31}, ...]"""
        return self._get("/v1/languages")["data"]

    def themes(self) -> List[Dict[str, Any]]:
        """[{'name': 'Animals', 'count': 22}, ...]"""
        return self._get("/v1/themes")["data"]
