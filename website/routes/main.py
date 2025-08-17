from fastapi import APIRouter, Depends, Cookie, HTTPException,status,UploadFile,BackgroundTasks,WebSocket,WebSocketDisconnect
from fastapi.responses import RedirectResponse, HTMLResponse,JSONResponse
from typing import Optional
import os 

import uuid
from fastapi.templating import Jinja2Templates
from fastapi import Request
from .. import templates

from ..utils.upload_file import FileUpload
from ..gimini.runner import Gimini_Proccess
from ..firebase.Exam import db, UploadExamToDB, GetExamFromDB
from ..utils.jobs import UploadExamJobs
from ..utils.auth import get_current_user
router = APIRouter()
from .. import connections
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
URL = os.environ.get("URL")




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
        "URL":URL,
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
    job_id = str(uuid.uuid4())

    uploader = UploadExamToDB(user)
    job = UploadExamJobs(job_id)
    check_max = await uploader.check_max_exams()
    file_hash = await FileUpload(file_content, file_size).hash_file()
    same_exam_exists_in_userDB= await uploader.same_exam_exists(file_hash)
    exam_exists_on_other_users = await uploader.exam_exists_on_other_user(file_hash)

    if not check_max:
        raise HTTPException(status_code=403, detail="You can only upload up to 6 exams.")
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 10MB")
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    if same_exam_exists_in_userDB:
        raise HTTPException(status_code=400, detail="This Exam Already exists")
    if exam_exists_on_other_users: # if exam already exists on other users set status to done      
        await job.set_job_status("done", user["sub"])
        return {"job_id": job_id, "status": "done"}
    

    await job.set_job_status("processing", user["sub"])
    background_tasks.add_task(job.process_and_notify, job_id, user, file_content, file_size, file_hash, file.filename)
    return {"job_id": job_id, "status": "processing"}





@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str, user: Optional[dict] = Depends(get_current_user)):
    """WebSocket endpoint to handle job status updates. receive keep alive messages from the frontend."""
    if not user:
        await websocket.close(code=1008)  # Policy Violation
        return
    job = UploadExamJobs(job_id)
    data = await job.get_job_status()
    if not data or data.get("user_id") != user["sub"]:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    connections[job_id] = websocket
    try:
        while True:
            message = await websocket.receive_text()  # keep alive
            if message == "ack":
                db.reference('jobs').child(job_id).delete()
                
    except WebSocketDisconnect:
        connections.pop(job_id, None)

@router.get("/job-status/{job_id}")
async def get_job_status_route(job_id: str, user: Optional[dict] = Depends(get_current_user)):
    """Get the status of a job by its ID."""

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    job = UploadExamJobs(job_id)
    data = await job.get_job_status()
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership
    if data.get("user_id") != user["sub"]:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this job")

    return data

