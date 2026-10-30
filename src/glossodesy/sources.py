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
    tag: str
    licence: str
    citation: str

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repo}.git"


SOURCES: dict[str, Source] = {
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
    return raw_dir / SOURCES[key].repo.split("/")[-1]


def fetch(raw_dir: Path = DEFAULT_RAW_DIR, keys: list[str] | None = None) -> None:
    """Shallow-clone each pinned source into ``raw_dir`` (skips ones already present)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    for key in keys or list(SOURCES):
        src = SOURCES[key]
        dest = source_dir(key, raw_dir)
        if dest.exists():
            print(f"{key}: already present at {dest}")
            continue
        print(f"{key}: cloning {src.repo} @ {src.tag}")
        subprocess.run(
            ["git", "clone", "-q", "--depth", "1", "--branch", src.tag, src.url, str(dest)],
            check=True,
        )
