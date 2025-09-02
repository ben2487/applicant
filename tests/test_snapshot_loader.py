import asyncio
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from webbot.forms import load_snapshot_manifest, load_snapshot_as_page, scan_snapshot_for_selector


def test_manifest_roundtrip():
    base = Path(__file__).parent / "fixtures" / "realworld" / "ashby-infisical-direct" / "initial"
    m = load_snapshot_manifest(base)
    assert m.url
    assert m.page_html.exists()


def test_load_snapshot_and_check_file_input():
    base = Path(__file__).parent / "fixtures" / "realworld" / "ashby-infisical-direct" / "initial"

    async def run():
        total = await scan_snapshot_for_selector(base, 'input[type="file"]')
        assert total >= 1

    asyncio.run(run())


