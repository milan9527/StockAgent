"""
认证模块 - 支持本地DB认证和Amazon Cognito
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User
from config.settings import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def authenticate_cognito(username: str, password: str) -> dict:
    """Authenticate via Amazon Cognito"""
    import boto3
    client = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)

    try:
        response = client.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )

        # Handle NEW_PASSWORD_REQUIRED challenge
        if response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            # Auto-respond with the same password for first login
            challenge_response = client.respond_to_auth_challenge(
                ClientId=settings.COGNITO_CLIENT_ID,
                ChallengeName="NEW_PASSWORD_REQUIRED",
                Session=response["Session"],
                ChallengeResponses={"USERNAME": username, "NEW_PASSWORD": password},
            )
            return {
                "success": True,
                "id_token": challenge_response["AuthenticationResult"]["IdToken"],
                "access_token": challenge_response["AuthenticationResult"]["AccessToken"],
            }

        return {
            "success": True,
            "id_token": response["AuthenticationResult"]["IdToken"],
            "access_token": response["AuthenticationResult"]["AccessToken"],
        }
    except client.exceptions.NotAuthorizedException:
        return {"success": False, "error": "用户名或密码错误"}
    except client.exceptions.UserNotFoundException:
        return {"success": False, "error": "用户不存在"}
    except client.exceptions.InvalidPasswordException as e:
        return {"success": False, "error": f"密码不符合要求: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def authenticate_user(username: str, password: str, db: AsyncSession) -> tuple[bool, str, Optional[User]]:
    """Authenticate user - try Cognito first, fallback to local DB"""

    # Try Cognito if configured
    if settings.COGNITO_USER_POOL_ID and settings.COGNITO_CLIENT_ID:
        cognito_result = authenticate_cognito(username, password)
        if cognito_result["success"]:
            # Ensure user exists in local DB (sync from Cognito)
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            if not user:
                user = User(
                    username=username,
                    email=f"{username}@cognito.local",
                    hashed_password=get_password_hash(password),
                    full_name=username,
                    risk_preference="moderate",
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            return True, "", user
        # If Cognito auth fails, don't fallback — return the error
        return False, cognito_result.get("error", "认证失败"), None

    # Local DB auth (when Cognito not configured)
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return False, "用户名或密码错误", None
    return True, "", user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user
