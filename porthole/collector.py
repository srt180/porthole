from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Iterable

from porthole.models import PortRecord, ProcessDetails, ProtocolFilter


class CollectionError(RuntimeError):
    """Raised when system port collection fails."""


@dataclass(slots=True)
class _SocketDraft:
    pid: int
    command: str
    user: str
    fd: str
    protocol: str | None = None
    ip_version: str | None = None
    endpoint: str | None = None
    state: str | None = None


def split_endpoint(endpoint: str) -> tuple[str, str]:
    if ":" not in endpoint:
        return endpoint, ""
    host, port = endpoint.rsplit(":", 1)
    return host, port


def parse_port_stream(output: str) -> list[PortRecord]:
    records: list[PortRecord] = []
    current_process = {"pid": 0, "command": "", "user": ""}
    current_socket: _SocketDraft | None = None

    def flush_socket() -> None:
        nonlocal current_socket
        if current_socket is None:
            return
        if not current_socket.protocol or not current_socket.endpoint or not current_socket.ip_version:
            current_socket = None
            return
        host, port = split_endpoint(current_socket.endpoint)
        records.append(
            PortRecord(
                pid=current_socket.pid,
                command=current_socket.command,
                user=current_socket.user,
                fd=current_socket.fd,
                protocol=current_socket.protocol,
                ip_version=current_socket.ip_version,
                endpoint=current_socket.endpoint,
                host=host,
                port=port,
                state=current_socket.state,
            )
        )
        current_socket = None

    for raw_line in output.splitlines():
        if not raw_line:
            continue
        field, value = raw_line[0], raw_line[1:]
        if field == "p":
            flush_socket()
            current_process = {"pid": int(value), "command": "", "user": ""}
        elif field == "c":
            current_process["command"] = value
        elif field == "L":
            current_process["user"] = value
        elif field == "u" and not current_process["user"]:
            current_process["user"] = value
        elif field == "f":
            flush_socket()
            current_socket = _SocketDraft(
                pid=current_process["pid"],
                command=current_process["command"],
                user=current_process["user"],
                fd=value,
            )
        elif current_socket is not None:
            if field == "P":
                current_socket.protocol = value
            elif field == "t":
                current_socket.ip_version = value
            elif field == "n":
                current_socket.endpoint = value
            elif field == "T" and value.startswith("ST="):
                current_socket.state = value[3:]

    flush_socket()
    return records


def parse_process_details(output: str, pid: int) -> ProcessDetails:
    executable: str | None = None
    cwd: str | None = None
    current_fd: str | None = None

    for raw_line in output.splitlines():
        if not raw_line:
            continue
        field, value = raw_line[0], raw_line[1:]
        if field == "f":
            current_fd = value
        elif field == "n" and current_fd == "cwd":
            cwd = value
        elif field == "n" and current_fd == "txt" and executable is None:
            executable = value

    return ProcessDetails(pid=pid, executable=executable, cwd=cwd)


class PortCollector:
    def __init__(self) -> None:
        self._details_cache: dict[int, ProcessDetails] = {}

    def clear_details_cache(self) -> None:
        self._details_cache.clear()

    def collect(self, protocol_filter: ProtocolFilter) -> list[PortRecord]:
        records: list[PortRecord] = []
        if protocol_filter in (ProtocolFilter.ALL, ProtocolFilter.TCP):
            records.extend(
                parse_port_stream(
                    self._run_lsof(["-iTCP", "-sTCP:LISTEN", "-FpcuLfnPtT"])
                )
            )
        if protocol_filter in (ProtocolFilter.ALL, ProtocolFilter.UDP):
            records.extend(parse_port_stream(self._run_lsof(["-iUDP", "-FpcuLfnPtT"])))
        return sorted(records, key=self._sort_key)

    def get_process_details(self, pid: int) -> ProcessDetails:
        if pid in self._details_cache:
            return self._details_cache[pid]

        output = self._run_lsof(["-a", "-p", str(pid), "-d", "cwd,txt", "-Ffn"])
        details = parse_process_details(output, pid)
        self._details_cache[pid] = details
        return details

    def _run_lsof(self, args: Iterable[str]) -> str:
        command = ["lsof", "-nP", *args]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
            )
        except FileNotFoundError as exc:
            raise CollectionError("未找到 lsof，请先安装后再运行。") from exc
        except OSError as exc:
            raise CollectionError(f"执行 lsof 失败: {exc}") from exc

        if completed.returncode not in (0, 1):
            stderr = completed.stderr.strip() or "未知错误"
            raise CollectionError(f"lsof 执行失败: {stderr}")
        return completed.stdout

    @staticmethod
    def _sort_key(record: PortRecord) -> tuple[int, int, str, int, str]:
        protocol_weight = 0 if record.protocol == "TCP" else 1
        try:
            port_weight = int(record.port)
        except ValueError:
            port_weight = 999999
        return (protocol_weight, port_weight, record.host, record.pid, record.fd)
