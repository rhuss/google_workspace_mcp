"""
Unit tests for Google Drive MCP tools.

Tests create_drive_folder with mocked API responses, and the `detailed`
parameter added to search_drive_files, list_drive_items, and
build_drive_list_params.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gdrive.drive_helpers import build_drive_list_params
from gdrive.drive_tools import list_drive_items, search_drive_files


def _unwrap(tool):
    """Unwrap a FunctionTool + decorator chain to the original async function.

    Handles both older FastMCP (FunctionTool with .fn) and newer FastMCP
    (server.tool() returns the function directly).
    """
    fn = tool.fn if hasattr(tool, "fn") else tool
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_file(
    file_id: str,
    name: str,
    mime_type: str,
    link: str = "http://link",
    modified: str = "2024-01-01T00:00:00Z",
    size: str | None = None,
) -> dict:
    item = {
        "id": file_id,
        "name": name,
        "mimeType": mime_type,
        "webViewLink": link,
        "modifiedTime": modified,
    }
    if size is not None:
        item["size"] = size
    return item


# ---------------------------------------------------------------------------
# create_drive_folder
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_drive_folder():
    """Test create_drive_folder returns success message with folder id, name, and link."""
    from gdrive.drive_tools import _create_drive_folder_impl

    mock_service = Mock()
    mock_response = {
        "id": "folder123",
        "name": "My Folder",
        "webViewLink": "https://drive.google.com/drive/folders/folder123",
    }
    mock_request = Mock()
    mock_request.execute.return_value = mock_response
    mock_service.files.return_value.create.return_value = mock_request

    with patch(
        "gdrive.drive_tools.resolve_folder_id",
        new_callable=AsyncMock,
        return_value="root",
    ):
        result = await _create_drive_folder_impl(
            service=mock_service,
            user_google_email="user@example.com",
            folder_name="My Folder",
            parent_folder_id="root",
        )

    assert "Successfully created folder" in result
    assert "My Folder" in result
    assert "folder123" in result
    assert "user@example.com" in result
    assert "https://drive.google.com/drive/folders/folder123" in result


# ---------------------------------------------------------------------------
# build_drive_list_params — detailed flag (pure unit tests, no I/O)
# ---------------------------------------------------------------------------


def test_build_params_detailed_true_includes_extra_fields():
    """detailed=True requests modifiedTime, webViewLink, and size from the API."""
    params = build_drive_list_params(query="name='x'", page_size=10, detailed=True)
    assert "modifiedTime" in params["fields"]
    assert "webViewLink" in params["fields"]
    assert "size" in params["fields"]


def test_build_params_detailed_false_omits_extra_fields():
    """detailed=False omits modifiedTime, webViewLink, and size from the API request."""
    params = build_drive_list_params(query="name='x'", page_size=10, detailed=False)
    assert "modifiedTime" not in params["fields"]
    assert "webViewLink" not in params["fields"]
    assert "size" not in params["fields"]


def test_build_params_detailed_false_keeps_core_fields():
    """detailed=False still requests id, name, and mimeType."""
    params = build_drive_list_params(query="name='x'", page_size=10, detailed=False)
    assert "id" in params["fields"]
    assert "name" in params["fields"]
    assert "mimeType" in params["fields"]


def test_build_params_default_is_detailed():
    """Omitting detailed behaves identically to detailed=True."""
    params_default = build_drive_list_params(query="q", page_size=5)
    params_true = build_drive_list_params(query="q", page_size=5, detailed=True)
    assert params_default["fields"] == params_true["fields"]


# ---------------------------------------------------------------------------
# search_drive_files — detailed flag
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_detailed_true_output_includes_metadata():
    """detailed=True (default) includes modified time and link in output."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _make_file(
                "f1",
                "My Doc",
                "application/vnd.google-apps.document",
                modified="2024-06-01T12:00:00Z",
                link="http://link/f1",
            )
        ]
    }

    result = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="my doc",
        detailed=True,
    )

    assert "My Doc" in result
    assert "2024-06-01T12:00:00Z" in result
    assert "http://link/f1" in result


