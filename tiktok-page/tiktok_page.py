import asyncio, argparse, sys, math, time
import psutil, re
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from dataclasses import dataclass
from typing import List, Set, Tuple

from tiktok.tiktok import TiktokPageMetadata


@dataclass
class TiktokPageMetadata:
    name: str
    author: str
    following: str
    followers: str
    likes: str
    bio: str
    link: str
    videos: List[str] = None
    playlists: List[str] = None
    repos: List[str] = None


class Colors:
    RESET = "\033[0m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    GRAY = "\033[90m"


def log(message: str) -> None:
    with open("tiktok_page.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


def time_taken(start: float, stop: float) -> str:
    elapsed = stop - start
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)

def is_tiktok_url(url: str) -> bool:
    return "tiktok.com/" in url

def get_author_from_url(url: str) -> str:
    match = re.search(r'tiktok\.com/@([^/]+)/', url)
    return match.group(1) if match else ""


def save_tiktok_metadata_json(metadatas: List[TiktokPageMetadata], filepath: Path) -> None:
    import json
    with open(filepath, 'w', encoding='utf-8') as output_file:
        json.dump([s.__dict__ for s in metadatas], output_file, ensure_ascii=False, indent=4)

async def fetch_tiktok_page_metadata(url: str, page, retry: int = 0) -> TiktokPageMetadata:
    await page.goto(url, timeout=60000)
    comment_count = await page.locator('strong[data-e2e="comment-count"]').first.inner_text()
    likes = await page.locator('strong[data-e2e="like-count"]').first.inner_text()
    bookmarks = await page.locator('strong[data-e2e="undefined-count"]').first.inner_text()
    shares = await page.locator('strong[data-e2e="share-count"]').first.inner_text()
    description = await page.locator('div[data-e2e="video-desc"]').first.inner_text()



async def main():
    if len(sys.argv) < 2:
        print("Usage: python tiktok_page.py <page_name_or_link_or_id>")
        sys.exit(1)
    page_input = sys.argv[1]
    await grab_channel_info(normalize_page_input(page_input))


if __name__ == "__main__":
    asyncio.run(main())
