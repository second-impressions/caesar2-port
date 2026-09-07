#!/usr/bin/env python3
"""Cut a release, in the two steps a pull-request-only main allows.

    tools/release.py prepare 1.0.0          # final release
    tools/release.py prepare 1.1.0-rc1      # pre-release of the version main is at
    tools/release.py publish 1.0.0          # after the pull request is merged

prepare, on a clean checkout of origin/main:
  1. turns CHANGELOG.md's "## Unreleased" section into "## <version> - <date>"
     (a release must have notes; an empty section is refused),
  2. sets project(VERSION) in CMakeLists.txt and adds the release to the
     AppStream metainfo,
  3. commits "release: <version>" on a branch release/<version>, pushes it
     and opens the pull request.

publish finds the merged release commit on origin/main and starts the
Release workflow on it, which tags that commit v<version>, builds every
download and opens a *draft* GitHub release with the changelog section as
its notes; publishing the draft is up to you.

project(VERSION) only names releases: builds from main are main-<commit>,
pull requests prN-<commit>. So nothing is bumped afterwards; the next
prepare sets the next version.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CMAKE = ROOT / "CMakeLists.txt"
CHANGELOG = ROOT / "CHANGELOG.md"
METAINFO = ROOT / "packaging" / "io.github.second_impressions.caesar2.metainfo.xml"

VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(-[0-9A-Za-z.]+)?$")
CMAKE_RE = re.compile(r"^(project\(caesar2-port VERSION )(\d+\.\d+\.\d+)(\b.*)$", re.M)


def run(*args, capture=True, check=True):
    result = subprocess.run(list(args), cwd=ROOT, text=True, capture_output=capture, check=check)
    return result.stdout.strip() if capture else ""


def git(*args, **kw):
    return run("git", *args, **kw)


def fail(message):
    print(f"release: {message}", file=sys.stderr)
    sys.exit(1)


def parse_version(text):
    m = VERSION_RE.match(text)
    if not m:
        fail(f"version must be X.Y.Z or X.Y.Z-suffix, got {text}")
    return ".".join(m.group(1, 2, 3)), m.group(4) or ""


def cmake_version(text):
    m = CMAKE_RE.search(text)
    if not m:
        fail("project(caesar2-port VERSION ...) not found")
    return m.group(2)


def set_cmake_version(version):
    CMAKE.write_text(CMAKE_RE.sub(lambda m: f"{m.group(1)}{version}{m.group(3)}", CMAKE.read_text(), 1))


def release_changelog(version, today):
    text = CHANGELOG.read_text()
    m = re.search(r"^## Unreleased\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        fail("CHANGELOG.md has no '## Unreleased' section")
    notes = m.group(1).strip("\n")
    if not re.search(r"^\s*[-*]", notes, re.M):
        fail("the Unreleased section has no entries; a release needs notes")
    if re.search(rf"^## {re.escape(version)} ", text, re.M):
        fail(f"CHANGELOG.md already has a {version} section")
    CHANGELOG.write_text(text[:m.start()] + f"## Unreleased\n\n## {version} - {today}\n\n{notes}\n\n" + text[m.end():])
    return notes


def add_metainfo_release(version, today):
    text = METAINFO.read_text()
    entry = f'    <release version="{version}" date="{today}"/>\n'
    if "<releases>" in text:
        text = text.replace("<releases>\n", "<releases>\n" + entry, 1)
    else:
        text = text.replace("</component>", f"  <releases>\n{entry}  </releases>\n</component>", 1)
    METAINFO.write_text(text)


def prepare(args):
    base, suffix = parse_version(args.version)
    branch = f"release/{args.version}"
    today = dt.date.today().isoformat()

    if not args.dry_run:
        if git("status", "--porcelain"):
            fail("the worktree is not clean")
        git("fetch", "-q", "origin", "main")
        if git("rev-parse", "HEAD") != git("rev-parse", "origin/main"):
            fail("check out origin/main first")
        if git("ls-remote", "--tags", "origin", f"refs/tags/v{args.version}"):
            fail(f"tag v{args.version} exists")
    notes = release_changelog(args.version, today)
    set_cmake_version(base)
    add_metainfo_release(args.version, today)
    print(f"release {args.version}\n\n{notes}\n")
    if args.dry_run:
        print("dry run: files edited, nothing committed")
        return

    git("checkout", "-q", "-b", branch)
    git("add", str(CMAKE), str(CHANGELOG), str(METAINFO))
    git("commit", "-q", "-m", f"release: {args.version}")
    git("push", "-q", "-u", "origin", branch)
    body = (f"Release {args.version}. Merge (rebase) when green, then\n\n"
            f"    tools/release.py publish {args.version}\n\n"
            f"tags the merged commit and builds the downloads into a draft release.\n\n{notes}")
    url = run("gh", "pr", "create", "--base", "main", "--head", branch,
              "--title", f"release: {args.version}", "--body", body)
    print(f"\n{url}\nmerge it, then: tools/release.py publish {args.version}")


def publish(args):
    base, suffix = parse_version(args.version)
    if git("status", "--porcelain"):
        fail("the worktree is not clean")
    git("fetch", "-q", "origin", "main")
    subject = f"release: {args.version}"
    found = git("log", "--format=%H %s", "origin/main", "-n", "50")
    commit = next((line.split()[0] for line in found.splitlines() if line.split(" ", 1)[1] == subject), None)
    if commit is None:
        fail(f"no '{subject}' commit in the last 50 on origin/main; merge the release pull request first")
    if git("ls-remote", "--tags", "origin", f"refs/tags/v{args.version}"):
        fail(f"tag v{args.version} exists; the workflow already ran")
    run("gh", "workflow", "run", "release.yml", "--ref", "main",
        "-f", f"version={args.version}", "-f", f"commit={commit}", capture=False)
    print(f"Release workflow started: it tags {commit[:8]} as v{args.version} and builds it.\n"
          f"Follow it with: gh run watch; the draft appears under Releases.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="open the release pull request")
    p.add_argument("version")
    p.add_argument("--dry-run", action="store_true", help="edit files, do not commit or push")
    p.set_defaults(func=prepare)
    p = sub.add_parser("publish", help="tag the merged release commit and build the downloads")
    p.add_argument("version")
    p.set_defaults(func=publish)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
