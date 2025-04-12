from fastapi import HTTPException, Depends, Header
from typing import Optional
from webapp.db import get_supabase_client

# Initialize Supabase client

async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Remove 'Bearer ' prefix if present
        token = authorization.replace("Bearer ", "")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Verify the JWT token
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user.user
        
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) 