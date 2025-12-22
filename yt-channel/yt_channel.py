import asyncio, argparse, sys, math, random, time, re
from pathlib import Path
from playwright.async_api import async_playwright
from dataclasses import dataclass, fields
from typing import List, Set, Tuple, Dict

BATCH = 20

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

def save_meta_data_json(meta_data: ChannelMetaData, file: Path):
    import json
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(meta_data.__dict__, f, ensure_ascii=False, indent=4)
    print(f"{Colors.GREEN}Saved metadata to {file}{Colors.RESET}")

async def channel_data(url: str, page) -> Tuple[ChannelMetaData, ChannelTabs]:
    await page.goto(url, timeout=60000)
    more_info_btn = page.locator("button[class*='yt-truncated-text__absolute-button']")
    if await more_info_btn.count() > 0:
        await more_info_btn.click()
        await asyncio.sleep(1)

    name = await page.locator("h2[class*='style-scope ytd-engagement-panel-title-header-renderer']").inner_text()
    about = page.locator("div[id='about-container']")
    texts = about.locator("span[class*='yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap']")
    description = await texts.nth(1).inner_text()
    banner = await page.locator("img[class='ytCoreImageHost ytCoreImageFillParentHeight ytCoreImageFillParentWidth ytCoreImageContentModeScaleAspectFill ytCoreImageLoaded']").get_attribute("src")
    channel_image = await page.locator("img[class='ytCoreImageHost yt-spec-avatar-shape__image ytCoreImageFillParentHeight ytCoreImageFillParentWidth ytCoreImageContentModeScaleToFill ytCoreImageLoaded']").get_attribute("src")
    
    links = page.locator("div[id='link-list-container']")
    key = await links.locator("span[class*='yt-core-attributed-string ytChannelExternalLinkViewModelTitle yt-core-attributed-string--ellipsis-truncate']").all_inner_texts()
    value = await links.locator("a[class*='yt-core-attributed-string__link yt-core-attributed-string__link--call-to-action-color yt-core-attributed-string--link-inherit-color']").all_inner_texts()
    link = {k:v for k,v in zip(key, value)}

    more_info= page.locator("table[class='style-scope ytd-about-channel-renderer']")
    rows = await more_info.locator("tr").all()
    views = str(await rows[-1].inner_text()).lower().replace(" views","").strip()
    videos_count = str(await rows[-2].inner_text()).lower().replace(" videos","").strip()
    subscribers = str(await rows[-3].inner_text()).lower().replace(" subscribers","").strip()
    joined = str(await rows[-4].inner_text()).lower().replace("joined ","").strip()
    country = str(await rows[-5].inner_text()).lower().strip().capitalize()

    meta_data = ChannelMetaData(
        name=name,
        description=description,
        subscribers=subscribers,
        videos_count=videos_count,
        country=country,
        total_views=views,
        joined=joined,
        channel_image=channel_image,    
        channel_banner=banner,
        links=link,
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
    return dict(data)

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
    return dict(data)

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
    return dict(data)

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



async def pull_videos(url, page, tab_index: int) -> List[Dict[str, str]]:
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

async def pull_shorts(url, page, tab_index: int) -> List[Dict[str, str]]:
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

async def pull_live_streams(url, page, tab_index: int) -> List[Dict[str, str]]:
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
    
async def pull_playlists(url, page, tab_index: int) -> List[Dict[str, str]]:
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
    
async def pull_podcasts(url, page, tab_index: int) -> List[Dict[str, str]]:
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

async def scrape_with_context(browser, coro):
    """
    Utility to run a scraper in its own context/page.
    """
    context = await browser.new_context()
    page = await context.new_page()
    try:
        return await coro(page)
    finally:
        await context.close()

async def grab_channel_info(url: str) -> ChannelMetaData:
    start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # --- Initial context to discover tabs & metadata ---
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

        # --- Run all scrapers concurrently ---
        results = await asyncio.gather(*tasks.values())

        # --- Assign results back to metadata ---
        for key, value in zip(tasks.keys(), results):
            setattr(meta_data, key, value)

        await browser.close()

    save_meta_data_json(meta_data, Path("channel.json"))

    end = time.time()
    print(f"Time taken: {end - start:.2f} seconds")

    return meta_data

async def main():
    await grab_channel_info("https://www.youtube.com/@mkbhd")
    # await grab_channel_info("https://www.youtube.com/@tseries")


if __name__ == "__main__":
    asyncio.run(main())


# Found 1625 video containers
# 520 seconds -> single
# 173.50 seconds -> batch