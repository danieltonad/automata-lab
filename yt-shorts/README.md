# YouTube Shorts Metadata Scraper

A CLI tool to extract metadata from YouTube Shorts — title, views, likes, upload date, and top comments — in CSV or JSON.

Part of [automata-lab](https://github.com/danieltonad/automata-lab).

---

## 🔧 Setup

First, clone the repo and navigate to the project:

```bash
git clone https://github.com/danieltonad/automata-lab.git
cd automata-lab/yt-shorts
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install browser (Chromium):

```bash
playwright install chromium
```

## 📖 Usage

Scrape a single Shorts URL and save to JSON (includes comments):

```bash
python yt_shorts.py "https://youtube.com/shorts/abc123" --json
```

Scrape from a file, save CSV (no comments) and JSON (with comments):

```bash
python yt_shorts.py -r links.txt --csv --json
```

Specify custom output filenames:

```bash
python yt_shorts.py -r links.txt --csv results.csv --json results.jsonf
```

Use base name for both outputs (creates results.csv and results.json):

```bash
python yt_shorts.py -r links.txt -o results --csv --json
```

## ⚙️ Options

- `link`: Optional: A single YouTube Shorts URL (e.g., https://youtube.com/shorts/...)
- `-r, --read FILE`: Path to a text file containing one Shorts URL per line
- `-o, --output BASENAME`: Base name for output files (used when --csv or --json has no filename)
- `--csv [FILE]`: Export to CSV. If FILE is omitted, uses `-o` or defaults to `output.csv`. Note: CSV output excludes the 'comments' field.
- `--json [FILE]`: Export to JSON. If FILE is omitted, uses `-o` or defaults to `output.json`. Note: JSON output includes all fields, including 'comments'.

## 📝 Notes

- Only URLs containing "youtube.com/shorts/" are processed.
- At least one of --csv or --json must be specified.
- Cannot specify both a single link and --read file.
- Comments are extracted from the visible comment section after clicking the comment button.