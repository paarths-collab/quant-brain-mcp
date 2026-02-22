import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory (backend) to sys.path so we can import backend1
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend1.controllers.strategy_controller import StrategyController

if __name__ == "__main__":

    controller = StrategyController()

    user_input = input("Enter your question: ")

    raw_response = controller.plan(user_input)
    print("\n--- CONTROLLER RAW OUTPUT ---\n")
    print(raw_response)

    # Robust Parser with Retry
    from backend1.utils.json_extractor import extract_json_from_output
    
    schema = extract_json_from_output(raw_response)
    
    # Retry once if failed
    if not schema:
        print("\n⚠️ JSON parsing failed. Retrying controller...\n")
        raw_response = controller.plan(user_input)
        print("\n--- CONTROLLER RAW OUTPUT (RETRY) ---\n")
        print(raw_response)
        schema = extract_json_from_output(raw_response)

    if schema:
        from backend1.orchestrator.execution_engine import ExecutionEngine
        
        print("\n--- EXECUTING PLAN ---\n")
        engine = ExecutionEngine()
        final_state = engine.execute(schema)

        print("\n--- FINAL EXECUTION OUTPUT ---\n")
        import pprint
        pprint.pprint(final_state)
    else:
        print("\n❌ Failed to extract valid JSON after retry.")
