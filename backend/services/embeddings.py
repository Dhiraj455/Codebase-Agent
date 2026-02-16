

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


    def __init__(
        self,
        embeddings_model: Optional[Any] = None,
        vector_store_path: str = "./vector_store",
        api_key: Optional[str] = None,
    ):

        self.vector_store_path = Path(vector_store_path)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)

        if embeddings_model is not None:
            self.embeddings = embeddings_model
        else:
            api_key = api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError(
                    "Google Gemini API key required. Set GEMINI_API_KEY environment variable "
                    "or pass api_key parameter."
                )

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

        if FAISS is None or Document is None:
            raise ImportError(
                "FAISS vector store not available. "
                "Install with: pip install faiss-cpu langchain"
            )

        documents = []
        metadatas = []

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
            metadatas.append(chunk.get("metadata", {}))

        self.vector_store = FAISS.from_documents(
            documents=documents,
            embedding=self.embeddings,
        )

        self.save_vector_store(store_name)

        return self.vector_store

    def add_chunks_to_store(
        self, chunks: List[Dict[str, Any]], store_name: str = "default"
    ) -> None:

        if self.vector_store is None:
            try:
                self.load_vector_store(store_name)
            except FileNotFoundError:
                self.create_vector_store_from_chunks(chunks, store_name)
                return

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

        self.vector_store.add_documents(documents)
        self.save_vector_store(store_name)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:

        if self.vector_store is None:
            raise ValueError("Vector store not initialized. Load or create a store first.")

        if filter_dict:
            results = self.vector_store.similarity_search_with_score(
                query, k=k, filter=filter_dict
            )
        else:
            results = self.vector_store.similarity_search_with_score(query, k=k)

        formatted_results = []
        for doc, score in results:
            metadata = doc.metadata.copy()

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

        return self.similarity_search(
            query, k=k, filter_dict={"file_path": file_path}
        )

    def similarity_search_by_type(
        self, query: str, chunk_type: str, k: int = 4
    ) -> List[Dict[str, Any]]:

        return self.similarity_search(
            query, k=k, filter_dict={"chunk_type": chunk_type}
        )

    def save_vector_store(self, store_name: str = "default") -> None:

        if self.vector_store is None:
            raise ValueError("No vector store to save.")

        store_dir = self.vector_store_path / store_name
        store_dir.mkdir(parents=True, exist_ok=True)

        self.vector_store.save_local(str(store_dir))

        metadata_file = store_dir / "metadata.json"
        metadata = {
            "store_name": store_name,
            "embeddings_model": "google_gemini",
            "vector_count": len(self.vector_store.index.ntotal) if hasattr(self.vector_store.index, 'ntotal') else 0,
        }

        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def load_vector_store(self, store_name: str = "default") -> Any:

        store_dir = self.vector_store_path / store_name

        if not store_dir.exists():
            raise FileNotFoundError(
                f"Vector store '{store_name}' not found at {store_dir}"
            )

        if FAISS is None:
            raise ImportError(
                "FAISS vector store not available. "
                "Install with: pip install faiss-cpu langchain"
            )

        self.vector_store = FAISS.load_local(
            str(store_dir),
            self.embeddings,
            allow_dangerous_deserialization=True,
        )

        return self.vector_store

    def get_store_info(self, store_name: str = "default") -> Dict[str, Any]:

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
                if hasattr(self.vector_store.index, 'ntotal'):
                    info["vector_count"] = self.vector_store.index.ntotal
            except Exception:
                pass

        return info

    def delete_vector_store(self, store_name: str = "default") -> bool:

        store_dir = self.vector_store_path / store_name

        if not store_dir.exists():
            return False

        import shutil
        shutil.rmtree(store_dir)
        return True

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:

        return self.embeddings.embed_documents(texts)

    def create_embedding(self, text: str) -> List[float]:

        return self.embeddings.embed_query(text)


if __name__ == "__main__":
    pass
