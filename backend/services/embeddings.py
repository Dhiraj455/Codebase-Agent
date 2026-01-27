"""
Embeddings and Vector Store Service

Handles creating embeddings from code chunks and storing them in FAISS vector store.
Supports similarity search for RAG (Retrieval-Augmented Generation).
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pickle

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_community.vectorstores import FAISS
    try:
        from langchain_core.documents import Document
    except ImportError:
        from langchain.schema import Document
except ImportError:
    # Fallback
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from langchain.vectorstores import FAISS
        try:
            from langchain_core.documents import Document
        except ImportError:
            from langchain.schema import Document
    except ImportError:
        GoogleGenerativeAIEmbeddings = None
        FAISS = None
        Document = None

import numpy as np


class EmbeddingsService:
    """Service for creating embeddings and managing vector store."""

    def __init__(
        self,
        embeddings_model: Optional[Any] = None,
        vector_store_path: str = "./vector_store",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the embeddings service.

        Args:
            embeddings_model: Optional pre-initialized embeddings model.
                            If None, creates Google Gemini embeddings.
            vector_store_path: Path to store/load FAISS vector store
            api_key: Google Gemini API key. If None, reads from GEMINI_API_KEY env var.
        """
        self.vector_store_path = Path(vector_store_path)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)

        # Initialize embeddings
        if embeddings_model is not None:
            self.embeddings = embeddings_model
        else:
            api_key = api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError(
                    "Google Gemini API key required. Set GEMINI_API_KEY environment variable "
                    "or pass api_key parameter."
                )
            
            # Initialize Google Gemini embeddings
            if GoogleGenerativeAIEmbeddings is None:
                raise ImportError(
                    "langchain_google_genai is not installed. "
                    "Install with: pip install langchain-google-genai"
                )
            
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=api_key
            )

        self.vector_store: Optional[Any] = None

    def create_vector_store_from_chunks(
        self, chunks: List[Dict[str, Any]], store_name: str = "default"
    ) -> Any:
        """
        Create FAISS vector store from code chunks.

        Args:
            chunks: List of chunk dictionaries from chunking service
            store_name: Name identifier for this vector store

        Returns:
            FAISS vector store instance
        """
        if FAISS is None or Document is None:
            raise ImportError(
                "FAISS vector store not available. "
                "Install with: pip install faiss-cpu langchain"
            )

        # Convert chunks to LangChain Documents
        documents = []
        metadatas = []

        for chunk in chunks:
            # Create document with content
            doc = Document(
                page_content=chunk.get("content", ""),
                metadata={
                    "chunk_id": chunk.get("chunk_id", ""),
                    "file_path": chunk.get("file_path", ""),
                    "file_name": chunk.get("file_name", ""),
                    "chunk_type": chunk.get("chunk_type", ""),
                    "name": chunk.get("name", ""),
                    "start_line": chunk.get("start_line", 0),
                    "end_line": chunk.get("end_line", 0),
                    # Store full metadata as JSON string for retrieval
                    "metadata_json": json.dumps(chunk.get("metadata", {})),
                },
            )
            documents.append(doc)
            metadatas.append(chunk.get("metadata", {}))

        # Create FAISS vector store
        self.vector_store = FAISS.from_documents(
            documents=documents,
            embedding=self.embeddings,
        )

        # Save to disk
        self.save_vector_store(store_name)

        return self.vector_store

    def add_chunks_to_store(
        self, chunks: List[Dict[str, Any]], store_name: str = "default"
    ) -> None:
        """
        Add new chunks to existing vector store.

        Args:
            chunks: List of chunk dictionaries to add
            store_name: Name identifier for the vector store
        """
        if self.vector_store is None:
            # Load existing store or create new one
            try:
                self.load_vector_store(store_name)
            except FileNotFoundError:
                self.create_vector_store_from_chunks(chunks, store_name)
                return

        # Convert chunks to documents
        documents = []
        for chunk in chunks:
            doc = Document(
                page_content=chunk.get("content", ""),
                metadata={
                    "chunk_id": chunk.get("chunk_id", ""),
                    "file_path": chunk.get("file_path", ""),
                    "file_name": chunk.get("file_name", ""),
                    "chunk_type": chunk.get("chunk_type", ""),
                    "name": chunk.get("name", ""),
                    "start_line": chunk.get("start_line", 0),
                    "end_line": chunk.get("end_line", 0),
                    "metadata_json": json.dumps(chunk.get("metadata", {})),
                },
            )
            documents.append(doc)

        # Add to existing store
        self.vector_store.add_documents(documents)
        self.save_vector_store(store_name)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search in the vector store.

        Args:
            query: Search query string
            k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of relevant chunks with similarity scores
        """
        if self.vector_store is None:
            raise ValueError("Vector store not initialized. Load or create a store first.")

        # Perform search
        if filter_dict:
            results = self.vector_store.similarity_search_with_score(
                query, k=k, filter=filter_dict
            )
        else:
            results = self.vector_store.similarity_search_with_score(query, k=k)

        # Format results
        formatted_results = []
        for doc, score in results:
            metadata = doc.metadata.copy()
            
            # Parse metadata JSON if present
            if "metadata_json" in metadata:
                try:
                    metadata["metadata"] = json.loads(metadata["metadata_json"])
                except json.JSONDecodeError:
                    metadata["metadata"] = {}

            formatted_results.append({
                "content": doc.page_content,
                "score": float(score),
                "metadata": metadata,
            })

        return formatted_results

    def similarity_search_by_file(
        self, query: str, file_path: str, k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks within a specific file.

        Args:
            query: Search query string
            file_path: Path to filter by
            k: Number of results to return

        Returns:
            List of relevant chunks from the specified file
        """
        return self.similarity_search(
            query, k=k, filter_dict={"file_path": file_path}
        )

    def similarity_search_by_type(
        self, query: str, chunk_type: str, k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks of a specific type.

        Args:
            query: Search query string
            chunk_type: Type of chunk (class, function, module, etc.)
            k: Number of results to return

        Returns:
            List of relevant chunks of the specified type
        """
        return self.similarity_search(
            query, k=k, filter_dict={"chunk_type": chunk_type}
        )

    def save_vector_store(self, store_name: str = "default") -> None:
        """
        Save vector store to disk.

        Args:
            store_name: Name identifier for the vector store
        """
        if self.vector_store is None:
            raise ValueError("No vector store to save.")

        store_dir = self.vector_store_path / store_name
        store_dir.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        self.vector_store.save_local(str(store_dir))

        # Save additional metadata
        metadata_file = store_dir / "metadata.json"
        metadata = {
            "store_name": store_name,
            "embeddings_model": "google_gemini",
            "vector_count": len(self.vector_store.index.ntotal) if hasattr(self.vector_store.index, 'ntotal') else 0,
        }
        
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def load_vector_store(self, store_name: str = "default") -> Any:
        """
        Load vector store from disk.

        Args:
            store_name: Name identifier for the vector store

        Returns:
            Loaded FAISS vector store instance
        """
        store_dir = self.vector_store_path / store_name

        if not store_dir.exists():
            raise FileNotFoundError(
                f"Vector store '{store_name}' not found at {store_dir}"
            )

        # Load FAISS index
        if FAISS is None:
            raise ImportError(
                "FAISS vector store not available. "
                "Install with: pip install faiss-cpu langchain"
            )

        self.vector_store = FAISS.load_local(
            str(store_dir),
            self.embeddings,
            allow_dangerous_deserialization=True,  # Required for FAISS
        )

        return self.vector_store

    def get_store_info(self, store_name: str = "default") -> Dict[str, Any]:
        """
        Get information about a vector store.

        Args:
            store_name: Name identifier for the vector store

        Returns:
            Dictionary with store information
        """
        store_dir = self.vector_store_path / store_name
        metadata_file = store_dir / "metadata.json"

        info = {
            "store_name": store_name,
            "path": str(store_dir),
            "exists": store_dir.exists(),
        }

        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                info.update(json.load(f))

        if self.vector_store is not None:
            try:
                # Try to get vector count
                if hasattr(self.vector_store.index, 'ntotal'):
                    info["vector_count"] = self.vector_store.index.ntotal
            except Exception:
                pass

        return info

    def delete_vector_store(self, store_name: str = "default") -> bool:
        """
        Delete a vector store from disk.

        Args:
            store_name: Name identifier for the vector store

        Returns:
            True if successfully deleted, False otherwise
        """
        store_dir = self.vector_store_path / store_name

        if not store_dir.exists():
            return False

        import shutil
        shutil.rmtree(store_dir)
        return True

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        return self.embeddings.embed_documents(texts)

    def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector
        """
        return self.embeddings.embed_query(text)


# Example usage
if __name__ == "__main__":
    # Example: Create embeddings service
    # service = EmbeddingsService(
    #     vector_store_path="./vector_store",
    #     api_key="your-api-key"  # or set GEMINI_API_KEY env var
    # )
    #
    # # Create vector store from chunks
    # chunks = [...]  # From chunking service
    # vector_store = service.create_vector_store_from_chunks(chunks, "my_repo")
    #
    # # Search
    # results = service.similarity_search("How does authentication work?", k=5)
    # for result in results:
    #     print(f"Score: {result['score']:.4f}")
    #     print(f"File: {result['metadata']['file_name']}")
    #     print(f"Content: {result['content'][:100]}...")
    #     print()
    pass  # Placeholder for example code
