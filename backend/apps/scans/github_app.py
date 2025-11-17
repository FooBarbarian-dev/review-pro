"""
GitHub App authentication for ephemeral token generation (ADR-004).

Generates short-lived installation access tokens for secure repository access
in isolated Docker containers.
"""
import jwt
import time
import requests
import logging
from typing import Optional
from django.conf import settings
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GitHubAppAuth:
    """
    Generate ephemeral GitHub App tokens for secure repository access.

    GitHub App tokens expire after 15 minutes, providing strong security
    for worker containers per ADR-004.
    """

    def __init__(self):
        """Initialize GitHub App authentication."""
        self.app_id = settings.GITHUB_APP_ID
        self.private_key = settings.GITHUB_APP_PRIVATE_KEY
        self.installation_id = settings.GITHUB_APP_INSTALLATION_ID

        if not self.app_id or not self.private_key:
            logger.warning("GitHub App credentials not configured")

    def generate_app_token(self) -> str:
        """
        Generate JWT for GitHub App authentication.

        This token is used to authenticate as the GitHub App itself,
        and is then exchanged for an installation access token.

        Returns:
            JWT token string (valid for 10 minutes)

        Raises:
            ValueError: If credentials are not configured
            jwt.PyJWTError: If token generation fails
        """
        if not self.app_id or not self.private_key:
            raise ValueError("GitHub App credentials not configured")

        # JWT payload for GitHub App
        # See: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app
        now = int(time.time())
        payload = {
            'iat': now,  # Issued at time
            'exp': now + 600,  # Expires in 10 minutes (max allowed)
            'iss': self.app_id  # GitHub App ID
        }

        try:
            # Sign JWT with private key (RS256 algorithm)
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm='RS256'
            )

            logger.debug(f"Generated GitHub App JWT (expires at {datetime.fromtimestamp(payload['exp'])})")
            return token

        except jwt.PyJWTError as e:
            logger.error(f"Failed to generate GitHub App JWT: {e}")
            raise

    def generate_installation_token(
        self,
        installation_id: Optional[str] = None,
        repositories: Optional[list] = None,
        permissions: Optional[dict] = None
    ) -> dict:
        """
        Generate installation access token for repository access.

        Installation tokens are short-lived (15 minutes default) and provide
        scoped access to specific repositories.

        Args:
            installation_id: GitHub App installation ID (uses default if not provided)
            repositories: Optional list of repository names to limit access
            permissions: Optional dict of permissions (e.g., {"contents": "read"})

        Returns:
            Dictionary containing:
            - token: The installation access token
            - expires_at: ISO 8601 timestamp when token expires
            - permissions: Granted permissions
            - repository_selection: 'all' or 'selected'

        Raises:
            requests.RequestException: If API call fails
            ValueError: If credentials are not configured
        """
        if not installation_id:
            installation_id = self.installation_id

        if not installation_id:
            raise ValueError("GitHub App installation ID not configured")

        # Get GitHub App JWT
        app_token = self.generate_app_token()

        # API endpoint for creating installation token
        url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'

        headers = {
            'Authorization': f'Bearer {app_token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }

        # Request body (optional repository/permission scoping)
        body = {}
        if repositories:
            body['repositories'] = repositories
        if permissions:
            body['permissions'] = permissions

        try:
            logger.info(f"Requesting installation token for installation {installation_id}")

            response = requests.post(url, headers=headers, json=body, timeout=10)
            response.raise_for_status()

            token_data = response.json()

            logger.info(
                f"Generated installation token (expires at {token_data.get('expires_at')})"
            )

            return {
                'token': token_data['token'],
                'expires_at': token_data['expires_at'],
                'permissions': token_data.get('permissions', {}),
                'repository_selection': token_data.get('repository_selection', 'all')
            }

        except requests.RequestException as e:
            logger.error(f"Failed to generate installation token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    def get_repository_token(self, repository_name: str) -> str:
        """
        Generate token scoped to a specific repository.

        Args:
            repository_name: Repository name (e.g., "owner/repo")

        Returns:
            Installation access token string

        Raises:
            requests.RequestException: If API call fails
        """
        # Extract just the repo name if full name provided
        if '/' in repository_name:
            repo_name = repository_name.split('/')[-1]
        else:
            repo_name = repository_name

        token_data = self.generate_installation_token(
            repositories=[repo_name],
            permissions={'contents': 'read'}
        )

        return token_data['token']

    def validate_token(self, token: str) -> bool:
        """
        Validate that a token is still valid.

        Args:
            token: Installation access token

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Try to access GitHub API with the token
            url = 'https://api.github.com/user'
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github+json'
            }

            response = requests.get(url, headers=headers, timeout=5)
            return response.status_code == 200

        except requests.RequestException as e:
            logger.error(f"Token validation failed: {e}")
            return False

    def get_installation_repositories(
        self,
        installation_id: Optional[str] = None
    ) -> list:
        """
        Get list of repositories accessible to the installation.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            List of repository names
        """
        if not installation_id:
            installation_id = self.installation_id

        try:
            token_data = self.generate_installation_token(installation_id)
            token = token_data['token']

            url = 'https://api.github.com/installation/repositories'
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github+json'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            repositories = [repo['full_name'] for repo in data.get('repositories', [])]

            logger.info(f"Found {len(repositories)} accessible repositories")
            return repositories

        except requests.RequestException as e:
            logger.error(f"Failed to get installation repositories: {e}")
            return []


# Singleton instance
_github_app_instance = None


def get_github_app() -> GitHubAppAuth:
    """
    Get singleton GitHubAppAuth instance.

    Returns:
        GitHubAppAuth instance
    """
    global _github_app_instance

    if _github_app_instance is None:
        _github_app_instance = GitHubAppAuth()

    return _github_app_instance
