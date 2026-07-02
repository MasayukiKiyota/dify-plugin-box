import base64
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from box_utils import BoxApiError, BoxUtils


class DownloadFileTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Download a file from Box.
        """
        file_id = tool_parameters.get("file_id", "")
        include_content = tool_parameters.get("include_content", False)

        if not file_id:
            yield self.create_text_message("File ID is required.")
            return

        access_token = self.runtime.credentials.get("access_token")
        if not access_token:
            yield self.create_text_message("Box access token is required.")
            return

        try:
            result = BoxUtils.download_file(access_token, file_id)
        except BoxApiError as e:
            yield self.create_text_message(str(e))
            return
        except Exception as e:
            yield self.create_text_message(f"Error downloading file: {str(e)}")
            return

        content: bytes = result["content"]

        response = {
            "id": result["id"],
            "name": result["name"],
            "size": result["size"],
            "modified": result["modified"],
            "mime_type": result["mime_type"],
        }

        if include_content:
            response["content_base64"] = base64.b64encode(content).decode("utf-8")
            # Provide decoded text as well for small text files.
            if result.get("size") and result["size"] < 1024 * 1024:
                try:
                    response["content_text"] = content.decode("utf-8")
                except UnicodeDecodeError:
                    pass

        yield self.create_text_message(f"File '{result['name']}' downloaded successfully.")
        yield self.create_json_message(response)
        # Emit the raw file so it can be consumed as a file variable in Dify.
        yield self.create_blob_message(
            content,
            meta={"file_name": result["name"], "mime_type": result["mime_type"]},
        )
