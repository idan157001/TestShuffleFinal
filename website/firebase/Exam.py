from . import db
import os


MAX_EXAMS = 6  # Maximum number of exams per user



def get_exams_ref():
    """Return the exams reference safely after initialization."""
    return db.reference("exams")


# --- Upload Exam Class ---
class UploadExamToDB:
    def __init__(self, user: dict):
        self.MAX_EXAMS = MAX_EXAMS
        self.user = user
        self.user_email = user.get('email')
        self.user_id = user['sub']  # User ID from the authentication token

        # Each user gets their own exams reference
        self.exams_ref = get_exams_ref().child(self.user_id)

    def get_user_exams(self):
        """Retrieve all exams for this user."""
        return self.exams_ref.get() or {}

    def pydantic_to_dict(self, obj):
        """Convert Pydantic model or other objects to a dictionary."""
        if isinstance(obj, list):
            return [self.pydantic_to_dict(i) for i in obj]
        if isinstance(obj, dict):
            return {k: self.pydantic_to_dict(v) for k, v in obj.items()}
        if hasattr(obj, "dict") and callable(obj.dict):
            return self.pydantic_to_dict(obj.dict())
        return obj

    async def save_to_firebase(self, file_hash: str, data, exam_name: str) -> str:
        """ 
        Save exam data to Firebase.
        Args:
            file_hash (str): Unique identifier for the exam file.
            data (Pydantic model): Data to be saved, should be a Pydantic model.
            exam_name (str): Name of the exam.
        """
        data_dict = self.pydantic_to_dict(data)  # Convert Pydantic model to dict
        exam_id = self.exams_ref.push({
            "exam_name": exam_name,
            "file_hash": file_hash,
            "data": data_dict,
            "user_email": self.user_email,
            "status": None
        })
        return exam_id.key  # Return the exam ID

    async def check_max_exams(self) -> bool:
        """Check if the user has reached the maximum number of exams."""
        user_exams = self.get_user_exams()
        return len(user_exams) < self.MAX_EXAMS

    async def same_exam_exists(self, file_hash: str) -> bool:
        """Check if an exam with the same file hash already exists for the user. If so, return True."""
        user_exams = self.get_user_exams()
        for exam in user_exams.values():
            if exam.get("file_hash") == file_hash:
                return True
        return False

    async def exam_exists_on_other_user(self, file_hash: str) -> bool:
        """
        Check if an exam with the same file hash exists for another user.
        If so, copy it to the current user.
        Uses Firebase indexing for fast lookup.
        """
        exams_ref = get_exams_ref()  # Global exams reference
        # Query exams where file_hash equals the given hash
        query_result = exams_ref.order_by_child("file_hash").equal_to(file_hash).get() or {}

        for exam_id, exam_data in query_result.items():
            # Skip exams already uploaded by this user
            if exam_data.get("user_id") != self.user_id:
                # Copy exam to current user
                new_exam = exam_data.copy()
                new_exam['user_email'] = self.user_email
                self.exams_ref.push(new_exam)
                return True  # Found and copied

        return False  # No matching exam found


# --- Get Exam Class ---
class GetExamFromDB:
    def __init__(self, user: dict = None):
        self.user = user
        self.user_id = user['sub'] if user else None
        # Each user gets their own exams reference
        self.exams_ref = get_exams_ref().child(self.user_id) if self.user_id else None

    def get_exams(self):
        """
        Retrieve exams from Firebase for the user.
        Raises:
            ValueError: If user_id is missing.
        """
        if not self.user_id:
            raise ValueError("User ID is required to get exams for a user.")
        return self.exams_ref.get() or {}

    def get_exam_details_by_exam_id(self, exam_id: str):
        """
        Search all users' exams for a given exam_id.
        Args:
            exam_id (str): ID of the exam to find.
        Returns:
            dict: Exam data if found, else empty dict.
        """
        all_exams = get_exams_ref().get() or {}
        for user_id, exams in all_exams.items():
            if exams and exam_id in exams:
                return exams[exam_id]
        return {}

    def delete_exam(self, exam_id: str) -> bool:
        """
        Delete an exam by exam_id for the user.
        Args:
            exam_id (str): ID of the exam to delete.
        Returns:
            bool: True if deletion succeeded, else raises ValueError
        """
        if not self.user_id:
            raise ValueError("User ID is required to delete an exam.")
        try:
            self.exams_ref.child(exam_id).delete()
            return True
        except Exception as e:
            raise ValueError(f"An error occurred while deleting the exam: {str(e)}")
