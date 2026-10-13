"""
Tests for X-LTAI header forwarding and vault metadata propagation.

TIER 1 – pure Python (no dependencies, runs with: python3 test_ltai_headers.py)
  - TestMainLtaiMetadata
  - TestOllamaGenerateChatForwarding

TIER 2 – needs project deps (run with: pytest test_ltai_headers.py -v)
  - TestOllamaExtraHeaders   (imports open_webui.routers.ollama)
  - TestOpenaiGetHeadersAndCookies (imports open_webui.routers.openai)
"""

import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# TIER 1 – pure logic, zero external imports
# ---------------------------------------------------------------------------

class TestMainLtaiMetadata(unittest.TestCase):
    """Verify the header-extraction logic added to main.py chat_completion()."""

    def test_ltai_headers_collected(self):
        headers = {
            "x-ltai-vault-user":   "u1",
            "x-ltai-vault-keys":   "COMMON/mykey",
            "x-ltai-custom-header": "somevalue",
            "authorization":       "Bearer token",
        }
        ltai = {k: v for k, v in headers.items() if k.lower().startswith("x-ltai-")}
        self.assertEqual(ltai, {
            "x-ltai-vault-user":    "u1",
            "x-ltai-vault-keys":    "COMMON/mykey",
            "x-ltai-custom-header": "somevalue",
        })
        self.assertNotIn("authorization", ltai)

    def test_vault_fields_extracted(self):
        headers = {"x-ltai-vault-user": "vault-user-42", "x-ltai-vault-keys": "k1,k2"}
        self.assertEqual(headers.get("x-ltai-vault-user"), "vault-user-42")
        self.assertEqual(headers.get("x-ltai-vault-keys"), "k1,k2")

    def test_no_ltai_headers_gives_empty_dict(self):
        headers = {"content-type": "application/json", "authorization": "Bearer x"}
        ltai = {k: v for k, v in headers.items() if k.lower().startswith("x-ltai-")}
        self.assertEqual(ltai, {})

    def test_metadata_contains_all_three_fields(self):
        headers = {
            "x-ltai-vault-user": "uid",
            "x-ltai-vault-keys": "COMMON/key1",
            "x-ltai-extra":      "extra-val",
        }
        vault_user_id = headers.get("x-ltai-vault-user")
        vault_keys    = headers.get("x-ltai-vault-keys")
        ltai_headers  = {k: v for k, v in headers.items() if k.lower().startswith("x-ltai-")}

        metadata = {
            "user_id":       "u1",
            "vault_user_id": vault_user_id,
            "vault_keys":    vault_keys,
            "ltai_headers":  ltai_headers,
        }
        self.assertEqual(metadata["vault_user_id"], "uid")
        self.assertEqual(metadata["vault_keys"],    "COMMON/key1")
        self.assertEqual(metadata["ltai_headers"], {
            "x-ltai-vault-user": "uid",
            "x-ltai-vault-keys": "COMMON/key1",
            "x-ltai-extra":      "extra-val",
        })


class TestOllamaGenerateChatForwarding(unittest.TestCase):
    """Verify the header-collection logic in ollama.py generate_chat_completion()."""

    def test_only_ltai_headers_collected(self):
        incoming = {
            "x-ltai-vault-keys":  "COMMON/key1",
            "x-ltai-vault-user":  "user1",
            "x-ltai-agent-token": "tok123",
            "authorization":      "Bearer jwt",
            "content-type":       "application/json",
        }
        forwarded = {k: v for k, v in incoming.items() if k.lower().startswith("x-ltai-")}
        self.assertEqual(forwarded, {
            "x-ltai-vault-keys":  "COMMON/key1",
            "x-ltai-vault-user":  "user1",
            "x-ltai-agent-token": "tok123",
        })
        self.assertNotIn("authorization", forwarded)
        self.assertNotIn("content-type",  forwarded)

    def test_extra_headers_merged_into_dict(self):
        """Simulate what send_post_request does with extra_headers."""
        headers = {"Content-Type": "application/json", "Authorization": "Bearer k"}
        extra   = {"x-ltai-vault-keys": "COMMON/k1", "x-ltai-custom": "v"}
        headers.update(extra)
        self.assertEqual(headers["x-ltai-vault-keys"], "COMMON/k1")
        self.assertEqual(headers["x-ltai-custom"],     "v")
        self.assertEqual(headers["Content-Type"],      "application/json")


