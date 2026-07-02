from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from box_utils import BoxApiError, BoxUtils


class DeleteFileTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Delete a file or folder from Box.
        """
        item_id = tool_parameters.get("item_id", "")
        is_folder = bool(tool_parameters.get("is_folder", False))

        if not item_id:
            yield self.create_text_message("File or folder ID is required.")
            return

        access_token = self.runtime.credentials.get("access_token")
        if not access_token:
            yield self.create_text_message("Box access token is required.")
            return

        try:
            result = BoxUtils.delete_item(access_token, item_id, is_folder)
        except BoxApiError as e:
            if e.status_code == 404:
                yield self.create_text_message(f"No item found with ID '{item_id}'.")
            else:
                yield self.create_text_message(str(e))
            return
        except Exception as e:
            yield self.create_text_message(f"Error deleting item: {str(e)}")
            return

        item_type = "Folder" if is_folder else "File"
        yield self.create_text_message(f"{item_type} '{item_id}' deleted successfully.")
        yield self.create_json_message(result)
