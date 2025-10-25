"""
Authentication Routes
Handles user authentication, verification codes, and session management
"""

import logging
from fastapi import APIRouter, HTTPException

from api.schemas import (
    AuthRequestCodeRequest,
    AuthRequestCodeResponse,
    AuthVerifyCodeRequest,
    AuthVerifyCodeResponse,
    UpdateProfileRequest,
    UpdateProfileResponse
)
from models.user_auth import auth_db_instance as auth_db
from services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/request-code", response_model=AuthRequestCodeResponse)
async def request_verification_code(request: AuthRequestCodeRequest):
    """Request a verification code to be sent to email"""
    try:
        # Create or get user
        user = auth_db.create_or_get_user(request.email, request.display_name)
        
        # Generate verification code
        code = auth_db.create_verification_code(user['id'], expires_in_minutes=10)
        
        # Send email with code
        email_sent = email_service.send_verification_code(request.email, code, request.display_name)
        
        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to send verification email")
        
        return AuthRequestCodeResponse(
            success=True,
            message=f"Verification code sent to {request.email}. Check your email (or server logs in DEV MODE). Code: {code}",
            user_id=user['id']
        )
    except Exception as e:
        logger.error(f"❌ Failed to create verification code: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send verification code: {str(e)}")


@router.post("/verify-code", response_model=AuthVerifyCodeResponse)
async def verify_code(request: AuthVerifyCodeRequest):
    """Verify the code and create session"""
    try:
        # Verify code
        is_valid, user = auth_db.verify_code(request.email, request.code)
        
        if not is_valid or not user:
            return AuthVerifyCodeResponse(
                success=False,
                message="Invalid or expired verification code"
            )
        
        # Create session
        session_token = auth_db.create_session(user['id'], expires_in_days=30)
        
        logger.info(f"✅ User logged in: {request.email}")
        
        return AuthVerifyCodeResponse(
            success=True,
            message="Login successful",
            session_token=session_token,
            user={
                "id": user['id'],
                "email": user['email'],
                "display_name": user['display_name'],
                "is_verified": user['is_verified']
            }
        )
    except Exception as e:
        logger.error(f"❌ Code verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.post("/logout")
async def logout(session_token: str):
    """Logout and invalidate session"""
    try:
        auth_db.invalidate_session(session_token)
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"❌ Logout failed: {e}")
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


@router.get("/verify-session")
async def verify_session(session_token: str):
    """Verify if session is still valid"""
    try:
        user = auth_db.get_user_by_session(session_token)
        
        if user:
            return {
                "success": True,
                "user": {
                    "id": user['id'],
                    "email": user['email'],
                    "display_name": user['display_name'],
                    "is_verified": user['is_verified']
                }
            }
        else:
            return {"success": False, "message": "Invalid or expired session"}
    except Exception as e:
        logger.error(f"❌ Session verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session verification failed: {str(e)}")


@router.post("/update-profile", response_model=UpdateProfileResponse)
async def update_profile(request: UpdateProfileRequest):
    """Update user profile (display name)"""
    try:
        # Verify session first
        user = auth_db.get_user_by_session(request.session_token)
        
        if not user:
            return UpdateProfileResponse(
                success=False,
                message="Invalid or expired session"
            )
        
        # Update display name
        updated_user = auth_db.update_user_profile(user['id'], request.display_name)
        
        if updated_user:
            logger.info(f"✅ Profile updated for {user['email']}: {request.display_name}")
            return UpdateProfileResponse(
                success=True,
                message="Profile updated successfully",
                user={
                    "id": updated_user['id'],
                    "email": updated_user['email'],
                    "display_name": updated_user['display_name'],
                    "is_verified": updated_user['is_verified']
                }
            )
        else:
            return UpdateProfileResponse(
                success=False,
                message="Failed to update profile"
            )
    except Exception as e:
        logger.error(f"❌ Profile update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")


@router.get("/stats")
async def get_auth_stats():
    """Get authentication statistics"""
    try:
        stats = auth_db.get_user_stats()
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get auth stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
