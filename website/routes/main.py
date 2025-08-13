from fastapi import APIRouter, Depends, Cookie, HTTPException,status,UploadFile,BackgroundTasks,WebSocket,WebSocketDisconnect
from fastapi.responses import RedirectResponse, HTMLResponse,JSONResponse
from jose import jwt, JWTError
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
from typing import Optional

import asyncio
import uuid
import os
import json
from fastapi.templating import Jinja2Templates
from fastapi import Request
from .. import templates

from ..utils.upload_file import FileUpload
from ..gimini.runner import Gimini_Proccess
from ..firebase.Exam import *
router = APIRouter()
connections = {}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
JWT_SECRET = os.environ.get("JWT_SECRET")


async def set_job_status(job_id: str, status: str, user_id: str, result: dict = None):
    ref = db.reference(f'jobs/{job_id}')
    data = {
        "status": status,
        "user_id": user_id
    }
    if result == "error":
        data["error"] = "An error occurred during processing"
    if result is not None:
        data["result"] = result
    ref.set(data)

async def get_job_status(job_id: str):
    ref = db.reference(f'jobs/{job_id}')
    data = ref.get()
    return data  # dict or None


def get_current_user(access_token: str = Cookie(None)):
    if not access_token:
        return None  # Not logged in
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=["HS256"])
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
    background_tasks: BackgroundTasks,
    file: UploadFile,
    request: Request = None,
    user: Optional[dict] = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    file_content = await file.read()
    file_size = len(file_content)

    uploader = UploadExamToDB(user)
    check_max = await uploader.check_max_exams()
    print(file_size)
    if not check_max:
        raise HTTPException(status_code=403, detail="You can only upload up to 6 exams.")
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 10MB")
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    

    file_hash = await FileUpload(file_content, file_size).hash_file()
    exam_exists = await uploader.exam_already_exists(file_hash)

    if exam_exists == "Exam already exists":
        raise HTTPException(status_code=400, detail="This Exam Already exists")

    job_id = str(uuid.uuid4())
    print(user)
    await set_job_status(job_id, "processing", user["sub"])

    # Start async job with all needed params
    background_tasks.add_task(process_and_notify, job_id, user, file_content, file_size, file_hash, file.filename)

    return {"job_id": job_id, "status": "processing"}

async def process_and_notify(job_id, user, file_content, file_size, file_hash, filename):
    uploader = UploadExamToDB(user)

    # Call Gemini processing
    try:
        gimini_data = await Gimini_Proccess(file_content).call_gimini_progress()
        if not gimini_data:
            return
        exam_name = gimini_data.get("test_data", {}).get("test_description", "Unknown Exam")

        # Save exam to firebase with real data
        exam_id = await uploader.save_to_firebase(
            file_hash=file_hash,
            data=gimini_data,
            exam_name=exam_name
        )

        result = {"examId": exam_id, "examName": exam_name}

        # Update job status in DB
        await set_job_status(job_id, "done", user["sub"], result)
    
        # Notify frontend if connected and delete the job
        websocket = connections.get(job_id)
        if websocket:
            await websocket.send_text("done")
      
    except Exception as e:
        # Handle any errors during processing
        await set_job_status(job_id, "error", user["sub"], {"error": str(e)})
        websocket = connections.get(job_id)
        if websocket:
            await websocket.send_text("error")


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str, user: Optional[dict] = Depends(get_current_user)):
    if not user:
        await websocket.close(code=1008)  # Policy Violation
        return

    # Check ownership on connect
    data = await get_job_status(job_id)
    if not data or data.get("user_id") != user["sub"]:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    connections[job_id] = websocket
    try:
        while True:
            message = await websocket.receive_text()  # keep alive
            if message == "ack":
                db.reference('jobs/{job_id}').delete()

    except WebSocketDisconnect:
        connections.pop(job_id, None)

@router.get("/job-status/{job_id}")
async def get_job_status_route(job_id: str, user: Optional[dict] = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    data = await get_job_status(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership
    if data.get("user_id") != user["sub"]:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this job")

    return data