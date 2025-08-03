from pydantic import BaseModel, Field
from typing import List

class Answers(BaseModel):
    """
    Represents a single answer option for a question.
    - Remove any enumeration or label symbols (e.g., 'a. ', 'b. ', 'א. ', etc.) from the answer text.
    - The answer should be clean and ready for display.
    """
    answer: str = Field(
        description=(
            "The answer text, with all enumeration or label symbols (such as 'a. ', 'b. ', 'א. ', etc.) removed. "
            "Ensure 100% accuracy in cleaning these symbols for clean display."
        )
    )

class Questions(BaseModel):
    """
    Represents a single closed question in the exam.
    - Copy the entire question text, including any associated data, graphs, or tables.
    - Answers must be cleaned as described in the Answers model.
    """
    question_number: int = Field(description="The question's number in the exam.")
    question_data: str = Field(
        description=(
            "The full question text. Do not cut any data. "
            "If the question includes additional data, graphs, tables, or any attachments, copy them as well. but dont include the answers options"
            """ **For code snippets or blocks:** If the content is clearly a code snippet, script, or preformatted text that represents code, wrap it in `<pre dir="ltr" style="text-align:left"><code>...</code></pre>` tags. This ensures proper formatting (monospace font, whitespace preservation). add also <br> to structure the code well. tabs should be kept as \t, and whitespace should be preserved for correct code alignment"""
        )
    )
    answers: List[Answers] = Field(
        description=(
            "A list of all possible answer options for the question. "
            "Remove any leading enumeration or label symbols (e.g., 'a. ', 'b. ', 'א. ', etc.) from each answer. "
            "Ensure answers are displayed cleanly."
        )
    )

    # correct_answer: str = Field(description="The first answer is the correct one (after cleaning).")
class TestMeta(BaseModel):
    test_description: str = Field(description=(
            "Extract the exam subject and date from the test data. "
            "Format the date as day/month/year. "
            "Display as: '$name of the exam with all of the data$ | $date of the exam$'."
        ))
    test_time: str = Field(description="get the exam time in the format of 'hh:mm' (24-hour format).")

class Main(BaseModel):
    """
    The main exam structure.
    - 'questions' should contain all closed questions with their cleaned answers.
    - 'test_data' should include the exam subject/description, date, and time.
    """
    questions: List[Questions] = Field(description="A list of all closed questions in the exam.")
    test_data: TestMeta = Field(description="Exam metadata: subject/description and date/time.")
