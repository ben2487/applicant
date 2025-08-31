import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from webbot.profiles import discover_profiles


def test_discover_profiles_runs():
    # On some CI machines this may return [], but it must not crash.
    _ = discover_profiles()
