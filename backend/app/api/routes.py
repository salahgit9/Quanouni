from fastapi import APIRouter, UploadFile, File, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import jwt
from passlib.context import CryptContext
from app.services.ingestion import save_uploaded_file, process_document
from app.services.rag import rag_pipeline
from app.services.database import get_supabase
from app.core.config import settings

router = APIRouter()

# --- Security Config ---
SECRET_KEY = "YOUR_SECRET_KEY_CHANGE_IN_PROD" # Should be in .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Check for fake/legacy tokens for backward compatibility during migration
        if token.startswith("fake-jwt"):
             # Mock user based on token suffix
             username = "admin" if "admin" in token else "salah"
             return {"id": "legacy_id", "username": username, "role": "premium"}

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None:
            raise credentials_exception
        return {"id": user_id, "role": role}
    except jwt.PyJWTError:
        raise credentials_exception

# --- Models ---

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str
    email: Optional[str] = None
    role: str = "normal"

class CaseCreate(BaseModel):
    case_number: str
    case_type: str
    court: str
    defendant_name: Optional[str] = None
    plaintiff_name: Optional[str] = None
    charges: Optional[List[str]] = []
    facts: Optional[str] = ""
    notes: Optional[str] = ""

class CaseUpdate(BaseModel):
    case_number: Optional[str] = None
    case_type: Optional[str] = None
    court: Optional[str] = None
    defendant_name: Optional[str] = None
    plaintiff_name: Optional[str] = None
    charges: Optional[List[str]] = None
    facts: Optional[str] = None
    notes: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    filters: Optional[dict] = None
    skip_generation: bool = False

# --- Endpoints ---

@router.post("/register")
async def register(request: RegisterRequest):
    supabase = get_supabase()
    
    # Check if user exists
    existing = supabase.table("users").select("id").eq("username", request.username).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="اسم المستخدم موجود بالفعل")
    
    hashed_pw = get_password_hash(request.password)
    
    user_data = {
        "username": request.username,
        "password_hash": hashed_pw,
        "full_name": request.full_name,
        "email": request.email,
        "role": request.role
    }
    
    res = supabase.table("users").insert(user_data).execute()
    new_user = res.data[0]
    
    # Auto login
    access_token = create_access_token(data={"sub": new_user['id'], "role": new_user['role']})
    
    return {
        "success": True,
        "token": access_token,
        "user": {
            "username": new_user['username'],
            "full_name": new_user['full_name'],
            "role": new_user['role']
        }
    }

@router.post("/login")
async def login(request: LoginRequest):
    supabase = get_supabase()
    
    # Find user
    res = supabase.table("users").select("*").eq("username", request.username).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="اسم المستخدم أو كلمة المرور غير صحيحة")
    
    user = res.data[0]
    
    # Check password
    if not verify_password(request.password, user['password_hash']):
        raise HTTPException(status_code=400, detail="اسم المستخدم أو كلمة المرور غير صحيحة")
        
    access_token = create_access_token(data={"sub": user['id'], "role": user['role']})
    
    return {
        "success": True,
        "token": access_token,
        "user": {
            "username": user['username'],
            "full_name": user['full_name'],
            "role": user['role']
        }
    }

@router.get("/cases")
async def get_cases(current_user: dict = Depends(get_current_user)):
    """Get cases for current user only"""
    try:
        supabase = get_supabase()
        
        query = supabase.table("cases").select("*").order("created_at", desc=True)
        
        # Filter by user_id unless admin
        if current_user['role'] != 'admin':
            if current_user['id'] == 'legacy_id':
                 # Demo mode fallback: return all (or specific logic)
                 pass 
            else:
                query = query.eq("user_id", current_user['id'])
                
        response = query.execute()
        return {"cases": response.data, "total": len(response.data)}
    except Exception as e:
        print(f"Error fetching cases: {e}")
        return {"cases": [], "total": 0}

