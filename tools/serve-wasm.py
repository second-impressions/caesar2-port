#!/usr/bin/env python3
"""Serve an Emscripten build with the headers required by pthreads."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import ssl


class Caesar2Handler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        # A preview server must always hand out the build that is on disk;
        # heuristic caching otherwise mixes an old page with a new runtime.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--entry")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--certfile", type=Path)
    parser.add_argument("--keyfile", type=Path)
    args = parser.parse_args()

    if bool(args.certfile) != bool(args.keyfile):
        parser.error("--certfile and --keyfile must be supplied together")

    directory = args.directory.resolve()
    if args.entry:
        entry = directory / args.entry
    else:
        entries = [directory / "index.html"]
        if not entries[0].is_file():
            entries = sorted(directory.glob("caesar2*.html"))
        if len(entries) != 1 or not entries[0].is_file():
            parser.error(
                f"{directory} must contain index.html; "
                "use --entry to select another page"
            )
        entry = entries[0]
    if entry.parent != directory or not entry.is_file():
        parser.error(f"{entry} is not a build entry point")

    handler = partial(Caesar2Handler, directory=str(directory))
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    scheme = "http"
    if args.certfile:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(args.certfile, args.keyfile)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        scheme = "https"
    port = server.server_address[1]
    print(f"Serving {scheme}://{args.bind}:{port}/{entry.name}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
