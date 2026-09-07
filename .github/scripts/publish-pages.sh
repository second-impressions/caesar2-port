#!/usr/bin/env bash
# Write one directory of the GitHub Pages site (the gh-pages branch).
#
#   publish-pages.sh <target> <source-dir> <description>
#
# target is "." for the site root (the latest published release), "main"
# for the main branch, "pr/N" for a pull request. Each target owns only
# its own directory: publishing the root leaves main/ and pr/ alone.
# Needs GH_TOKEN and GITHUB_REPOSITORY.
set -euo pipefail
target=$1
source=$2
description=$3

git config --global user.name "github-actions[bot]"
git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
remote="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
if git clone --quiet --depth 1 --branch gh-pages "$remote" pages 2>/dev/null; then
    cd pages
else
    mkdir pages && cd pages && git init --quiet -b gh-pages && git remote add origin "$remote"
fi
if [ "$target" = "." ]; then
    find . -mindepth 1 -maxdepth 1 ! -name .git ! -name pr ! -name main -exec rm -rf {} +
else
    rm -rf "$target"
    mkdir -p "$target"
fi
cp -R "$source/." "$target/"
touch .nojekyll
git add -A
git commit --quiet -m "Publish ${target}: ${description}" || { echo "nothing changed"; exit 0; }
for attempt in 1 2 3; do
    git push --quiet origin gh-pages && exit 0
    git fetch --quiet origin gh-pages && git rebase --quiet origin/gh-pages
done
exit 1
