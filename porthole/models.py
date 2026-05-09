from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProtocolFilter(StrEnum):
    ALL = "all"
    TCP = "tcp"
    UDP = "udp"


@dataclass(slots=True, frozen=True)
class PortRecord:
    pid: int
    command: str
    user: str
    fd: str
    protocol: str
    ip_version: str
    endpoint: str
    host: str
    port: str
    state: str | None = None

    @property
    def selection_key(self) -> tuple[int, str, str, str]:
        return (self.pid, self.fd, self.endpoint, self.protocol)


@dataclass(slots=True, frozen=True)
class ProcessDetails:
    pid: int
    executable: str | None
    cwd: str | None

