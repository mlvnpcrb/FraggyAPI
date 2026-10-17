"""Heuristic credential scan of nonignored files and all committed blobs.

Print paths only, never matching values. This complements review, not a guarantee.
The documented disposable localhost database password is intentionally allowed.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{40,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(
        rb"(?i)(?:password|api_key|secret|token)\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']"
    ),
]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def suspect(data: bytes) -> bool:
    for pattern in PATTERNS:
        for match in pattern.finditer(data):
            if match.lastindex and match.group(1) == b"fraggy_local_only":
                continue
            return True
    return False


def main() -> None:
    paths = set(
        git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0")
    ) - {b""}
    findings = []
    for raw in paths:
        path = ROOT / raw.decode()
        if path.is_file() and suspect(path.read_bytes()):
            findings.append(str(path.relative_to(ROOT)))
        if path.name == ".env" or (
            path.name.startswith(".env.") and not path.name.endswith(".example")
        ):
            findings.append(str(path.relative_to(ROOT)) + " (environment file)")
    objects: set[bytes] = set()
    commits = git("rev-list", "--all").splitlines()
    for commit in commits:
        for entry in git("ls-tree", "-r", "-z", commit.decode()).split(b"\0"):
            if not entry:
                continue
            info, name = entry.split(b"\t", 1)
            _, kind, oid = info.split()
            if kind == b"blob" and oid not in objects:
                objects.add(oid)
                if suspect(git("cat-file", "blob", oid.decode())):
                    findings.append("history:" + name.decode())
    for finding in sorted(set(findings)):
        print("REVIEW:", finding)
    print(
        f"Scanned {len(paths)} working-tree files, {len(commits)} commits, "
        f"{len(objects)} historical blobs; {len(findings)} findings"
    )
    raise SystemExit(bool(findings))


if __name__ == "__main__":
    main()
