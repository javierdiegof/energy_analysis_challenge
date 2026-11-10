"""
Captures high-DPI (2880x1720 Retina) PNG screenshots of all three Monclova Analyst Dashboard tabs
using headless Google Chrome via an ephemeral local HTTP server.
"""

import functools
import http.server
import socketserver
import subprocess
import threading
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent
SHOT_DIR = SITE_DIR / "screenshots"
SHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    handler = functools.partial(QuietHandler, directory=str(SITE_DIR))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        targets = [
            ("tab1", SHOT_DIR / "01_tab1_day_ahead_planner.png"),
            ("tab2", SHOT_DIR / "02_tab2_realtime_monitor.png"),
            ("tab3", SHOT_DIR / "03_tab3_settlement_review.png"),
        ]

        for tab_id, out_png in targets:
            url = f"http://127.0.0.1:{port}/index.html?tab={tab_id}"
            cmd = [
                CHROME_BIN,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--window-size=1440,860",
                "--force-device-scale-factor=2",
                "--virtual-time-budget=1500",
                f"--screenshot={out_png}",
                url,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Captured {out_png.name} ({out_png.stat().st_size / 1024:.1f} KB)")

        httpd.shutdown()


if __name__ == "__main__":
    main()
