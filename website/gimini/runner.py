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
            """Extract all closed questions with answer options from the provided exam PDF.
            if its not a closed question, return (e.g , {"exam_name":"Physics Exam | 21/06/2025,"status": "error"} as JSON.

            Rules:
            - Copy the full question text, including any data, graphs, or tables.
            - Remove all enumeration or label symbols like "a. ", "b. ", "א. ", etc. from the answers.
            - Format code snippets or blocks with <pre dir="ltr" style="text-align:left"><code>...</code></pre> tags, preserving tabs and whitespace. Add <br> tags to maintain line breaks.
            - If the PDF is unrelated or does not contain exam questions, return {"test_data": "error"} as JSON.
            - The output must be valid JSON exactly matching this schema:
            - test_data: {
                test_description: string (e.g., "Physics Exam | 21/06/2025") Do not change the language of the exam name, keep it as is.
                test_time: string in Hours and minutes (e.g., "3:30 Hours")
                }
            - questions: list of objects with:
                - question_number: integer
                - question_data: string (full question text, excluding answers)
                - answers: list of objects each with:
                    - answer: string (clean answer text without enumeration)

            Example Input:
            Question 1: What is the speed of light?
            a. 3 x 10^8 m/s
            b. 1.5 x 10^8 m/s
            c. 9.8 m/s^2

            Example Output:
            {
            "test_data": {
                "test_description": "Physics Exam | 21/06/2025",
                "test_time": "3 Hours"
            },
            "questions": [
                {
                "question_number": 1,
                "question_data": "What is the speed of light?",
                "answers": [
                    {"answer": "3 x 10^8 m/s"},
                    {"answer": "1.5 x 10^8 m/s"},
                    {"answer": "9.8 m/s^2"}
                ]
                }
            ]
            }

            Now extract from the following PDF:"""
        )
        
        response = await client.aio.models.generate_content(  
            model="models/gemini-2.5-flash",
            contents=[types.Part.from_bytes(data=self.file, mime_type='application/pdf'), prompt],
            config={'response_mime_type': 'application/json', 'response_schema': Main}
        )
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
            if not data:
                return False
            
            return await self.shuffle_exam(data)
        
        except Exception as e:
            raise e
