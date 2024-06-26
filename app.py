from flask import Flask, request, jsonify, render_template, redirect, url_for
from werkzeug.utils import secure_filename  # Import secure_filename
from pymongo import MongoClient
import pdfplumber
from transformers import pipeline
import pandas as pd
import os

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client['syllabusReader']
collection = db['searchQueries']

qa_pipeline = pipeline('question-answering', model="bert-base-uncased")  # Change to a BERT model

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['syllabusFile']
    search_query = request.form['searchQuery']

    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)  # Secure the filename before saving
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))  # Save file to uploads directory
        pdf_text = extract_text_from_pdf(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        document = {
            'searchQuery': search_query,
            'content': pdf_text,
            'timestamp': pd.Timestamp.now(),
            'filename': filename  # Optionally, store the filename in MongoDB
        }
        collection.insert_one(document)
        return redirect(url_for('success'))
    return 'File format not supported', 400

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/search')
def search():
    return render_template('search.html')

@app.route('/ask', methods=['POST'])
def ask_question():
    question = request.form['question']
    pdf_content = collection.find().sort('timestamp', -1).limit(1)[0]['content']
    answer = qa_pipeline(question=question, context=pdf_content)
    return jsonify(answer)

def extract_text_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        text = ''
        for page in pdf.pages:
            text += page.extract_text()
    return text

if __name__ == '__main__':
    app.config['UPLOAD_FOLDER'] = 'uploads'  # Configure upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Create uploads directory if not exists
    print("Starting Flask server on http://localhost:8000")
    app.run(debug=True, port=8000)
