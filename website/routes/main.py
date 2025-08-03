from fastapi import APIRouter, Depends, Cookie, HTTPException,status,UploadFile
from fastapi.responses import RedirectResponse, HTMLResponse,JSONResponse
from jose import jwt, JWTError
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
from typing import Optional

import os
import json
from fastapi.templating import Jinja2Templates
from fastapi import Request
from .. import templates

from ..utils.upload_file import FileUpload
from ..gimini.runner import Gimini_Proccess
from ..firebase.Exam import *
router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
JWT_SECRET = os.environ.get("JWT_SECRET")


def get_current_user(access_token: str = Cookie(None)):
    if not access_token:
        return None  # Not logged in
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=["HS256"])
        print(payload)
        return payload
    except JWTError:
        return None

@router.get("/", response_class=HTMLResponse)
def home(request: Request, user=Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse("/home.html",{ "request": request })

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(user=Depends(get_current_user), request: Request = None):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Not authenticated",
            headers={"Location": "/"}
        )
    user_exams = GetExamFromDB(user).get_exams()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "email": user.get("email"),
        "name": user.get("name", None),  
        "exams":user_exams if user_exams else []  # Pass exams to the template
    })


@router.get("/exam/{exam_id}", response_class=HTMLResponse)
async def exam_detail(user=Depends(get_current_user), request: Request = None, exam_id: str = None):
    """
    Display exam details and questions.
    """
    # Fetch exam details from the database
    exam_details = GetExamFromDB(user).get_exam_details_by_exam_id(exam_id)
    if not exam_details:
        raise HTTPException(status_code=404, detail="Exam not found")
    return templates.TemplateResponse("exam.html", {
        "request": request,
        "name": user.get("name") if user else None,  
        "exam": exam_details,})


@router.delete("/delete_exam/{exam_id}", response_class=JSONResponse)
async def delete_exam(user=Depends(get_current_user), exam_id: str = None):
    """
    Delete an exam by its ID.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Not authenticated",
            headers={"Location": "/"}
        )
    
    if not exam_id:
        raise HTTPException(status_code=400, detail="Exam ID is required")
    
    try:
        result =  GetExamFromDB(user).delete_exam(exam_id)
        if result:
            return JSONResponse(status_code=200, content={"detail": "Exam deleted successfully"})
        else:
            raise HTTPException(status_code=404, detail="Exam not found")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile, 
    request: Request, 
    user: Optional[dict] = Depends(get_current_user)
):
    """
    Handle PDF file upload with validation and Gemini processing.
    """
    # User check
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Not authenticated",
            headers={"Location": "/"}
        )

    try:
        # === File Type Validation ===
        if file.content_type != "application/pdf" or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only PDF files are allowed."
            )
        
        # === Read and Check File Size ===
        file_content = await file.read()
        file_size = len(file_content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."
            )
        
        # === Reset File Pointer (optional depending on use) ===
        await file.seek(0)

        #
        check_max_exams = await UploadExamToDB(user).check_max_exams()
        if not check_max_exams:
            raise HTTPException(
                status_code=403,
                detail="You can only upload up to 5 exams."
            )

        # === Process the file ===
        hashed_file = await FileUpload(file_content, file_size).hash_file()
        exam_exists = await UploadExamToDB(user).exam_already_exists(hashed_file)

        if exam_exists == "Exam already exists": # IF exam already exists in the user's exams
            raise HTTPException(
                status_code=400,
                detail="This Exam Already exits"
            )
        elif exam_exists is True: #if exam in database but not in user's exams
            raise HTTPException(
                status_code=200,
                detail="Exam Uploaded Successfully"
            )
        
        gimini_data = await Gimini_Proccess(file_content).call_gimini_progress()
        exam_name = gimini_data.get("test_data", {}).get("test_description", "Unknown Exam")
        
        # Save to database and get the exam ID
        exam_id = await UploadExamToDB(user).save_to_firebase(
            file_hash=hashed_file,
            data=gimini_data,
            exam_name=exam_name
        )
        
        # Return success with exam details for frontend
        return {
            "detail": "Upload successful",
            "examId": exam_id,  # Make sure your UploadExamToDB.save_to_firebase() returns the exam ID
            "examName": exam_name
        }

    except HTTPException as e:
        # Already well-formed, re-raise
        raise e

    except Exception as e:
        # Log the error optionally
        raise HTTPException(
            status_code=500,
            detail=f"An internal error occurred while processing the file: {str(e)}"
        )

    finally:
        await file.close()