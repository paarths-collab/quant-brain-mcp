import glob
files = glob.glob('backend/*/core/*.py')
for f in files:
    with open(f, 'r') as file:
        content = file.read()
    if r'\n' in content and 'Auto-generated stub' in content:
        new_content = content.replace(r'\n', '\n')
        with open(f, 'w') as file:
            file.write(new_content)
        print(f"Fixed {f}")
