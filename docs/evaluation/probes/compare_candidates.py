"""Reproduce a computational smoke comparison; no market-performance claim.

Requires Python 3.12 and Node 24.17. Downloads only immutable, audited public
source files into an isolated temporary directory and verifies SHA-256 hashes.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


def main():
    here = Path(__file__).resolve().parent
    lock = json.loads((here.parent / "source-lock.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="chart-evaluation-") as temp:
        root = Path(temp)
        for source in lock["runtime_probe_sources"]:
            url = source["url"]
            raw = urllib.request.urlopen(url, timeout=30).read()
            if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                raise RuntimeError("Source digest mismatch: " + source["name"])
            (root / source["name"]).write_bytes(raw)
        shutil.copyfile(here / "candidate_smoke.mjs", root / "smoke.test.mjs")
        shutil.copyfile(here / "generate_fixture.py", root / "compare.py")
        subprocess.run([sys.executable, str(root / "compare.py")], check=True)
        subprocess.run(["node", "--test", str(root / "smoke.test.mjs")], check=True)
        print((root / "comparison-results.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
