from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from ocr_back.process_pdf import PDFProcessor
from ocr_back.chat_with_pdf import ChatManager
from ocr_back.cv_matching import CVJDMatcher
from typing import List
import os
from dotenv import load_dotenv
import httpx
import PyPDF2
import io
import uvicorn

load_dotenv()

app = FastAPI()

# CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the PDF processor and chatbots
pdf_processor = PDFProcessor(os.getenv("GOOGLE_API_KEY"))
chat_bot = ChatManager(os.getenv("OPENAI_API_KEY"))
cv_matcher = CVJDMatcher(
    gemini_api_key=os.getenv("GOOGLE_API_KEY"), 
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# Configuration for real-time API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_ID = "gpt-4o-realtime-preview-2024-12-17"
VOICE = "sage"
OPENAI_SESSION_URL = "https://api.openai.com/v1/realtime/sessions"
OPENAI_API_URL = "https://api.openai.com/v1/realtime"
DEFAULT_INSTRUCTIONS = """You are an expert PDF assistant. Follow these rules:
1. Use only information from the uploaded PDF
2. If unsure, say you don't know
3. Reference page numbers when possible"""

# Global storage for PDF content
uploaded_pdf = None
uploaded_jd_content = None
uploaded_cvs_content = []
extracted_text = ""
current_pdf_content = None
current_pdf_pages = 0

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global uploaded_pdf, current_pdf_content, current_pdf_pages, extracted_text
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    uploaded_pdf = await file.read()
    
    # Extract text using PyPDF2 for real-time processing
    try:
        pdf_file = io.BytesIO(uploaded_pdf)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        pdf_text = ""
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            page_text = page.extract_text()
            pdf_text += f"[Page {page_num}]\n{page_text}\n\n"
        
        current_pdf_content = pdf_text
        current_pdf_pages = len(pdf_reader.pages)
        
        extracted_text = pdf_processor.extract_text_from_pdf(uploaded_pdf)
        # chat_bot.set_document_content(extracted_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing error: {str(e)}")
    
    return JSONResponse(content={"message": "PDF uploaded successfully"})

@app.post("/process-pdf")
async def process_pdf():
    global uploaded_pdf, extracted_text
    if not uploaded_pdf:
        raise HTTPException(status_code=400, detail="No PDF uploaded")
    
    extracted_info = await pdf_processor.process_pdf(uploaded_pdf)
    await chat_bot.set_document_content(extracted_text)
    
    return JSONResponse(extracted_info)

@app.post("/chat")
async def chat(request: Request):
    global extracted_text
    data = await request.json()
    question = data.get("question")
    
    if not question:
        raise HTTPException(status_code=400, detail="No question provided")
    
    if not extracted_text:
        raise HTTPException(status_code=400, detail="Please upload and process a document first")
    
    response = await chat_bot.ask_question(question)
    
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
    
    return JSONResponse(content={"response": response["response"]})

@app.post("/rtc-connect")
async def connect_rtc(request: Request):
    """Real-time WebRTC connection endpoint"""
    global current_pdf_content
    
    if not current_pdf_content:
        raise HTTPException(status_code=400, detail="Please upload a PDF first")
    
    try:
        client_sdp = await request.body()
        if not client_sdp:
            raise HTTPException(status_code=400, detail="No SDP provided")
        
        client_sdp = client_sdp.decode()
        
        # Generate instructions with PDF content
        instructions = f"{DEFAULT_INSTRUCTIONS}\n\nPDF Content:\n{current_pdf_content}"
        
        async with httpx.AsyncClient() as client:
            # Get ephemeral token
            token_res = await client.post(
                OPENAI_SESSION_URL,
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": MODEL_ID, 
                    "modalities": ["audio", "text"],
                    "voice": VOICE, 
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1",
                        "language": "en"
                    },
                }
            )
            
            if token_res.status_code != 200:
                raise HTTPException(status_code=500, detail="Token request failed")
            
            token_data = token_res.json()
            ephemeral_token = token_data.get('client_secret', {}).get('value', '')
            
            if not ephemeral_token:
                raise HTTPException(status_code=500, detail="Invalid token response")
            
            # Perform SDP exchange
            sdp_res = await client.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {ephemeral_token}",
                    "Content-Type": "application/sdp"
                },
                params={
                    "model": MODEL_ID,
                    "instructions": instructions,
                    "voice": VOICE,
                },
                content=client_sdp
            )
            
            return Response(
                content=sdp_res.content,
                media_type='application/sdp',
                status_code=sdp_res.status_code
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pdf-info")
async def get_pdf_info():
    global current_pdf_content, current_pdf_pages
    if not current_pdf_content:
        raise HTTPException(status_code=404, detail="No PDF uploaded")
    
    return JSONResponse(content={
        "pages": current_pdf_pages,
        "preview": current_pdf_content,
    })

@app.post("/clear-pdf")
async def clear_pdf():
    global uploaded_pdf, extracted_text, current_pdf_content, current_pdf_pages
    uploaded_pdf = None
    extracted_text = ""
    current_pdf_content = None
    current_pdf_pages = 0
    chat_bot.clear_history()
    return JSONResponse(content={"message": "PDF and chat history cleared"})

@app.post("/clear-chat")
async def clear_chat():
    chat_bot.clear_history()
    return JSONResponse(content={"message": "Chat history cleared"})

@app.post("/upload-jd")
async def upload_jd(file: UploadFile = File(...)):
    global uploaded_jd_content
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Just store the raw content without processing
    uploaded_jd_content = await file.read()
    
    # Extract basic info for confirmation only
    try:
        pdf_file = io.BytesIO(uploaded_jd_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        page_count = len(pdf_reader.pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF reading error: {str(e)}")
    
    print(f"Uploaded JD: {file.filename} ({page_count} pages)")
    
    return JSONResponse(content={
        "message": "Job description uploaded successfully", 
        "pages": page_count,
        "filename": file.filename
    })

@app.post("/upload-cvs")
async def upload_cvs(files: List[UploadFile] = File(...)):
    global uploaded_cvs_content
    
    uploaded_cvs_content = []
    file_info = []
    
    for file in files:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail=f"File {file.filename} must be a PDF")
        
        # Store raw PDF content without processing
        content = await file.read()
        
        # Extract basic info for confirmation only
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF reading error: {str(e)}")
        
        uploaded_cvs_content.append((content, file.filename))
        file_info.append({
            "filename": file.filename,
            "pages": page_count
        })
    
    return JSONResponse(content={
        "message": f"Successfully uploaded {len(files)} CVs",
        "cv_count": len(files),
        "files": file_info
    })

@app.post("/compare-cvs")
async def compare_cvs():
    global uploaded_jd_content, uploaded_cvs_content
    
    if not uploaded_jd_content:
        raise HTTPException(status_code=400, detail="Please upload a job description first")
    
    if not uploaded_cvs_content:
        raise HTTPException(status_code=400, detail="Please upload at least one CV first")
    
    # Clear previous results first to avoid duplicates
    cv_matcher.clear_all()
    
    # Process JD now (at comparison time)
    await cv_matcher.process_jd(uploaded_jd_content)
    
    # Process CVs now (at comparison time)
    await cv_matcher.process_cvs(uploaded_cvs_content)
    
    # Now compare the processed documents
    result = await cv_matcher.compare_documents()
    return JSONResponse(content=result)

@app.post("/clear-matching")
async def clear_matching():
    global uploaded_jd_content, uploaded_cvs_content
    uploaded_jd_content = None
    uploaded_cvs_content = []
    cv_matcher.clear_all()
    return JSONResponse(content={"message": "All documents cleared"})

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)