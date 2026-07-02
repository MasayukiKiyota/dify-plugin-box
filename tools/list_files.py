from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from box_utils import BoxApiError, BoxUtils


class ListFilesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        List files and folders inside a Box folder.
        """
        folder_id = tool_parameters.get("folder_id") or BoxUtils.ROOT_FOLDER_ID
        try:
            limit = int(tool_parameters.get("limit", 100))
        except (TypeError, ValueError):
            limit = 100

        access_token = self.runtime.credentials.get("access_token")
        if not access_token:
            yield self.create_text_message("Box access token is required.")
            return

        try:
            items = BoxUtils.list_folder(access_token, folder_id, limit)
        except BoxApiError as e:
            yield self.create_text_message(str(e))
            return
        except Exception as e:
            yield self.create_text_message(f"Error listing folder contents: {str(e)}")
            return

        if not items:
            yield self.create_text_message(f"No files or folders found in folder '{folder_id}'.")
            return

        result = {
            "folder_id": folder_id,
            "item_count": len(items),
            "items": items,
        }
        yield self.create_text_message(f"Found {len(items)} items in folder '{folder_id}'.")
        yield self.create_json_message(result)
