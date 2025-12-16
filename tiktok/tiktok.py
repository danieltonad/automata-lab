import asyncio, argparse, sys, math, random, time
import psutil, re
from pathlib import Path
from playwright.async_api import async_playwright
from dataclasses import dataclass
from typing import List, Set, Tuple


@dataclass
class TiktokMetadata:
    link: str
    title: str
    likes: str
    comment_count: str
    views: str
    upload_date: str
    comments: List[str]

class Colors:
    RESET = "\033[0m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    GRAY = "\033[90m"


def optimal_chunk_size(n: int) -> int:
    """
    Compute optimal chunk size for YouTube scraping based on number of URLs and system resources.
    """
    if n <= 4:
        return max(1, n)
    if n <= 10:
        return max(2, n // 2)

    try:
        # Hardware metrics
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)  # in GB
        cpu_count = psutil.cpu_count(logical=True) or 1
        try:
            freq = psutil.cpu_freq()
            clock_ghz = freq.max / 1000.0 if freq and freq.max > 0 else freq.current / 1000.0
        except (AttributeError, NotImplementedError):
            clock_ghz = 2.5

        # Compute adaptive chunk size
        base = 8
        cpu_scale = min(cpu_count / 2.0, 4.0)
        ram_scale = min(ram_gb / 8.0, 3.0)
        speed_scale = min(clock_ghz / 2.5, 2.0)
        chunk = int(base * cpu_scale * ram_scale * speed_scale ** 0.5)
        
        # Clamp and ensure reasonable bounds
        chunk = max(5, min(chunk, 30, n))
        # decreasing chunk size slightly to improve balance
        for candidate in range(chunk, max(4, chunk - 6), -1):
            num_chunks = math.ceil(n / candidate)
            last = n - (num_chunks - 1) * candidate
            if last >= max(2, int(0.65 * candidate)):
                return candidate

        # fallback to original balancing logic if refinement fails
        max_chunk = min(25, n)
        for candidate in range(max_chunk, 4, -1):
            num_chunks = math.ceil(n / candidate)
            last = n - (num_chunks - 1) * candidate
            if last >= max(2, int(0.65 * candidate)):
                return candidate
        return min(5, n)

    except Exception:
        # Fallback to pure n-based logic (psutil not installed)
        max_chunk = min(15, n)
        for chunk in range(max_chunk, 4, -1):
            num_chunks = math.ceil(n / chunk)
            last_chunk = n - (num_chunks - 1) * chunk
            if last_chunk >= max(1, int(0.7 * chunk)):
                return chunk
        return min(5, n)


def log(message: str) -> None:
    with open("tiktok.log", "a", encoding="utf-8") as log_file:
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
    return match.group(1) if match else "unknown_author"

def description_sanitize(description: str) -> Tuple[str, str]:
    tags = re.findall(r'#\w+', description)
    clean_description = re.sub(r'#\w+', '', description).strip()
    return clean_description, ' '.join(tags)

def load_links(file_path: Path = None) -> Set[str]:
    if file_path:
        if not file_path.is_file():
            sys.exit(f"Error: File '{file_path}' not found.")
        with open(file_path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip() if is_tiktok_url(line.strip())}
    return set()



async def fetch_tiktok_metadata(url: str, page) -> TiktokMetadata:
    await page.goto(url, timeout=60000)
    comment_count = await page.locator('strong[data-e2e="comment-count"]').first.inner_text()
    likes = await page.locator('strong[data-e2e="like-count"]').first.inner_text()
    bookmarks = await page.locator('strong[data-e2e="undefined-count"]').first.inner_text()
    shares = await page.locator('strong[data-e2e="share-count"]').first.inner_text()
    description = await page.locator('div[data-e2e="video-desc"]').first.inner_text()
    title, tags = description_sanitize(description)
    author = get_author_from_url(url)
    
    print(f"Likes: {likes} Comments: {comment_count}  Bookmarks: {bookmarks} Shares: {shares} Author: {author} \n Title: {title} Tags: {tags}")

    comment_button = page.get_by_role("button", name=re.compile("Read or add comments"))
    await comment_button.first.click()
    await asyncio.sleep(1.5)  # wait for comments to load
    # print(await page.locator('div[class="TUXTabBar-content"]').count())
    comment_block = page.locator('div[class="TUXTabBar-content"]').first
    comments = await page.locator('span[data-e2e="comment-level-1"]').all_inner_texts()
    print("Comments:")
    for comment in comments:
        print(f"- {comment}")

    # views = await page.locator('strong[data-e2e="play-count"]').first.inner()


    



async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        # Example usage
        url = "https://www.tiktok.com/@yum.bubs/video/7581714645912718623"
        metadata = await fetch_tiktok_metadata(url, page)
        # print(metadata)
        await browser.close()




if __name__ == "__main__":
    asyncio.run(main())
