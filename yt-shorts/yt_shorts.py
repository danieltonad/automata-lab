import asyncio, argparse, sys, math, random, time
import psutil
from pathlib import Path
from playwright.async_api import async_playwright
from dataclasses import dataclass
from typing import List, Set


@dataclass
class ShortMetaData:
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
    with open("yt_shorts.log", "a", encoding="utf-8") as log_file:
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



def is_comment(text: str) -> bool:
    # Filter out UI text seen in comment sections
    ui_phrases = {
        "top comments",
        "newest first",
        "top is selected",
        "featured comments",
        "sort by",
        "comments •",
    }
    text_lower = text.strip().lower()
    return len(text) > 2 and not any(phrase in text_lower for phrase in ui_phrases)

def is_short_url(url: str) -> bool:
    return "youtube.com/shorts/" in url


def load_links(file_path: Path = None) -> Set[str]:
    if file_path:
        if not file_path.is_file():
            sys.exit(f"Error: File '{file_path}' not found.")
        with open(file_path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip() if is_short_url(line.strip())}
    return set()



def save_shorts_csv(shorts: List[ShortMetaData], filepath: Path) -> None:
    import csv
    fieldnames = [f for f in ShortMetaData.__dataclass_fields__.keys() if f != "comments"]

    with open(filepath, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        dict_writer.writeheader()
        for short in shorts:
            row = {k: v for k, v in short.__dict__.items() if k != "comments"}
            dict_writer.writerow(row)

def save_shorts_json(shorts: List[ShortMetaData], filepath: Path) -> None:
    import json
    with open(filepath, 'w', encoding='utf-8') as output_file:
        json.dump([s.__dict__ for s in shorts], output_file, ensure_ascii=False, indent=4)



async def grab_short_info(page, url: str, retry: int = 0) -> ShortMetaData:
    try:
        await page.goto(url, timeout=60000)
        
        short_title = page.locator('span[class*="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap yt-core-attributed-string--link-inherit-color"]')
        stats_elem = 'span[class*="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap yt-core-attributed-string--text-alignment-center yt-core-attributed-string--word-wrapping"]'
        stats_elem = page.locator(stats_elem)
        await stats_elem.first.wait_for(state="visible", timeout=3000)
        stats_texts = await stats_elem.all_inner_texts()
        likes, comment_count = stats_texts[0], stats_texts[2]

        description = page.locator('div[class*="style-scope ytd-video-description-header-renderer"]') 
        description = description.locator('div[class*="ytwFactoidRendererFactoid"]')
        n = await description.count()
        aria_labels = []
        for i in range(n):
            # Get the i-th element and extract aria-label
            el = description.nth(i)
            label = await el.get_attribute("aria-label") or ""
            aria_labels.append(label)

        views, date = "N/A", "N/A"
        if aria_labels:
            views = aria_labels[1].replace(" views", "")
            date = aria_labels[2]
        
        try:
            # comments
            await stats_elem.nth(2).click() # Click on comments count to load comments
            await asyncio.sleep(1.5)  # Wait for comments to load
            comments_section = page.locator('div[class*=" style-scope ytd-item-section-renderer style-scope ytd-item-section-renderer"]')
            comments_section = await comments_section.locator('span[class*="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap"]').all_inner_texts()
            comments = []
            for comment in comments_section:
                if is_comment(comment):
                    comments.append(comment)
        except:
            comments = []

        return ShortMetaData(
            link=url,
            title=await short_title.inner_text(),
            likes=likes,
            comment_count=comment_count,
            views=views,
            upload_date=date,
            comments=comments
        )

    except Exception as e:
        if retry >= 2:
            return ShortMetaData(link=url, title="N/A", likes="N/A", comment_count="N/A", views="N/A", upload_date="N/A", comments=[])
        else:
            await page.close()
            return await grab_short_info(page, url, retry + 1)
    

async def bulk_grab_short_info(urls: Set[str], args: argparse.Namespace) -> List[ShortMetaData]:
    url_list = list(urls)
    n = len(url_list)
    print(f"{Colors.CYAN}Processing {n} YT short URLs...{Colors.RESET}", flush=True)
    chunk_size = optimal_chunk_size(n)
    total_completed = 0
    all_results: List[ShortMetaData] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # log progress
        context = await browser.new_context()
        # Process in chunks
        start = time.time()
        for i in range(0, n, chunk_size):
            print(f"Progress: {total_completed:,} of {n:,}", end='\r', flush=True)
            chunk_urls = url_list[i:i + chunk_size]
            # Launch one page per URL in this chunk
            tasks, pages = [], []
            for url in chunk_urls:
                page = await context.new_page()
                await page.set_viewport_size({"width": random.randint(800, 1120), "height": random.randint(600, 1080)}) # randomize viewport size
                pages.append(page)
                tasks.append(grab_short_info(page, url))

            # Process chunk with live progress
            chunk_results: List[ShortMetaData] = []
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
            save_shorts_csv(all_results, args.csv)
            print(f"{Colors.GRAY}  [Saved CSV to: {args.csv}]{Colors.RESET}", flush=True)
        if args.json:
            save_shorts_json(all_results, args.json)
            print(f"{Colors.GRAY}  [Saved JSON to: {args.json}]{Colors.RESET}", flush=True)

        print(f"\n{Colors.GREEN} Completed  {n:,} Shorts in {time_taken(start, stop)}.{Colors.RESET}", flush=True)

        await browser.close()
        return all_results


async def single_grab_short_info(url: str, args: argparse.Namespace) -> List[ShortMetaData]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        start = time.time()
        short_info = await grab_short_info(page,url)
        stop = time.time()
    
    if short_info.title == "N/A":
        print(f"[{url}] Failed to retrieve data.", flush=True)
        return

    if args.csv:
        save_shorts_csv([short_info], args.csv)
        print(f"{Colors.GRAY}  [Saved CSV to: {args.csv}]{Colors.RESET}", flush=True)

    if args.json:
        save_shorts_json([short_info], args.json)
        print(f"{Colors.GRAY}  [Saved JSON to: {args.json}]{Colors.RESET}", flush=True)
    
    print(f"\n{Colors.GREEN}Completed in {time_taken(start, stop)}.{Colors.RESET}", flush=True)

    


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch metadata from YouTube Shorts URLs and export to CSV/JSON."
    )

    # Positional: single link (optional, since we allow --read)
    parser.add_argument(
        "link",
        nargs="?",
        help="Single YouTube Shorts URL"
    )

    # Input: file with links
    parser.add_argument(
        "-r", "--read",
        type=Path,
        help="File containing one Shorts URL per line"
    )

    # Output basename (optional, used if --csv/--json are given without paths)
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

    # Resolve output filenames intelligently
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
        await single_grab_short_info(args.link, args)
    elif args.read:
        urls = load_links(args.read)
        await bulk_grab_short_info(urls, args)
    


if __name__ == "__main__":
    asyncio.run(main())
