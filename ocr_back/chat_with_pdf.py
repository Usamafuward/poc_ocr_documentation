import logging
from typing import List, Dict, Any
import openai
import faiss
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
from openai import AsyncOpenAI
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self, api_key: str):
        """Initialize the chat bot with OpenAI API key"""
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.chat_history: List[Dict[str, str]] = []
        self.document_content = ""
        self.index = None
        self.chunked_content = []
        self.batch_size = 20

    def chunk_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end > len(text):
                end = len(text)
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - chunk_overlap)
        return chunks

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError))
    )
    async def create_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        """Creates embeddings for a batch of texts."""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
                dimensions=1536
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error in batch embedding creation: {e}")
            raise

    async def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Creates embeddings for texts in batches."""
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            try:
                # Add timeout for each batch
                batch_embeddings = await asyncio.wait_for(
                    self.create_embedding_batch(batch),
                    timeout=30  # 30 seconds timeout per batch
                )
                all_embeddings.extend(batch_embeddings)
                
                # Add a small delay between batches to avoid rate limits
                await asyncio.sleep(0.2)
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout processing batch {i//self.batch_size + 1}")
                raise
            except Exception as e:
                logger.error(f"Error processing batch {i//self.batch_size + 1}: {e}")
                raise

        return np.array(all_embeddings, dtype='float32')

    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.IndexFlatIP:
        """Builds a FAISS index with progress logging."""
        start_time = time.time()
        logger.info("Starting FAISS index building...")
        
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)
        
        build_time = time.time() - start_time
        logger.info(f"FAISS index built in {build_time:.2f} seconds")
        return index

    async def set_document_content(self, content: str):
        """Set document content with progress tracking and timeout handling."""
        try:
            logger.info("Starting document processing...")
            
            # Step 1: Chunk text
            start_time = time.time()
            self.document_content = content
            self.chunked_content = self.chunk_text(self.document_content)
            logger.info(f"Text chunking completed: {len(self.chunked_content)} chunks created")
            
            # Step 2: Create embeddings with timeout
            logger.info("Creating embeddings...")
            embeddings = await self.create_embeddings(self.chunked_content)
            logger.info(f"Embeddings created for {len(embeddings)} chunks")
            
            # Step 3: Build FAISS index
            self.index = self.build_faiss_index(embeddings)
            
            total_time = time.time() - start_time
            logger.info(f"Document processing completed in {total_time:.2f} seconds")
            
        except asyncio.TimeoutError as e:
            logger.error("Document processing timed out")
            raise TimeoutError("Document processing timed out. Try with a smaller document or in chunks.") from e
        except Exception as e:
            logger.error(f"Error in document processing: {e}")
            raise

    async def retrieve_relevant_chunks(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieves the most relevant chunks from the document based on the query."""
        if self.index is None:
            logger.warning("FAISS index not built. Returning empty list.")
            return []

        try:
            # Await the embedding creation
            query_embeddings = await self.create_embeddings([query])
            query_embedding = query_embeddings[0].reshape(1, -1)

            D, I = self.index.search(query_embedding, top_k)
            relevant_chunks = [self.chunked_content[i] for i in I[0]]

            return relevant_chunks

        except Exception as e:
            logger.error(f"Error retrieving relevant chunks: {e}")
            raise

    async def ask_question(self, question: str) -> Dict[str, Any]:
        """Process a question and return a response."""
        try:
            if self.index is None:
                return {
                    "error": "No document content available. Please upload a document first.",
                    "success": False
                }

            # Await the retrieval of relevant chunks
            relevant_chunks = await self.retrieve_relevant_chunks(question)
            context = "\n".join(relevant_chunks)
            
            print("Context:", context)

            # Initialize the chat with the retrieved context
            self._initialize_chat(context)

            # Add user question to history
            self.chat_history.append({"role": "user", "content": question})

            # Generate response using OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in self.chat_history
                ],
                temperature=0.7,
                max_tokens=1000
            )

            # Extract the response text
            response_text = response.choices[0].message.content

            # Add response to history
            self.chat_history.append({"role": "assistant", "content": response_text})

            return {
                "response": response_text,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return {
                "error": f"Failed to process question: {str(e)}",
                "success": False
            }

    def _initialize_chat(self, context: str = ""):
        """Initialize chat with retrieved context."""
        system_prompt = f"""
        You are a helpful assistant that answers questions based on the provided context.
        Use the following context to answer the user's question:

        {context}

        Guidelines:
        1. Answer questions based only on the information in the document context provided.
        2. If information is not in the document, say so clearly.
        3. Keep responses clear and concise.
        4. If you're unsure about something, admit it.
        5. Don't use bold or italics formatting in your responses.
        6. Write in clear
        7. Use proper capitalization and punctuation
        8. Avoid all special characters, symbols, or bullet points
        9. Never use markdown or formatting symbols
        10. Present lists in sentence form with proper transitions
        """

        self.chat_history = [{"role": "system", "content": system_prompt}]

    def clear_history(self):
        """Clear chat history and re-initialize."""
        if self.document_content:
            self._initialize_chat()
        else:
            self.chat_history = []

    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the chat history excluding system prompt."""
        return [msg for msg in self.chat_history if msg["role"] != "system"]