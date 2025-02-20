import logging
from fasthtml.common import *
from shad4fast import *
from starlette.datastructures import UploadFile
from starlette.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
import httpx
import uvicorn
from ocr_front.cv_chat import get_upload_card, get_information_display, get_rtc_chat_interface
from ocr_front.cv_matcher import get_cv_jd_section, get_comparison_results

load_dotenv()
if not os.path.exists("static"):
    os.makedirs("static")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app, rt = fast_app(
    pico=False,
    hdrs=(
        ShadHead(tw_cdn=True, theme_handle=False),
        Link(
            rel="stylesheet",
            href="/static/style.css",
            type="text/css"
        ),
        Script(
            src="/static/script.js",
            type="text/javascript",
            defer=True
        ),
    )
)

app.mount("/static", StaticFiles(directory="static"), name="static")

uploaded_pdf = None
extracted_text = ""
BACKEND_URL = os.getenv("BACKEND_URL")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting PDF Document Extractor application...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down PDF Document Extractor application...")
    global uploaded_pdf, extracted_text
    uploaded_pdf = None
    extracted_text = ""

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return Alert(
        AlertTitle("Error"),
        AlertDescription(f"An error occurred: {str(exc)}"),
        variant="destructive",
        cls="mt-4 backdrop-blur-sm glass"
    )
    
def get_tabs():
    """Generate the Tabs component for Document Extractor and CV Matcher"""
    return Tabs(
        TabsList(
            TabsTrigger(
                Div(Lucide("file-text", cls="w-4 h-4 mr-2"), "CV Extractor", cls="flex items-center"),
                value="document-extractor",
                cls="data-[state=active]:bg-zinc-800 data-[state=active]:text-white text-gray-400 hover:text-white"
            ),
            TabsTrigger(
                Div(Lucide("users", cls="w-4 h-4 mr-2"), "CV Matcher", cls="flex items-center"),
                value="cv-matcher",
                cls="data-[state=active]:bg-zinc-800 data-[state=active]:text-white text-gray-400 hover:text-white"
            ),
            cls="grid w-full grid-cols-2 bg-zinc-900 rounded-lg gap-1 border border-zinc-800"
        ),
        TabsContent(
            Div(
                get_upload_card(),
                Div(
                    get_information_display(),
                    get_rtc_chat_interface(),
                    cls="flex flex-cols-2 gap-6"
                ),
                cls="space-y-6"
            ),
            value="document-extractor",
            cls="space-y-7 transition-all duration-500 ease-in-out"
        ),
        TabsContent(
            Div(
                get_cv_jd_section(),
                Div(id="matching-results", cls="mt-6"),
                cls="space-y-6"
            ),
            value="cv-matcher",
            cls="space-y-7 transition-all duration-500 ease-in-out"
        ),
        default_value="document-extractor",
        cls="w-full max-w-7xl mx-auto space-y-7"
    )

@rt('/')
def get():
    return (
        Title("PDF CV Extractor & Matcher"),
        Script(f"window.BACKEND_URL = '{os.getenv('BACKEND_URL')}';"),  # Inject environment variable
        Body(
            Section(
                H1("PDF CV Extractor & Matcher",
                   cls="text-4xl font-bold tracking-tight text-center mb-6 text-white"),
                cls="container max-w-full mx-auto my-8"
            ),
            Section(
                get_tabs(),
                cls="container max-w-7xl mx-auto px-4 space-y-6 mb-6"
            ),
            cls="min-h-screen bg-black text-white"
        )
    )


@rt('/upload-pdf')
async def upload_pdf(req: Request):
    """Handle PDF upload"""
    if req.method != "POST":
        logger.warning(f"Invalid method {req.method} for upload")
        return Alert(
            AlertTitle("Error"),
            AlertDescription("Method not allowed"),
            variant="destructive"
        ), 405
    
    try:
        form = await req.form()
        pdf_field_name = "pdf_document"
        
        if pdf_field_name not in form:
            return Alert(
                AlertTitle("Error"),
                AlertDescription("No file field found in form"),
                variant="destructive"
            ), 400
            
        pdf = form[pdf_field_name]
        
        if not isinstance(pdf, UploadFile):
            return Alert(
                AlertTitle("Error"),
                AlertDescription("Invalid file upload"),
                variant="destructive"
            ), 400
            
        if not pdf.filename:
            return Alert(
                AlertTitle("Error"),
                AlertDescription("No file selected"),
                variant="destructive"
            ), 400
            
        # Send to FastAPI localhost
        files = {'file': (pdf.filename, await pdf.read(), 'application/pdf')}
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f'{BACKEND_URL}/upload-pdf', files=files)
            
        if response.status_code != 200:
            raise Exception(response.json().get('detail', 'Upload failed'))
            
        return Div(
            Script("document.getElementById('upload-container-pdf').style.display = 'none';"),
            get_information_display(),
            cls="mx-auto justify-center w-full"
        )
            
    except Exception as e:
        logger.error(f"Upload error for PDF: {str(e)}", exc_info=True)
        return Alert(
            AlertTitle("Upload Failed"),
            AlertDescription(str(e)),
            variant="destructive",
            cls="mt-4"
        ), 500

