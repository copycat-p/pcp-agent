from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """
    v2 요구사항: Agent Auth Token 검증 (Bearer Token)
    """
    def __init__(self, expected_token: str):
        self.expected_token = expected_token
        self.security = HTTPBearer()

    async def verify_token(self, credentials: HTTPAuthorizationCredentials = None):
        if not credentials or credentials.credentials != self.expected_token:
            logger.warning("Unauthorized MCP request attempt with invalid or missing token.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing Agent Auth Token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return True
