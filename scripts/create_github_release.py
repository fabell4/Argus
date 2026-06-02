"""Create or update a GitHub release via the API."""

import json
import os
import subprocess
import sys
import tempfile

TAG = os.environ["TAG"]
VERSION = os.environ["VERSION"]
GH_USER = os.environ["GH_USERNAME"]
GH_PAT = os.environ["GH_PAT"]
_tmpdir = tempfile.gettempdir()
NOTES_FILE = os.environ.get("NOTES_FILE", os.path.join(_tmpdir, "changelog_notes.txt"))
PAYLOAD_FILE = os.environ.get(
    "PAYLOAD_FILE", os.path.join(_tmpdir, "gh_release_payload.json")
)
RESPONSE_FILE = os.environ.get(
    "RESPONSE_FILE", os.path.join(_tmpdir, "gh_response.json")
)

IS_PRE = any(x in TAG for x in ("alpha", "beta", "rc"))

try:
    with open(NOTES_FILE, encoding="utf-8") as fh:
        NOTES = fh.read().strip()
except OSError:
    NOTES = ""

DOCKER_LINE = f"**Docker image:** `docker pull ghcr.io/{GH_USER}/argus:{VERSION}`"
BODY = f"{NOTES}\n\n---\n\n{DOCKER_LINE}" if NOTES else DOCKER_LINE

payload = {"tag_name": TAG, "name": TAG, "prerelease": IS_PRE, "body": BODY}

fd = os.open(PAYLOAD_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(payload, f)

BASE_URL = f"https://api.github.com/repos/{GH_USER}/argus/releases"
HEADERS = [
    "-H",
    f"Authorization: Bearer {GH_PAT}",
    "-H",
    "Content-Type: application/json",
]

r = subprocess.run(
    [
        "curl",
        "-s",
        "-o",
        RESPONSE_FILE,
        "-w",
        "%{http_code}",
        "-X",
        "POST",
        *HEADERS,
        BASE_URL,
        "-d",
        f"@{PAYLOAD_FILE}",
    ],
    capture_output=True,
    text=True,
    check=False,
)
code = r.stdout.strip()

if code == "422":
    r2 = subprocess.run(
        ["curl", "-fsSL", *HEADERS, f"{BASE_URL}/tags/{TAG}"],
        capture_output=True,
        text=True,
        check=True,
    )
    release_id = json.loads(r2.stdout)["id"]
    subprocess.run(
        [
            "curl",
            "-fsSL",
            "-X",
            "PATCH",
            *HEADERS,
            f"{BASE_URL}/{release_id}",
            "-d",
            f"@{PAYLOAD_FILE}",
        ],
        check=True,
    )
elif code not in ("200", "201"):
    print(f"GitHub release API returned HTTP {code}", file=sys.stderr)
    sys.exit(1)