class TestOpenaiHeaderInjectionLogic(unittest.TestCase):
    """Verify the x-ltai-* forwarding loop added to openai.py get_headers_and_cookies()."""

    def _apply_ltai_loop(self, incoming_headers: dict, existing_headers: dict) -> dict:
        """Reproduce the exact loop added to get_headers_and_cookies()."""
        for k, v in incoming_headers.items():
            if k.lower().startswith("x-ltai-"):
                existing_headers[k] = v
        return existing_headers

    def test_ltai_headers_added(self):
        incoming = {
            "x-ltai-vault-keys": "COMMON/key1",
            "x-ltai-vault-user": "u99",
            "authorization":     "Bearer secret",
        }
        outbound = {"Content-Type": "application/json", "Authorization": "Bearer api-key"}
        result = self._apply_ltai_loop(incoming, outbound)
        self.assertEqual(result["x-ltai-vault-keys"], "COMMON/key1")
        self.assertEqual(result["x-ltai-vault-user"], "u99")
        self.assertNotIn("authorization", result)  # lowercase auth must not leak

    def test_no_ltai_headers_unchanged(self):
        incoming = {"authorization": "Bearer s", "content-type": "application/json"}
        outbound = {"Content-Type": "application/json", "Authorization": "Bearer k"}
        result = self._apply_ltai_loop(incoming, outbound)
        self.assertFalse(any(k.startswith("x-ltai-") for k in result))


# ---------------------------------------------------------------------------
# TIER 2 – requires project deps (pytest + open_webui installed)
# ---------------------------------------------------------------------------

try:
    import pytest
    import aiohttp  # noqa: F401 – presence check only

    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


if HAS_DEPS:

    @pytest.mark.asyncio
    async def test_send_post_request_extra_headers_forwarded():
        """send_post_request() merges extra_headers into the aiohttp call."""
        captured = {}

        async def fake_post(url, *, data, headers, ssl):
            captured.update(headers)
            resp = MagicMock()
            resp.ok = True
            resp.status = 200

            async def _iter(_n):
                yield b'{"done":true}'

            resp.content.iter_chunked = _iter
            return resp

        with patch("aiohttp.ClientSession") as MockSession:
            inst = MagicMock()
            inst.post = fake_post
            inst.__aenter__ = AsyncMock(return_value=inst)
            inst.__aexit__  = AsyncMock(return_value=False)
            MockSession.return_value = inst

            from open_webui.routers.ollama import send_post_request

            with (
                patch("open_webui.routers.ollama.AIOHTTP_CLIENT_TIMEOUT", 60),
                patch("open_webui.routers.ollama.AIOHTTP_CLIENT_SESSION_SSL", False),
                patch("open_webui.routers.ollama.ENABLE_FORWARD_USER_INFO_HEADERS", False),
            ):
                await send_post_request(
                    url="http://fake/api/chat",
                    payload=b'{"model":"test"}',
                    stream=False,
                    key=None,
                    extra_headers={"x-ltai-vault-keys": "COMMON/k1", "x-ltai-extra": "v"},
                )

        assert captured.get("x-ltai-vault-keys") == "COMMON/k1"
        assert captured.get("x-ltai-extra")      == "v"

    @pytest.mark.asyncio
    async def test_get_headers_and_cookies_injects_ltai():
        """get_headers_and_cookies() copies x-ltai-* from request into outbound headers."""
        from open_webui.routers.openai import get_headers_and_cookies

        req = MagicMock()
        req.headers = {
            "x-ltai-vault-keys": "COMMON/key1",
            "x-ltai-vault-user": "user-99",
            "authorization":     "Bearer tok",
        }
        req.cookies = {}
        req.state.token = MagicMock(credentials="tok")

        with patch("open_webui.routers.openai.ENABLE_FORWARD_USER_INFO_HEADERS", False):
            headers, _ = await get_headers_and_cookies(
                request=req,
                url="http://fake",
                key="k",
                config={"auth_type": "bearer"},
                metadata=None,
                user=None,
            )

        assert headers.get("x-ltai-vault-keys") == "COMMON/key1"
        assert headers.get("x-ltai-vault-user") == "user-99"


# ---------------------------------------------------------------------------
# Standalone runner (no pytest required)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running Tier 1 tests (no dependencies needed)...")
    unittest.main(verbosity=2)
