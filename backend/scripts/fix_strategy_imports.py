
import os
import glob

# Path to strategies
strategies_dir = "backend/finverse_integration/strategies"

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace obsolete absolute imports with relative paths
    new_content = content.replace("from utils.data_loader", "from ..utils.data_loader")
    new_content = new_content.replace("from utils.market_utils", "from ..utils.market_utils")
    
    if content != new_content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Fixed {filepath}")
    else:
        print(f"No changes needed for {filepath}")

for filepath in glob.glob(os.path.join(strategies_dir, "*.py")):
    fix_file(filepath)
