import asyncio
import json
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from webbot.forms.extractor import extract_form_schema_from_snapshot_dir


def test_extract_from_ashby_direct_reports_valid_with_file():
    base = Path(__file__).parent / "fixtures" / "realworld" / "ashby-infisical-direct" / "initial"

    async def run():
        schema = await extract_form_schema_from_snapshot_dir(base)
        assert schema.validity.is_valid_job_application_form is True
        # Expect at least one file-like input
        kinds = [f.type for s in schema.sections for f in s.fields]
        assert "file" in kinds or any(f.meta.get("hasDnd") for s in schema.sections for f in s.fields)

    asyncio.run(run())


def test_extract_from_infisical_jd_initial_is_invalid():
    base = Path(__file__).parent / "fixtures" / "realworld" / "ashby-infisical-jd" / "initial"

    async def run():
        schema = await extract_form_schema_from_snapshot_dir(base)
        assert schema.validity.is_valid_job_application_form is False

    asyncio.run(run())


