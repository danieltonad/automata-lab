# YouTube Channel Metadata Scraper

CLI tool to extract metadata from YouTube channels — name, description, subscriber count, total views, country, joined date, channel image, channel banner, and external links.

Part of [automata-lab](https://github.com/danieltonad/automata-lab).

---

## 🔧 Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/danieltonad/automata-lab.git
   cd automata-lab/yt-channel
   ```

2. **Create a virtual environment** (optional but recommended):

   ```bash
   python -m venv env
   env\Scripts\activate.bat  # For CMD on Windows
   # or
   "env/Scripts/Activate.ps1"  # For PowerShell on Windows
   ```

3. **Install Python dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Install the browser runtime (Chromium)**:
   ```bash
   playwright install chromium
   ```

## 📖 Usage

Scrape a YouTube channel by providing a channel URL, handle, ID, or username:

```bash
python yt_channel.py <channel_name_or_link_or_id>
```

### Supported Input Formats:

- Full channel URL: `https://www.youtube.com/@channelhandle` or `https://www.youtube.com/channel/UC...`
- Channel handle: `@channelhandle`
- Channel ID: `UCxxxxxxxxxxxxxxxxxxxx` (24-character ID starting with UC)
- Plain username: `channelname`

### Examples:

```bash
# Using channel handle
python yt_channel.py @mkbhd

# Using full URL
python yt_channel.py https://www.youtube.com/@mkbhd

# Using channel ID
python yt_channel.py UCBJycsmduvYEL83R_U4JriQ

# Using plain username
python yt_channel.py mkbhd
```

## 📦 Output

The tool saves channel metadata to `channel.json` in the current directory and displays a summary of content counts.

JSON fields:

- `name`: Channel Name
- `description`: Channel Description
- `subscribers`: Subscriber Count
- `videos_count`: Total Videos Count
- `country`: Country
- `total_views`: Total Views
- `joined`: Join Date
- `channel_image`: Channel Image URL
- `channel_banner`: Channel Banner URL
- `links`: External Links (Dictionary)
- `videos`: Array of video objects (title, link, thumbnail, duration, views, published)
- `shorts`: Array of shorts objects (title, link, thumbnail, views)
- `playlists`: Array of playlist objects (title, link, thumbnail, badge)
- `live_streams`: Array of live stream objects (title, link, thumbnail, duration, published)
- `podcasts`: Array of podcast objects (title, link, thumbnail, badge)

Note: Only tabs available on the channel will be scraped. Some channels may not have all content types.

## 🚀 Performance

The script uses Playwright with adaptive concurrency to scrape channel tabs efficiently. Content is scraped in batches (default: 15 items per batch). For channels with many videos, scraping stops at 3,500 videos to prevent excessive load times.

## 🛠️ Troubleshooting

- Install error for `playwright`: ensure you have run `playwright install chromium`.
- Empty or partial results: YouTube UI can change; update Playwright and try again.
- Slow runs: channels with many videos/shorts take longer to scrape. The script will display progress as it works.
- Logs: failures are appended to `yt_shorts.log` in the project directory.
