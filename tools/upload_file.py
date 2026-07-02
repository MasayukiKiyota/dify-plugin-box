import base64
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from box_utils import BoxApiError, BoxUtils


class UploadFileTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Upload a new file to Box.
        """
        file_name = tool_parameters.get("file_name", "")
        parent_folder_id = tool_parameters.get("parent_folder_id") or BoxUtils.ROOT_FOLDER_ID
        file_content = tool_parameters.get("file_content", "")
        file_content_base64 = tool_parameters.get("file_content_base64", "")

        if not file_name:
            yield self.create_text_message("File name is required.")
            return

        if not file_content and not file_content_base64:
            yield self.create_text_message("File content is required (either as text or base64).")
            return

        access_token = self.runtime.credentials.get("access_token")
        if not access_token:
            yield self.create_text_message("Box access token is required.")
            return

        if file_content_base64:
            try:
                content = base64.b64decode(file_content_base64)
            except Exception:
                yield self.create_text_message("Invalid base64 content provided.")
                return
        else:
            content = file_content.encode("utf-8")

        try:
            result = BoxUtils.upload_file(access_token, file_name, content, parent_folder_id)
        except BoxApiError as e:
            if e.status_code == 409:
                yield self.create_text_message(
                    f"A file named '{file_name}' already exists in folder '{parent_folder_id}'."
                )
            else:
                yield self.create_text_message(str(e))
            return
        except Exception as e:
            yield self.create_text_message(f"Error uploading file: {str(e)}")
            return

        yield self.create_text_message(
            f"File '{result['name']}' uploaded successfully (ID: {result['id']})."
        )
        yield self.create_json_message(result)
