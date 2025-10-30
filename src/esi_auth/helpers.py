"""Helper functions for esi-auth package."""

from importlib import metadata


def get_user_agent(
    character_name: str, user_email: str, user_app_name: str, user_app_version: str
) -> str:
    """Construct the User-Agent string for HTTP requests."""
    user_portion = (
        f"{user_app_name}/{user_app_version} (eve:{character_name}; {user_email})"
    )
    app_metadata = metadata.metadata("esi-auth")
    app_name = app_metadata["name"]
    app_version = app_metadata["version"]
    app_source_url = get_package_url("esi-auth", "Source")
    _, author_email = get_author_email("esi-auth")
    esi_auth_portion = f"{app_name}/{app_version} ({author_email}; +{app_source_url})"
    return f"{user_portion} {esi_auth_portion}"


def get_package_url(package_name: str, url_name: str) -> str:
    """Get the project URL for a given package."""
    # TODO add to snippets.
    try:
        app_metadata = metadata.metadata(package_name)
        project_urls = app_metadata.get_all("Project-URL")
        if project_urls:
            # Project-URL can contain multiple URLs separated by commas
            urls = [url.split(",") for url in project_urls]
            for url in urls:
                if len(url) == 2 and url[0].strip().lower() == url_name.lower():
                    return url[1].strip()
        return "Unknown"
    except metadata.PackageNotFoundError:
        return "Unknown"


def get_author_email(package_name: str) -> tuple[str, str]:
    """Get the author email and name from package metadata."""
    # TODO add to snippets.
    try:
        app_metadata = metadata.metadata(package_name)
        app_author_email = app_metadata.get("Author-email", "Unknown")
        author_name, author_email = app_author_email.split(" <", 1)
        author_email = author_email.rstrip(">")
        return author_name, author_email
    except metadata.PackageNotFoundError:
        return "Unknown", "Unknown"
