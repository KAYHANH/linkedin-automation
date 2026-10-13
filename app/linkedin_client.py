"""Official LinkedIn API client for OAuth verification and post publishing."""

import logging
from typing import Any, Dict, Optional
import httpx

from app.config import get_settings
from app.models import LinkedInPostResponse

logger = logging.getLogger(__name__)


class LinkedInClient:
    """Official LinkedIn API client supporting both modern Posts API and UGC Posts API."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        author_urn: Optional[str] = None,
        api_version: Optional[str] = None,
        endpoint_style: Optional[str] = None,
        client: Optional[httpx.Client] = None
    ):
        settings = get_settings()
        self.access_token = access_token or settings.linkedin_access_token
        self.author_urn = author_urn or settings.linkedin_author_urn
        self.api_version = api_version or settings.linkedin_api_version
        self.endpoint_style = (endpoint_style or settings.linkedin_endpoint_style).lower()
        self._custom_client = client

    def _get_client(self) -> httpx.Client:
        return self._custom_client or httpx.Client(timeout=25.0)

    def publish_text_post(self, commentary: str) -> LinkedInPostResponse:
        """
        Publish a text-only LinkedIn post to the authenticated member's personal feed.
        Enforces at-most-once semantics: network timeouts are flagged as ambiguous and NEVER retried.
        """
        settings = get_settings()

        if not self.access_token:
            return LinkedInPostResponse(
                success=False,
                status_code=401,
                error_message="LINKEDIN_ACCESS_TOKEN is missing. Cannot publish to LinkedIn."
            )

        if not self.author_urn:
            return LinkedInPostResponse(
                success=False,
                status_code=400,
                error_message="LINKEDIN_AUTHOR_URN is missing. Cannot identify post author."
            )

        if self.endpoint_style == "v2/ugcposts":
            return self._publish_via_ugc_posts(commentary)
        else:
            return self._publish_via_rest_posts(commentary)

    def _publish_via_rest_posts(self, commentary: str) -> LinkedInPostResponse:
        """
        Publish using official Posts API (POST https://api.linkedin.com/rest/posts).
        Requires 'w_member_social' permission and Linkedin-Version header.
        """
        settings = get_settings()
        url = "https://api.linkedin.com/rest/posts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": self.api_version,
            "Content-Type": "application/json",
            "User-Agent": "Groq-LinkedIn-Automation/1.0"
        }

        payload: Dict[str, Any] = {
            "author": self.author_urn,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        client = self._get_client()
        try:
            resp = client.post(url, headers=headers, json=payload)
            response_headers = {k.lower(): v for k, v in resp.headers.items()}

            if resp.status_code == 201:
                # Posts API returns post URN in x-restli-id header
                post_id = resp.headers.get("x-restli-id") or resp.headers.get("X-RestLi-Id")
                if not post_id and resp.text:
                    try:
                        post_id = resp.json().get("id")
                    except Exception:
                        pass
                post_id = post_id or f"confirmed_{resp.status_code}"

                logger.info("Successfully published post to LinkedIn Posts API. Post ID: %s", post_id)
                return LinkedInPostResponse(
                    success=True,
                    status_code=resp.status_code,
                    post_id=post_id,
                    response_headers=response_headers
                )

            # Error handling
            redacted_text = settings.redact(resp.text)
            if resp.status_code == 401:
                error_msg = f"LinkedIn Unauthorized (401): Access token expired or invalid. Details: {redacted_text}"
            elif resp.status_code == 403:
                error_msg = f"LinkedIn Forbidden (403): Missing required 'w_member_social' scope or app not approved. Details: {redacted_text}"
            elif resp.status_code == 429:
                error_msg = f"LinkedIn Rate Limit Exceeded (429). Details: {redacted_text}"
            else:
                error_msg = f"LinkedIn API request failed with status {resp.status_code}: {redacted_text}"

            logger.error(error_msg)
            return LinkedInPostResponse(
                success=False,
                status_code=resp.status_code,
                error_message=error_msg,
                response_headers=response_headers
            )

        except httpx.TimeoutException as e:
            redacted_err = settings.redact(str(e))
            logger.critical("Ambiguous timeout occurred while publishing to LinkedIn: %s. REFUSING TO RETRY to prevent duplicate posting.", redacted_err)
            return LinkedInPostResponse(
                success=False,
                status_code=0,
                is_ambiguous_timeout=True,
                error_message=f"Ambiguous timeout during LinkedIn write request: {redacted_err}. At-most-once safety: manual reconciliation required."
            )
        except httpx.RequestError as e:
            redacted_err = settings.redact(str(e))
            logger.error("Network request error communicating with LinkedIn: %s", redacted_err)
            return LinkedInPostResponse(
                success=False,
                status_code=0,
                is_ambiguous_timeout=True,
                error_message=f"Network error during LinkedIn request: {redacted_err}."
            )

    def _publish_via_ugc_posts(self, commentary: str) -> LinkedInPostResponse:
        """
        Publish using official UGC Posts API (POST https://api.linkedin.com/v2/ugcPosts).
        Fallback for legacy self-serve Share on LinkedIn integrations.
        """
        settings = get_settings()
        url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "User-Agent": "Groq-LinkedIn-Automation/1.0"
        }

        payload: Dict[str, Any] = {
            "author": self.author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": commentary
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        client = self._get_client()
        try:
            resp = client.post(url, headers=headers, json=payload)
            response_headers = {k.lower(): v for k, v in resp.headers.items()}

            if resp.status_code == 201:
                post_id = resp.headers.get("x-restli-id")
                if not post_id and resp.text:
                    try:
                        post_id = resp.json().get("id")
                    except Exception:
                        pass
                post_id = post_id or f"confirmed_{resp.status_code}"

                logger.info("Successfully published post to LinkedIn UGC API. Post ID: %s", post_id)
                return LinkedInPostResponse(
                    success=True,
                    status_code=resp.status_code,
                    post_id=post_id,
                    response_headers=response_headers
                )

            redacted_text = settings.redact(resp.text)
            error_msg = f"LinkedIn UGC API failed with HTTP {resp.status_code}: {redacted_text}"
            logger.error(error_msg)
            return LinkedInPostResponse(
                success=False,
                status_code=resp.status_code,
                error_message=error_msg,
                response_headers=response_headers
            )

        except httpx.TimeoutException as e:
            redacted_err = settings.redact(str(e))
            logger.critical("Ambiguous timeout occurred while publishing to LinkedIn UGC API: %s.", redacted_err)
            return LinkedInPostResponse(
                success=False,
                status_code=0,
                is_ambiguous_timeout=True,
                error_message=f"Ambiguous timeout: {redacted_err}. Manual reconciliation required."
            )
        except httpx.RequestError as e:
            redacted_err = settings.redact(str(e))
            return LinkedInPostResponse(
                success=False,
                status_code=0,
                is_ambiguous_timeout=True,
                error_message=f"Network error: {redacted_err}."
            )

    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh OAuth 2.0 access token using refresh_token grant if configured.
        Returns refreshed token dictionary.
        """
        settings = get_settings()
        if not (settings.linkedin_client_id and settings.linkedin_client_secret and settings.linkedin_refresh_token):
            raise ValueError("LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, and LINKEDIN_REFRESH_TOKEN are required for token refresh.")

        url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": settings.linkedin_refresh_token,
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        client = self._get_client()
        resp = client.post(url, headers=headers, data=data)
        if resp.status_code == 200:
            return resp.json()
        else:
            redacted_resp = settings.redact(resp.text)
            raise RuntimeError(f"LinkedIn token refresh failed with HTTP {resp.status_code}: {redacted_resp}")
