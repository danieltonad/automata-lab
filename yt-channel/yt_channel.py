import asyncio, sys, time, re
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from dataclasses import dataclass, fields
from typing import List, Tuple, Dict

BATCH = 15
VID_LIMIT = 3_500
_spinner_task = None

@dataclass
class ChannelMetaData:
    name: str
    description: str
    subscribers: str
    videos_count: str
    country: str
    total_views: str
    joined: str
    channel_image: str
    channel_banner: str
    links: Dict[str, str]
    videos: List[Dict[str, str]] | None
    shorts: List[Dict[str, str]] | None
    playlists: List[Dict[str, str]] | None
    live_streams: List[Dict[str, str]] | None
    podcasts: List[Dict[str, str]] | None

@dataclass
class ChannelTabs:
    home: int | None
    videos: int | None
    shorts: int | None
    playlists: int | None
    live: int | None
    podcasts: int | None


class Colors:
    RESET = "\033[0m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    GRAY = "\033[90m"

def log(message: str) -> None:
    with open("yt_shorts.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

async def _spinner(msg):
    symbols = "|/-\\"
    i = 0
    try:
        while True:
            sys.stdout.write(f"\r{msg} {symbols[i % len(symbols)]}")
            sys.stdout.flush()
            i += 1
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        sys.stdout.write("\r" + " " * (len(msg) + 4) + "\r")
        sys.stdout.flush()
        raise

def show_spinner(msg):
    global _spinner_task
    _spinner_task = asyncio.create_task(_spinner(msg))

async def off_spinner():
    global _spinner_task
    if _spinner_task:
        _spinner_task.cancel()
        try:
            await _spinner_task
        except asyncio.CancelledError:
            pass
        _spinner_task = None

def normalize_yt_channel(input_value: str) -> str:
    if not input_value or not input_value.strip():
        raise ValueError("Empty channel input")
    value = input_value.strip()
    # Already a URL
    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        if "youtube.com" not in parsed.netloc and "youtu.be" not in parsed.netloc:
            raise ValueError("Not a YouTube URL")
        # Remove query params, fragments, trailing slashes
        clean_path = parsed.path.rstrip("/")
        return f"https://www.youtube.com{clean_path}"
    # Handle @username
    if value.startswith("@"):
        handle = value[1:]
        if not handle:
            raise ValueError("Invalid handle")
        return f"https://www.youtube.com/@{handle}"
    # Channel
    if re.fullmatch(r"UC[a-zA-Z0-9_-]{22}", value):
        return f"https://www.youtube.com/channel/{value}"
    # Plain username
    return f"https://www.youtube.com/@{value}"

def duration_to_seconds(duration) -> int:
    if not duration:
        return 0

    try:
        parts = duration.split(':')
        # convert each part to int
        parts = [int(p) for p in parts]
        # depending on length, calculate seconds
        if len(parts) == 3:  # hh:mm:ss
            h, m, s = parts
        elif len(parts) == 2:  # mm:ss
            h = 0
            m, s = parts
        elif len(parts) == 1:  # ss
            h = 0
            m = 0
            s = parts[0]
        else:
            return 0
        return h * 3600 + m * 60 + s
    except ValueError:
        return 0


def to_int(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    v = str(value).lower().replace(',', '').strip()
    if v.endswith('k'):
        return int(float(v[:-1]) * 1_000)
    if v.endswith('m'):
        return int(float(v[:-1]) * 1_000_000)
    if v.endswith('b'):
        return int(float(v[:-1]) * 1_000_000_000)
    return int(float(v))

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

def save_meta_data_json(meta_data: ChannelMetaData, file: Path, time: str):
    import json
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(meta_data.__dict__, f, ensure_ascii=False, indent=4)
    print(f"{Colors.GRAY}Saved metadata to {file} {Colors.GREEN} [{time}] {Colors.RESET}")

async def channel_data(url: str, page, retry: int = 0) -> Tuple[ChannelMetaData, ChannelTabs]:
    try:
        await page.goto(url, timeout=60000)
        more_info_btn = page.locator("button[class*='yt-truncated-text__absolute-button']")
        if await more_info_btn.count() > 0:
            await more_info_btn.click()
            await asyncio.sleep(1)

        data = await page.evaluate("""
            () => {
            const qs = (sel) => document.querySelector(sel);
            const qsa = (sel) => Array.from(document.querySelectorAll(sel));
            const text = (el) => el?.innerText?.trim() ?? null;
            const src = (el) => el?.getAttribute("src") ?? null;

            // Channel name
            const name = text(
                qs("h2[class*='ytd-engagement-panel-title-header-renderer']")
            );

            // Description
            const description = text(
                qsa(
                "#about-container span.yt-core-attributed-string--white-space-pre-wrap"
                )[1]
            );

            // Images
            const banner = src(
                qs("img.ytCoreImageHost.ytCoreImageFillParentHeight")
            );

            const channel_image = src(
                qs("img.yt-spec-avatar-shape__image")
            );

            // External links
            const linkTitles = qsa(
                "#link-list-container span.ytChannelExternalLinkViewModelTitle"
            ).map(text);

            const linkUrls = qsa(
                "#link-list-container a.yt-core-attributed-string__link"
            ).map(text);

            const links = {};
            linkTitles.forEach((k, i) => {
                if (k && linkUrls[i]) links[k] = linkUrls[i];
            });

            // About table rows
            const rows = qsa(
                "table.ytd-about-channel-renderer tr"
            ).map(text);

            const safeRow = (idx) =>
                rows.length > idx ? rows[rows.length - 1 - idx] : null;

            const total_views   = safeRow(0)?.replace(/ views/i, "") ?? null;
            const videos_count  = safeRow(1)?.replace(/ videos/i, "") ?? null;
            const subscribers   = safeRow(2)?.replace(/ subscribers/i, "") ?? null;
            const joined        = safeRow(3)?.replace(/joined /i, "") ?? null;
            const country       = safeRow(4);

            return {
                name,
                description,
                subscribers,
                videos_count,
                total_views,
                joined,
                country,
                channel_image,
                channel_banner: banner ? banner : null,
                links
            };
            }
            """)
        
        meta_data = ChannelMetaData(
        name=data.get("name"),
        description=data.get("description"),
        subscribers=data.get("subscribers"),
        videos_count=to_int(data.get("videos_count")),
        country=data.get("country"),
        total_views=to_int(data.get("total_views")),
        joined=data.get("joined"),
        channel_image=data.get("channel_image"),
        channel_banner=data.get("channel_banner"),
        links=data.get("links"),
        videos=None,
        shorts=None,
        playlists=None,
        live_streams=None,
        podcasts=None,
    )



        # tabs
        tabs = page.locator("div[class='tabGroupShapeTabs']")
        tabs_text = await tabs.all_inner_texts()
        tabs_dict = {tab.lower(): i for i, tab in enumerate(tabs_text[0].split('\n'))}

        allowed = {f.name for f in fields(ChannelTabs)}
        filtered_tabs = {name: tabs_dict.get(name, None) for name in allowed}

        return meta_data, ChannelTabs(**filtered_tabs)
    except Exception as e:
        if retry < 3:
            log(f"Retrying channel_data due to error: {e}")
            return await channel_data(url, page, retry + 1)
        else:
            log(f"Failed to get channel data after retries: {e}")
            raise

async def extract_video_data(target) -> dict:
    await target.scroll_into_view_if_needed()
    data = await target.evaluate("""
    el => {
    const linkEl = el.querySelector("a#thumbnail.ytd-thumbnail");
    const imgEl = el.querySelector(
        "img.ytCoreImageHost.ytCoreImageFillParentHeight"
    );
    const durationEl = el.querySelector(
        "ytd-thumbnail #thumbnail .yt-badge-shape__text"
    );
    const titleEl = el.querySelector(
        "a.yt-simple-endpoint.focus-on-expand.style-scope.ytd-rich-grid-media"
    );

    const meta = el.querySelectorAll(
        "span.inline-metadata-item.style-scope.ytd-video-meta-block"
    );

    return {
        title: titleEl ? titleEl.innerText : null,
        link: linkEl ? "https://www.youtube.com" + linkEl.getAttribute("href") : null,
        thumbnail: imgEl ? imgEl.getAttribute("src") || imgEl.getAttribute("data-src") : null,
        duration: durationEl ? durationEl.innerText : null,
        views: meta[0] ? meta[0].innerText.replace(" views", "") : null,
        published: meta[1] ? meta[1].innerText : null
    };
    }
    """)

    data = dict(data)
    data['views'] = to_int(data['views'])
    data['duration'] = duration_to_seconds(data.get('duration'))
    return data

async def extract_short_data(target) -> dict:
    await target.scroll_into_view_if_needed()
    data = await target.evaluate("""
    el => {
    const linkEl = el.querySelector("a.shortsLockupViewModelHostEndpoint.shortsLockupViewModelHostOutsideMetadataEndpoint");
    const imgEl = el.querySelector(
        "img.ytCoreImageHost.ytCoreImageFillParentHeight"
    );
    const titleEl = el.querySelector(
        "span.yt-core-attributed-string.yt-core-attributed-string--white-space-pre-wrap"
    );

    const meta = el.querySelectorAll(
        "span.yt-core-attributed-string.yt-core-attributed-string--white-space-pre-wrap"
    );

    return {
        title:  meta[0] ? meta[0].innerText : null,
        link: linkEl ? "https://www.youtube.com" + linkEl.getAttribute("href") : null,
        thumbnail: imgEl ? imgEl.getAttribute("src") || imgEl.getAttribute("data-src") : null,
        views: meta[1] ? meta[1].innerText.replace(" views", "") : null,
    };
    }
    """)
    data = dict(data)
    data['views'] = to_int(data['views'])
    return data

async def extract_live_data(target) -> dict:
    await target.scroll_into_view_if_needed()
    data = await target.evaluate(r"""
        el => {
        const linkEl = el.querySelector("a#thumbnail.ytd-thumbnail");
        const imgEl = el.querySelector(
            "img.ytCoreImageHost.ytCoreImageFillParentHeight"
        );
        const durationEl = el.querySelector(
            "ytd-thumbnail #thumbnail .yt-badge-shape__text"
        );
        const titleEl = el.querySelector(
            "a.yt-simple-endpoint.focus-on-expand.style-scope.ytd-rich-grid-media"
        );

        const metaEls = Array.from(
            el.querySelectorAll("span.inline-metadata-item.style-scope.ytd-video-meta-block")
        ).map(el => el.innerText.trim());
                                 
        let published = null;
        for (const text of metaEls) {
            if (/views$/i.test(text)) {
            views = text.replace(" views", "");
            } else if (/streamed|ago|premiered/i.test(text)) {
            published = text.replace(/^Streamed\s*/i, "");
            }
        }

        return {
            title: titleEl ? titleEl.innerText.replace(" [LIVE]", "") : null,
            link: linkEl ? "https://www.youtube.com" + linkEl.getAttribute("href") : null,
            thumbnail: imgEl ? imgEl.getAttribute("src") || imgEl.getAttribute("data-src") : null,
            duration: durationEl ? durationEl.innerText : null,
            published
        };}""")
    data = dict(data)
    data['duration'] = duration_to_seconds(data.get('duration'))
    return data

async def extract_playlist_data(target) -> dict:
    await target.scroll_into_view_if_needed()
    data = await target.evaluate("""
    el => {
    const linkEl = el.querySelector("a.yt-lockup-view-model__content-image");
    const imgEl = el.querySelector("img.ytCoreImageHost");
    const badgeEl = el.querySelector("div.yt-badge-shape__text")
    const meta = el.querySelectorAll("span.yt-core-attributed-string.yt-core-attributed-string--white-space-pre-wrap");

    return {
        title:  meta[0] ? meta[0].innerText : null,
        link: linkEl ? "https://www.youtube.com" + linkEl.getAttribute("href") : null,
        thumbnail: imgEl ? imgEl.getAttribute("src") || imgEl.getAttribute("data-src") : null,
        badge: badgeEl ? badgeEl.innerText : null,
    };
    }
    """)
    return dict(data)

async def extract_podcast_data(target) -> dict:
    await target.scroll_into_view_if_needed()
    data = await target.evaluate("""
    el => {
    const linkEl = el.querySelector("a.yt-lockup-view-model__content-image");
    const imgEl = el.querySelector("img.ytCoreImageHost.ytCoreImageFillParentHeight.ytCoreImageFillParentWidth");
    const badgeEl = el.querySelector("div.yt-badge-shape__text")
    const meta = el.querySelectorAll("span.yt-core-attributed-string.yt-core-attributed-string--white-space-pre-wrap");

    return {
        title:  meta[0] ? meta[0].innerText : null,
        link: linkEl ? "https://www.youtube.com" + linkEl.getAttribute("href") : null,
        thumbnail: imgEl ? imgEl.getAttribute("src") || imgEl.getAttribute("data-src") : null,
        badge: badgeEl ? badgeEl.innerText : null,
    };
    }
    """)
    return dict(data)


async def get_video_ids(page) -> set[str]:
    return set(await page.evaluate("""
        () => Array.from(
            document.querySelectorAll("a[href*='watch?v=']")
        ).map(a => {
            const m = a.href.match(/v=([^&]+)/);
            return m ? m[1] : null;
        }).filter(Boolean)
    """))


async def pull_videos(url, page, tab_index: int) -> List[Dict[str, str]]:
    try:
        await page.goto(url)
        tabs = page.locator("div[class='tabGroupShapeTabs']")
        last_spin = True
        # navigate to videos tab
        await tabs.locator('.yt-tab-shape.yt-tab-shape--host-clickable').nth(tab_index).click()
        await asyncio.sleep(2)
        await page.mouse.wheel(0, 7000)
        
        # continuous scrolling till all videos are loaded
        while last_spin:
            await page.mouse.wheel(0, 2500)
            last_spin = await page.locator("div[class*='circle-clipper left style-scope tp-yt-paper-spinner']").nth(1).is_visible()
            await asyncio.sleep(0.5)
            vids = await get_video_ids(page)
            if len(vids) >= VID_LIMIT:
                break

        videos = []
        containers = page.locator("div[class*='style-scope ytd-rich-item-renderer']")
        size = await containers.count()

        for start in range(0, size, BATCH):
            tasks = []
            for i in range(start, min(start + BATCH, size)):
                target = containers.nth(i)
                tasks.append(extract_video_data(target))
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in batch_results:
                if isinstance(r, dict):
                    videos.append(r)
        return videos
    except Exception as e:
        log(f"Error in pull_videos: {e}")
        return []

async def pull_shorts(url, page, tab_index: int) -> List[Dict[str, str]]:
    try:
        await page.goto(url)
        tabs = page.locator("div[class='tabGroupShapeTabs']")
        last_spin = True
        # navigate to shorts tab
        await tabs.locator('.yt-tab-shape.yt-tab-shape--host-clickable').nth(tab_index).click()
        await asyncio.sleep(2)
        await page.mouse.wheel(0, 7000)
        
        # continuous scrolling till all shorts are loaded
        while last_spin:
            await page.mouse.wheel(0, 2500)
            last_spin = await page.locator("div[class*='circle-clipper left style-scope tp-yt-paper-spinner']").nth(1).is_visible()
            await asyncio.sleep(0.5)

        shorts = []
        containers = page.locator("div[class*='style-scope ytd-rich-item-renderer']")
        size = await containers.count()

        for start in range(0, size, BATCH):
            tasks = []
            for i in range(start, min(start + BATCH, size)):
                target = containers.nth(i)
                tasks.append(extract_short_data(target))
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in batch_results:
                if isinstance(r, dict):
                    shorts.append(r)
            return shorts
    except Exception as e:
        log(f"Error in pull_shorts: {e}")
        return []

async def pull_live_streams(url, page, tab_index: int) -> List[Dict[str, str]]:
    try:
        await page.goto(url)
        tabs = page.locator("div[class='tabGroupShapeTabs']")
        last_spin = True
        # navigate to live tab
        await tabs.locator('.yt-tab-shape.yt-tab-shape--host-clickable').nth(tab_index).click()
        await asyncio.sleep(2)
        await page.mouse.wheel(0, 7000)
        
        # continuous scrolling till all shorts are loaded
        while last_spin:
            await page.mouse.wheel(0, 2500)
            last_spin = await page.locator("div[class*='circle-clipper left style-scope tp-yt-paper-spinner']").nth(1).is_visible()
            await asyncio.sleep(0.5)

        live_streams = []
        containers = page.locator("div.style-scope.ytd-rich-item-renderer")
        size = await containers.count()

        for start in range(0, size, BATCH):
            tasks = []
            for i in range(start, min(start + BATCH, size)):
                target = containers.nth(i)
                tasks.append(extract_live_data(target))
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in batch_results:
                if isinstance(r, dict):
                    live_streams.append(r)
        return live_streams
    except Exception as e:
        log(f"Error in pull_live_streams: {e}")
        return []
    
async def pull_playlists(url, page, tab_index: int) -> List[Dict[str, str]]:
    try:
        await page.goto(url)
        tabs = page.locator("div[class='tabGroupShapeTabs']")
        last_spin = True
        # navigate to playlists tab
        await tabs.locator('.yt-tab-shape.yt-tab-shape--host-clickable').nth(tab_index).click()
        await asyncio.sleep(2)
        await page.mouse.wheel(0, 7000)
        
        # continuous scrolling till all shorts are loaded
        while last_spin:
            await page.mouse.wheel(0, 2500)
            last_spin = await page.locator("div[class*='circle-clipper left style-scope tp-yt-paper-spinner']").nth(1).is_visible()
            await asyncio.sleep(0.5)
        
        playlists = []
        containers = page.locator("div.yt-lockup-view-model.yt-lockup-view-model--vertical")
        size = await containers.count()

        for start in range(0, size, BATCH):
            tasks = []
            for i in range(start, min(start + BATCH, size)):
                target = containers.nth(i)
                tasks.append(extract_playlist_data(target))
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in batch_results:
                if isinstance(r, dict):
                    playlists.append(r)
        return playlists
    except Exception as e:
        log(f"Error in pull_playlists: {e}")
        return []
    
async def pull_podcasts(url, page, tab_index: int) -> List[Dict[str, str]]:
    try:
        await page.goto(url)
        tabs = page.locator("div[class='tabGroupShapeTabs']")
        last_spin = True
        # navigate to playlists tab
        await tabs.locator('.yt-tab-shape.yt-tab-shape--host-clickable').nth(tab_index).click()
        await asyncio.sleep(2)
        await page.mouse.wheel(0, 7000)
        
        # continuous scrolling till all shorts are loaded
        while last_spin:
            await page.mouse.wheel(0, 2500)
            last_spin = await page.locator("div[class*='circle-clipper left style-scope tp-yt-paper-spinner']").nth(1).is_visible()
            await asyncio.sleep(0.5)
        
        playlists = []
        containers = page.locator("div.yt-lockup-view-model.yt-lockup-view-model--vertical")
        size = await containers.count()

        for start in range(0, size, BATCH):
            tasks = []
            for i in range(start, min(start + BATCH, size)):
                target = containers.nth(i)
                tasks.append(extract_playlist_data(target))
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in batch_results:
                if isinstance(r, dict):
                    playlists.append(r)
        return playlists
    except Exception as e:
        log(f"Error in pull_podcasts: {e}")
        return []

async def scrape_with_context(browser, coro):
    """
    Utility to run a scraper in its own context.
    """
    context = await browser.new_context()
    page = await context.new_page()
    try:
        return await coro(page)
    finally:
        await context.close()

async def grab_channel_info(url: str) -> None:
    try:
        show_spinner("Grabbing channel info")
        start = time.time()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            base_context = await browser.new_context()
            base_page = await base_context.new_page()

            meta_data, tabs = await channel_data(url, base_page)
            await base_context.close()
            tasks = {}
            if tabs.videos:
                tasks["videos"] = scrape_with_context(
                    browser,
                    lambda page: pull_videos(url, page, tabs.videos)
                )

            if tabs.shorts:
                tasks["shorts"] = scrape_with_context(
                    browser,
                    lambda page: pull_shorts(url, page, tabs.shorts)
                )

            if tabs.live:
                tasks["live_streams"] = scrape_with_context(
                    browser,
                    lambda page: pull_live_streams(url, page, tabs.live)
                )

            if tabs.playlists:
                tasks["playlists"] = scrape_with_context(
                    browser,
                    lambda page: pull_playlists(url, page, tabs.playlists)
                )

            if tabs.podcasts:
                tasks["podcasts"] = scrape_with_context(
                    browser,
                    lambda page: pull_podcasts(url, page, tabs.podcasts)
                )
            # --- Run scrapers concurrently ---
            results = await asyncio.gather(*tasks.values())

            # --- Assign results back to metadata ---
            for key, value in zip(tasks.keys(), results):
                setattr(meta_data, key, value)
            await browser.close()
        
        await off_spinner()
        save_meta_data_json(meta_data, Path("channel.json"), time=time_taken(start, time.time()))
        print(f"Shorts: {len(meta_data.shorts):,} | Playlists: {len(meta_data.playlists):,} | Live Streams: {len(meta_data.live_streams):,} | Videos: {len(meta_data.videos):,} | Podcasts: {len(meta_data.podcasts):,}")
    except Exception as e:
        await off_spinner()
        log(f"Error in grab_channel_info: {e}")
        print(f"{Colors.BLUE}Unable to grab channel info, please try again later.{Colors.RESET}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python yt-channel.py <channel_name_or_link_or_id>")
        sys.exit(1)
    channel_input = sys.argv[1]
    await grab_channel_info(normalize_yt_channel(channel_input))


if __name__ == "__main__":
    asyncio.run(main())
