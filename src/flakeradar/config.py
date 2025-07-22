from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional
from .team_backend import TeamConfig, FlakeRadarTier

@dataclass
class Config:
    project: str
    mode: str = "local"
    results_glob: str = ""
    logs_glob: Optional[str] = None
    build_id: str = "local-run"
    commit_sha: str = "local"
    db_path: str = os.path.expanduser("~/.flakeradar/history.db")
    
    # Team features
    team_config: Optional[TeamConfig] = None
    tier: FlakeRadarTier = FlakeRadarTier.FREE
    
    def __post_init__(self):
        if self.team_config is None:
            self.team_config = TeamConfig.from_env()
        
        # Determine tier based on token
        if self.team_config.is_team_mode():
            is_valid, tier, message = self.team_config.validate_token()
            if is_valid:
                self.tier = tier
                print(f"✅ FlakeRadar {tier.value.title()} mode activated")
            else:
                print(f"⚠️  Team token invalid: {message}")
                print(f"📱 Falling back to Free tier (local mode)")
                self.tier = FlakeRadarTier.FREE
        else:
            print(f"📱 FlakeRadar Free tier (local mode)")

def config_from_cli(args) -> Config:
    db_path = os.getenv("FLAKERADAR_DB_PATH", os.path.expanduser("~/.flakeradar/history.db"))
    
    # Create team config with token if provided
    team_config = None
    if hasattr(args, 'team_token') and args.team_token:
        # Use provided token and local dev server
        team_config = TeamConfig.from_token(
            args.team_token, 
            backend_url="http://localhost:8000"
        )
        if hasattr(args, 'environment') and args.environment:
            team_config.environment = args.environment
    else:
        # Use environment variables or default
        team_config = TeamConfig.from_env()
        if hasattr(args, 'environment') and args.environment:
            team_config.environment = args.environment
    
    return Config(
        project=args.project,
        mode=args.mode,
        results_glob=args.results,
        logs_glob=args.logs,
        build_id=args.build,
        commit_sha=args.commit,
        db_path=db_path,
        team_config=team_config,
    )