@rt('/process-pdf')
async def process_pdf(req: Request):
    """Process PDF to extract information"""
    try:
        print("Processing PDF")
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f'{BACKEND_URL}/process-pdf')
            print(response)
            
        if response.status_code != 200:
            raise Exception(response.json().get('detail', 'Processing failed'))
            
        extracted_info = response.json()
        
        return get_information_display(extracted_info=extracted_info)
    
    except Exception as e:
        logger.error(f"Process error for PDF: {str(e)}", exc_info=True)
        return Alert(
            AlertTitle("Processing Failed"),
            AlertDescription(str(e)),
            variant="destructive",
            cls="mt-4"
        ), 500

@rt('/clear-pdf')
async def clear_pdf(req: Request):
    """Clear uploaded PDF"""
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f'{BACKEND_URL}/clear-pdf')
            
        if response.status_code != 200:
            raise Exception(response.json().get('detail', 'Clear failed'))
        
        return Div(
            get_information_display(),
            Script("""
                document.getElementById('upload-container-pdf').style.display = 'block';
                document.getElementById('file-upload-pdf').value = '';
                document.getElementById('chat-messages').innerHTML = '';
                document.getElementById('audio-output').innerHTML = '';
            """),
            cls="mx-auto justify-center w-full"
        )
    except Exception as e:
        logger.error(f"Clear error for PDF: {str(e)}", exc_info=True)
        return Alert(
            AlertTitle("Clear Failed"),
            AlertDescription(str(e)),
            variant="destructive",
            cls="mt-4"
        ), 500

@rt('/chat')
async def chat(req: Request):
    """Handle chat interaction with the document"""
    try:
        data = await req.json()
        question = data.get("question")
        
        if not question:
            return {"error": "No question provided"}, 400
        
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f'{BACKEND_URL}/chat', json={"question": question})
            
        if response.status_code != 200:
            raise Exception(response.json().get('detail', 'Chat failed'))
            
        return response.json()
    
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500
    
@rt('/upload-jd')
async def upload_jd(req: Request):
    if req.method != "POST":
        return Alert(
            AlertTitle("Error"),
            AlertDescription("Method not allowed"),
            variant="destructive"
        ), 405
    
    try:
        form = await req.form()
        pdf_field_name = "job_description"
        
        if pdf_field_name not in form:
            return Alert(
                AlertTitle("Error"),
                AlertDescription("No file field found in form"),
                variant="destructive"
            ), 400
            
        jd_file = form[pdf_field_name]
            
        if not isinstance(jd_file, UploadFile):
            return Alert(
                AlertTitle("Error"),
                AlertDescription("Invalid file upload"),
                variant="destructive"
            ), 400
            
        files = {'file': (jd_file.filename, await jd_file.read(), 'application/pdf')}
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f'{BACKEND_URL}/upload-jd', files=files)
            
        if response.status_code != 200:
            raise Exception(response.json().get('detail', 'Upload failed'))
            
        return Div(
            Alert(
                AlertTitle("Success", cls="text-white"),
                AlertDescription("Job description analyzed successfully", cls="text-white"),
                variant="default",
                cls="bg-green-400/10 border-green-400/30 text-white mt-6",
                id="success-alert"
            ),
            Script("""
                resetButton('upload-jd-btn', 'Upload Job Description');
                document.getElementById('jd-upload-container').style.display = 'none';
                setTimeout(() => {
                    const alert = document.getElementById('success-alert');
                    if (alert) {
                        alert.style.opacity = '0';
                        alert.style.transform = 'translateY(-10px)';
                        alert.style.transition = 'all 0.3s ease-out';
                        setTimeout(() => alert.remove(), 300);
                    }
                }, 3000);
            """)
        )
            
    except Exception as e:
        logger.error(f"Upload error for JD: {str(e)}", exc_info=True)
        return Div(
            Alert(
                AlertTitle("Upload Failed"),
                AlertDescription(str(e)),
                variant="destructive"
            ),
            Script("resetButton('upload-jd-btn', 'Upload Job Description');")
        ), 500

