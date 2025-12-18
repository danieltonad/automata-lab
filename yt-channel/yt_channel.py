import asyncio, argparse, sys, math, random, time, re
from pathlib import Path
from playwright.async_api import async_playwright
from dataclasses import dataclass, fields
from typing import List, Set, Tuple, Dict


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

@dataclass
class ChannelTabs:
    home: int | None
    videos: int | None
    shorts: int | None
    playlists: int | None
    live: int | None


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
        live_streams=None
    )


    # tabs
    tabs = page.locator("div[class='tabGroupShapeTabs']")
    tabs_text = await tabs.all_inner_texts()
    tabs_dict = {tab.lower(): i for i, tab in enumerate(tabs_text[0].split('\n'))}


    allowed = {f.name for f in fields(ChannelTabs)}
    filtered_tabs = {k: v for k, v in tabs_dict.items() if k in allowed}

    return meta_data, ChannelTabs(**filtered_tabs)


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

    await asyncio.sleep(0.5)
    containers = page.locator("div[class*='style-scope ytd-rich-item-renderer']")
    size = await page.locator("div[class*='style-scope ytd-rich-item-renderer']").count()
    videos = []
    for i in range(size):
        target = containers.nth(i)
        await target.scroll_into_view_if_needed()
        link = await target.locator( "a#thumbnail.ytd-thumbnail").get_attribute("href")
        thumbnail = await target.locator( "a#thumbnail.ytd-thumbnail").locator("img[class='ytCoreImageHost ytCoreImageFillParentHeight ytCoreImageFillParentWidth ytCoreImageContentModeScaleAspectFill ytCoreImageLoaded']").nth(0).get_attribute("src")
        duration = await target.locator("ytd-thumbnail #thumbnail .yt-badge-shape__text").first.inner_text()
        title  = await target.locator("a[class='yt-simple-endpoint focus-on-expand style-scope ytd-rich-grid-media']").inner_text()
        pane = target.locator("span[class*='inline-metadata-item style-scope ytd-video-meta-block']")
        views = await pane.nth(0).inner_text()
        views = views.replace(" views","")
        publshed = await pane.nth(1).inner_text()
        videos.append({
            "title": title,
            "link": f"https://www.youtube.com{link}",
            "thumbnail": thumbnail,
            "duration": duration,
            "views": views,
            "published": publshed
        })

    print(videos[-4:])
    print(f"Found {size} video containers")
    
   
    return videos


async def grab_channel_info(url: str) -> ChannelMetaData:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        meta_data, tabs = await channel_data(url, page)
        print(f"Channel MetaData: {meta_data}")
        print(f"Channel Tabs: {tabs}")

        videos = await pull_videos(url, page, tabs.videos) if tabs.videos is not None else None
        # print(f"Videos: {videos}")

async def main():
    await grab_channel_info("https://www.youtube.com/@mkbhd")


if __name__ == "__main__":
    asyncio.run(main())