"""
FlakeRadar Team Backend Configuration
Supports both local (free) and team (paid) modes
Enhanced with enterprise team collaboration features
"""
from __future__ import annotations
import os
import json
import hashlib
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class FlakeRadarTier(Enum):
    FREE = "free"           # Local SQLite only
    TEAM = "team"           # Centralized backend + team collaboration
    ENTERPRISE = "enterprise"  # Full features + on-prem + advanced analytics

@dataclass
class TestExecution:
    """Single test execution record for team backend"""
    test_name: str
    class_name: str
    project: str
    environment: str
    build_id: str
    commit_sha: str
    timestamp: datetime
    duration: float
    status: str  # 'pass', 'fail', 'skip'
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    jenkins_url: Optional[str] = None
    ci_platform: str = 'unknown'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API submission"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class TeamAnalysisResult:
    """Analysis result from team backend with cross-environment data"""
    test_name: str
    total_executions: int
    failure_count: int
    environments: List[str]
    first_seen: datetime
    last_seen: datetime
    flakiness_score: float
    confidence_level: float
    is_flaky_global: bool
    is_flaky_local: bool
    affected_environments: List[str]
    recent_failures: List[Dict[str, Any]]
    team_impact_score: float
    cross_env_pattern: Optional[str] = None

@dataclass
class DashboardData:
    """Centralized dashboard data for team collaboration"""
    team_id: str
    organization: str
    total_runs: int
    total_tests: int
    flaky_tests_count: int
    environments: List[str]
    contributors: List[Dict[str, Any]]  # List of team members who contributed data
    recent_activity: List[Dict[str, Any]]  # Recent test runs by team members
    flakiness_trends: Dict[str, List[float]]  # Trends per environment
    top_flaky_tests: List[Dict[str, Any]]  # Most problematic tests across team
    environment_health: Dict[str, Dict[str, Any]]  # Health metrics per environment
    last_updated: datetime
    dashboard_url: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['last_updated'] = self.last_updated.isoformat()
        return data

@dataclass
class JenkinsIntegration:
    """Jenkins CI/CD integration data"""
    jenkins_url: str
    job_name: str
    build_number: int
    build_url: str
    workspace: str
    git_branch: str
    git_commit: str
    triggered_by: str
    build_duration: float
    build_status: str  # 'SUCCESS', 'FAILURE', 'UNSTABLE', 'ABORTED'
    
    @classmethod
    def from_jenkins_env(cls) -> 'JenkinsIntegration':
        """Create from Jenkins environment variables"""
        return cls(
            jenkins_url=os.getenv("JENKINS_URL", ""),
            job_name=os.getenv("JOB_NAME", "unknown"),
            build_number=int(os.getenv("BUILD_NUMBER", "0")),
            build_url=os.getenv("BUILD_URL", ""),
            workspace=os.getenv("WORKSPACE", ""),
            git_branch=os.getenv("GIT_BRANCH", "unknown"),
            git_commit=os.getenv("GIT_COMMIT", "unknown"),
            triggered_by=os.getenv("BUILD_USER", "jenkins"),
            build_duration=float(os.getenv("BUILD_DURATION", "0")) / 1000,  # Convert ms to seconds
            build_status=os.getenv("BUILD_STATUS", "UNKNOWN")
        )

@dataclass  
class TeamMember:
    """Information about a team member who contributed test data"""
    username: str
    display_name: str
    last_contribution: datetime
    total_runs: int
    environments_contributed: List[str]
    avatar_url: Optional[str] = None

