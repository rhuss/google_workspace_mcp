import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gmail.gmail_tools import manage_gmail_filter


def _unwrap(tool):
    """Unwrap FunctionTool + decorators to the original async function."""
    fn = tool.fn if hasattr(tool, "fn") else tool
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


# ---------------------------------------------------------------------------
# Unit tests for the coercion helper (core/utils.py)
# ---------------------------------------------------------------------------
class TestCoerceJsonStrToDict:
    """Verify _coerce_json_str_to_dict mirrors StringList's coercion pattern."""

    def test_passes_dict_through(self):
        from core.utils import _coerce_json_str_to_dict

        d = {"from": "test@example.com"}
        assert _coerce_json_str_to_dict(d) == d

    def test_coerces_json_string_to_dict(self):
        from core.utils import _coerce_json_str_to_dict

        raw = '{"from": "test@example.com"}'
        assert _coerce_json_str_to_dict(raw) == {"from": "test@example.com"}

    def test_leaves_non_dict_json_alone(self):
        from core.utils import _coerce_json_str_to_dict

        # A JSON array string should NOT be coerced to a dict
        assert _coerce_json_str_to_dict('["a", "b"]') == '["a", "b"]'

    def test_leaves_invalid_json_alone(self):
        from core.utils import _coerce_json_str_to_dict

        assert _coerce_json_str_to_dict("not-json") == "not-json"

    def test_leaves_none_alone(self):
        from core.utils import _coerce_json_str_to_dict

        assert _coerce_json_str_to_dict(None) is None


# ---------------------------------------------------------------------------
# Integration tests for manage_gmail_filter (unwrapped)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_manage_gmail_filter_creates_with_dict_criteria():
    """Native dict params work (baseline regression guard)."""
    mock_service = Mock()
    mock_service.users().settings().filters().create().execute.return_value = {
        "id": "filter_abc"
    }

    result = await _unwrap(manage_gmail_filter)(
        service=mock_service,
        user_google_email="user@example.com",
        action="create",
        criteria={"from": "notifications@github.com"},
        filter_action={"addLabelIds": ["Label_1"], "removeLabelIds": ["INBOX"]},
    )

    assert "filter_abc" in result


@pytest.mark.asyncio
async def test_manage_gmail_filter_delete_works():
    """Delete action works without criteria/filter_action."""
    mock_service = Mock()
    mock_service.users().settings().filters().get().execute.return_value = {
        "id": "filter_123",
        "criteria": {"from": "old@example.com"},
        "action": {"addLabelIds": ["TRASH"]},
    }
    mock_service.users().settings().filters().delete().execute.return_value = None

    result = await _unwrap(manage_gmail_filter)(
        service=mock_service,
        user_google_email="user@example.com",
        action="delete",
        filter_id="filter_123",
    )

    assert "deleted" in result.lower()
    assert "filter_123" in result
