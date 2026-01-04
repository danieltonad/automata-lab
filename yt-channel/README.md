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

To scrape metadata from a YouTube channel, run the following command:

```bash
python yt_channel.py <channel_url>
```

### Parameters:

- `<channel_url>`: The URL of the YouTube channel you want to scrape.

### Output:

The tool will output the channel metadata in JSON format, including:

- `name`: Channel Name
- `description`: Channel Description
- `subscribers`: Subscriber Count
- `videos_count`: Total Videos Count
- `country`: Country
- `total_views`: Total Views
- `joined`: Join Date
- `channel_image`: Channel Image URL
- `channel_banner`: Channel Banner URL
- `links`: External Links
- `videos`: Videos List
- `shorts`: Shorts List
- `playlists`: Playlists List
- `live_streams`: Live Streams List
- `podcasts`: Podcasts List

### Example:

```bash
python yt_channel.py https://www.youtube.com/c/YourChannelName
```

### Logs:

Failures are logged in `yt_channel.log` in the project directory.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