@dataclass
class TeamConfig:
    """Enhanced configuration for team/enterprise features"""
    api_token: Optional[str] = None
    backend_url: str = "http://localhost:8000"
    team_id: Optional[str] = None
    environment: str = "default"
    organization: Optional[str] = None
    timeout: int = 30
    
    @classmethod
    def from_env(cls) -> 'TeamConfig':
        """Load team config from environment variables"""
        return cls(
            api_token=os.getenv("FLAKERADAR_TOKEN"),
            backend_url=os.getenv("FLAKERADAR_BACKEND_URL", "http://localhost:8000"),
            team_id=os.getenv("FLAKERADAR_TEAM_ID"),
            environment=os.getenv("FLAKERADAR_ENVIRONMENT", "default"),
            organization=os.getenv("FLAKERADAR_ORG"),
            timeout=int(os.getenv("FLAKERADAR_TIMEOUT", "30"))
        )
    
    @classmethod
    def from_token(cls, token: str, **kwargs) -> 'TeamConfig':
        """Create team config from token with optional overrides"""
        return cls(api_token=token, **kwargs)
    
    def is_team_mode(self) -> bool:
        """Check if team features are enabled"""
        return self.api_token is not None
    
    def validate_token(self) -> tuple[bool, FlakeRadarTier, str]:
        """
        Validate API token and determine tier
        Returns: (is_valid, tier, message)
        """
        if not self.api_token:
            return False, FlakeRadarTier.FREE, "No API token provided"
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/team/validate",
                headers={"Authorization": f"Bearer {self.api_token}"},
                json={"team_id": self.team_id, "org": self.organization},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                tier = FlakeRadarTier(data.get("tier", "team"))
                
                # Update team_id from server response if not already set
                if data.get("team_id") and not self.team_id:
                    self.team_id = data["team_id"]
                
                return True, tier, data.get("message", "Token valid")
            elif response.status_code == 401:
                return False, FlakeRadarTier.FREE, "Invalid API token"
            elif response.status_code == 403:
                return False, FlakeRadarTier.FREE, "Token expired or subscription inactive"
            else:
                return False, FlakeRadarTier.FREE, f"Token validation failed: {response.status_code}"
                
        except requests.RequestException as e:
            return False, FlakeRadarTier.FREE, f"Network error: {e}"

@dataclass
class Config:
    """Enhanced config supporting both local and team modes"""
    project: str
    mode: str = "local"
    results_glob: str = ""
    logs_glob: Optional[str] = None
    build_id: str = "local-run"
    commit_sha: str = "local"
    db_path: str = os.path.expanduser("~/.flakeradar/history.db")
    
    # Team features
    team_config: TeamConfig = None
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
    """Create config from CLI arguments with team support"""
    db_path = os.getenv("FLAKERADAR_DB_PATH", os.path.expanduser("~/.flakeradar/history.db"))
    
    config = Config(
        project=args.project,
        mode=args.mode,
        results_glob=args.results,
        logs_glob=args.logs,
        build_id=args.build,
        commit_sha=args.commit,
        db_path=db_path,
    )
    
    return config

