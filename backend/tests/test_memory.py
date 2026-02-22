from backend.memory.vector_store import VectorStore
from backend.memory.session_memory import SessionMemory

def test_vector_store():
    store = VectorStore()
    # Unique ID to prevent collision in persistent DB on re-runs
    import uuid
    test_id = str(uuid.uuid4())
    
    store.add(test_id, "AI stocks are growing fast")
    result = store.search("AI")

    assert result is not None
    assert "ids" in result
    assert len(result["ids"][0]) > 0

def test_session_memory():
    mem = SessionMemory()
    mem.save("session_1", "query", "apple")
    
    val = mem.get("session_1", "query")
    assert val == "apple"
