import logging
from typing import List, Dict, Any
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self, api_key: str):
        """Initialize the chat bot with Google API key"""
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chat_history: List[Dict[str, str]] = []
        self.document_content = ""

    def set_document_content(self, content: str):
        """Set the document content for context"""
        self.document_content = content
        # Initialize chat with context
        self._initialize_chat()

    def _initialize_chat(self):
        """Initialize chat with document context"""
        system_prompt = f"""
        You are a helpful assistant that answers questions based on the provided document.
        Use the following document content as context for answering questions:

        {self.document_content}

        Guidelines:
        1. Answer questions based only on the information in the document
        2. If information is not in the document, say so clearly
        3. Provide specific references from the document when possible
        4. Keep responses clear and concise
        5. If you're unsure about something, admit it
        """
        
        self.chat_history = [{"role": "system", "content": system_prompt}]

    async def ask_question(self, question: str) -> Dict[str, Any]:
        """Process a question and return a response"""
        try:
            if not self.document_content:
                return {
                    "error": "No document content available. Please upload a document first."
                }

            # Add user question to history
            self.chat_history.append({"role": "user", "content": question})

            # Generate response
            response = self.model.generate_content([
                msg["content"] for msg in self.chat_history
            ])

            # Add response to history
            self.chat_history.append({"role": "assistant", "content": response.text})

            return {
                "response": response.text,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return {
                "error": f"Failed to process question: {str(e)}",
                "success": False
            }

    def clear_history(self):
        """Clear chat history but maintain document context"""
        self._initialize_chat()

    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the chat history excluding system prompt"""
        return [msg for msg in self.chat_history if msg["role"] != "system"]