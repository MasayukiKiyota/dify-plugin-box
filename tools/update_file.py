from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from box_utils import BoxApiError, BoxUtils


class UpdateFileTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Move a file to another folder and/or rename it in Box.
        """
        item_id = tool_parameters.get("item_id", "")
        new_name = (tool_parameters.get("new_name") or "").strip()
        parent_folder_id = (tool_parameters.get("parent_folder_id") or "").strip()

        if not item_id:
            yield self.create_text_message("File ID is required.")
            return

        if not new_name and not parent_folder_id:
            yield self.create_text_message(
                "Provide a new name and/or a destination folder ID."
            )
            return

        if parent_folder_id == BoxUtils.ROOT_FOLDER_ID:
            yield self.create_text_message(
                "Moving a file to the root folder (ID '0') is not allowed. "
                "Please specify a non-root destination folder ID."
            )
            return

        access_token = self.runtime.credentials.get("access_token")
        if not access_token:
            yield self.create_text_message("Box access token is required.")
            return

        try:
            result = BoxUtils.update_file(
                access_token,
                item_id,
                new_name=new_name or None,
                parent_folder_id=parent_folder_id or None,
            )
        except BoxApiError as e:
            if e.status_code == 404:
                yield self.create_text_message(f"No file found with ID '{item_id}'.")
            elif e.status_code == 409:
                if new_name:
                    yield self.create_text_message(
                        f"A file named '{new_name}' already exists in the destination folder."
                    )
                else:
                    yield self.create_text_message(
                        "A file with the same name already exists in the destination folder."
                    )
            else:
                yield self.create_text_message(str(e))
            return
        except Exception as e:
            yield self.create_text_message(f"Error updating file: {str(e)}")
            return

        actions = []
        if new_name:
            actions.append(f"renamed to '{result['name']}'")
        if parent_folder_id:
            actions.append(f"moved to folder '{parent_folder_id}'")
        yield self.create_text_message(
            f"File '{item_id}' {' and '.join(actions)} successfully."
        )
        yield self.create_json_message(result)
