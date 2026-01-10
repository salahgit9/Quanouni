from app.services.database import get_supabase
from datetime import datetime
import asyncio

class AuditService:
    @staticmethod
    async def log_action(
        user_id: str,
        username: str,
        action: str,
        details: dict = None,
        resource: str = None,
        ip_address: str = None
    ):
        """
        Logs an action to the audit_logs table.
        This function should ideally be fire-and-forget or async to not block the main request.
        """
        try:
            supabase = get_supabase()
            
            payload = {
                "user_id": user_id,
                "username": username,
                "action": action,
                "details": details or {},
                "resource": resource,
                "ip_address": ip_address,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Using fire-and-forget approach or ensure it awaits depending on critical nature
            # For now, we await it to ensure it's written, but can be backgrounded.
            data = supabase.table("audit_logs").insert(payload).execute()
            return data
            
        except Exception as e:
            print(f"[AUDIT LOG ERROR] Failed to log action '{action}': {e}")
            # We do NOT raise the exception to avoid breaking the user flow
            return None

audit_service = AuditService()
