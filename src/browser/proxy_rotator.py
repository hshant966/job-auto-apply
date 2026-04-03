"""Proxy rotation for anti-detection."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Proxy:
    host: str
    port: int
    username: str = ""
    password: str = ""
    protocol: str = "http"

    @property
    def playwright_config(self) -> dict:
        cfg = {"server": f"{self.protocol}://{self.host}:{self.port}"}
        if self.username:
            cfg["username"] = self.username
        if self.password:
            cfg["password"] = self.password
        return cfg

    @property
    def url(self) -> str:
        if self.username:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"


class ProxyRotator:
    """Round-robin or random proxy rotation."""

    def __init__(self, proxies: Optional[list[Proxy]] = None):
        self._proxies = proxies or []
        self._index = 0

    def add(self, proxy: Proxy):
        self._proxies.append(proxy)

    def add_from_urls(self, urls: list[str]):
        for url in urls:
            try:
                # Parse: protocol://user:pass@host:port
                if "://" in url:
                    proto, rest = url.split("://", 1)
                else:
                    proto, rest = "http", url
                if "@" in rest:
                    auth, hostport = rest.rsplit("@", 1)
                    user, pwd = auth.split(":", 1)
                else:
                    user, pwd, hostport = "", "", rest
                host, _, port = hostport.partition(":")
                self.add(Proxy(host=host, port=int(port or "8080"),
                               username=user, password=pwd, protocol=proto))
            except Exception as e:
                logger.warning(f"Failed to parse proxy URL: {url}: {e}")

    def next(self) -> Optional[Proxy]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._index % len(self._proxies)]
        self._index += 1
        return proxy

    def random(self) -> Optional[Proxy]:
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    @property
    def count(self) -> int:
        return len(self._proxies)
