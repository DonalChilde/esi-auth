import base64
import hashlib
import secrets
import string


def generate_code_challenge_and_verifier() -> tuple[str, str]:
    """Generate a PKCE code challenge and verifier.

    The verifier uses only RFC 7636 unreserved characters and length constraints.
    """
    allowed_chars = string.ascii_letters + string.digits + "-._~"

    # RFC 7636 requires code_verifier length to be between 43 and 128 chars.
    code_verifier = "".join(secrets.choice(allowed_chars) for _ in range(64))

    if not (43 <= len(code_verifier) <= 128):
        raise ValueError("PKCE code_verifier length must be between 43 and 128")

    if not all(ch in allowed_chars for ch in code_verifier):
        raise ValueError("PKCE code_verifier contains invalid characters")

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    return code_challenge, code_verifier
