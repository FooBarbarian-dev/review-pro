"""
Custom social auth pipeline for GitHub OAuth.
Creates organization membership when user logs in via GitHub OAuth.
"""
from apps.organizations.models import Organization, OrganizationMembership


def create_organization_membership(backend, user, response, *args, **kwargs):
    """
    Create organization membership based on GitHub organization.
    This is called after the user is created/authenticated via GitHub OAuth.
    """
    if backend.name == 'github':
        # Get GitHub username and ID
        github_username = response.get('login')
        github_id = response.get('id')

        # Update user's GitHub info
        if github_username:
            user.github_username = github_username
        if github_id:
            user.github_id = str(github_id)

        # Get avatar URL
        avatar_url = response.get('avatar_url')
        if avatar_url:
            user.avatar_url = avatar_url

        user.save()

        # TODO: Fetch user's GitHub organizations and create/link to platform organizations
        # This would require additional GitHub API calls with proper permissions

    return {'user': user}
