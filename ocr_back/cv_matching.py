# from typing import List, Dict
# import PyPDF2
# import io
# import spacy
# from pydantic import BaseModel
# from fastapi import HTTPException
# import re

# # Load spaCy model
# try:
#     nlp = spacy.load("en_core_web_sm")
# except:
#     raise ImportError("Please install spacy and download en_core_web_sm model: python -m spacy download en_core_web_sm")

# class MatchResult(BaseModel):
#     cv_name: str
#     match_percentage: float
#     matching_skills: List[str]
#     missing_skills: List[str]
#     experience_match: bool
#     education_match: bool
#     overall_summary: str

# class CVJDMatcher:
#     def __init__(self):
#         self.current_jd = None
#         self.current_cvs = []

#     def extract_text_from_pdf(self, pdf_content: bytes) -> str:
#         """Extract text from PDF content"""
#         try:
#             pdf_file = io.BytesIO(pdf_content)
#             pdf_reader = PyPDF2.PdfReader(pdf_file)
#             text = ""
#             for page in pdf_reader.pages:
#                 text += page.extract_text() + "\n"
#             return text
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"PDF processing error: {str(e)}")

#     def extract_skills(self, text: str) -> List[str]:
#         """Extract skills from text using spaCy and common patterns"""
#         doc = nlp(text.lower())
        
#         # Common skill-related patterns
#         skill_patterns = [
#             r'proficient in (.*?)\.',
#             r'experience with (.*?)\.',
#             r'skills: (.*?)\.',
#             r'technologies: (.*?)\.',
#             r'frameworks: (.*?)\.',
#             r'languages: (.*?)\.'
#         ]
        
#         skills = set()
        
#         # Extract skills using patterns
#         for pattern in skill_patterns:
#             matches = re.finditer(pattern, text.lower())
#             for match in matches:
#                 skills.update([skill.strip() for skill in match.group(1).split(',')])
        
#         # Extract technical terms using spaCy
#         for ent in doc.ents:
#             if ent.label_ in ['ORG', 'PRODUCT']:
#                 skills.add(ent.text.strip())
        
#         return list(skills)

#     def extract_experience(self, text: str) -> Dict:
#         """Extract experience information from text"""
#         doc = nlp(text.lower())
        
#         # Look for years of experience
#         experience_patterns = [
#             r'(\d+)[\+]?\s*(?:years?|yrs?)(?:\s+of)?\s+experience',
#             r'experience:\s*(\d+)[\+]?\s*(?:years?|yrs?)',
#         ]
        
#         years = 0
#         for pattern in experience_patterns:
#             matches = re.finditer(pattern, text.lower())
#             for match in matches:
#                 try:
#                     years = max(years, int(match.group(1)))
#                 except:
#                     continue
        
#         return {
#             "years": years,
#             "has_experience": years > 0
#         }

#     def extract_education(self, text: str) -> Dict:
#         """Extract education information from text"""
#         education_levels = {
#             'phd': 4,
#             'doctorate': 4,
#             'master': 3,
#             'bachelor': 2,
#             'undergraduate': 2,
#             'diploma': 1,
#             'certificate': 1
#         }
        
#         text_lower = text.lower()
#         max_level = 0
#         degrees = []
        
#         for edu, level in education_levels.items():
#             if edu in text_lower:
#                 max_level = max(max_level, level)
#                 degrees.append(edu)
        
#         return {
#             "level": max_level,
#             "degrees": degrees,
#             "has_degree": max_level > 0
#         }

#     def analyze_job_description(self, jd_text: str) -> dict:
#         """Extract key information from job description"""
#         return {
#             "required_skills": self.extract_skills(jd_text),
#             "required_experience": self.extract_experience(jd_text),
#             "required_education": self.extract_education(jd_text),
#             "full_text": jd_text
#         }

#     def analyze_cv(self, cv_text: str, filename: str) -> dict:
#         """Extract key information from CV"""
#         return {
#             "skills": self.extract_skills(cv_text),
#             "experience": self.extract_experience(cv_text),
#             "education": self.extract_education(cv_text),
#             "filename": filename,
#             "full_text": cv_text
#         }

