
import os
import glob

# Path to utils
utils_dir = "backend/finverse_integration/utils"

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Skipping {filepath}: {e}")
        return
    
    # Replace absolute imports with relative paths within utils package
    # Crucial Fixes for "No module named utils.XXX"
    new_content = content.replace("from utils.llm_manager", "from .llm_manager")
    new_content = new_content.replace("from utils.portfolio_engine", "from .portfolio_engine")
    new_content = new_content.replace("from utils.news_fetcher", "from .news_fetcher")
    new_content = new_content.replace("from utils.market_utils", "from .market_utils")
    new_content = new_content.replace("from utils.data_loader", "from .data_loader")
    new_content = new_content.replace("from utils.guardrails", "from .guardrails") # Added just in case
    
    if content != new_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {filepath}")
    else:
        print(f"No changes needed for {filepath}")

for filepath in glob.glob(os.path.join(utils_dir, "*.py")):
    fix_file(filepath)
