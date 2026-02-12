"""
Multi-Agent Chat System
AutoGen + CrewAI Human-in-the-Loop Architecture
"""

# Lazy imports to avoid circular dependencies
def get_chat_orchestrator():
    from .orchestrator import get_chat_orchestrator as _get
    return _get()

def get_intent_router():
    from .intent_router import get_intent_router as _get
    return _get()

def get_pipeline_manager():
    from .pipelines import get_pipeline_manager as _get
    return _get()
