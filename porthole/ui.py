from __future__ import annotations

import curses
from datetime import datetime
import textwrap
import time

from porthole.collector import CollectionError, PortCollector
from porthole.models import PortRecord, ProcessDetails, ProtocolFilter

AUTO_REFRESH_SECONDS = 5.0


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))


def truncate(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text.ljust(width)
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


class PortholeUI:
    def __init__(self, collector: PortCollector) -> None:
        self.collector = collector
        self.protocol_filter = ProtocolFilter.ALL
        self.records: list[PortRecord] = []
        self.selected_index = 0
        self.selected_details: ProcessDetails | None = None
        self.status = "准备中"
        self.last_refresh_label = "尚未刷新"
        self.last_refresh_mono = 0.0

    def run(self) -> int:
        try:
            curses.wrapper(self._main)
        except KeyboardInterrupt:
            return 0
        return 0

    def _main(self, stdscr: curses.window) -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.keypad(True)
        stdscr.timeout(250)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)

        self.refresh_data("初次加载")

        while True:
            self.render(stdscr)
            key = stdscr.getch()
            if key == -1:
                if time.monotonic() - self.last_refresh_mono >= AUTO_REFRESH_SECONDS:
                    self.refresh_data("自动刷新")
                continue

            if key in (ord("q"), ord("Q")):
                return
            if key in (ord("j"), curses.KEY_DOWN):
                self.move_selection(1)
                continue
            if key in (ord("k"), curses.KEY_UP):
                self.move_selection(-1)
                continue
            if key in (ord("a"), ord("A")):
                self.set_filter(ProtocolFilter.ALL, "切换到全部协议")
                continue
            if key in (ord("t"), ord("T")):
                self.set_filter(ProtocolFilter.TCP, "切换到 TCP")
                continue
            if key in (ord("u"), ord("U")):
                self.set_filter(ProtocolFilter.UDP, "切换到 UDP")
                continue
            if key in (ord("r"), ord("R")):
                self.refresh_data("手动刷新")

    def set_filter(self, protocol_filter: ProtocolFilter, reason: str) -> None:
        self.protocol_filter = protocol_filter
        self.refresh_data(reason)

    def move_selection(self, offset: int) -> None:
        if not self.records:
            return
        self.selected_index = clamp(self.selected_index + offset, 0, len(self.records) - 1)
        self._load_selected_details()

    def refresh_data(self, trigger: str) -> None:
        previous_key = self.current_record.selection_key if self.current_record else None
        self.collector.clear_details_cache()
        try:
            self.records = self.collector.collect(self.protocol_filter)
            self.selected_index = self._find_index(previous_key)
            self.last_refresh_mono = time.monotonic()
            self.last_refresh_label = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status = f"{trigger}完成，共 {len(self.records)} 条记录"
        except CollectionError as exc:
            self.records = []
            self.selected_index = 0
            self.selected_details = None
            self.last_refresh_mono = time.monotonic()
            self.last_refresh_label = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status = str(exc)
            return

        self._load_selected_details()

    def _load_selected_details(self) -> None:
        record = self.current_record
        if record is None:
            self.selected_details = None
            return
        try:
            self.selected_details = self.collector.get_process_details(record.pid)
        except CollectionError as exc:
            self.selected_details = None
            self.status = f"{self.status}；详情读取失败: {exc}"

    @property
    def current_record(self) -> PortRecord | None:
        if not self.records:
            return None
        if self.selected_index >= len(self.records):
            self.selected_index = len(self.records) - 1
        return self.records[self.selected_index]

    def _find_index(self, selection_key: tuple[int, str, str, str] | None) -> int:
        if not self.records:
            return 0
        if selection_key is None:
            return 0
        for index, record in enumerate(self.records):
            if record.selection_key == selection_key:
                return index
        return 0

    def render(self, stdscr: curses.window) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if height < 12 or width < 70:
            self._safe_addstr(stdscr, 0, 0, "窗口太小，请扩大终端后重试。")
            stdscr.refresh()
            return

        list_width = max(44, int(width * 0.58))
        detail_x = list_width + 1

        title = f"Porthole  本机监听端口视图  过滤: {self.protocol_filter.upper()}  记录: {len(self.records)}"
        self._safe_addstr(stdscr, 0, 0, truncate(title, width - 1))
        self._safe_addstr(stdscr, 1, 0, truncate(f"最近刷新: {self.last_refresh_label}", width - 1))
        self._draw_vertical_rule(stdscr, detail_x - 1, 2, height - 3)

        self._render_list(stdscr, 2, 0, height - 5, list_width)
        self._render_details(stdscr, 2, detail_x, height - 5, width - detail_x)

        self._safe_addstr(
            stdscr,
            height - 2,
            0,
            truncate("j/k/↑/↓: 移动  a:全部  t:TCP  u:UDP  r:刷新  q:退出", width - 1),
        )
        self._safe_addstr(stdscr, height - 1, 0, truncate(self.status, width - 1))
        stdscr.refresh()

    def _render_list(self, stdscr: curses.window, top: int, left: int, height: int, width: int) -> None:
        header = self._format_list_row("协议", "端口", "监听地址", "PID", "进程", width)
        self._safe_addstr(stdscr, top, left, header, curses.A_BOLD)

        visible_rows = max(0, height - 1)
        start_index = 0
        if self.selected_index >= visible_rows:
            start_index = self.selected_index - visible_rows + 1

        for row in range(visible_rows):
            record_index = start_index + row
            if record_index >= len(self.records):
                break
            record = self.records[record_index]
            text = self._format_list_row(
                record.protocol,
                record.port or "-",
                record.host or record.endpoint,
                str(record.pid),
                record.command,
                width,
            )
            attr = curses.A_REVERSE
            if curses.has_colors():
                attr = curses.color_pair(1) if record_index == self.selected_index else curses.A_NORMAL
            elif record_index != self.selected_index:
                attr = curses.A_NORMAL
            self._safe_addstr(stdscr, top + 1 + row, left, text, attr)

        if not self.records:
            self._safe_addstr(stdscr, top + 2, left, "没有可显示的监听记录。")

    def _render_details(self, stdscr: curses.window, top: int, left: int, height: int, width: int) -> None:
        self._safe_addstr(stdscr, top, left, truncate("详情", width - 1), curses.A_BOLD)
        record = self.current_record
        if record is None:
            self._safe_addstr(stdscr, top + 2, left, "请选择或刷新后查看详情。")
            return

        details = self.selected_details
        lines = [
            f"进程: {record.command}",
            f"PID: {record.pid}",
            f"用户: {record.user}",
            f"协议: {record.protocol} / {record.ip_version}",
            f"端点: {record.endpoint}",
            f"状态: {record.state or '-'}",
            f"FD: {record.fd}",
            f"可执行文件: {details.executable if details else '加载中...'}",
            f"工作目录: {details.cwd if details else '加载中...'}",
        ]

        current_y = top + 1
        for line in lines:
            wrapped = textwrap.wrap(line, width=max(10, width - 1)) or [""]
            for part in wrapped:
                if current_y >= top + height:
                    return
                self._safe_addstr(stdscr, current_y, left, truncate(part, width - 1))
                current_y += 1

    @staticmethod
    def _format_list_row(protocol: str, port: str, host: str, pid: str, command: str, width: int) -> str:
        proto_width = 6
        port_width = 8
        host_width = 18
        pid_width = 8
        fixed = proto_width + port_width + host_width + pid_width + 4
        command_width = max(8, width - fixed)
        return " ".join(
            [
                truncate(protocol, proto_width),
                truncate(port, port_width),
                truncate(host, host_width),
                truncate(pid, pid_width),
                truncate(command, command_width),
            ]
        )

    @staticmethod
    def _draw_vertical_rule(
        stdscr: curses.window, x: int, start_y: int, end_y: int
    ) -> None:
        for y in range(start_y, end_y + 1):
            try:
                stdscr.addch(y, x, curses.ACS_VLINE)
            except curses.error:
                pass

    @staticmethod
    def _safe_addstr(
        stdscr: curses.window, y: int, x: int, text: str, attr: int = 0
    ) -> None:
        try:
            stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass
