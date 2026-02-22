import os
import ast
from typing import Dict, Any, List
from pathlib import Path

# Try to import langchain, provide fallback
try:
    from langchain_core.tools import tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    def tool(func):
        func.is_tool = True
        return func

class CodebaseTools:
    """
    Tools for analyzing the backend codebase structure and content.
    """
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        
    @tool
    def list_files(self, directory: str = ".") -> List[str]:
        """
        List all files in a specific directory (non-recursive).
        
        Args:
            directory: Relative path to the directory (e.g., "backend/agents")
            
        Returns:
            List of filenames
        """
        try:
            target_dir = (self.root_dir / directory).resolve()
            if not target_dir.exists():
                return [f"Error: Directory {directory} does not exist"]
            
            files = [f.name for f in target_dir.glob("*") if f.is_file()]
            return files
        except Exception as e:
            return [f"Error listing files: {str(e)}"]

    @tool
    def count_classes_in_file(self, filepath: str) -> Dict[str, Any]:
        """
        Count the number of classes and functions in a specific Python file.
        
        Args:
            filepath: Relative path to the file (e.g., "backend/main.py")
            
        Returns:
            Dictionary with counts and names of classes/functions
        """
        try:
            target_path = (self.root_dir / filepath).resolve()
            if not target_path.exists():
                return {"error": f"File {filepath} does not exist"}
                
            with open(target_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
                
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            
            return {
                "filepath": filepath,
                "class_count": len(classes),
                "function_count": len(functions),
                "classes": classes,
                "functions": functions[:10]  # Limit detailed list to 10
            }
        except Exception as e:
            return {"error": f"Error parsing file: {str(e)}"}
            
    @tool
    def read_file_snippet(self, filepath: str, start_line: int = 1, end_line: int = 50) -> str:
        """
        Read a specific range of lines from a file.
        
        Args:
            filepath: Relative path to the file
            start_line: 1-indexed start line
            end_line: 1-indexed end line
            
        Returns:
            String content of the file snippet
        """
        try:
            target_path = (self.root_dir / filepath).resolve()
            if not target_path.exists():
                return f"Error: File {filepath} does not exist"
                
            with open(target_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            # Adjust for 0-based index
            start = max(0, start_line - 1)
            end = min(len(lines), end_line)
            
            return "".join(lines[start:end])
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def get_tools(self) -> List:
        return [
            self.list_files,
            self.count_classes_in_file,
            self.read_file_snippet
        ]

def create_codebase_tools(root_dir: str = ".") -> CodebaseTools:
    return CodebaseTools(root_dir)
