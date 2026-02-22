import os
from typing import Any, Dict, List, Optional

try:
    import chromadb  # type: ignore
except Exception:
    chromadb = None

class VectorStore:

    def __init__(self):
        self._fallback_items: List[Dict[str, Any]] = []
        self.collection = None

        # Allow disabling Chroma (useful for tests/offline environments)
        if os.getenv("DISABLE_CHROMA", "").strip().lower() in {"1", "true", "yes"}:
            return

        if chromadb is None:
            return

        # Persist data to a local directory so memory survives restarts
        persist_path = os.path.join(os.getcwd(), "chroma_db")
        try:
            client = chromadb.PersistentClient(path=persist_path)
            self.collection = client.get_or_create_collection("investment_memory")
        except BaseException:
            # Chroma can fail to initialize (e.g., rust/sqlite binding panic).
            # Do not crash the whole app; fall back to an in-memory store.
            self.collection = None

    def add(self, id, text, metadata=None):
        if metadata is None:
            metadata = {"source": "user"} # Default metadata to avoid empty dict error

        if self.collection is not None:
            try:
                self.collection.add(
                    documents=[text],
                    ids=[id],
                    metadatas=[metadata]
                )
                return
            except Exception:
                # Fall back to in-memory
                self.collection = None

        self._fallback_items.append({"id": id, "text": text, "metadata": metadata})

    def search(self, query, n_results=3):
        if self.collection is not None:
            try:
                return self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
            except Exception:
                self.collection = None

        # Minimal compatible shape with Chroma's `query()` response
        docs = [i["text"] for i in self._fallback_items[-int(n_results):][::-1]]
        metas = [i["metadata"] for i in self._fallback_items[-int(n_results):][::-1]]
        ids = [i["id"] for i in self._fallback_items[-int(n_results):][::-1]]
        return {"ids": [ids], "documents": [docs], "metadatas": [metas]}
