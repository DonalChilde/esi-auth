from collections.abc import Sequence

SSO_META_DATA_URL = "https://login.eveonline.com/.well-known/oauth-authorization-server"
JWK_ALGORITHM = "RS256"
JWK_ISSUERS = ("login.eveonline.com", "https://login.eveonline.com")
JWK_AUDIENCE = "EVE Online"
JWKS_URL = "https://login.eveonline.com/oauth/jwks"


def validate_eve_jwt(
    token: str,
    audience: str = JWK_AUDIENCE,
    issuer: str | Sequence[str] = JWK_ISSUERS,
    jwks_url: str = JWKS_URL,
) -> dict:
    """Validate an EVE Online JWT token.

    Args:
        token: The JWT token string to validate.
        audience: The expected audience claim.
        issuer: The expected issuer claim.

    Returns:
        The decoded token payload if valid.

    Raises:
        jwt.PyJWTError: If the token is invalid or verification fails.
    """
    import jwt
    from jwt import PyJWKClient

    # Fetch the JWKS
    jwk_client = PyJWKClient(jwks_url)
    signing_key = jwk_client.get_signing_key_from_jwt(token)

    # Decode and verify the token
    decoded_token = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer,
    )

    return decoded_token
