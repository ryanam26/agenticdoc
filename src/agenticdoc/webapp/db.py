from functools import lru_cache
import os
from fastapi import HTTPException
from supabase import create_client, Client

@lru_cache()
def get_supabase_client():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Supabase configuration missing")
    return create_client(supabase_url, supabase_key)