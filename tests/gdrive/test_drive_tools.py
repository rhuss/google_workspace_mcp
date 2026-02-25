"""
Unit tests for Google Drive MCP tools.

Tests create_drive_folder with mocked API responses,
and the list_drive_items and search_drive_files tools 
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


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



from gdrive.drive_tools import list_drive_items, search_drive_files


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unwrap(tool):
    """Unwrap a FunctionTool + decorator chain to the original async function."""
    fn = tool.fn
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn

def _make_file(
    file_id: str,
    name: str,
    mime_type: str,
    link: str = "http://link",
    modified: str = "2024-01-01T00:00:00Z",
) -> dict:
    return {
        "id": file_id,
        "name": name,
        "mimeType": mime_type,
        "webViewLink": link,
        "modifiedTime": modified,
    }


# ---------------------------------------------------------------------------
# search_drive_files
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_free_text_returns_results():
    """Free-text query is wrapped in fullText contains and results are formatted."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _make_file("f1", "My Doc", "application/vnd.google-apps.document"),
        ]
    }

    result = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="my doc",
    )

    assert "Found 1 files" in result
    assert "My Doc" in result
    assert "f1" in result


@pytest.mark.asyncio
async def test_search_no_results():
    """No results returns a clear message."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    result = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="nothing here",
    )

    assert "No files found" in result


@pytest.mark.asyncio
async def test_search_file_type_folder_adds_mime_filter():
    """file_type='folder' appends the folder MIME type to the query."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _make_file(
                "fold1", "My Folder", "application/vnd.google-apps.folder"
            )
        ]
    }

    result = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="my",
        file_type="folder",
    )

    assert "Found 1 files" in result
    assert "My Folder" in result

    # Verify the API was called with the mimeType filter in the query
    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "mimeType = 'application/vnd.google-apps.folder'" in call_kwargs["q"]


@pytest.mark.asyncio
async def test_search_file_type_document_alias():
    """Alias 'doc' resolves to the Google Docs MIME type."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="report",
        file_type="doc",
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "mimeType = 'application/vnd.google-apps.document'" in call_kwargs["q"]


@pytest.mark.asyncio
async def test_search_file_type_sheet_alias():
    """Alias 'sheet' resolves to the Google Sheets MIME type."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="budget",
        file_type="sheet",
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "mimeType = 'application/vnd.google-apps.spreadsheet'" in call_kwargs["q"]


@pytest.mark.asyncio
async def test_search_file_type_raw_mime():
    """A raw MIME type string is passed through unchanged."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [_make_file("p1", "Report.pdf", "application/pdf")]
    }

    result = await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="report",
        file_type="application/pdf",
    )

    assert "Report.pdf" in result
    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "mimeType = 'application/pdf'" in call_kwargs["q"]


@pytest.mark.asyncio
async def test_search_file_type_none_no_mime_filter():
    """When file_type is None no mimeType clause is added to the query."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="anything",
        file_type=None,
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "mimeType" not in call_kwargs["q"]


@pytest.mark.asyncio
async def test_search_file_type_structured_query_combined():
    """file_type filter is appended even when the query is already structured."""
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(search_drive_files)(
        service=mock_service,
        user_google_email="user@example.com",
        query="name contains 'budget'",  # structured query
        file_type="spreadsheet",
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    q = call_kwargs["q"]
    assert "name contains 'budget'" in q
    assert "mimeType = 'application/vnd.google-apps.spreadsheet'" in q


@pytest.mark.asyncio
async def test_search_file_type_unknown_raises_value_error():
    """An unrecognised friendly type name raises ValueError immediately."""
    mock_service = Mock()

    with pytest.raises(ValueError, match="Unknown file_type"):
        await _unwrap(search_drive_files)(
            service=mock_service,
            user_google_email="user@example.com",
            query="something",
            file_type="notatype",
        )


# ---------------------------------------------------------------------------
# list_drive_items
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_items_basic(mock_resolve_folder):
    """Basic listing without filters returns all items."""
    mock_resolve_folder.return_value = "resolved_root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _make_file("id1", "Folder A", "application/vnd.google-apps.folder"),
            _make_file("id2", "Doc B", "application/vnd.google-apps.document"),
        ]
    }

    result = await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="root",
    )

    assert "Found 2 items" in result
    assert "Folder A" in result
    assert "Doc B" in result


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_items_no_results(mock_resolve_folder):
    """Empty folder returns a clear message."""
    mock_resolve_folder.return_value = "resolved_root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    result = await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="root",
    )

    assert "No items found" in result


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_items_file_type_folder_adds_mime_filter(mock_resolve_folder):
    """file_type='folder' appends the folder MIME clause to the query."""
    mock_resolve_folder.return_value = "resolved_root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {
        "files": [
            _make_file("sub1", "SubFolder", "application/vnd.google-apps.folder")
        ]
    }

    result = await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="root",
        file_type="folder",
    )

    assert "Found 1 items" in result
    assert "SubFolder" in result

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    q = call_kwargs["q"]
    assert "'resolved_root' in parents" in q
    assert "trashed=false" in q
    assert "mimeType = 'application/vnd.google-apps.folder'" in q


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_items_file_type_spreadsheet(mock_resolve_folder):
    """file_type='spreadsheet' appends the Sheets MIME clause."""
    mock_resolve_folder.return_value = "folder_xyz"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="folder_xyz",
        file_type="spreadsheet",
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "mimeType = 'application/vnd.google-apps.spreadsheet'" in call_kwargs["q"]


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_items_file_type_raw_mime(mock_resolve_folder):
    """A raw MIME type string is passed through unchanged."""
    mock_resolve_folder.return_value = "folder_abc"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="folder_abc",
        file_type="application/pdf",
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "mimeType = 'application/pdf'" in call_kwargs["q"]


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_items_file_type_none_no_mime_filter(mock_resolve_folder):
    """When file_type is None no mimeType clause is added."""
    mock_resolve_folder.return_value = "resolved_root"
    mock_service = Mock()
    mock_service.files().list().execute.return_value = {"files": []}

    await _unwrap(list_drive_items)(
        service=mock_service,
        user_google_email="user@example.com",
        folder_id="root",
        file_type=None,
    )

    call_kwargs = mock_service.files.return_value.list.call_args.kwargs
    assert "mimeType" not in call_kwargs["q"]


@pytest.mark.asyncio
@patch("gdrive.drive_tools.resolve_folder_id", new_callable=AsyncMock)
async def test_list_items_file_type_unknown_raises(mock_resolve_folder):
    """An unrecognised friendly type name raises ValueError."""
    mock_resolve_folder.return_value = "resolved_root"
    mock_service = Mock()

    with pytest.raises(ValueError, match="Unknown file_type"):
        await _unwrap(list_drive_items)(
            service=mock_service,
            user_google_email="user@example.com",
            folder_id="root",
            file_type="unknowntype",
        )
