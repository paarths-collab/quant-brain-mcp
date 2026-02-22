import chromadb
from chromadb.config import Settings
from datetime import datetime

class MemoryStore:
    def __init__(self, persist_dir="./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("investment_memory")

    async def store(self, session_id, query, result, confidence):
        """Store interaction"""
        doc_id = f"{session_id}_{datetime.now().timestamp()}"
        self.collection.add(
            documents=[f"Query: {query}\nResult: {result}"],
            metadatas=[{
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "confidence": confidence
            }],
            ids=[doc_id]
        )
        
    async def close(self):
        pass
