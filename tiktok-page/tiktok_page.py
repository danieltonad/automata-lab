import asyncio, argparse, sys, math, time, re
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from dataclasses import dataclass
from typing import List, Set, Tuple


@dataclass
class TiktokPageMetadata:
    name: str
    author: str
    page_image: str
    following: str
    followers: str
    likes: str
    bio: str
    link: str
    videos: List[str] = None
    playlists: List[str] = None
    reposts: List[str] = None


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


def save_tiktok_metadata_json(metadatas: List[TiktokPageMetadata], filepath: Path) -> None:
    import json
    with open(filepath, 'w', encoding='utf-8') as output_file:
        json.dump([s.__dict__ for s in metadatas], output_file, ensure_ascii=False, indent=4)


async def pull_info_from_page(page, url: str) -> TiktokPageMetadata:
    await page.goto(url)
    
    author = await page.locator('h1[data-e2e="user-title"]').inner_text()
    name = await page.locator('h2[data-e2e="user-subtitle"]').inner_text()
    following = await page.locator('strong[data-e2e="following-count"]').inner_text()
    followers = await page.locator('strong[data-e2e="followers-count"]').inner_text()
    likes = await page.locator('strong[data-e2e="likes-count"]').inner_text()
    bio = await page.locator('h2[data-e2e="user-bio"]').inner_text()
    link_elements = await page.locator('span[class*="SpanLink"]').all()
    link = await link_elements[0].inner_text() if link_elements else None
    page_image = await page.locator('div > span > img').first.get_attribute('src')


    # await page.evaluate("""
    #     async () => {
    #         let lastHeight = 0;

    #         while (true) {
    #             window.scrollBy(0, window.innerHeight);
    #             await new Promise(r => setTimeout(r, 500));

    #             const newHeight = document.body.scrollHeight;
    #             if (newHeight === lastHeight) break;
    #             lastHeight = newHeight;
    #         }
    #     }
    #     """)

    # await asyncio.sleep(5)
    # loading = await page.locator('svg circle[stroke="#3AF2FF"]').is_visible()
    # print("Loading indicator visible:", loading)

    return TiktokPageMetadata(
        name=name,
        author=author,
        page_image=page_image,
        following=following,
        followers=followers,
        likes=likes,
        bio=bio,
        link=link
    )



async def fetch_tiktok_page_metadata(url: str) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()
        metadata = await pull_info_from_page(page, url)
        print(metadata)
        await browser.close()


def normalize_page_input(page_input: str) -> str:
    if is_tiktok_url(page_input):
        return page_input
    else:
        return f"https://www.tiktok.com/@{page_input}"

async def main():
    if len(sys.argv) < 2:
        print("Usage: python tiktok_page.py <page_name_or_link_or_id>")
        sys.exit(1)
    page_input = sys.argv[1]
    await fetch_tiktok_page_metadata(normalize_page_input(page_input))


if __name__ == "__main__":
    asyncio.run(main())
