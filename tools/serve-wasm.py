#!/usr/bin/env python3
"""Serve an Emscripten build with the headers required by pthreads."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Caesar2Handler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    directory = args.directory.resolve()
    if not (directory / "caesar2.html").is_file():
        parser.error(f"{directory} does not contain caesar2.html")

    handler = partial(Caesar2Handler, directory=str(directory))
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    port = server.server_address[1]
    print(f"Serving http://{args.bind}:{port}/caesar2.html", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
