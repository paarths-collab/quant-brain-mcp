import asyncio
import sys
import os
from dotenv import load_dotenv

# Load env from backend/.env
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, "..")
project_root = os.path.join(current_dir, "..", "..") # Go up to project root

sys.path.append(backend_path)
sys.path.append(project_root) # Add project root just in case

load_dotenv(os.path.join(backend_path, ".env"))

from backend.agentic.super_agent import SuperAgent

async def main():
    print("Initializing SuperAgent v2.0...")
    print("Agentic OS Online. Type 'exit' to quit.")
    agent = SuperAgent()
    
    while True:
        try:
            query = input("\nEnter your query: ")
            if query.lower() in ['exit', 'quit']:
                break
                
            print(f"\nExecuting Query: {query}")
        
            result = await agent.execute(query)
            
            print("\n--- EXECUTION COMPLETE ---")
            print(f"Emotion: {result['emotional_status']}")
            print(f"Plan: {result['plan']}")
            print(f"Agent Outputs Keys: {list(result['agent_outputs'].keys())}")
            print("\n--- FINAL REPORT ---")
            print(result["final_report"])
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nCRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
