from __future__ import annotations

import unittest

from porthole.collector import parse_port_stream, parse_process_details, split_endpoint


TCP_SAMPLE = """\
p672
cDemoService
u501
Ldemo-user
f235
tIPv4
PTCP
n127.0.0.1:18080
TST=LISTEN
TQR=0
TQS=0
f240
tIPv4
PTCP
n127.0.0.1:18081
TST=LISTEN
"""


UDP_SAMPLE = """\
p94852
cDemoWorker
u501
Ldemo-user
f67
tIPv4
PUDP
n*:5353
"""


DETAIL_SAMPLE = """\
p672
fcwd
n/Users/demo-user/project
ftxt
n/Applications/DemoApp.app/Contents/MacOS/DemoApp
ftxt
n/usr/lib/dyld
"""


class CollectorParsingTests(unittest.TestCase):
    def test_split_endpoint(self) -> None:
        self.assertEqual(split_endpoint("127.0.0.1:8080"), ("127.0.0.1", "8080"))
        self.assertEqual(split_endpoint("*:*"), ("*", "*"))
        self.assertEqual(split_endpoint("[::1]:9000"), ("[::1]", "9000"))

    def test_parse_port_stream_supports_tcp_and_udp(self) -> None:
        records = parse_port_stream(TCP_SAMPLE + UDP_SAMPLE)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].command, "DemoService")
        self.assertEqual(records[0].protocol, "TCP")
        self.assertEqual(records[0].state, "LISTEN")
        self.assertEqual(records[2].command, "DemoWorker")
        self.assertEqual(records[2].protocol, "UDP")
        self.assertEqual(records[2].port, "5353")

    def test_parse_process_details_returns_first_executable(self) -> None:
        details = parse_process_details(DETAIL_SAMPLE, pid=672)
        self.assertEqual(details.pid, 672)
        self.assertEqual(details.cwd, "/Users/demo-user/project")
        self.assertEqual(details.executable, "/Applications/DemoApp.app/Contents/MacOS/DemoApp")


if __name__ == "__main__":
    unittest.main()
