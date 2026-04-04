import ast
import os
import sys

def audit_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read())
        except Exception as e:
            return f"Error parsing {filepath}: {e}"

    issues = []
    
    # Check imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                if n.name == 'yfinance' and 'core/safe_yfinance.py' not in filepath:
                    issues.append(f"[ISSUE] Direct yfinance import in {filepath}")
        if isinstance(node, ast.ImportFrom):
            if node.module == 'yfinance' and 'core/safe_yfinance.py' not in filepath:
                issues.append(f"[ISSUE] Direct yfinance import from in {filepath}")
            
    # Check for local market_data_service imports (inconsistent imports)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and 'market_data_service' in node.module:
                if not node.module.startswith('backend.services'):
                    issues.append(f"[ISSUE] Local/Inconsistent service import in {filepath}: {node.module}")

    # Detect business logic in routers (simplified check for data fetching/calculations)
    if 'main.py' in filepath or '/routers/' in filepath:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['download', 'history', 'Ticker']:
                         issues.append(f"[ISSUE] Potential business logic (yf call) in router {filepath}")

    return issues

def main():
    root_dir = 'backend'
    all_issues = []
    for root, dirs, files in os.walk(root_dir):
        if '.venv' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                res = audit_file(path)
                if isinstance(res, list):
                    all_issues.extend(res)
                else:
                    print(res)

    for issue in sorted(list(set(all_issues))):
        print(issue)

if __name__ == '__main__':
    main()
