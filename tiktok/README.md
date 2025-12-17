# TikTok Metadata Scraper

CLI tool to extract metadata from TikTok videos — title, author, hashtags, likes, shares, bookmarks, total comment count, and top-level comments — and export to CSV and/or JSON.

Part of [automata-lab](https://github.com/danieltonad/automata-lab).

---

## 🔧 Setup

Clone and enter the project folder:

```bash
git clone https://github.com/danieltonad/automata-lab.git
cd automata-lab/tiktok
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
# playwright-stealth is required by this tool
pip install playwright-stealth
```

Install the browser runtime (Chromium):

```bash
playwright install chromium
```

## 📖 Usage

Scrape a single TikTok URL and save JSON (includes comments):

```bash
python tiktok.py "https://www.tiktok.com/@someuser/video/1234567890" --json
```

Scrape multiple URLs from a file, save CSV (no comments field) and JSON (with comments):

```bash
python tiktok.py -r links.txt --csv --json
```

Specify custom output filenames:

```bash
python tiktok.py -r links.txt --csv results.csv --json results.json
```

Use a base name for both outputs (creates results.csv and results.json):

```bash
python tiktok.py -r links.txt -o results --csv --json
```

Example `links.txt` format:

```
https://www.tiktok.com/@user1/video/123...
https://www.tiktok.com/@user2/video/456...
```

## ⚙️ Options

- `link`: Optional single TikTok URL
- `-r, --read FILE`: Path to a text file containing one TikTok URL per line
- `-o, --output BASENAME`: Base name for outputs when `--csv`/`--json` have no filenames
- `--csv [FILE]`: Export to CSV. If FILE is omitted, uses `-o` or defaults to `output.csv`
- `--json [FILE]`: Export to JSON. If FILE is omitted, uses `-o` or defaults to `output.json`

Notes:

- Only URLs containing `tiktok.com/` are processed.
- Provide either a single `link` or `--read FILE`, not both.
- At least one output format (`--csv` or `--json`) is required.

## 📦 Output

CSV columns (one row per video):

- `link`, `author`, `title`, `tags`, `likes`, `shares`, `bookmarks`, `comment_count`

JSON fields (one object per video):

- `link`, `author`, `title`, `tags`, `likes`, `shares`, `bookmarks`, `comment_count`, `comments` (array of strings)

## 🚀 Performance

Batch scraping uses Playwright with stealth evasion and adaptive concurrency. The script computes an optimal chunk size based on your CPU, RAM, and clock speed to balance throughput and stability. Progress is printed per chunk; failures are retried up to 3 times with exponential backoff.

## 🛠️ Troubleshooting

- Install error for `playwright`: ensure you have run `playwright install chromium`.
- Import error `playwright_stealth`: run `pip install playwright-stealth`.
- Rate limiting/CAPTCHA: re-run later, reduce batch size (fewer URLs), or use a stable IP.
- Slow or flaky runs: close other heavy apps, ensure enough RAM, or process fewer URLs at once (reduce the input list).
- Logs: failures are appended to `tiktok.log` in the project directory.

## ✅ Compatibility

- Tested on Windows with Python 3.12. Should also work on Linux/macOS.

## 📚 Project Files

- `tiktok.py`: CLI entry point and scraper implementation
- `requirements.txt`: Python dependencies (install `playwright-stealth` separately if missing)
- `links.txt`: Example input (one URL per line)
- `output.csv`, `output.json`: Example outputs
