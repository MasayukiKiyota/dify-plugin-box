from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from box_utils import BoxApiError, BoxUtils


class CreateFolderTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Create a new folder in Box.
        """
        name = tool_parameters.get("name", "")
        parent_folder_id = tool_parameters.get("parent_folder_id") or BoxUtils.ROOT_FOLDER_ID

        if not name:
            yield self.create_text_message("Folder name is required.")
            return

        access_token = self.runtime.credentials.get("access_token")
        if not access_token:
            yield self.create_text_message("Box access token is required.")
            return

        try:
            result = BoxUtils.create_folder(access_token, name, parent_folder_id)
        except BoxApiError as e:
            if e.status_code == 409:
                yield self.create_text_message(
                    f"A folder named '{name}' already exists in folder '{parent_folder_id}'."
                )
            else:
                yield self.create_text_message(str(e))
            return
        except Exception as e:
            yield self.create_text_message(f"Error creating folder: {str(e)}")
            return

        yield self.create_text_message(
            f"Folder '{result['name']}' created successfully (ID: {result['id']})."
        )
        yield self.create_json_message(result)
