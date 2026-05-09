from __future__ import annotations

from porthole.collector import PortCollector
from porthole.ui import PortholeUI


def main() -> int:
    ui = PortholeUI(PortCollector())
    return ui.run()