#     def calculate_match(self, jd_analysis: dict, cv_analysis: dict) -> MatchResult:
#         """Calculate how well a CV matches the job description"""
#         # Calculate skill match
#         jd_skills = set(jd_analysis["required_skills"])
#         cv_skills = set(cv_analysis["skills"])
        
#         matching_skills = list(jd_skills.intersection(cv_skills))
#         missing_skills = list(jd_skills - cv_skills)
        
#         # Calculate skill match percentage
#         skill_match = len(matching_skills) / len(jd_skills) if jd_skills else 1.0
        
#         # Check experience match
#         jd_exp = jd_analysis["required_experience"]["years"]
#         cv_exp = cv_analysis["experience"]["years"]
#         experience_match = cv_exp >= jd_exp
        
#         # Check education match
#         jd_edu = jd_analysis["required_education"]["level"]
#         cv_edu = cv_analysis["education"]["level"]
#         education_match = cv_edu >= jd_edu
        
#         # Calculate overall match percentage
#         match_percentage = (
#             skill_match * 0.5 +
#             (1.0 if experience_match else 0.0) * 0.3 +
#             (1.0 if education_match else 0.0) * 0.2
#         ) * 100
        
#         # Generate summary
#         summary = (
#             f"Candidate matches {len(matching_skills)} out of {len(jd_skills)} required skills. "
#             f"{'Has' if experience_match else 'Lacks'} required experience. "
#             f"{'Meets' if education_match else 'Does not meet'} education requirements."
#         )
        
#         return MatchResult(
#             cv_name=cv_analysis["filename"],
#             match_percentage=round(match_percentage, 2),
#             matching_skills=matching_skills,
#             missing_skills=missing_skills,
#             experience_match=experience_match,
#             education_match=education_match,
#             overall_summary=summary
#         )

#     async def process_jd(self, file_content: bytes) -> dict:
#         """Process uploaded JD"""
#         jd_text = self.extract_text_from_pdf(file_content)
#         self.current_jd = {
#             "text": jd_text,
#             "analysis": self.analyze_job_description(jd_text)
#         }
#         return {"message": "Job description processed successfully"}

#     async def process_cvs(self, files_content: List[tuple]) -> dict:
#         """Process uploaded CVs"""
#         self.current_cvs = []
#         for content, filename in files_content:
#             cv_text = self.extract_text_from_pdf(content)
#             self.current_cvs.append({
#                 "filename": filename,
#                 "text": cv_text,
#                 "analysis": self.analyze_cv(cv_text, filename)
#             })
#         return {
#             "message": f"Successfully processed {len(files_content)} CVs",
#             "cv_count": len(files_content)
#         }

#     async def compare_documents(self) -> dict:
#         """Compare CVs against JD"""
#         if not self.current_jd:
#             raise HTTPException(status_code=400, detail="Please upload a job description first")
        
#         if not self.current_cvs:
#             raise HTTPException(status_code=400, detail="Please upload CVs first")
        
#         matches = []
#         for cv in self.current_cvs:
#             match_result = self.calculate_match(self.current_jd["analysis"], cv["analysis"])
#             matches.append(match_result)
        
#         # Sort matches by match percentage in descending order
#         matches.sort(key=lambda x: x.match_percentage, reverse=True)
        
#         return {
#             "matches": [match.dict() for match in matches],
#             "total_candidates": len(matches)
#         }

#     def clear_all(self):
#         """Clear all uploaded documents"""
#         self.current_jd = None
#         self.current_cvs = []

# from typing import List, Dict
# import PyPDF2
# import io
# import openai
# from pydantic import BaseModel
# from fastapi import HTTPException
# import asyncio
# from openai import AsyncOpenAI
# import json

