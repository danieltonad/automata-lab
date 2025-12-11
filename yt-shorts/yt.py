import asyncio
from playwright.async_api import async_playwright

url = "https://www.youtube.com/shorts/hQhXFSXNaoM"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)

        short_title = page.locator('span[class*="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap yt-core-attributed-string--link-inherit-color"]')
        stats_elem = 'span[class*="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap yt-core-attributed-string--text-alignment-center yt-core-attributed-string--word-wrapping"]'
        stats = page.locator(stats_elem)
        await stats.first.wait_for(state="visible", timeout=10000)
        stats = await stats.all_inner_texts()
        print("Stats found:", stats)
        likes, comments = stats[0], stats[2]

        # await asyncio.sleep(15)  # Ensure all elements are loaded

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


        print("Short Title:", await short_title.inner_text())
        print("Likes:", likes)
        print("Comments:", comments)
        print("Views:", views)
        print("Upload Date:", date)

        await browser.close()

asyncio.run(main())