@router.get("/cases/{case_id}")
async def get_case(case_id: str, current_user: dict = Depends(get_current_user)):
    try:
        supabase = get_supabase()
        response = supabase.table("cases").select("*").eq("id", case_id).execute()
        
        if not response.data:
             raise HTTPException(status_code=404, detail="القضية غير موجودة")
        
        case = response.data[0]
        
        # Ensure ownership
        if current_user['role'] != 'admin' and current_user['id'] != 'legacy_id':
             if case.get('user_id') and case['user_id'] != current_user['id']:
                 raise HTTPException(status_code=403, detail="غير مصرح لك بالوصول لهذه القضية")
                 
        return {"case": case}
    except Exception as e:
        if "403" in str(e): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cases")
async def create_case(case_data: CaseCreate, current_user: dict = Depends(get_current_user)):
    try:
        supabase = get_supabase()
        payload = {
            "case_number": case_data.case_number,
            "case_type": case_data.case_type,
            "court": case_data.court,
            "defendant_name": case_data.defendant_name,
            "plaintiff_name": case_data.plaintiff_name,
            "charges": case_data.charges or [],
            "facts": case_data.facts or "",
            "notes": case_data.notes or "",
            "status": "جاري",
            "user_id": current_user['id'] if current_user['id'] != 'legacy_id' else None
        }
        response = supabase.table("cases").insert(payload).execute()
        return {"success": True, "case": response.data[0], "message": "تم إنشاء القضية بنجاح"}
    except Exception as e:
        print(f"Error creating case: {e}")
        raise HTTPException(status_code=500, detail=f"فشل إنشاء القضية: {str(e)}")

@router.put("/cases/{case_id}")
async def update_case(case_id: str, case_data: CaseUpdate, current_user: dict = Depends(get_current_user)):
    try:
        supabase = get_supabase()
        
        # Verify ownership first
        existing = supabase.table("cases").select("user_id").eq("id", case_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="القضية غير موجودة")
        
        if current_user['role'] != 'admin' and current_user['id'] != 'legacy_id':
            if existing.data[0].get('user_id') != current_user['id']:
                 raise HTTPException(status_code=403, detail="غير مصرح لك بتعديل هذه القضية")

        update_data = case_data.dict(exclude_unset=True)
        if not update_data:
             return {"success": False, "message": "لا توجد بيانات للتحديث"}
             
        update_data["updated_at"] = datetime.now().isoformat()
        
        response = supabase.table("cases").update(update_data).eq("id", case_id).execute()
        return {"success": True, "case": response.data[0], "message": "تم تحديث القضية بنجاح"}
    except Exception as e:
        if "403" in str(e): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cases/{case_id}")
async def delete_case(case_id: str, current_user: dict = Depends(get_current_user)):
    try:
        supabase = get_supabase()
        
         # Verify ownership first
        existing = supabase.table("cases").select("user_id").eq("id", case_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="القضية غير موجودة")
            
        if current_user['role'] != 'admin' and current_user['id'] != 'legacy_id':
            if existing.data[0].get('user_id') != current_user['id']:
                 raise HTTPException(status_code=403, detail="غير مصرح لك بحذف هذه القضية")

        response = supabase.table("cases").delete().eq("id", case_id).execute()
        return {"success": True, "message": "تم حذف القضية بنجاح"}
    except Exception as e:
         if "403" in str(e): raise e
         raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_rag(request: QueryRequest):
    # Public endpoint for RAG
    try:
        print(f"Received query: {request.query}, filters: {request.filters}, skip_gen: {request.skip_generation}")
        result = rag_pipeline(request.query, filters=request.filters, skip_generation=request.skip_generation)
        return result
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Upload remains public or should be secured? keeping public for verify scripts access
    file_path = save_uploaded_file(file)
    result = process_document(file_path)
    return {"message": "File processed successfully", "data": result}

@router.get("/documents")
async def get_documents():
    supabase = get_supabase()
    response = supabase.table("documents").select("*").order("upload_date", desc=True).execute()
    return {"documents": response.data}
