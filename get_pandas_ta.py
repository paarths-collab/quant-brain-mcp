import runpy
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    old_dir = project_root / "old"
    target_script = old_dir / "get_pandas_ta.py"

    if not target_script.exists():
        raise FileNotFoundError(f"Script not found: {target_script}")

    if str(old_dir) not in sys.path:
        sys.path.insert(0, str(old_dir))

    runpy.run_path(str(target_script), run_name="__main__")


if __name__ == "__main__":
    main()
