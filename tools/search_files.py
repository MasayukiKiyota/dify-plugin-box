from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from box_utils import BoxApiError, BoxUtils


class SearchFilesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Search for files and folders in Box.
        """
        query = tool_parameters.get("query", "")
        if not query:
            yield self.create_text_message("Search query is required.")
            return

        try:
            max_results = int(tool_parameters.get("max_results", 10))
        except (TypeError, ValueError):
            max_results = 10

        access_token = self.runtime.credentials.get("access_token")
        if not access_token:
            yield self.create_text_message("Box access token is required.")
            return

        try:
            items = BoxUtils.search(access_token, query, max_results)
        except BoxApiError as e:
            yield self.create_text_message(str(e))
            return
        except Exception as e:
            yield self.create_text_message(f"Error searching Box: {str(e)}")
            return

        if not items:
            yield self.create_text_message(f"No results found for '{query}'.")
            return

        result = {
            "query": query,
            "result_count": len(items),
            "results": items,
        }
        yield self.create_text_message(f"Found {len(items)} items matching '{query}'.")
        yield self.create_json_message(result)
