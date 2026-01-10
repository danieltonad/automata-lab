import asyncio, argparse, sys, math, time, re
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple


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


def save_tiktok_metadata_json(metadata: TiktokPageMetadata, filepath: Path) -> None:
    import json
    with open(filepath, 'w', encoding='utf-8') as output_file:
        json.dump(metadata.__dict__, output_file, ensure_ascii=False, indent=4)

async def is_loading_visible(page):
    """
    Check if the TikTok loading spinner is visible inside the user-page container.
    Looks for the SVG with circle stroke="#3AF2FF".
    """
    return await page.evaluate("""
        () => {
            const container = document.querySelector('div[data-e2e="user-page"]');
            //if (!container) return false;

            const svg = Array.from(container.querySelectorAll('svg'))
                .find(s => s.querySelector('circle[stroke="#3AF2FF"]'));
            if (!svg) return false;

            const style = window.getComputedStyle(svg);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;

            const rect = svg.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            const visibleHorizontally = rect.right > containerRect.left && rect.left < containerRect.right;
            const visibleVertically = rect.bottom > containerRect.top && rect.top < containerRect.bottom;

            return visibleHorizontally && visibleVertically;
        }
    """)

async def pull_reposts(page, url: str) -> List[str]:
    await page.goto(url)

    # click on reposts tab
    try:
        await page.locator('p[data-e2e="repost-tab"]').click()
    except:
        print("No reposts tab found.")
        return []

    await page.locator('div[data-e2e="user-repost-item-list"]').click()
    await page.mouse.wheel(0, 10_000)
    state = True
    false_streak = 0

    while state:
        for _ in range(5):
            await page.mouse.wheel(0, 2000)
            is_loading = await is_loading_visible(page)
            if is_loading:
                false_streak = 0  # reset if we see True
            else:
                false_streak += 1
            await asyncio.sleep(0.5)

        # after every batch of 5
        if false_streak >= 5:
            state = False
    videos = []
    videos = await page.evaluate("""
            () => {
            return Array.from(
                document.querySelectorAll('div[class*="DivPlayerContainer"]')
            ).map(item => {
                const linkEl = item.querySelector('a[class*="VideoContainer"]');
                const viewsEl = item.querySelector('strong[data-e2e="video-views"]');
                const imgEl = item.querySelector('picture img');

                return {
                link: linkEl?.href || null,
                views: viewsEl?.innerText || null,
                thumbnail: imgEl?.src || null
                };
            });
            }
            """)
    return videos

async def pull_metadata_from_page(page, url: str) -> TiktokPageMetadata:
    await page.goto(url)
    author = await page.locator('h1[data-e2e="user-title"]').inner_text()
    name = await page.locator('h2[data-e2e="user-subtitle"]').inner_text()
    following = await page.locator('strong[data-e2e="following-count"]').inner_text()
    followers = await page.locator('strong[data-e2e="followers-count"]').inner_text()
    likes = await page.locator('strong[data-e2e="likes-count"]').inner_text()
    bio = await page.locator('h2[data-e2e="user-bio"]').inner_text()
    link_elements = await page.locator('span[class*="SpanLink"]').all()
    link = await link_elements[0].inner_text() if link_elements else None
    page_image = await page.locator('img[src*="tiktokcdn"]').first.get_attribute('src')

    await page.locator('div[data-e2e="user-post-item-list"]').click()
    await page.mouse.wheel(0, 10_000)
    state = True
    false_streak = 0

    while state:
        for _ in range(5):
            await page.mouse.wheel(0, 2000)
            is_loading = await is_loading_visible(page)
            if is_loading:
                false_streak = 0  # reset if we see True
            else:
                false_streak += 1
            await asyncio.sleep(0.5)

        # after every batch of 5
        if false_streak >= 5:
            state = False

    videos = []
    videos = await page.evaluate("""
            () => {
            return Array.from(
                document.querySelectorAll('div[class*="DivItemContainer"]')
            ).map(item => {
                const linkEl = item.querySelector('a[class*="VideoContainer"]');
                const viewsEl = item.querySelector('strong[data-e2e="video-views"]');
                const imgEl = item.querySelector('picture img');

                return {
                link: linkEl?.href || null,
                views: viewsEl?.innerText || null,
                thumbnail: imgEl?.src || null
                };
            });
            }
            """)

    return TiktokPageMetadata(
        name=name,
        author=author,
        page_image=page_image,
        following=following,
        followers=followers,
        likes=likes,
        bio=bio,
        link=link,
        videos=videos,
        playlists=[],
        reposts=[]
    )



async def fetch_tiktok_page_metadata(url: str) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()
        metadata = await pull_metadata_from_page(page, url)
        metadata.reposts = await pull_reposts(page, url)
        save_tiktok_metadata_json(metadata, Path("tiktok_page_metadata.json"))
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
