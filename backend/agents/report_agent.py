# useless for now

# import os
# import json
# import streamlit as st
# from typing import Dict, Any

# # --- Import the master analyst agent ---
# # Ensure this import is correct and points to the right file
# from agents.llm_analyst_agent import LLMAnalystAgent

# class ReportAgent:
#     def __init__(self, gemini_key: str):
#         """
#         Initializes the ReportAgent.
#         It uses the Master LLM Analyst Agent as its core engine.
#         """
#         # --- THIS IS THE FIX ---
#         # The Master LLMAnalystAgent only needs the Gemini key.
#         # We only accept and pass the gemini_key now.
#         self.llm_analyst = LLMAnalystAgent(gemini_api_key=gemini_key)
#         # --- END OF FIX ---
#         print("[SUCCESS] ReportAgent: Initialized with LLM Analyst engine.")

#     def generate_investment_report(self, analysis_context: Dict[str, Any], user_query: str) -> str:
#         """
#         Synthesizes a comprehensive analysis into a professional report.
#         """
#         # The 'generate_brokerage_report' method is the correct one from our Master Analyst
#         return self.llm_analyst.generate_brokerage_report(analysis_context, user_query)

# # --- Streamlit Visualization ---
# if __name__ == "__main__":
#     st.set_page_config(page_title="Report Generation Agent", layout="wide")
#     st.title("📑 AI-Powered Report Generator")

#     # For standalone testing, we only need the Gemini key
#     GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))

#     if not GEMINI_KEY:
#         st.error("LLM API key (GEMINI_API_KEY) not found in secrets.")
#     else:
#         # --- FIX: Only pass the gemini_key ---
#         agent = ReportAgent(gemini_key=GEMINI_KEY)
        
#         st.info("This showcase demonstrates how the ReportAgent synthesizes data.")
        
#         # ... (The rest of the Streamlit UI for testing can remain the same)
#         mock_data = { "ticker": "AAPL", "technicals": {"SMA Signal": "BUY"} }
#         context_json = st.text_area("Analysis Context (JSON)", value=json.dumps(mock_data, indent=2), height=300)
#         user_query = "Provide a summary."
        
#         if st.button("📝 Generate Report", use_container_width=True):
#             try:
#                 context = json.loads(context_json)
#                 with st.spinner("AI Analyst is writing the report..."):
#                     report = agent.generate_investment_report(context, user_query)
#                     st.markdown(report)
#             except Exception as e:
#                 st.error(f"An error occurred: {e}")