#!/usr/bin/env bash
# Write one directory of the GitHub Pages site (the gh-pages branch).
#
#   publish-pages.sh <target> <source-dir> <description>
#
# target is "." for the site root (the latest published release), "main"
# for the main branch, "pr/N" for a pull request. Each target owns only
# its own directory: publishing the root leaves main/ and pr/ alone.
#
# The branch is kept at a single commit. Every publish carries several MB
# of build output, and a branch that remembered each of them would grow
# without bound; what was live when is recorded by the Deployments API
# instead (deployment.js). Needs GH_TOKEN and GITHUB_REPOSITORY.
set -euo pipefail
target=$1
source=$(cd "$2" && pwd)   # absolute: the clone below is entered with cd
description=$3

git config --global user.name "github-actions[bot]"
git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
remote="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"

publish() {
    rm -rf pages
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
    # One commit holding the whole site; the previous history is dropped.
    git checkout --quiet --orphan publish
    git add -A
    git commit --quiet -m "Publish ${target}: ${description}"
    git push --quiet --force origin publish:gh-pages
}

# Publishers are serialized by the workflow's concurrency group; the retry
# covers a push that still races an earlier one.
for attempt in 1 2 3; do
    (publish) && exit 0
    sleep $((attempt * 5))
done
exit 1