@pytest.mark.asyncio
async def test_search_detailed_false_output_excludes_metadata():
    """detailed=False omits modified time and link from output."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _make_file(
                "f1",
                "My Doc",
                "application/vnd.google-apps.document",
                modified="2024-06-01T12:00:00Z",
                link="http://link/f1",
            )
        ]
    }

    result = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="my doc",
        detailed=False,
    )

    assert "My Doc" in result
    assert "f1" in result
    assert "2024-06-01T12:00:00Z" not in result
    assert "http://link/f1" not in result


@pytest.mark.asyncio
async def test_search_detailed_true_with_size():
    """When the item has a size field, detailed=True includes it in output."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _make_file("f2", "Big File", "application/pdf", size="102400"),
        ]
    }

    result = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="big",
        detailed=True,
    )

    assert "102400" in result


@pytest.mark.asyncio
async def test_search_detailed_true_requests_extra_api_fields():
    """detailed=True passes full fields string to the Drive API."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="anything",
        detailed=True,
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "modifiedTime" in call_kwargs["fields"]
    assert "webViewLink" in call_kwargs["fields"]
    assert "size" in call_kwargs["fields"]


@pytest.mark.asyncio
async def test_search_detailed_false_requests_compact_api_fields():
    """detailed=False passes compact fields string to the Drive API."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="anything",
        detailed=False,
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "modifiedTime" not in call_kwargs["fields"]
    assert "webViewLink" not in call_kwargs["fields"]
    assert "size" not in call_kwargs["fields"]


@pytest.mark.asyncio
async def test_search_default_detailed_matches_detailed_true():
    """Omitting detailed produces the same output as detailed=True."""
    file = _make_file(
        "f1",
        "Doc",
        "application/vnd.google-apps.document",
        modified="2024-01-01T00:00:00Z",
        link="http://l",
    )

    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": [file]}
    result_default = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="doc",
    )

    mock_service.files().list().execute.return_value = {"files": [file]}
    result_true = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="doc",
        detailed=True,
    )

    assert result_default == result_true


# ---------------------------------------------------------------------------
# list_drive_items — detailed flag
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_detailed_true_output_includes_metadata(mock_resolve_folder):
    """detailed=True (default) includes modified time and link in output."""
    mock_resolve_folder.return_value = "resolved_root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _make_file(
                "id1",
                "Report",
                "application/vnd.google-apps.document",
                modified="2024-03-15T08:00:00Z",
                link="http://link/id1",
            )
        ]
    }

    result = await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="root",
        detailed=True,
    )

    assert "Report" in result
    assert "2024-03-15T08:00:00Z" in result
    assert "http://link/id1" in result


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_detailed_false_output_excludes_metadata(mock_resolve_folder):
    """detailed=False omits modified time and link from output."""
    mock_resolve_folder.return_value = "resolved_root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _make_file(
                "id1",
                "Report",
                "application/vnd.google-apps.document",
                modified="2024-03-15T08:00:00Z",
                link="http://link/id1",
            )
        ]
    }

    result = await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="root",
        detailed=False,
    )

    assert "Report" in result
    assert "id1" in result
    assert "2024-03-15T08:00:00Z" not in result
    assert "http://link/id1" not in result


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_detailed_true_with_size(mock_resolve_folder):
    """When item has a size field, detailed=True includes it in output."""
    mock_resolve_folder.return_value = "resolved_root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _make_file("id2", "Big File", "application/pdf", size="204800"),
        ]
    }

    result = await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="root",
        detailed=True,
    )

    assert "204800" in result


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_detailed_true_requests_extra_api_fields(mock_resolve_folder):
    """detailed=True passes full fields string to the Drive API."""
    mock_resolve_folder.return_value = "resolved_root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="root",
        detailed=True,
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "modifiedTime" in call_kwargs["fields"]
    assert "webViewLink" in call_kwargs["fields"]
    assert "size" in call_kwargs["fields"]


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_detailed_false_requests_compact_api_fields(mock_resolve_folder):
    """detailed=False passes compact fields string to the Drive API."""
    mock_resolve_folder.return_value = "resolved_root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="root",
        detailed=False,
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "modifiedTime" not in call_kwargs["fields"]
    assert "webViewLink" not in call_kwargs["fields"]
    assert "size" not in call_kwargs["fields"]
