"""Simple functions to download a text or JSON file from a web server."""

import asyncio
import logging
from time import perf_counter
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


async def _download_text(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    session: aiohttp.ClientSession | None = None,
) -> str:
    """Download a text file from a URL and return its content as a string."""
    logger.info(f"Downloading text from {url}")
    start = perf_counter()
    if session is None:
        session = aiohttp.ClientSession()
    if params is None:
        params = {}
    if headers is None:
        headers = {}
    if json is None:
        json = {}
    async with session.get(url, headers=headers, params=params, json=json) as response:
        logger.debug(
            f"Received response with status {response.status} from {response.real_url}"
        )
        logger.debug(f"Response headers: {response.headers}")
        response.raise_for_status()
        text = await response.text()
        await asyncio.sleep(0)  # allow other tasks to run
        logger.info(
            f"Downloaded text from {url} in {perf_counter() - start:.2f} seconds"
        )
        return text


def download_text(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    session: aiohttp.ClientSession | None = None,
) -> str:
    """Download a text file from a URL and return its content as a string."""
    return asyncio.run(
        _download_text(url, params=params, headers=headers, json=json, session=session)
    )


async def _download_json(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    session: aiohttp.ClientSession | None = None,
) -> Any:
    """Download a JSON file from a URL."""
    logger.info(f"Downloading JSON from {url}")
    start = perf_counter()
    if session is None:
        session = aiohttp.ClientSession()
    if params is None:
        params = {}
    if headers is None:
        headers = {}
    if json is None:
        json = {}
    async with session.get(url, headers=headers, params=params, json=json) as response:
        logger.debug(
            f"Received response with status {response.status} from {response.real_url}"
        )
        logger.debug(f"Response headers: {response.headers}")
        response.raise_for_status()
        json_data = await response.json()
        await asyncio.sleep(0)  # allow other tasks to run
        logger.info(
            f"Downloaded json from {url} in {perf_counter() - start:.2f} seconds"
        )
        return json_data


def download_json(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    session: aiohttp.ClientSession | None = None,
) -> Any:
    """Download a JSON file from a URL."""
    return asyncio.run(
        _download_json(url, params=params, headers=headers, json=json, session=session)
    )
