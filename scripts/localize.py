import os
import re
import shutil

MODULES = ['sectors', 'markets', 'technical', 'chat', 'portfolio', 'backtest', 'peers', 'research', 'dashboard', 'network', 'news', 'screener', 'profile']
BASE_DIR = 'backend'

# Find all core files to use as sources
core_files = {}
for m in MODULES:
    core_path = os.path.join(BASE_DIR, m, 'core')
    if os.path.exists(core_path):
        for f in os.listdir(core_path):
            if f.endswith('.py') and f != '__init__.py':
                if f not in core_files:
                    core_files[f] = os.path.join(core_path, f)

def fix_file(filepath, module_name):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Replace backend.services.X with .core.X (or just .X if in core)
    def replace_import(match):
        prefix = match.group(1)
        sub_module = match.group(2)
        target = match.group(3)
        filename = f"{target}.py"
        
        # If the file is already in the module's core, use it
        local_core = os.path.join(BASE_DIR, module_name, 'core')
        if not os.path.exists(local_core):
             os.makedirs(local_core, exist_ok=True)
             with open(os.path.join(local_core, '__init__.py'), 'w') as _: pass

        if not os.path.exists(os.path.join(local_core, filename)):
            # If not local, find it elsewhere
            if filename in core_files:
                shutil.copy(core_files[filename], os.path.join(local_core, filename))
                print(f"  [COPY] {filename} -> {module_name}/core/")
            else:
                print(f"  [WARN] Source for {filename} not found!")

        return f"from .core.{target}"

    # Pattern: from backend.services.X import Y or from backend.core.services.X import Y
    new_content = re.sub(r'from backend\.(?:core\.)?services\.([^\s\.]+)\.([^\s\.]+) import', replace_import, content) # Nested (e.g. strategies.sma)
    new_content = re.sub(r'from backend\.(?:core\.)?services\.([^\s\.]+) import', replace_import, content) # Simple
    new_content = re.sub(r'from backend\.core\.(?:agents|utils)\.([^\s\.]+) import', replace_import, content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  [FIXED] {filepath}")

for m in MODULES:
    m_dir = os.path.join(BASE_DIR, m)
    if not os.path.exists(m_dir): continue
    print(f"Processing module: {m}")
    for root, dirs, files in os.walk(m_dir):
        if 'core' in dirs and root == m_dir: # Special case for core/ itself
             pass
        for f in files:
            if f.endswith('.py'):
                fix_file(os.path.join(root, f), m)