@rt('/upload-cvs')
async def upload_cvs(req: Request):
    if req.method != "POST":
        return Alert(
            AlertTitle("Error"),
            AlertDescription("Method not allowed"),
            variant="destructive"
        ), 405
    
    try:
        form = await req.form()
        cv_files = form.getlist("cv_files")
        
        if not cv_files:
            return Alert(
                AlertTitle("Error"),
                AlertDescription("No CV files provided"),
                variant="destructive"
            ), 400
            
        files = []
        for cv_file in cv_files:
            if not isinstance(cv_file, UploadFile):
                continue
            files.append(('files', (cv_file.filename, await cv_file.read(), 'application/pdf')))
            
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f'{BACKEND_URL}/upload-cvs', files=files)
            
        if response.status_code != 200:
            raise Exception(response.json().get('detail', 'Upload failed'))
            
        result = response.json()
        print(result)
        return Div(
            Alert(
                AlertTitle("Success", cls="text-white"),
                AlertDescription(f"Successfully uploaded {result['cv_count']} CVs", cls="text-white"),
                variant="default",
                cls="bg-green-400/10 border-green-400/30 text-white mt-6",
                id="success-alert"
            ),
            Script("""
                resetButton('upload-cvs-btn', 'Upload CVs');
                document.getElementById('cv-upload-container').style.display = 'none';
                setTimeout(() => {
                    const alert = document.getElementById('success-alert');
                    if (alert) {
                        alert.style.opacity = '0';
                        alert.style.transform = 'translateY(-10px)';
                        alert.style.transition = 'all 0.3s ease-out';
                        setTimeout(() => alert.remove(), 300);
                    }
                }, 3000);
            """)
        )
            
    except Exception as e:
        logger.error(f"Upload error for CVs: {str(e)}", exc_info=True)
        return Div(
            Alert(
                AlertTitle("Upload Failed"),
                AlertDescription(str(e)),
                variant="destructive"
            ),
            Script("resetButton('upload-cvs-btn', 'Upload CVs');")
        ), 500

@rt('/compare-cvs')
async def compare_cvs(req: Request):
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f'{BACKEND_URL}/compare-cvs')
            
        if response.status_code != 200:
            raise Exception(response.json().get('detail', 'Comparison failed'))
            
        data = response.json()
        return Div(
            get_comparison_results(data["matches"]),
            Script("""
                const compareBtn = document.getElementById('compare-btn');
                const compareText = compareBtn.querySelector('.compare-btn-text');
                const compareLoading = compareBtn.querySelector('.compare-btn-loading');
                
                // Reset button state
                compareBtn.disabled = false;
                compareText.classList.remove('hidden');
                compareLoading.classList.add('hidden');
                
                // Remove any existing processing alerts with animation
                const alerts = document.querySelectorAll('.processing-alert');
                alerts.forEach(alert => {
                    alert.style.opacity = '0';
                    alert.style.transform = 'translateY(-10px)';
                    setTimeout(() => alert.remove(), 300);
                });
            """)
        )
    
    except Exception as e:
        logger.error(f"Comparison error: {str(e)}", exc_info=True)
        return Div(
            Alert(
                AlertTitle("Comparison Failed"),
                AlertDescription(str(e)),
                variant="destructive",
                cls="mt-4 backdrop-blur-sm"
            ),
            Script("""
                const compareBtn = document.getElementById('compare-btn');
                const compareText = compareBtn.querySelector('.compare-btn-text');
                const compareLoading = compareBtn.querySelector('.compare-btn-loading');
                
                compareBtn.disabled = false;
                compareText.classList.remove('hidden');
                compareLoading.classList.add('hidden');
            """)
        ), 500

@rt('/clear-matching')
async def clear_matching(req: Request):
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f'{BACKEND_URL}/clear-matching')
            
        if response.status_code != 200:
            raise Exception(response.json().get('detail', 'Clear failed'))
        
        return Div(
            Alert(
                AlertTitle("Success"),
                AlertDescription("All documents cleared successfully"),
                variant="default",
                cls="bg-green-400/10 border-green-400/30",
                id="success-alert"
            ),
            Script("""
                document.getElementById('jd-upload-container').style.display = 'block';
                document.getElementById('cv-upload-container').style.display = 'block';
                document.getElementById('file-upload-jd').value = '';
                document.getElementById('file-upload-cvs').value = '';
                setTimeout(() => {
                    const alert = document.getElementById('success-alert');
                    if (alert) {
                        alert.style.opacity = '0';
                        alert.style.transform = 'translateY(-10px)';
                        alert.style.transition = 'all 0.3s ease-out';
                        setTimeout(() => alert.remove(), 300);
                    }
                }, 3000);
            """)
        )
    
    except Exception as e:
        logger.error(f"Clear error: {str(e)}", exc_info=True)
        return Alert(
            AlertTitle("Clear Failed"),
            AlertDescription(str(e)),
            variant="destructive"
        ), 500

def run_server():
    """Run the server with proper configuration"""
    
    config = uvicorn.Config(
        "main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        workers=1,
        reload=True,
        timeout_keep_alive=None,
        loop="auto"
    )
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    run_server()
else:
    serve()
