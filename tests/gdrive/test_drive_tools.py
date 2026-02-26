"""
Unit tests for Google Drive MCP tools.

Tests create_drive_folder, search_drive_files, and list_drive_items with mocked API responses.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gdrive.drive_tools import list_drive_items, search_drive_files


def _unwrap(fn):
    """Unwrap a decorator chain to the original async function."""
    if hasattr(fn, "fn"):
        fn = fn.fn  # FunctionTool wrapper (other server versions)
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


# ---------------------------------------------------------------------------
# search_drive_files — page_token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_drive_files_page_token_passed_to_api():
    """page_token is forwarded to the Drive API as pageToken."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            {
                "id": "f1",
                "name": "Report.pdf",
                "mimeType": "application/pdf",
                "webViewLink": "https://drive.google.com/file/f1",
                "modifiedTime": "2024-01-01T00:00:00Z",
            }
        ]
    }

    await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="budget",
        page_token="tok_abc123",
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert call_kwargs.get("pageToken") == "tok_abc123"


@pytest.mark.asyncio
async def test_search_drive_files_next_page_token_in_output():
    """nextPageToken from the API response is appended at the end of the output."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            {
                "id": "f2",
                "name": "Notes.docx",
                "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "webViewLink": "https://drive.google.com/file/f2",
                "modifiedTime": "2024-02-01T00:00:00Z",
            }
        ],
        "nextPageToken": "next_tok_xyz",
    }

    result = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="notes",
    )

    assert result.endswith("nextPageToken: next_tok_xyz")


@pytest.mark.asyncio
async def test_search_drive_files_no_next_page_token_when_absent():
    """nextPageToken does not appear in output when the API has no more pages."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            {
                "id": "f3",
                "name": "Summary.txt",
                "mimeType": "text/plain",
                "webViewLink": "https://drive.google.com/file/f3",
                "modifiedTime": "2024-03-01T00:00:00Z",
            }
        ]
        # no nextPageToken key
    }

    result = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="summary",
    )

    assert "nextPageToken" not in result


# ---------------------------------------------------------------------------
# list_drive_items — page_token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_drive_items_page_token_passed_to_api(mock_resolve_folder):
    """page_token is forwarded to the Drive API as pageToken."""
    mock_resolve_folder.return_value = "root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            {
                "id": "folder1",
                "name": "Archive",
                "mimeType": "application/vnd.google-apps.folder",
                "webViewLink": "https://drive.google.com/drive/folders/folder1",
                "modifiedTime": "2024-01-15T00:00:00Z",
            }
        ]
    }

    await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        page_token="tok_page2",
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert call_kwargs.get("pageToken") == "tok_page2"


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_drive_items_next_page_token_in_output(mock_resolve_folder):
    """nextPageToken from the API response is appended at the end of the output."""
    mock_resolve_folder.return_value = "root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            {
                "id": "file99",
                "name": "data.csv",
                "mimeType": "text/csv",
                "webViewLink": "https://drive.google.com/file/file99",
                "modifiedTime": "2024-04-01T00:00:00Z",
            }
        ],
        "nextPageToken": "next_list_tok",
    }

    result = await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
    )

    assert result.endswith("nextPageToken: next_list_tok")


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_drive_items_no_next_page_token_when_absent(mock_resolve_folder):
    """nextPageToken does not appear in output when the API has no more pages."""
    mock_resolve_folder.return_value = "root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            {
                "id": "file100",
                "name": "readme.txt",
                "mimeType": "text/plain",
                "webViewLink": "https://drive.google.com/file/file100",
                "modifiedTime": "2024-05-01T00:00:00Z",
            }
        ]
        # no nextPageToken key
    }

    result = await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
    )

    assert "nextPageToken" not in result


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
