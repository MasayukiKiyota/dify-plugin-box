import time
import secrets
import urllib.parse
from collections.abc import Mapping
from typing import Any

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from werkzeug import Request

from dify_plugin import ToolProvider
from dify_plugin.entities.oauth import ToolOAuthCredentials
from dify_plugin.errors.tool import ToolProviderCredentialValidationError, ToolProviderOAuthError


class BoxProvider(ToolProvider):
    _AUTH_URL = "https://account.box.com/api/oauth2/authorize"
    _TOKEN_URL = "https://api.box.com/oauth2/token"
    _API_BASE_URL = "https://api.box.com/2.0"
    # Box OAuth apps do not use granular scopes in the authorization request;
    # the scopes are configured on the app itself in the Box Developer Console.

    def _get_requests_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.verify = certifi.where()
        return session

    def _validate_credentials(self, credentials: Mapping[str, Any]) -> None:
        """
        Validate that the stored access token can call the Box API.
        """
        access_token = credentials.get("access_token")
        if not access_token:
            raise ToolProviderCredentialValidationError("Box access token is required.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        session = self._get_requests_session()
        try:
            response = session.get(f"{self._API_BASE_URL}/users/me", headers=headers, timeout=30)
        except requests.RequestException as e:
            raise ToolProviderCredentialValidationError(
                f"Network error when validating Box credentials: {str(e)}"
            )

        if response.status_code == 401:
            raise ToolProviderCredentialValidationError(
                "Access token is invalid or expired. Please refresh or re-authorize."
            )
        elif response.status_code != 200:
            raise ToolProviderCredentialValidationError(
                f"Failed to validate credentials: {response.status_code} {response.text}"
            )

    def _oauth_get_authorization_url(self, redirect_uri: str, system_credentials: Mapping[str, Any]) -> str:
        """
        Generate the authorization URL for Box OAuth 2.0.
        """
        state = secrets.token_urlsafe(32)
        params = {
            "client_id": system_credentials["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    def _oauth_get_credentials(
        self, redirect_uri: str, system_credentials: Mapping[str, Any], request: Request
    ) -> ToolOAuthCredentials:
        """
        Exchange the authorization code for access and refresh tokens.
        """
        code = request.args.get("code")
        if not code:
            raise ToolProviderOAuthError("Authorization code not provided")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": system_credentials["client_id"],
            "client_secret": system_credentials["client_secret"],
            "redirect_uri": redirect_uri,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        session = self._get_requests_session()
        try:
            response = session.post(self._TOKEN_URL, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            response_data = response.json()
        except requests.RequestException as e:
            raise ToolProviderOAuthError(f"Failed to exchange code for token: {str(e)}")

        access_token = response_data.get("access_token")
        refresh_token = response_data.get("refresh_token")
        expires_at = int(time.time()) + response_data.get("expires_in", 3600)

        if not access_token:
            raise ToolProviderOAuthError(f"Failed to obtain access token: {response_data}")

        return ToolOAuthCredentials(
            expires_at=expires_at,
            credentials={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": response_data.get("token_type", "bearer"),
            },
        )

    def _oauth_refresh_credentials(
        self, redirect_uri: str, system_credentials: Mapping[str, Any], credentials: Mapping[str, Any]
    ) -> ToolOAuthCredentials:
        """
        Refresh the access token using the refresh token.
        """
        refresh_token = credentials.get("refresh_token")
        if not refresh_token:
            raise ToolProviderOAuthError("Refresh token not available")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": system_credentials["client_id"],
            "client_secret": system_credentials["client_secret"],
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        session = self._get_requests_session()
        try:
            response = session.post(self._TOKEN_URL, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            response_data = response.json()
        except requests.RequestException as e:
            raise ToolProviderOAuthError(f"Failed to refresh token: {str(e)}")

        access_token = response_data.get("access_token")
        new_refresh_token = response_data.get("refresh_token", refresh_token)
        expires_at = int(time.time()) + response_data.get("expires_in", 3600)

        if not access_token:
            raise ToolProviderOAuthError(f"Failed to refresh access token: {response_data}")

        return ToolOAuthCredentials(
            expires_at=expires_at,
            credentials={
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": response_data.get("token_type", "bearer"),
            },
        )
