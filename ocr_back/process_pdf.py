import base64
import logging
from typing import Dict, Any, List
import google.generativeai as genai
from PyPDF2 import PdfReader
import fitz
import io
from concurrent.futures import ThreadPoolExecutor
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, api_key: str):
        """Initialize the PDF processor with Google API key"""
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF using native extraction methods"""
        text = ""
        try:
            # First try native text extraction with PyPDF2
            pdf_reader = PdfReader(io.BytesIO(pdf_content))
            extracted_text = []
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text.append(page_text)
            
            text = "\n".join(extracted_text)
                
        except Exception as e:
            logger.error(f"Error in text extraction with PyPDF2: {str(e)}")
            try:
                text = self._extract_text_with_pymupdf(pdf_content)
            except Exception as pymupdf_error:
                logger.error(f"Both extraction methods failed: {str(pymupdf_error)}")
                raise
            
        return text

    def _extract_text_with_pymupdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF using PyMuPDF (fitz)"""
        text_parts = []
        doc = None
        
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text("text")
                    
                    if page_text.strip():
                        text_parts.append(page_text)
                        
                except Exception as e:
                    logger.error(f"Error processing page {page_num}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"PyMuPDF processing error: {str(e)}")
            raise
        finally:
            if doc:
                doc.close()
                
        return "\n".join(text_parts)
    
    def extract_information(self, text: str) -> Dict[str, Any]:
        """Extract all important information using Gemini"""
        prompt = """
        Analyze the following document text and extract all important information. 
        Return the information in a structured JSON format with key-value pairs.
        Focus on extracting key details and relevant information.

        in key-value pairs but value can be only list of strings, e.g.:
            "Title": "The Great Gatsby",
            "Author": "F. Scott Fitzgerald", "Francis Scott Key Fitzgerald",
            "Published": 1925,
            "Summary": "A novel about the American Dream and the Roaring Twenties."
        """

        try:
            response = self.model.generate_content(
                prompt + "\n\nDocument text:\n" + text,
                generation_config={
                    'temperature': 0.1,
                    'top_p': 0.8,
                    'top_k': 40,
                }
            )
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini")
                
            extracted_info = self._parse_gemini_response(response.text)
            return extracted_info
            
        except Exception as e:
            logger.error(f"Information extraction error: {str(e)}")
            return {
                "error": f"Failed to extract information: {str(e)}",
                "raw_text": text[:1000] + "..." if len(text) > 1000 else text
            }

    def format_value_as_string_list(self, value: Any) -> List[str]:
        """Convert any value into a list of strings"""
        if value is None:
            return []
            
        # If already a list, convert each item to string
        if isinstance(value, list):
            return [str(item) for item in value]
            
        # If dictionary, format it as a string with key-value pairs
        if isinstance(value, dict):
            formatted = ", ".join(f"{k}: {v}" for k, v in value.items())
            return [formatted]
            
        # Convert single values to a list with one string item
        return str(value)

    def format_complex_object(self, obj: Any) -> List[str]:
        """Format complex objects (like nested dictionaries) into strings"""
        if isinstance(obj, dict):
            return [", ".join(f"{k}: {v}" for k, v in obj.items())]
        elif isinstance(obj, list):
            # If list contains dictionaries, format each dictionary
            if any(isinstance(item, dict) for item in obj):
                return [", ".join(f"{k}: {v}" for k, v in item.items()) for item in obj if isinstance(item, dict)]
            else:
                return [str(item) for item in obj]
        else:
            return [str(obj)]

    def _parse_gemini_response(self, response: str) -> Dict[str, List[str]]:
        """Parse Gemini's response into a dictionary with list of strings values"""
        try:
            # Clean up the response text
            cleaned_response = response.strip()
            cleaned_response = cleaned_response.replace("```json", "").replace("```", "")
            
            try:
                # Parse JSON response
                parsed_data = json.loads(cleaned_response)
                
                # Convert all values to lists of strings
                formatted_result = {}
                for key, value in parsed_data.items():
                    if isinstance(value, list):
                        # Handle list of dictionaries or complex objects
                        if any(isinstance(item, (dict, list)) for item in value):
                            formatted_result[key] = []
                            for item in value:
                                formatted_result[key].extend(self.format_complex_object(item))
                        else:
                            # Simple list of values
                            formatted_result[key] = [str(item) for item in value]
                    else:
                        # Non-list values get converted to a single-item list
                        formatted_result[key] = self.format_value_as_string_list(value)
                
                return formatted_result
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {str(e)}")
                
                # Fallback parsing for malformed JSON
                result = {}
                current_key = None
                current_values = []
                
                for line in cleaned_response.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line.startswith('"') and ':' in line:
                        # If we were processing a previous key, save its values
                        if current_key is not None:
                            result[current_key] = current_values
                        
                        # Start new key
                        key, value = line.split(':', 1)
                        current_key = key.strip().strip('"')
                        current_values = []
                        
                        # Process value
                        value = value.strip().strip(',').strip()
                        if value.startswith('[') and value.endswith(']'):
                            # Handle array values
                            values = value[1:-1].split(',')
                            current_values.extend(self.format_value_as_string_list(v.strip()) for v in values)
                        else:
                            current_values.extend(self.format_value_as_string_list(value))
                
                # Don't forget to add the last key-value pair
                if current_key is not None:
                    result[current_key] = current_values
                
                return result

        except Exception as e:
            logger.error(f"Response parsing error: {str(e)}")
            return {"error": [f"Failed to parse response: {str(e)}"]}

        except Exception as e:
            logger.error(f"Response parsing error: {str(e)}")
            return {"error": f"Failed to parse response: {str(e)}"}

    async def process_pdf(self, pdf_content: bytes) -> Dict[str, Any]:
        """Process PDF and extract information"""
        try:
            extracted_text = self.extract_text_from_pdf(pdf_content)
            
            if not extracted_text.strip():
                raise ValueError("No text could be extracted from the PDF")
            
            extracted_info = self.extract_information(extracted_text)
            
            return extracted_info
            
        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "details": {
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            }