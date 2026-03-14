"""
Tests for strikethrough text style support.

Covers the helpers, validation, and batch manager integration.
"""

import pytest
from unittest.mock import AsyncMock, Mock

from gdocs.docs_helpers import build_text_style, create_format_text_request
from gdocs.managers.validation_manager import ValidationManager


class TestBuildTextStyleStrikethrough:
    def test_strikethrough_true(self):
        style, fields = build_text_style(strikethrough=True)
        assert style["strikethrough"] is True
        assert "strikethrough" in fields

    def test_strikethrough_false(self):
        style, fields = build_text_style(strikethrough=False)
        assert style["strikethrough"] is False
        assert "strikethrough" in fields

    def test_strikethrough_none_excluded(self):
        style, fields = build_text_style(strikethrough=None)
        assert "strikethrough" not in style
        assert "strikethrough" not in fields

    def test_strikethrough_combined_with_bold(self):
        style, fields = build_text_style(bold=True, strikethrough=True)
        assert style["bold"] is True
        assert style["strikethrough"] is True
        assert "bold" in fields
        assert "strikethrough" in fields


class TestCreateFormatTextRequestStrikethrough:
    def test_strikethrough_produces_correct_api_structure(self):
        result = create_format_text_request(1, 10, strikethrough=True)
        inner = result["updateTextStyle"]
        assert inner["range"] == {"startIndex": 1, "endIndex": 10}
        assert inner["textStyle"]["strikethrough"] is True
        assert "strikethrough" in inner["fields"]

    def test_strikethrough_with_tab_id(self):
        result = create_format_text_request(1, 10, strikethrough=True, tab_id="t.abc")
        inner = result["updateTextStyle"]
        assert inner["range"]["tabId"] == "t.abc"


class TestValidateTextFormattingStrikethrough:
    @pytest.fixture()
    def vm(self):
        return ValidationManager()

    def test_strikethrough_only_is_valid(self, vm):
        is_valid, _ = vm.validate_text_formatting_params(strikethrough=True)
        assert is_valid

    def test_strikethrough_wrong_type_rejected(self, vm):
        is_valid, msg = vm.validate_text_formatting_params(strikethrough="yes")
        assert not is_valid
        assert "strikethrough" in msg

    def test_strikethrough_in_all_none_check(self, vm):
        """strikethrough=None should not count as a provided param."""
        is_valid, _ = vm.validate_text_formatting_params(strikethrough=None)
        assert not is_valid


class TestBatchManagerIntegration:
    @pytest.fixture()
    def manager(self):
        from gdocs.managers.batch_operation_manager import BatchOperationManager

        return BatchOperationManager(Mock())

    def test_build_request_with_strikethrough(self, manager):
        op = {
            "type": "format_text",
            "start_index": 1,
            "end_index": 12,
            "strikethrough": True,
        }
        request, desc = manager._build_operation_request(op, "format_text")
        inner = request["updateTextStyle"]
        assert inner["textStyle"]["strikethrough"] is True
        assert "strikethrough" in inner["fields"]
        assert "strikethrough: True" in desc

    def test_batch_validation_with_strikethrough(self):
        vm = ValidationManager()
        ops = [
            {
                "type": "format_text",
                "start_index": 1,
                "end_index": 12,
                "strikethrough": True,
            },
        ]
        assert vm.validate_batch_operations(ops)[0]

    @pytest.mark.asyncio
    async def test_end_to_end_execute_strikethrough(self, manager):
        manager._execute_batch_requests = AsyncMock(return_value={"replies": [{}]})
        success, message, meta = await manager.execute_batch_operations(
            "doc-123",
            [
                {
                    "type": "format_text",
                    "start_index": 1,
                    "end_index": 12,
                    "strikethrough": True,
                }
            ],
        )
        assert success
        assert meta["operations_count"] == 1
