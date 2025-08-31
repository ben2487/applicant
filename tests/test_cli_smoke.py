import subprocess
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_cli_help():
    # Run the CLI module from the src directory
    src_path = Path(__file__).parent.parent / "src"
    out = subprocess.run(
        [sys.executable, "-m", "webbot.cli", "--help"],
        capture_output=True,
        text=True,
        cwd=str(src_path),
    )
    assert out.returncode == 0
    assert "list-browser-profiles" in out.stdout