# class MatchResult(BaseModel):
#     cv_name: str
#     match_percentage: float
#     matching_skills: List[str]
#     missing_skills: List[str]
#     experience_match: bool
#     education_match: bool
#     overall_summary: str
#     detailed_analysis: str

# class CVJDMatcher:
#     def __init__(self, api_key: str):
#         self.client = AsyncOpenAI(api_key=api_key)
#         self.current_jd = None
#         self.current_cvs = []

#     def extract_text_from_pdf(self, pdf_content: bytes) -> str:
#         """Extract text from PDF content"""
#         try:
#             pdf_file = io.BytesIO(pdf_content)
#             pdf_reader = PyPDF2.PdfReader(pdf_file)
#             text = ""
#             for page in pdf_reader.pages:
#                 text += page.extract_text() + "\n"
#             return text
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"PDF processing error: {str(e)}")

#     async def analyze_text_with_gpt(self, text: str, is_jd: bool = False) -> Dict:
#         """Analyze text using GPT to extract relevant information"""
        
#         if is_jd:
#             prompt = f"""Analyze this job description and extract the following information in JSON format:
#             1. required_skills (list): Technical and soft skills required
#             2. required_experience (dict): Years of experience required and any specific experience requirements
#             3. required_education (dict): Minimum education level and any specific degree requirements
#             4. key_responsibilities (list): Main job responsibilities
#             5. nice_to_have (list): Preferred but not required skills or qualifications

#             Job Description:
#             {text}
            
#             Provide the output in valid JSON format."""
#         else:
#             prompt = f"""Analyze this CV and extract the following information in JSON format:
#             1. skills (list): All technical and soft skills mentioned
#             2. experience (dict): Years of total experience and key experiences
#             3. education (dict): Highest education level and all degrees
#             4. key_achievements (list): Notable achievements
#             5. recent_roles (list): Recent job positions and responsibilities

#             CV Content:
#             {text}
            
#             Provide the output in valid JSON format."""

#         try:
#             response = await self.client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {"role": "system", "content": "You are an expert CV analyst. Provide output in valid JSON format only."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.1
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"GPT analysis error: {str(e)}")

#     async def match_cv_with_gpt(self, jd_analysis: dict, cv_analysis: dict) -> str:
#         """Use GPT to perform detailed matching analysis"""
#         prompt = f"""Compare this job description and CV and provide a detailed analysis:

#         Job Description Analysis:
#         {jd_analysis}

#         CV Analysis:
#         {cv_analysis}

#         Provide a detailed comparison including:
#         1. Skills match and gaps
#         2. Experience alignment
#         3. Education suitability
#         4. Overall match percentage
#         5. Specific strengths and weaknesses
#         6. Areas where the candidate exceeds requirements
#         7. Recommendations for the candidate

#         Format the response as JSON with these keys:
#         match_percentage (float), matching_skills (list of string), missing_skills (list of string), experience_match (boolean), education_match (boolean), detailed_analysis (string)"""

#         try:
#             response = await self.client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {"role": "system", "content": "You are an expert CV matcher. Provide detailed analysis in JSON format."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.3
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"GPT matching error: {str(e)}")

#     async def process_jd(self, file_content: bytes) -> dict:
#         """Process uploaded JD"""
#         jd_text = self.extract_text_from_pdf(file_content)
#         analysis = await self.analyze_text_with_gpt(jd_text, is_jd=True)
#         self.current_jd = {
#             "text": jd_text,
#             "analysis": analysis
#         }
#         return {"message": "Job description processed successfully", "analysis": analysis}

#     async def process_cvs(self, files_content: List[tuple]) -> dict:
#         """Process uploaded CVs"""
#         self.current_cvs = []
#         analyses = []
        
#         for content, filename in files_content:
#             cv_text = self.extract_text_from_pdf(content)
#             analysis = await self.analyze_text_with_gpt(cv_text)
#             self.current_cvs.append({
#                 "filename": filename,
#                 "text": cv_text,
#                 "analysis": analysis
#             })
#             analyses.append({"filename": filename, "analysis": analysis})
            
