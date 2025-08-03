from google import genai
from google.genai import types
from .instructions import Main
import random
import copy
import os
client = genai.Client(api_key=os.environ.get('GIMINI_API_KEY'))


class Gimini_Proccess():
    def __init__(self, file):
        self.file = file

    async def run(self):
        prompt = (
            "Extract the structured data from the following PDF. "
            "Extract all of the closed questions that have options to answer. "
            "Don't change the language. If it's not an exam or the PDF is unrelated, return test_data=error."
        )
        
        response = await client.aio.models.generate_content(  
            model="models/gemini-2.5-flash",
            contents=[types.Part.from_bytes(data=self.file, mime_type='application/pdf'), prompt],
            config={'response_mime_type': 'application/json', 'response_schema': Main}
        )
        if response.parsed.test_data == 'error':
            return False
        return response.parsed


    async def shuffle_exam(self, data: Main):
        """Shuffles answers and returns data in a JSON-friendly format."""
        shuffled_questions = []
        # Access the Config object fields
        test_data = {
            "test_description": data.test_data.test_description,
            "test_time": data.test_data.test_time
        }
        for item in data.questions:
            question_number = item.question_number
            question_data = item.question_data
            correct_answer = item.answers[0]  # Corrected line.

            # Shuffle answers
            answers_list = copy.deepcopy(item.answers)
            random.shuffle(answers_list)
            item.answers = answers_list

            shuffled_questions.append({
                "question_number": question_number,
                "question_data": question_data,
                "answers": item.answers,
                "correct_answer": correct_answer,
            })

        return {
            "test_data": test_data,  # Now a dict with description and time
            "questions": shuffled_questions 
        }
    
    async def call_gimini_progress(self):
        """Sending Request to gimini and suffle the exam"""
        try:
            data = await self.run()
            if(not data):
                return False
            
            return await self.shuffle_exam(data)
        
        except Exception as e:
            raise e
