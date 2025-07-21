from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    project: str
    mode: str = "local"
    results_glob: str = ""
    logs_glob: Optional[str] = None
    build_id: str = "local-run"
    commit_sha: str = "local"
    db_path: str = os.path.expanduser("~/.flakeradar/history.db")

def config_from_cli(args) -> Config:
    db_path = os.getenv("FLAKERADAR_DB_PATH", os.path.expanduser("~/.flakeradar/history.db"))
    return Config(
        project=args.project,
        mode=args.mode,
        results_glob=args.results,
        logs_glob=args.logs,
        build_id=args.build,
        commit_sha=args.commit,
        db_path=db_path,
    )