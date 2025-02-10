from typing import List, Dict, Any
import google.generativeai as genai
import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGChatManager:
    def __init__(self, api_key: str, chunk_size: int = 500, overlap: int = 50):
        """
        Initialize the RAG-enabled chat manager using TF-IDF instead of neural embeddings
        
        Args:
            api_key: Google API key
            chunk_size: Size of text chunks for splitting document
            overlap: Overlap between chunks to maintain context
        """
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chat_history: List[Dict[str, str]] = []
        
        # RAG-specific components
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2)
        )
        self.document_chunks = []
        self.chunk_vectors = None

    def _split_into_chunks(self, text: str) -> List[str]:
        """Split document into overlapping chunks"""
        chunks = []
        
        # Split by pages first
        pages = re.split(r'\[Page \d+\]\n', text)
        
        for page in pages:
            if not page.strip():
                continue
            
            sentences = re.split(r'(?<=[.!?])\s+', page)
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sentence_length = len(sentence)
                
                if current_length + sentence_length > self.chunk_size and current_chunk:
                    # Join the current chunk and add it to chunks
                    chunk_text = ' '.join(current_chunk)
                    if chunk_text.strip():
                        chunks.append(chunk_text)
                    
                    # Start new chunk with overlap
                    overlap_point = max(0, len(current_chunk) - 2)  # Keep last 2 sentences for context
                    current_chunk = current_chunk[overlap_point:]
                    current_length = sum(len(s) for s in current_chunk)
                
                current_chunk.append(sentence)
                current_length += sentence_length
            
            # Add the last chunk if it exists
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                if chunk_text.strip():
                    chunks.append(chunk_text)
        
        return chunks

    def set_document_content(self, content: str):
        """Process and store document content for RAG"""
        # Split document into chunks
        self.document_chunks = self._split_into_chunks(content)
        
        # Generate TF-IDF vectors for all chunks
        self.chunk_vectors = self.vectorizer.fit_transform(self.document_chunks)
        
        # Initialize chat with basic context
        self._initialize_chat()

    def _get_relevant_chunks(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve most relevant document chunks for the query"""
        # Generate query vector
        query_vector = self.vectorizer.transform([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.chunk_vectors)[0]
        
        # Get top-k chunk indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Return relevant chunks with their similarity scores
        return [
            f"[Relevance: {similarities[i]:.2f}] {self.document_chunks[i]}"
            for i in top_indices
        ]

    def _initialize_chat(self):
        """Initialize chat with basic system prompt"""
        system_prompt = """
        You are a helpful assistant that answers questions based on provided document excerpts.
        Guidelines:
        1. Answer questions based only on the provided context
        2. If the context doesn't contain enough information, say so clearly
        3. Provide specific references when possible
        4. Keep responses clear and concise
        5. If you're unsure about something, admit it
        """
        
        self.chat_history = [{"role": "system", "content": system_prompt}]

    async def ask_question(self, question: str) -> Dict[str, Any]:
        """Process a question using RAG and return a response"""
        try:
            if not self.document_chunks:
                return {
                    "error": "No document content available. Please upload a document first."
                }

            # Retrieve relevant chunks
            relevant_chunks = self._get_relevant_chunks(question)
            
            # Construct prompt with relevant context
            context = "\n\n".join(relevant_chunks)
            prompt = f"""
            Question: {question}
            
            Relevant document sections:
            {context}
            
            Please answer the question based on the provided document sections.
            """

            # Add to chat history
            self.chat_history.append({"role": "user", "content": prompt})

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
        """Clear chat history while maintaining document chunks and vectors"""
        self._initialize_chat()

    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the chat history excluding system prompt"""
        return [msg for msg in self.chat_history if msg["role"] != "system"]