class TeamBackend:
    """
    Enhanced API client for FlakeRadar team backend
    Provides enterprise team collaboration features
    """
    
    def __init__(self, team_config: TeamConfig):
        self.config = team_config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {team_config.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "FlakeRadar-Client/1.1.0"
        })
    
    def submit_test_results(self, executions: List[TestExecution]) -> bool:
        """
        Submit test execution results to team backend
        
        Args:
            executions: List of test execution records
            
        Returns:
            True if submission successful
        """
        try:
            payload = {
                'team_id': self.config.team_id,
                'environment': self.config.environment,
                'organization': self.config.organization,
                'timestamp': datetime.utcnow().isoformat(),
                'executions': [exec.to_dict() for exec in executions]
            }
            
            response = self.session.post(
                f"{self.config.backend_url}/api/v1/team/submit",
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code == 201:
                logger.info(f"Successfully submitted {len(executions)} test results")
                print(f"✅ Submitted {len(executions)} test results to team backend")
                return True
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded")
                print(f"⚠️  Rate limit exceeded, please try again later")
                return False
            else:
                logger.error(f"Failed to submit results: {response.status_code}")
                print(f"⚠️  Team submission failed: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to submit test results: {e}")
            print(f"⚠️  Team backend error: {e}")
            return False
    
    def get_team_analysis(self, project: str, test_names: List[str] = None) -> Dict[str, TeamAnalysisResult]:
        """
        Get cross-environment flakiness analysis for the team
        
        Args:
            project: Project name
            test_names: Optional list of specific tests to analyze
            
        Returns:
            Dictionary mapping test names to analysis results
        """
        try:
            params = {
                'team_id': self.config.team_id,
                'project': project,
                'environment': self.config.environment,
                'days': 30  # Analyze last 30 days
            }
            
            if test_names:
                params['tests'] = ','.join(test_names)
            
            response = self.session.get(
                f"{self.config.backend_url}/v1/analysis/team",
                params=params,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                results = {}
                
                for test_data in data.get('results', []):
                    result = TeamAnalysisResult(
                        test_name=test_data['test_name'],
                        total_executions=test_data['total_executions'],
                        failure_count=test_data['failure_count'],
                        environments=test_data['environments'],
                        first_seen=datetime.fromisoformat(test_data['first_seen']),
                        last_seen=datetime.fromisoformat(test_data['last_seen']),
                        flakiness_score=test_data['flakiness_score'],
                        confidence_level=test_data['confidence_level'],
                        is_flaky_global=test_data['is_flaky_global'],
                        is_flaky_local=test_data['is_flaky_local'],
                        affected_environments=test_data['affected_environments'],
                        recent_failures=test_data['recent_failures'],
                        team_impact_score=test_data['team_impact_score'],
                        cross_env_pattern=test_data.get('cross_env_pattern')
                    )
                    results[result.test_name] = result
                
                logger.info(f"Retrieved team analysis for {len(results)} tests")
                return results
            else:
                logger.error(f"Failed to get team analysis: {response.status_code}")
                return {}
                
        except requests.RequestException as e:
            logger.error(f"Failed to get team analysis: {e}")
            return {}
    
    
    def get_environment_comparison(self, project: str) -> Dict[str, Any]:
        """
        Get flakiness comparison across environments
        
        Args:
            project: Project name
            
        Returns:
            Environment comparison data
        """
        try:
            params = {
                'team_id': self.config.team_id,
                'project': project,
                'organization': self.config.organization
            }
            
            response = self.session.get(
                f"{self.config.backend_url}/v1/analysis/environments",
                params=params,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Retrieved environment comparison for {len(data.get('environments', []))} environments")
                return data
            else:
                logger.error(f"Failed to get environment comparison: {response.status_code}")
                return {}
                
        except requests.RequestException as e:
            logger.error(f"Failed to get environment comparison: {e}")
            return {}
    
    def get_team_dashboard_data(self) -> Dict[str, Any]:
        """
        Get data for team dashboard
        
        Returns:
            Dashboard data including trends, top offenders, team metrics
        """
        try:
            params = {
                'team_id': self.config.team_id,
                'organization': self.config.organization
            }
            
            response = self.session.get(
                f"{self.config.backend_url}/v1/dashboard/team",
                params=params,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get dashboard data: {response.status_code}")
                return {}
                
        except requests.RequestException as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {}

    def get_central_dashboard(self, project: str = None) -> Optional[DashboardData]:
        """
        Get centralized dashboard data that all team members can access
        
        Args:
            project: Optional project filter
            
        Returns:
            DashboardData object with team collaboration metrics
        """
        try:
            params = {
                'team_id': self.config.team_id,
                'organization': self.config.organization
            }
            
            if project:
                params['project'] = project
            
            response = self.session.get(
                f"{self.config.backend_url}/v1/dashboard/central",
                params=params,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                dashboard = DashboardData(
                    team_id=data['team_id'],
                    organization=data['organization'],
                    total_runs=data['total_runs'],
                    total_tests=data['total_tests'],
                    flaky_tests_count=data['flaky_tests_count'],
                    environments=data['environments'],
                    contributors=data['contributors'],
                    recent_activity=data['recent_activity'],
                    flakiness_trends=data['flakiness_trends'],
                    top_flaky_tests=data['top_flaky_tests'],
                    environment_health=data['environment_health'],
                    last_updated=datetime.fromisoformat(data['last_updated']),
                    dashboard_url=data['dashboard_url']
                )
                
                print(f"🎯 Central dashboard accessed: {dashboard.total_runs} runs from {len(dashboard.contributors)} contributors")
                return dashboard
            else:
                logger.error(f"Failed to get central dashboard: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Failed to get central dashboard: {e}")
            return None

    def get_team_members(self) -> List[TeamMember]:
        """
        Get list of team members who have contributed test data
        
        Returns:
            List of TeamMember objects
        """
        try:
            params = {
                'team_id': self.config.team_id,
                'organization': self.config.organization
            }
            
            response = self.session.get(
                f"{self.config.backend_url}/api/v1/team/members",
                params=params,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                members = []
                
                for member_data in data.get('members', []):
                    member = TeamMember(
                        username=member_data['username'],
                        display_name=member_data['display_name'],
                        last_contribution=datetime.fromisoformat(member_data['last_contribution']),
                        total_runs=member_data['total_runs'],
                        environments_contributed=member_data['environments_contributed'],
                        avatar_url=member_data.get('avatar_url')
                    )
                    members.append(member)
                
                print(f"👥 Found {len(members)} active team members")
                return members
            else:
                logger.error(f"Failed to get team members: {response.status_code}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Failed to get team members: {e}")
            return []

    def get_real_time_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get real-time activity feed of team test runs
        
        Args:
            limit: Maximum number of recent activities to fetch
            
        Returns:
            List of activity records
        """
        try:
            params = {
                'team_id': self.config.team_id,
                'organization': self.config.organization,
                'limit': limit
            }
            
            response = self.session.get(
                f"{self.config.backend_url}/v1/activity/feed",
                params=params,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                activities = data.get('activities', [])
                print(f"📈 Retrieved {len(activities)} recent team activities")
                return activities
            else:
                logger.error(f"Failed to get activity feed: {response.status_code}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Failed to get activity feed: {e}")
            return []

    def notify_test_run_complete(self, run_summary: Dict[str, Any]) -> bool:
        """
        Notify team members about completed test run via central dashboard
        
        Args:
            run_summary: Summary of the completed test run
            
        Returns:
            True if notification sent successfully
        """
        try:
            payload = {
                'team_id': self.config.team_id,
                'organization': self.config.organization,
                'environment': self.config.environment,
                'run_summary': run_summary,
                'timestamp': datetime.utcnow().isoformat(),
                'notification_type': 'test_run_complete'
            }
            
            response = self.session.post(
                f"{self.config.backend_url}/v1/notifications/send",
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                print(f"🔔 Team notification sent: {run_summary.get('total_tests', 0)} tests analyzed")
                return True
            else:
                logger.warning(f"Failed to send team notification: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.warning(f"Failed to send team notification: {e}")
            return False

    def get_dashboard_url(self, project: str = None) -> str:
        """
        Get URL to the centralized team dashboard
        
        Args:
            project: Optional project filter for dashboard
            
        Returns:
            Dashboard URL that team members can access
        """
        base_url = self.config.backend_url.replace('/api', '')  # Remove API path
        
        url = f"{base_url}/dashboard/{self.config.team_id}"
        
        if project:
            url += f"?project={project}"
            
        if self.config.organization:
            separator = "&" if "?" in url else "?"
            url += f"{separator}org={self.config.organization}"
            
        return url

    def submit_jenkins_results(self, executions: List[TestExecution], jenkins_data: JenkinsIntegration) -> bool:
        """
        Submit test execution results from Jenkins CI/CD pipeline
        
        Args:
            executions: List of test execution records
            jenkins_data: Jenkins build and environment information
            
        Returns:
            True if submission successful
        """
        try:
            payload = {
                'team_id': self.config.team_id,
                'environment': self.config.environment,
                'organization': self.config.organization,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'jenkins',
                'executions': [exec.to_dict() for exec in executions],
                'jenkins_integration': {
                    'jenkins_url': jenkins_data.jenkins_url,
                    'job_name': jenkins_data.job_name,
                    'build_number': jenkins_data.build_number,
                    'build_url': jenkins_data.build_url,
                    'workspace': jenkins_data.workspace,
                    'git_branch': jenkins_data.git_branch,
                    'git_commit': jenkins_data.git_commit,
                    'triggered_by': jenkins_data.triggered_by,
                    'build_duration': jenkins_data.build_duration,
                    'build_status': jenkins_data.build_status
                }
            }
            
            response = self.session.post(
                f"{self.config.backend_url}/v1/jenkins/submit",
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code == 201:
                logger.info(f"Successfully submitted Jenkins build {jenkins_data.build_number} results")
                print(f"✅ Jenkins build #{jenkins_data.build_number} submitted to team dashboard")
                print(f"🔗 Jenkins build: {jenkins_data.build_url}")
                return True
            elif response.status_code == 401:
                print(f"❌ Authentication failed - check your FLAKERADAR_TOKEN")
                return False
            elif response.status_code == 403:
                print(f"❌ Access denied - token may be expired or invalid")
                return False
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded")
                print(f"⚠️  Rate limit exceeded, please try again later")
                return False
            else:
                logger.error(f"Failed to submit Jenkins results: {response.status_code}")
                print(f"⚠️  Jenkins submission failed: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to submit Jenkins results: {e}")
            print(f"⚠️  Jenkins backend error: {e}")
            return False

    def get_jenkins_builds(self, project: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get Jenkins build history for a project
        
        Args:
            project: Project name
            limit: Maximum number of builds to retrieve
            
        Returns:
            List of Jenkins build records with test results
        """
        try:
            params = {
                'team_id': self.config.team_id,
                'project': project,
                'organization': self.config.organization,
                'limit': limit,
                'source': 'jenkins'
            }
            
            response = self.session.get(
                f"{self.config.backend_url}/v1/jenkins/builds",
                params=params,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                builds = data.get('builds', [])
                print(f"📊 Retrieved {len(builds)} Jenkins builds")
                return builds
            else:
                logger.error(f"Failed to get Jenkins builds: {response.status_code}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Failed to get Jenkins builds: {e}")
            return []

    def create_jenkins_dashboard_link(self, project: str) -> str:
        """
        Create dashboard link specifically for Jenkins integration
        
        Args:
            project: Project name for dashboard filtering
            
        Returns:
            Dashboard URL optimized for Jenkins CI/CD view
        """
        base_url = self.config.backend_url.replace('/api', '')
        url = f"{base_url}/jenkins-dashboard/{self.config.team_id}"
        
        params = []
        if project:
            params.append(f"project={project}")
        if self.config.organization:
            params.append(f"org={self.config.organization}")
        
        if params:
            url += "?" + "&".join(params)
            
        return url

    def submit_analysis(self, analysis_data: Dict[str, Any]) -> bool:
        """Submit analysis results to team backend (legacy method)"""
        try:
            # Add team metadata (preserve environment from analysis_data if provided)
            submit_data = {
                "team_id": self.config.team_id,
                "environment": analysis_data.get("environment", self.config.environment),
                "organization": self.config.organization,
                "timestamp": analysis_data.get("timestamp"),
                "source": "flakeradar-cli"
            }
            analysis_data.update(submit_data)
            
            response = self.session.post(
                f"{self.config.backend_url}/analysis/submit",
                json=analysis_data,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                print(f"✅ Analysis submitted to team backend")
                return True
            else:
                print(f"⚠️  Team submission failed: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            print(f"⚠️  Team backend error: {e}")
            return False

    def get_team_insights(self, project: str) -> Optional[Dict[str, Any]]:
        """Get team-wide insights for a project (legacy method)"""
        try:
            response = self.session.get(
                f"{self.config.backend_url}/insights/team",
                params={
                    "project": project,
                    "team_id": self.config.team_id,
                    "environment": self.config.environment
                },
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️  Failed to fetch team insights: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"⚠️  Team insights error: {e}")
            return None

    def get_cross_environment_data(self, test_name: str) -> Optional[Dict[str, Any]]:
        """Get flakiness data across all environments for a test (legacy method)"""
        try:
            response = self.session.get(
                f"{self.config.backend_url}/test/cross-env",
                params={
                    "test_name": test_name,
                    "team_id": self.config.team_id,
                    "organization": self.config.organization
                },
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except requests.RequestException as e:
            print(f"⚠️  Cross-environment data error: {e}")
            return None


def create_team_backend() -> Optional[TeamBackend]:
    """
    Create team backend client from environment configuration
    
    Returns:
        TeamBackend instance if team token is configured, None otherwise
    """
    config = TeamConfig.from_env()
    if not config.is_team_mode():
        return None
    
    backend = TeamBackend(config)
    
    # Verify token on initialization
    is_valid, tier, message = config.validate_token()
    if not is_valid:
        logger.warning(f"Team token verification failed: {message}")
        print(f"⚠️  Team features disabled: {message}")
        return None
    
    logger.info(f"Team backend initialized for team: {config.team_id}, environment: {config.environment}")
    print(f"🚀 Team mode activated: {tier.value.title()}")
    return backend


def convert_test_results_to_executions(test_results: List[Any], project: str, build_id: str, commit_sha: str, environment: str) -> List[TestExecution]:
    """
    Convert FlakeRadar test results to team backend execution format
    
    Args:
        test_results: List of TestCaseResult objects
        project: Project name
        build_id: CI build identifier
        commit_sha: Git commit SHA
        environment: Environment name
        
    Returns:
        List of TestExecution objects for team backend
    """
    executions = []
    
    for result in test_results:
        # Extract test name and class from full_name (e.g., "com.example.Class#method")
        parts = result.full_name.split('#')
        test_name = parts[-1] if len(parts) > 1 else result.full_name
        class_name = parts[0] if len(parts) > 1 else 'unknown'
        
        execution = TestExecution(
            test_name=test_name,
            class_name=class_name,
            project=project,
            environment=environment,
            build_id=build_id,
            commit_sha=commit_sha,
            timestamp=datetime.utcnow(),
            duration=(result.duration_ms or 0) / 1000.0,  # Convert ms to seconds
            status=result.status,
            error_message=result.error_message,
            error_type=result.error_type,
            stack_trace=result.error_details,
            jenkins_url=os.environ.get('BUILD_URL'),
            ci_platform=detect_ci_platform()
        )
        executions.append(execution)
    
    return executions


def detect_ci_platform() -> str:
    """Detect the CI platform from environment variables"""
    if os.environ.get('JENKINS_URL'):
        return 'jenkins'
    elif os.environ.get('GITHUB_ACTIONS'):
        return 'github_actions'
    elif os.environ.get('GITLAB_CI'):
        return 'gitlab_ci'
    elif os.environ.get('CIRCLECI'):
        return 'circleci'
    elif os.environ.get('TRAVIS'):
        return 'travis'
    else:
        return 'unknown'
