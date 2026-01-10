from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.rag import rag_service
from app.services.audit import audit_service
from app.api.routes import get_current_user # To get user info

router = APIRouter()

# --- Models ---
class ConsultationRequest(BaseModel):
    situation: str

class PleadingRequest(BaseModel):
    case_data: Dict[str, Any]
    pleading_type: str = "défense"
    style: str = "formel"
    top_k: int = 30

class JurisprudenceRequest(BaseModel):
    legal_issue: str
    chamber: Optional[str] = None
    top_k: int = 20

# --- Endpoints ---

@router.post("/legal-consultant")
async def legal_consultant(request: ConsultationRequest, req: Request = None, current_user: dict = Depends(get_current_user)):
    """
    Legal Consultant Mode:
    Analyzes a user situation and provides structured legal advice.
    """
    try:
        # Basic validation
        if not request.situation or len(request.situation) < 5:
             raise HTTPException(status_code=400, detail="Situation description too short")
        
        # Call RAG Service
        # Note: 'consult' will be async wrapper or sync method called in threadpool if needed.
        # Since rag_service methods are currently sync (mostly), we might need to await if we make them async or just call them.
        # Based on previous code, they seem to be standard sync methods using `genai`. 
        # But FastAPI handles sync routes in threadpool. 
        # However, to be safe and future proof, we can define them as async if they do I/O.
        # For now, assuming they are sync, we just call them.
        
        # ACTUALLY: existing 'rag_service.answer_query' is blocking.
        # We will make the new methods blocking too for simplicity, FastAPI will run them in threadpool.
        
        result = rag_service.consult(request.situation)
        
        # Log Consultation
        await audit_service.log_action(
            user_id=current_user['id'],
            username=current_user.get('username', 'unknown'),
            action="CONSULTATION",
            details={"situation_snippet": request.situation[:100] + "..." if len(request.situation) > 100 else request.situation},
            ip_address=req.client.host if req else "unknown"
        )
        
        return result
    except Exception as e:
        print(f"Error in legal_consultant: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/legal/pleading")
async def generate_pleading(request: PleadingRequest, req: Request = None, current_user: dict = Depends(get_current_user)):
    """
    Legal Advocate Mode:
    Generates a formal legal pleading based on case facts.
    """
    try:
        result = rag_service.draft_pleading(
            case_data=request.case_data,
            pleading_type=request.pleading_type,
            style=request.style,
            top_k=request.top_k
        )
        
        # Log Pleading
        await audit_service.log_action(
            user_id=current_user['id'],
            username=current_user.get('username', 'unknown'),
            action="PLEADING_GENERATION",
            details={"pleading_type": request.pleading_type, "case_type": request.case_data.get("case_type", "unknown")},
            ip_address=req.client.host if req else "unknown"
        )
        
        return result
    except Exception as e:
        print(f"Error in generate_pleading: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/legal/jurisprudence")
async def search_jurisprudence(request: JurisprudenceRequest, req: Request = None, current_user: dict = Depends(get_current_user)):
    """
    Jurisprudence Mode:
    Searches specifically for court decisions/jurisprudence.
    """
    try:
        result = rag_service.search_jurisprudence(
            legal_issue=request.legal_issue,
            chamber=request.chamber,
            top_k=request.top_k
        )
        
        # Log Jurisprudence Search
        await audit_service.log_action(
            user_id=current_user['id'],
            username=current_user.get('username', 'unknown'),
            action="JURISPRUDENCE_SEARCH",
            details={"legal_issue": request.legal_issue, "chamber": request.chamber},
            ip_address=req.client.host if req else "unknown"
        )
        
        return result
    except Exception as e:
        print(f"Error in search_jurisprudence: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
