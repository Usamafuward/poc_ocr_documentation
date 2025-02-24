from typing import List, Dict
import PyPDF2
import io
import google.generativeai as genai
from openai import AsyncOpenAI
from pydantic import BaseModel
from fastapi import HTTPException
import json

class MatchResult(BaseModel):
    cv_name: str
    match_percentage: float
    matching_skills: List[str]
    missing_skills: List[str]
    experience_match: bool
    education_match: bool
    overall_summary: str
    detailed_analysis: str

class CVJDMatcher:
    def __init__(self, gemini_api_key: str, openai_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.current_jd = None
        self.current_cvs = []

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF processing error: {str(e)}")

    async def analyze_text_with_gemini(self, text: str, is_jd: bool = False) -> Dict:
        """Analyze text using Gemini to extract relevant information"""
        
        if is_jd:
            prompt = """You are a professional CV analyzer. Your task is to analyze the following job description and extract key information.
            Return ONLY valid JSON with this exact structure, no other text:
            {
                "required_skills": [],
                "required_experience": {},
                "required_education": {},
                "key_responsibilities": [],
                "nice_to_have": []
            }

            Job Description:
            """ + text
        else:
            prompt = """You are a professional CV analyzer. Your task is to analyze the following CV and extract key information.
            Return ONLY valid JSON with this exact structure, no other text:
            {
                "skills": [],
                "experience": {},
                "education": {},
                "key_achievements": [],
                "recent_roles": []
            }

            CV Content:
            """ + text

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1
                )
            )
            
            # Clean the response text to ensure it's valid JSON
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]  # Remove ```json and ``` if present
            response_text = response_text.strip()
            
            # Parse and validate JSON
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail="Invalid JSON response from Gemini")
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini analysis error: {str(e)}")

    async def process_jd(self, file_content: bytes) -> dict:
        """Process uploaded JD"""
        jd_text = self.extract_text_from_pdf(file_content)
        analysis = await self.analyze_text_with_gemini(jd_text, is_jd=True)
        self.current_jd = {
            "text": jd_text,
            "analysis": analysis
        }
        return {"message": "Job description processed successfully", "analysis": analysis}

    async def process_cvs(self, files_content: List[tuple]) -> dict:
        """Process uploaded CVs"""
        # Clear existing CVs to avoid duplicates
        self.current_cvs = []
        analyses = []
        
        for content, filename in files_content:
            cv_text = self.extract_text_from_pdf(content)
            analysis = await self.analyze_text_with_gemini(cv_text)
            self.current_cvs.append({
                "filename": filename,
                "text": cv_text,
                "analysis": analysis
            })
            analyses.append({"filename": filename, "analysis": analysis})
            
        return {
            "message": f"Successfully processed {len(files_content)} CVs",
            "cv_count": len(files_content),
            "analyses": analyses
        }

    async def compare_documents(self) -> dict:
        """Compare CVs against JD using OpenAI"""
        if not self.current_jd:
            raise HTTPException(status_code=400, detail="Please upload a job description first")
        
        if not self.current_cvs:
            raise HTTPException(status_code=400, detail="Please upload CVs first")
        
        # Create a set to track processed CV filenames to avoid duplicates
        processed_filenames = set()
        matches = []
        
        for cv in self.current_cvs:
            # Skip if we've already processed this filename
            if cv["filename"] in processed_filenames:
                continue
            
            processed_filenames.add(cv["filename"])
            
            # Rest of your existing comparison code...
            system_prompt = "You are a professional CV and job description matching assistant."
            user_prompt = f"""Analyze the following job description and CV data.
            Return ONLY valid JSON with this exact example structure, no other text:
            {{
                "match_percentage": exact matching float value 2 decimal places don't give 0.00 or 100.00,
                "matching_skills": Analyze full CV data and give matching skills list ["skill1", "skill2"],
                "missing_skills": Analyze full CV data and give missing skills list ["skill3", "skill4"],
                "experience_match": true,
                "education_match": true,
                "detailed_analysis": "Detailed analysis about CV matching text here"
            }}

            Job Description Data:
            {json.dumps(self.current_jd["analysis"])}

            CV Data:
            {json.dumps(cv["analysis"])}"""
            
            try:
                # Call OpenAI API using the new client API (v1.0.0+)
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1
                )
                
                # Extract and parse response
                response_text = response.choices[0].message.content.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:-3]  # Remove ```json and ``` if present
                response_text = response_text.strip()
                
                # Parse and validate JSON
                try:
                    match_analysis = json.loads(response_text)
                    # Ensure all required fields are present
                    required_fields = ["match_percentage", "matching_skills", "missing_skills", 
                                    "experience_match", "education_match", "detailed_analysis"]
                    for field in required_fields:
                        if field not in match_analysis:
                            raise HTTPException(
                                status_code=500,
                                detail=f"Missing required field in matching analysis: {field}"
                            )
                except json.JSONDecodeError:
                    # If JSON parsing fails, create a default response
                    match_analysis = {
                        "match_percentage": 0.0,
                        "matching_skills": [],
                        "missing_skills": ["Unable to parse skills"],
                        "experience_match": False,
                        "education_match": False,
                        "detailed_analysis": "Error analyzing CV: Invalid response format"
                    }
                    
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"OpenAI matching error: {str(e)}")
            
            match_result = MatchResult(
                cv_name=cv["filename"],
                match_percentage=match_analysis["match_percentage"],
                matching_skills=match_analysis["matching_skills"],
                missing_skills=match_analysis["missing_skills"],
                experience_match=match_analysis["experience_match"],
                education_match=match_analysis["education_match"],
                overall_summary=f"Match: {match_analysis['match_percentage']}%",
                detailed_analysis=match_analysis["detailed_analysis"]
            )
            matches.append(match_result)
        
        # Sort matches by match percentage in descending order
        matches.sort(key=lambda x: x.match_percentage, reverse=True)
        
        return {
            "matches": [match.dict() for match in matches],
            "total_candidates": len(matches)
        }

    def clear_all(self):
        """Clear all uploaded documents"""
        self.current_jd = None
        self.current_cvs = []