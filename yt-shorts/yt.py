import asyncio, argparse, sys
from pathlib import Path
from playwright.async_api import async_playwright
from dataclasses import dataclass
from typing import List



@dataclass
class ShortInfo:
    link: str
    title: str
    likes: str
    comment_count: str
    views: str
    upload_date: str
    comments: list




def is_comment(text) -> bool:
    return True if len(text.split(" ")[-1]) > 2 else False

def is_short_url(url: str) -> bool:
    return "youtube.com/shorts/" in url


def load_links(link: str = None, file_path: Path = None) -> List[str]:
    if link:
        return [link.strip()]
    elif file_path:
        if not file_path.is_file():
            sys.exit(f"Error: File '{file_path}' not found.")
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() if is_short_url(line.strip())]
    return []



def save_shorts_csv(shorts: List[ShortInfo], filename: str = "shorts_info.csv") -> None:
    import csv
    fieldnames = [f for f in ShortInfo.__dataclass_fields__.keys() if f != "comments"]

    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        dict_writer.writeheader()
        for short in shorts:
            row = {k: v for k, v in short.__dict__.items() if k != "comments"}
            dict_writer.writerow(row)

def save_shorts_json(shorts: List[ShortInfo], filename: str = "shorts_info.json") -> None:
    import json
    with open(filename, 'w', encoding='utf-8') as output_file:
        json.dump([s.__dict__ for s in shorts], output_file, ensure_ascii=False, indent=4)


async def grab_short_info(url: str) -> ShortInfo:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)

            short_title = page.locator('span[class*="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap yt-core-attributed-string--link-inherit-color"]')
            stats_elem = 'span[class*="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap yt-core-attributed-string--text-alignment-center yt-core-attributed-string--word-wrapping"]'
            stats_elem = page.locator(stats_elem)
            await stats_elem.first.wait_for(state="visible", timeout=10000)
            stats_texts = await stats_elem.all_inner_texts()
            likes, comment_count = stats_texts[0], stats_texts[2]

            description = page.locator('div[class*="style-scope ytd-video-description-header-renderer"]') 
            description = description.locator('div[class*="ytwFactoidRendererFactoid"]')
            n = await description.count()
            aria_labels = []
            for i in range(n):
                # Get the i-th element and extract aria-label
                el = description.nth(i)
                label = await el.get_attribute("aria-label")
                aria_labels.append(label)

            views, date = "N/A", "N/A"
            if aria_labels:
                views = aria_labels[1].replace(" views", "")
                date = aria_labels[2]

            
            
            # comments
            await stats_elem.nth(2).click() # Click on comments count to load comments
            await asyncio.sleep(1.5)  # Wait for comments to load
            comments_section = page.locator('div[class*=" style-scope ytd-item-section-renderer style-scope ytd-item-section-renderer"]')
            comments_section = await comments_section.locator('span[class*="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap"]').all_inner_texts()
            comments = []
            for comment in comments_section:
                if is_comment(comment):
                    comments.append(comment)


            return ShortInfo(
                link=url,
                title=await short_title.inner_text(),
                likes=likes,
                comment_count=comment_count,
                views=views,
                upload_date=date,
                comments=comments
            )

        await browser.close()

    except Exception as e:
        print(f"Error occurred: {e}")
        await browser.close()
        return ShortInfo(
            link=url,
            title="N/A",
            likes="N/A",
            comment_count="N/A",
            views="N/A",
            upload_date="N/A",
            comments=[]
        )


async def main():
    
    url = "https://www.youtube.com/shorts/jrzK4xL_W4Q"
    short_info = await grab_short_info(url)
    print("Short Title:", short_info.title, 
          "\nLikes:", short_info.likes, 
          "\nComments Count:", short_info.comment_count, 
          "\nViews:", short_info.views, 
          "\nUpload Date:", short_info.upload_date, 
          "\nComments:", short_info.comments[1:3])
    

def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape YouTube Shorts metadata.",
        epilog="Examples:\n"
               "  python name.py https://youtube.com/shorts/abc123\n"
               "  python name.py -r ./links.txt -csv shorts.csv\n"
               "  python name.py -r ./links.txt -json shorts.json",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Positional: single link
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

    # Output: CSV
    parser.add_argument(
        "-csv", "--csv",
        type=Path,
        metavar="FILE",
        help="Export results to CSV"
    )

    # Output: JSON
    parser.add_argument(
        "-json", "--json",
        type=Path,
        metavar="FILE",
        help="Export results to JSON"
    )

    args = parser.parse_args()

    # Validation
    if not args.link and not args.read:
        parser.error("Either a LINK or --read FILE must be provided.")
    
    if args.link and args.read:
        parser.error("Specify either a LINK or --read FILE, not both.")

    if not (args.csv or args.json):
        parser.error("At least one output format (--csv or --json) is required.")

    return args




asyncio.run(main())
