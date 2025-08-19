from .. import connections
from ..firebase import db
from ..firebase.Exam import UploadExamToDB
from ..gimini.runner import Gimini_Proccess
import asyncio
class UploadExamJobs:
    def __init__(self,job_id:str):
        self.job_id = job_id
        self.ref = db.reference(f'jobs/{self.job_id}')


    async def set_job_status(self, status: str, user_id: str, result: dict = None):
        data = {
            "status": status,
            "user_id": user_id
        }
        if result == "error":
            data["error"] = "An error occurred during processing"
        if result is not None:
            data["result"] = result
        await asyncio.to_thread(lambda: self.ref.set(data))

    async def get_job_status(self):
        return await asyncio.to_thread(lambda: self.ref.get())


    async def process_and_notify(self,job_id, user, file_content, file_size, file_hash, filename):
        uploader = UploadExamToDB(user)
        # Call Gemini processing
        try:
            gimini_data = await Gimini_Proccess(file_content).call_gimini_progress()
            if not gimini_data:
                raise ValueError("Exam Error")
            try:
                exam_name = gimini_data["test_data"]["test_description"]
            except KeyError:
                exam_name = "Unknown Exam"
            # Save exam to firebase with real data
            exam_id = await uploader.save_to_firebase(
                file_hash=file_hash,
                data=gimini_data,
                exam_name=exam_name
            )
            result = {"examId": exam_id, "examName": exam_name}
            
            # Update job status in DB
            job = UploadExamJobs(job_id)
            await job.set_job_status("done", user["sub"], result)
        
            # Notify frontend if connected and delete the job
            websocket = connections.get(job_id)
            if websocket:
                await websocket.send_text("done")
        
        except Exception as e:
            job = UploadExamJobs(job_id)
            # Handle any errors during processing
            await job.set_job_status("error", user["sub"], {"error": str(e)})
            websocket = connections.get(job_id)
            if websocket:
                await websocket.send_text("error")