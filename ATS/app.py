from flask import Flask, render_template, request, jsonify
import os
import google.generativeai as genai
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import PyPDF2
from docx import Document

app = Flask(__name__)

# Load API key from .env file
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Gemini model
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create the upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def extract_text_from_docx(docx_path):
    text = ""
    try:
        document = Document(docx_path)
        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX: {e}")
    return text

def extract_text_from_txt(txt_path):
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading TXT: {e}")
        return ""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ats_analysis")
def ats_analysis():
    return render_template("ats_analysis.html")

@app.route("/analyze_resume", methods=["POST"])
def analyze_resume():
    job_description = request.form.get("job_description", "")
    resume_text = ""

    # Check if a file was uploaded
    if 'resume_file' in request.files:
        file = request.files['resume_file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            file_extension = filename.rsplit('.', 1)[1].lower()
            if file_extension == 'pdf':
                resume_text = extract_text_from_pdf(filepath)
            elif file_extension == 'docx':
                resume_text = extract_text_from_docx(filepath)
            elif file_extension == 'txt':
                resume_text = extract_text_from_txt(filepath)

            os.remove(filepath) # Clean up the uploaded file
        elif file:
            return jsonify({"analysis": "Invalid file type. Allowed types are: pdf, docx, txt"})
    elif 'resume_text' in request.form:
        resume_text = request.form['resume_text']

    if not resume_text or not job_description:
        return jsonify({"analysis": "Please provide both the resume and the job description."})

    try:
        prompt = f"""Analyze the following resume text against the following job description. Provide a comprehensive summary of how well the resume aligns with the job description, clearly highlighting key strengths and specific areas for improvement. Focus on matching skills, relevant experience, quantifiable achievements, and overall suitability for the role.

                Maintain a structured format for all replies using clearly highlighted headers. Format headers by placing them on their own line and using all caps with spaces between letters (like "S K I L L S   M A T C H").

                Resume Text: 
                {resume_text}

                Job Description:
                {job_description}

                Analysis:
                """
        response = model.generate_content(prompt)
        return jsonify({"analysis": response.text})

    except Exception as e:
        print("Error:", e)
        return jsonify({"analysis": f"API Error during resume analysis: {e}"})

@app.route("/analyze_ats", methods=["POST"])
def analyze_ats():
    resume_text = ""

    # Check if a file was uploaded
    if 'resume_file' in request.files:
        file = request.files['resume_file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            file_extension = filename.rsplit('.', 1)[1].lower()
            if file_extension == 'pdf':
                resume_text = extract_text_from_pdf(filepath)
            elif file_extension == 'docx':
                resume_text = extract_text_from_docx(filepath)
            elif file_extension == 'txt':
                resume_text = extract_text_from_txt(filepath)

            os.remove(filepath) # Clean up the uploaded file
        elif file:
            return jsonify({"analysis": "Invalid file type. Allowed types are: pdf, docx, txt"})
    elif 'resume_text' in request.form:
        resume_text = request.form['resume_text']

    if not resume_text:
        return jsonify({"analysis": "Please provide the resume for ATS analysis."})

    try:
        prompt = f"""Analyze the following resume text for Applicant Tracking System (ATS) compatibility. Provide a detailed assessment covering these aspects:
        
        1. Formatting: Is the resume using ATS-friendly formatting? Check for proper headings, standard fonts, and lack of complex layouts.
        2. Keywords: Does the resume include sufficient relevant keywords for the target industry/role?
        3. Structure: Is the resume properly structured with clear sections (Experience, Education, Skills)?
        4. Content: Does the content avoid elements that might confuse ATS (tables, headers/footers, images)?
        5. Optimization: Provide specific recommendations for improving ATS compatibility.
        6. Score: Give an estimated ATS compatibility score (0-100) based on the analysis.
        
        For each point, provide:
        - Current status (what's working well)
        - Potential issues
        - Specific improvement suggestions
        
        Resume Text:
        {resume_text}
        
        ATS Analysis:
        """
        response = model.generate_content(prompt)
        return jsonify({"analysis": response.text})

    except Exception as e:
        print("Error during ATS analysis:", e)
        return jsonify({"analysis": f"API Error during ATS analysis: {e}"})

@app.route("/ask_resume_question", methods=["POST"])
def ask_resume_question():
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "Please provide a question or try speaking again."})

    try:
        prompt = f"""Answer the following resume question clearly and concisely:
        
        Question: {question}
        
        Answer in this format:
        **Answer:** [your answer here]
        **Tips:** [additional tips if relevant]"""
        
        response = model.generate_content(prompt)
        return jsonify({"answer": response.text})
    except Exception as e:
        return jsonify({"answer": f"Error processing your question. Please try again. ({str(e)})"})



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')