# Exam Shuffler
A FastAPI web app that processes exam PDFs using an AI service (Gemini), extracts multiple-choice questions, shuffles answer order, and stores results in Firebase then allows users to test themself
https://testshufflefinal.onrender.com

## How it began
As a student, I noticed that all past exams available for practice were only provided as PDF files, with the first answer always being correct. This made self-testing ineffective, since I could easily recognize the correct answer’s position while practicing.

To address this issue—and help both myself and my fellow students—I developed a project that automatically extracts questions and answers from PDF exams, shuffles the answer order for each question, and presents randomized quizzes in a web interface. This allows for authentic exam practice, making it much easier to test our knowledge and prepare effectively.

## Features
- Upload PDF exams and extract closed (multiple-choice) questions.
- AI processing (Gemini) to parse exam content and format code blocks.
- Web UI for viewing exams and taking shuffled quizzes.

## Prerequisites
- Python 3.10+
- Firebase project and service account JSON
- Gemini (Gimini) API access

## Project layout (important files)
- website/             — FastAPI app code and templates
- website/templates    — Jinja2 templates (exam.html, base template, ...)
- website/static       — Static JS/CSS
- website/gimini       — AI prompt and runner code
- website/firebase     — Firebase helpers
- requirements.txt     — Python deps

