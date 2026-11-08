#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 1 || ! $1 =~ ^[0-9a-f]{40}$ ]]; then
    echo 'Usage: bash deploy/prepare-release.sh <full Git commit SHA>' >&2
    exit 2
fi

commit=$1
repository=$(git rev-parse --show-toplevel)
release_dir="/home/ubuntu/safehome-releases/$commit"
git -C "$repository" cat-file -e "$commit^{commit}"
mkdir -p "$(dirname "$release_dir")"
if [[ ! -e $release_dir ]]; then
    git -C "$repository" worktree add --detach "$release_dir" "$commit"
elif [[ $(git -C "$release_dir" rev-parse --show-toplevel) != "$release_dir" ||
        $(git -C "$release_dir" rev-parse HEAD) != "$commit" ||
        -n $(git -C "$release_dir" status --porcelain) ]]; then
    echo 'Existing release directory does not match the requested clean checkout.' >&2
    exit 1
fi
python3.14 -m venv "$release_dir/venv"
"$release_dir/venv/bin/python" -m pip install -r "$release_dir/requirements-production.txt"
"$release_dir/venv/bin/python" -m pip check
printf 'Prepared %s\n' "$release_dir"
