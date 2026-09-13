#!/usr/bin/env python3
"""Serve an Emscripten build with the headers required by pthreads."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import ssl
from urllib.parse import unquote, urlsplit


class Caesar2Handler(SimpleHTTPRequestHandler):
    # --game-data FILE is served at /smoke-data/<name>, for the page to
    # import when a smoke test starts in a browser that has none.
    game_data: Path | None = None

    def translate_path(self, path: str) -> str:
        requested = unquote(urlsplit(path).path)
        if self.game_data and requested == f"/smoke-data/{self.game_data.name}":
            return str(self.game_data)
        return super().translate_path(path)

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
    parser.add_argument("--game-data", type=Path,
                        help="a disc image, ZIP or pack to serve at /smoke-data/<name>")
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

    if args.game_data:
        if not args.game_data.is_file():
            raise SystemExit(f"{args.game_data} is not a file")
        Caesar2Handler.game_data = args.game_data.resolve()
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
