"""Bearer authentication and OAuth resource-server verification (external IdP)."""

import asyncio
from collections import defaultdict, deque
import hashlib
import hmac
import time
import jwt
from starlette.responses import JSONResponse


class Auth:
    def __init__(self, base_url, api_key="", issuer="", audience="", jwks_url=""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.issuer = issuer
        self.audience = audience
        if not api_key and not (issuer and audience and jwks_url):
            raise ValueError(
                "Configure MANIM_API_KEY or complete OAuth issuer/audience/JWKS settings"
            )
        if api_key and len(api_key) < 32:
            raise ValueError("MANIM_API_KEY must contain at least 32 characters")
        if issuer and (
            not jwks_url.startswith("https://") or not issuer.startswith("https://")
        ):
            raise ValueError("OAuth issuer and JWKS require HTTPS")
        self.jwks = jwt.PyJWKClient(jwks_url, timeout=5) if jwks_url else None

    async def identity(self, header):
        if not header.startswith("Bearer "):
            raise ValueError("Authentication required")
        token = header[7:]
        if self.api_key and hmac.compare_digest(token, self.api_key):
            return "personal"
        if self.jwks:
            try:
                key = await asyncio.to_thread(self.jwks.get_signing_key_from_jwt, token)
                claims = jwt.decode(
                    token,
                    key.key,
                    algorithms=["RS256", "ES256"],
                    audience=self.audience,
                    issuer=self.issuer,
                    options={"require": ["exp", "iat", "sub", "iss", "aud"]},
                )
                if "animations:write" not in claims.get("scope", "").split():
                    raise ValueError("Required scope: animations:write")
                return hashlib.sha256(
                    (claims["iss"] + "|" + claims["sub"]).encode()
                ).hexdigest()
            except (jwt.PyJWTError, ValueError, TypeError) as e:
                raise ValueError("Invalid or expired access token") from e
        raise ValueError("Invalid access token")

    @property
    def challenge(self):
        if not self.issuer:
            return 'Bearer realm="Manim Animation"'
        return f'Bearer resource_metadata="{self.base_url}/.well-known/oauth-protected-resource"'

    def metadata(self):
        return {
            "resource": self.base_url + "/mcp",
            "authorization_servers": [self.issuer] if self.issuer else [],
            "scopes_supported": ["animations:write"],
            "bearer_methods_supported": ["header"],
        }


class Guard:
    def __init__(self, app, auth, per_minute=120):
        self.app = app
        self.auth = auth
        self.limit = per_minute
        self.requests = defaultdict(deque)
        self.ingress = deque()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/mcp"):
            return await self.app(scope, receive, send)
        now = time.monotonic()
        while self.ingress and now - self.ingress[0] > 60:
            self.ingress.popleft()
        if len(self.ingress) >= 600:
            return await JSONResponse(
                {"error": "Ingress rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "60"},
            )(scope, receive, send)
        self.ingress.append(now)
        headers = dict(scope["headers"])
        # Origin checks prevent browser cross-site invocation; MCP clients normally omit Origin.
        origin = headers.get(b"origin", b"").decode()
        if origin and origin != self.auth.base_url:
            return await JSONResponse({"error": "Origin not allowed"}, status_code=403)(
                scope, receive, send
            )
        try:
            owner = await self.auth.identity(
                headers.get(b"authorization", b"").decode()
            )
        except ValueError as e:
            return await JSONResponse(
                {"error": str(e)},
                status_code=401,
                headers={"WWW-Authenticate": self.auth.challenge},
            )(scope, receive, send)
        if scope["method"] != "POST":
            return await JSONResponse(
                {"error": "This stateless transport accepts POST only"},
                status_code=405,
                headers={"Allow": "POST"},
            )(scope, receive, send)
        if len(self.requests) > 1024:
            self.requests = defaultdict(
                deque,
                {k: v for k, v in self.requests.items() if v and now - v[-1] < 60},
            )
        q = self.requests[owner]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.limit:
            return await JSONResponse(
                {"error": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "60"},
            )(scope, receive, send)
        q.append(now)
        scope.setdefault("state", {})["owner"] = owner
        return await self.app(scope, receive, send)
