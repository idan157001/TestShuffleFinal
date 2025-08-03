import firebase_admin
from firebase_admin import credentials, db
import os 

FIREBASE_DB_URL = os.environ.get("FIREBASE_DATABASE_URL")
FIREBASE_JSON = os.environ.get("FIREBASE_JSON")


class UploadExamToDB():
    def __init__(self, user):
        self.MAX_EXAMS=6 # Maximum number of exams per user
        self.user = user
        self.user_id = user['sub']
        self.user_email = user.get('email')
        

        self.setup_connection()


    def setup_connection(self):
        """
        Initialize Firebase connection.
        """
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_JSON) #change it in production remind me
            firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})

    def pydantic_to_dict(self, obj):
        if isinstance(obj, list):
            return [self.pydantic_to_dict(i) for i in obj]
        if isinstance(obj, dict):
            return {k: self.pydantic_to_dict(v) for k, v in obj.items()}
        if hasattr(obj, "dict") and callable(obj.dict):
            return self.pydantic_to_dict(obj.dict())
        return obj
        
    async def save_to_firebase(self,file_hash, data, exam_name):

        """
        Save the exam data to Firebase.
        """
        self.file_hash = file_hash  
        self.data = self.pydantic_to_dict(data)  # Convert Pydantic model to dict
        self.exam_name = exam_name

        user_exams_ref = db.reference("exams").child(self.user_id)
        db.reference("exams").child(self.user_id).push({
            "exam_name": self.exam_name,
            "file_hash": self.file_hash,
            "data": self.data,
            "user_email": self.user_email
        })

    async def check_max_exams(self):
        """
        Check if the user has reached the maximum number of exams.
        """
    
        user_exams_ref = db.reference("exams").child(self.user_id)
        exams_data = user_exams_ref.get()

        # Check if fewer than 5 exams exist
        return len(exams_data or {}) < self.MAX_EXAMS
    
    async def exam_already_exists(self, file_hash):
        """
        Check if an exam with the same file hash already exists for the user.
        """
        exams_ref = db.reference("exams")
        user_exams = exams_ref.child(self.user_id).get() or {}
        for exam in user_exams.values():
            if exam.get("file_hash") == file_hash:
                return "Exam already exists"
    

        # Check all users' exams
        all_users_exams = exams_ref.get() or {}
        for user_id, exams in all_users_exams.items():
            for exam in exams.values():
                if exam.get("file_hash") == file_hash:
                    new_exam = exam.copy()
                    new_exam['user_email'] = self.user_email
                    db.reference("exams").child(self.user_id).push(new_exam)
                    return True

        return False
                    






class GetExamFromDB():
    def __init__(self, user=None):
        self.user = user
        self.user_id = user['sub'] if user else None
        self.setup_connection()

    def setup_connection(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_JSON)  # change it in production
            firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})

    def get_exams(self):
        """
        Retrieve exams from Firebase for the user.
        """
        if not self.user_id:
            raise ValueError("User ID is required to get exams for a user.")
        exams_ref = db.reference("exams").child(self.user_id)
        return exams_ref.get() or {}

    def get_exam_details_by_exam_id(self, exam_id):
        """
        Search all users' exams for a given exam_id.
        """
        exams_ref = db.reference("exams")
        all_users_exams = exams_ref.get() or {}

        for user_id, exams in all_users_exams.items():
            if exams and exam_id in exams:
                return exams[exam_id]
        return {}
    
    def delete_exam(self, exam_id):
        """
        Delete an exam by exam_id for the user.
        """
        if not self.user_id:
            raise ValueError("User ID is required to delete an exam.")
        
        if self.user_id and exam_id:
            try:
                exam_ref = db.reference("exams").child(self.user_id).child(exam_id)
                exam_ref.delete()
                return True
            except Exception as e:
                raise ValueError(f"An error occurred while deleting the exam: {str(e)}")
