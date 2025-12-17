# YouTube Shorts Metadata Scraper

CLI tool to extract metadata from YouTube Shorts — title, views, likes, upload date, comment count, channel link, hashtags, and top-level comments — and export to CSV and/or JSON.

Part of [automata-lab](https://github.com/danieltonad/automata-lab).

---

## 🔧 Setup

Clone and enter the project folder:

```bash
git clone https://github.com/danieltonad/automata-lab.git
cd automata-lab/yt-shorts
```

Create a virtual environment (optional but recommended):

```bash
python -m venv env
"env/Scripts/Activate.ps1"   # PowerShell on Windows
# or
env\Scripts\activate.bat     # CMD on Windows
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Install the browser runtime (Chromium):

```bash
playwright install chromium
```

## 📖 Usage

Scrape a single Shorts URL and save JSON (includes comments):

```bash
python yt_shorts.py "https://youtube.com/shorts/abc123" --json
```

Scrape multiple URLs from a file, save CSV (no comments field) and JSON (with comments):

```bash
python yt_shorts.py -r links.txt --csv --json
```

Specify custom output filenames:

```bash
python yt_shorts.py -r links.txt --csv results.csv --json results.json
```

Use a base name for both outputs (creates results.csv and results.json):

```bash
python yt_shorts.py -r links.txt -o results --csv --json
```

Example `links.txt` format:

```
https://youtube.com/shorts/abc123
https://www.youtube.com/shorts/xyz456
```

## ⚙️ Options

- `link`: Optional single YouTube Shorts URL (e.g., https://youtube.com/shorts/...)
- `-r, --read FILE`: Path to a text file containing one Shorts URL per line
- `-o, --output BASENAME`: Base name for outputs when `--csv`/`--json` have no filenames
- `--csv [FILE]`: Export to CSV. If FILE is omitted, uses `-o` or defaults to `output.csv`
- `--json [FILE]`: Export to JSON. If FILE is omitted, uses `-o` or defaults to `output.json`

Notes:

- Only URLs containing `youtube.com/shorts/` are processed.
- Provide either a single `link` or `--read FILE`, not both.
- At least one output format (`--csv` or `--json`) is required.

## 📦 Output

CSV columns (one row per Short):

- `link`, `title`, `tags`, `channel_link`, `likes`, `comment_count`, `views`, `upload_date`

JSON fields (one object per Short):

- `link`, `title`, `tags`, `channel_link`, `likes`, `comment_count`, `views`, `upload_date`, `comments` (array of strings)

## 🚀 Performance

Batch scraping uses Playwright with adaptive concurrency. The script computes an optimal chunk size based on your CPU, RAM, and clock speed to balance throughput and stability. Progress is printed per chunk; failures are retried with a limited backoff.

## 🛠️ Troubleshooting

- Install error for `playwright`: ensure you have run `playwright install chromium`.
- Empty or partial results: YouTube UI can change; update Playwright and try again.
- Slow or flaky runs: close other heavy apps, ensure enough RAM, or process fewer URLs at once (reduce the input list).
- Logs: failures are appended to `yt_shorts.log` in the project directory.