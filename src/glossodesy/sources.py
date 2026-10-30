"""Pinned upstream datasets and how to fetch them.

Every dataset is a CLDF release on GitHub, pinned to a tag so builds are
reproducible. Bump a tag here to move to a newer release.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_RAW_DIR = Path("data/raw")


@dataclass(frozen=True)
class Source:
    key: str
    repo: str
    tag: str  # a release tag, or a commit hash where the repo has no releases
    licence: str
    citation: str
    subdir: str | None = None  # fetch only this folder of a larger repo

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repo}.git"


SOURCES: dict[str, Source] = {
    "linguameta": Source(
        key="linguameta",
        repo="google-research/url-nlp",
        tag="452a21ad3dae5668c06ceeac21ff073e1e40f9be",
        licence="CC-BY-SA-4.0",
        citation=(
            "Ritchie, Sandy, Daan van Esch, Uche Okonkwo, Shikhar Vashishth & Emily Drummond. "
            "2024. LinguaMeta: Unified Metadata for Thousands of Languages. LREC-COLING 2024."
        ),
        subdir="linguameta",
    ),
    "glottolog": Source(
        key="glottolog",
        repo="glottolog/glottolog-cldf",
        tag="v5.3",
        licence="CC-BY-4.0",
        citation=(
            "Hammarström, Harald, Robert Forkel, Martin Haspelmath & Sebastian Bank. "
            "Glottolog 5.3. Leipzig: Max Planck Institute for Evolutionary Anthropology."
        ),
    ),
    "asjp": Source(
        key="asjp",
        repo="lexibank/asjp",
        tag="v21.1",
        licence="CC-BY-4.0",
        citation=(
            "Wichmann, Søren, Eric W. Holman & Cecil H. Brown (eds.). "
            "The ASJP Database (version 21.1)."
        ),
    ),
}


def source_dir(key: str, raw_dir: Path = DEFAULT_RAW_DIR) -> Path:
    src = SOURCES[key]
    root = raw_dir / src.repo.split("/")[-1]
    return root / src.subdir if src.subdir else root


def fetch(raw_dir: Path = DEFAULT_RAW_DIR, keys: list[str] | None = None) -> None:
    """Shallow-clone each pinned source into ``raw_dir`` (skips ones already present)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    for key in keys or list(SOURCES):
        src = SOURCES[key]
        if source_dir(key, raw_dir).exists():
            print(f"{key}: already present at {source_dir(key, raw_dir)}")
            continue
        dest = raw_dir / src.repo.split("/")[-1]
        print(f"{key}: fetching {src.repo} @ {src.tag[:12]}")
        if src.subdir:  # sparse checkout of one folder at a pinned commit
            git = ["git", "-C", str(dest)]
            subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", "--sparse",
                            src.url, str(dest)], check=True)
            subprocess.run(git + ["sparse-checkout", "set", src.subdir], check=True)
            subprocess.run(git + ["-c", "advice.detachedHead=false", "checkout", "-q", src.tag], check=True)
        else:
            subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "-q", "--depth", "1",
                            "--branch", src.tag, src.url, str(dest)], check=True)
