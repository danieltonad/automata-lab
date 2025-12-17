import asyncio, argparse, sys, math, random, time
import psutil, re
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from dataclasses import dataclass
from typing import List, Set, Tuple


@dataclass
class TiktokMetadata:
    link: str
    author : str
    title: str
    tags: str
    likes: str
    shares: str
    bookmarks: str
    comment_count: str

class Colors:
    RESET = "\033[0m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    GRAY = "\033[90m"


def optimal_chunk_size(n: int) -> int:
    """
    Compute optimal chunk size for TikTok scraping based on number of URLs and system resources.
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

        # fallback to original balancing logic if refinement fails
        max_chunk = min(11, n)
        for candidate in range(max_chunk, 4, -1):
            num_chunks = math.ceil(n / candidate)
            last = n - (num_chunks - 1) * candidate
            if last >= max(2, int(0.65 * candidate)):
                return candidate
        return min(5, n)

    except Exception:
        # Fallback to pure n-based logic (psutil not installed)
        max_chunk = min(11, n)
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
    return match.group(1) if match else ""

def description_sanitize(description: str) -> Tuple[str, str]:
    tags = re.findall(r'#\w+', description)
    clean_description = re.sub(r'#\w+', '', description).strip()
    clean_description = re.sub(r'[\t\n]', ' ', clean_description).strip()
    clean_description = re.sub(r'\s+', ' ', clean_description).strip()
    return clean_description, ' '.join(tags)

def load_links(file_path: Path = None) -> Set[str]:
    if file_path:
        if not file_path.is_file():
            sys.exit(f"Error: File '{file_path}' not found.")
        with open(file_path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip() if is_tiktok_url(line.strip())}
    return set()


def save_tiktok_metadata_csv(metadatas: List[TiktokMetadata], filepath: Path) -> None:
    import csv
    fieldnames = [f for f in TiktokMetadata.__dataclass_fields__.keys() if f != "comments"]

    with open(filepath, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        dict_writer.writeheader()
        for metadata in metadatas:
            row = {k: v for k, v in metadata.__dict__.items() if k != "comments"}
            dict_writer.writerow(row)

def save_tiktok_metadata_json(metadatas: List[TiktokMetadata], filepath: Path) -> None:
    import json
    with open(filepath, 'w', encoding='utf-8') as output_file:
        json.dump([s.__dict__ for s in metadatas], output_file, ensure_ascii=False, indent=4)

async def fetch_tiktok_metadata(url: str, page, retry: int = 0) -> TiktokMetadata:
    try:
        await page.goto(url, timeout=60000)
        comment_count = await page.locator('strong[data-e2e="comment-count"]').first.inner_text()
        likes = await page.locator('strong[data-e2e="like-count"]').first.inner_text()
        bookmarks = await page.locator('strong[data-e2e="undefined-count"]').first.inner_text()
        shares = await page.locator('strong[data-e2e="share-count"]').first.inner_text()
        description = await page.locator('div[data-e2e="video-desc"]').first.inner_text()
        title, tags = description_sanitize(description)
        author = get_author_from_url(url)

        # comment_button = page.get_by_role("button", name=re.compile("Read or add comments"))
        # await comment_button.first.click()
        # await asyncio.sleep(1.2)
        # comment_block = page.locator('div[class="TUXTabBar-content"]').first
        # comments = await comment_block.locator('span[data-e2e="comment-level-1"]').all_inner_texts()

        return TiktokMetadata(
            link=url,
            title=title,
            tags=tags,
            likes=likes,
            author=author,
            shares=shares,
            bookmarks=bookmarks,
            comment_count=comment_count
        )
    except Exception as e:
        if retry < 3:
            await asyncio.sleep(2 ** retry)
            return await fetch_tiktok_metadata(url, page, retry + 1)
        else:
            log(f"Failed to fetch metadata for {url}: {e}")
            return TiktokMetadata(
                link=url,
                title="N/A",
                tags="",
                likes="0",
                author="",
                shares="0",
                bookmarks="0",
                comment_count="0"
            )

async def bulk_tiktok_metadata(urls: Set[str], args: argparse.Namespace) -> List[TiktokMetadata]:   
    url_list = list(urls)
    n = len(url_list)
    print(f"{Colors.CYAN}Processing {n} TikTok URLs...{Colors.RESET}", flush=True)
    chunk_size = optimal_chunk_size(n)
    total_completed = 0
    all_results: List[TiktokMetadata] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        # Process in chunks
        start = time.time()
        for i in range(0, n, chunk_size):
            print(f"Progress: {total_completed:,} of {n:,}", end='\r', flush=True)
            chunk_urls = url_list[i:i + chunk_size]
            tasks, pages = [], []
            for url in chunk_urls:
                page = await context.new_page()
                await Stealth().apply_stealth_async(page)
                pages.append(page)
                tasks.append(fetch_tiktok_metadata(url, page))

            # Process chunk with live progress
            chunk_results: List[TiktokMetadata] = []
            completed = 0

            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    chunk_results.append(result)
                except Exception as e:
                    print(f"\nTask failed: {e}", flush=True)
                completed += 1
            
            await asyncio.gather(*[page.close() for page in pages], return_exceptions=True)
            all_results.extend(chunk_results)
            total_completed += completed
        
        stop = time.time()
        
    if args.csv:
        save_tiktok_metadata_csv(all_results, args.csv)
        print(f"{Colors.GRAY}  [Saved CSV to: {args.csv}]{Colors.RESET}", flush=True)
    if args.json:
        save_tiktok_metadata_json(all_results, args.json)
        print(f"{Colors.GRAY}  [Saved JSON to: {args.json}]{Colors.RESET}", flush=True)

    print(f"\n{Colors.GREEN} Completed  {n:,} TikToks in {time_taken(start, stop)}.{Colors.RESET}", flush=True)

    await browser.close()

async def single_tiktok_metadata(url: str, args: argparse.Namespace) -> TiktokMetadata:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        start = time.time()
        await Stealth().apply_stealth_async(page)
        metadata = await fetch_tiktok_metadata(url, page)
        stop = time.time()
        await browser.close() #close browser

    if args.csv:
        save_tiktok_metadata_csv([metadata], args.csv)
        print(f"{Colors.GRAY}  [Saved CSV to: {args.csv}]{Colors.RESET}", flush=True)
    
    if args.json:
        save_tiktok_metadata_json([metadata], args.json)
        print(f"{Colors.GRAY}  [Saved JSON to: {args.json}]{Colors.RESET}", flush=True)
    
    print(f"\n{Colors.GREEN}Completed in {time_taken(start, stop)}.{Colors.RESET}", flush=True)




def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch metadata from TikTok URLs and export to CSV/JSON."
    )

    # single link
    parser.add_argument(
        "link",
        nargs="?",
        help="Single TikTok URL"
    )

    # Input: file with links
    parser.add_argument(
        "-r", "--read",
        type=Path,
        help="File containing one TikTok URL per line"
    )

    # Output basename
    parser.add_argument(
        "-o", "--output",
        type=str,
        metavar="BASENAME",
        help="Base name for output files ('results' → results.csv, results.json)"
    )

    # Output flags: --csv [FILE], --json [FILE]
    parser.add_argument(
        "--csv",
        nargs="?",
        const=True,
        metavar="FILE",
        help="Export to CSV. If no FILE given, use --output or default 'output.csv'."
    )
    parser.add_argument(
        "--json",
        nargs="?",
        const=True,
        metavar="FILE",
        help="Export to JSON. If no FILE given, use --output or default 'output.json'."
    )

    args = parser.parse_args()

    # Validation: require input
    if not args.link and not args.read:
        parser.error("Either a LINK or --read FILE must be provided.")
    if args.link and args.read:
        parser.error("Specify either a LINK or --read FILE, not both.")

    # Validation: require at least one output format
    if not (args.csv or args.json):
        parser.error("At least one output format (--csv or --json) is required.")

    # If --csv/--json used *without* filename (i.e., const=True), derive path
    if args.csv is True:
        base = args.output or "output"
        args.csv = Path(f"{base}.csv")
    elif args.csv:
        args.csv = Path(args.csv)

    if args.json is True:
        base = args.output or "output"
        args.json = Path(f"{base}.json")
    elif args.json:
        args.json = Path(args.json)

    return args


async def main():
    args = parse_args()
    if args.link:
        await single_tiktok_metadata(args.link, args)
    elif args.read:
        urls = load_links(args.read)
        await bulk_tiktok_metadata(urls, args)




if __name__ == "__main__":
    asyncio.run(main())