#         return {
#             "message": f"Successfully processed {len(files_content)} CVs",
#             "cv_count": len(files_content),
#             "analyses": analyses
#         }

#     async def compare_documents(self) -> dict:
#         """Compare CVs against JD using GPT"""
#         if not self.current_jd:
#             raise HTTPException(status_code=400, detail="Please upload a job description first")
        
#         if not self.current_cvs:
#             raise HTTPException(status_code=400, detail="Please upload CVs first")
        
#         matches = []
#         for cv in self.current_cvs:
#             match_analysis_str = await self.match_cv_with_gpt(
#                 self.current_jd["analysis"],
#                 cv["analysis"]
#             )
            
#             try:
#                 match_analysis = json.loads(match_analysis_str)
#             except json.JSONDecodeError as e:
#                 raise HTTPException(
#                     status_code=500, 
#                     detail=f"Failed to parse matching analysis for {cv['filename']}: {str(e)}"
#                 )
            
#             match_result = MatchResult(
#                 cv_name=cv["filename"],
#                 match_percentage=match_analysis["match_percentage"],
#                 matching_skills=match_analysis["matching_skills"],
#                 missing_skills=match_analysis["missing_skills"],
#                 experience_match=match_analysis["experience_match"],
#                 education_match=match_analysis["education_match"],
#                 overall_summary=f"Match: {match_analysis['match_percentage']}%",
#                 detailed_analysis=match_analysis["detailed_analysis"]
#             )
#             matches.append(match_result)
        
#         # Sort matches by match percentage in descending order
#         matches.sort(key=lambda x: x.match_percentage, reverse=True)
        
#         return {
#             "matches": [match.dict() for match in matches],
#             "total_candidates": len(matches)
#         }

#     def clear_all(self):
#         """Clear all uploaded documents"""
#         self.current_jd = None
#         self.current_cvs = []

from typing import List, Dict
import PyPDF2
import io
import google.generativeai as genai
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
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
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

    async def match_cv_with_gemini(self, jd_analysis: dict, cv_analysis: dict) -> str:
        """Use Gemini to perform detailed matching analysis"""
        prompt = """You are a professional CV matcher. Analyze the following job description and CV data.
        Return ONLY valid JSON with this exact structure, no other text:
        {
            "match_percentage": 85.5,
            "matching_skills": ["skill1", "skill2"],
            "missing_skills": ["skill3", "skill4"],
            "experience_match": true,
            "education_match": true,
            "detailed_analysis": "Detailed analysis text here"
        }

        Job Description Data:
        """ + json.dumps(jd_analysis) + """

        CV Data:
        """ + json.dumps(cv_analysis)

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3
                )
            )
            
            # Clean the response text to ensure it's valid JSON
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]  # Remove ```json and ``` if present
            response_text = response_text.strip()
            
            # Parse and validate JSON
            try:
                result = json.loads(response_text)
                # Ensure all required fields are present
                required_fields = ["match_percentage", "matching_skills", "missing_skills", 
                                 "experience_match", "education_match", "detailed_analysis"]
                for field in required_fields:
                    if field not in result:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Missing required field in matching analysis: {field}"
                        )
                return result
            except json.JSONDecodeError as e:
                # If JSON parsing fails, create a default response
                return {
                    "match_percentage": 0.0,
                    "matching_skills": [],
                    "missing_skills": ["Unable to parse skills"],
                    "experience_match": False,
                    "education_match": False,
                    "detailed_analysis": "Error analyzing CV: Invalid response format"
                }
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini matching error: {str(e)}")

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
        """Compare CVs against JD using Gemini"""
        if not self.current_jd:
            raise HTTPException(status_code=400, detail="Please upload a job description first")
        
        if not self.current_cvs:
            raise HTTPException(status_code=400, detail="Please upload CVs first")
        
        matches = []
        for cv in self.current_cvs:
            match_analysis = await self.match_cv_with_gemini(
                self.current_jd["analysis"],
                cv["analysis"]
            )
            
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