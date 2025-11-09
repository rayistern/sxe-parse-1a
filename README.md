# Google Drive to Markdown Knowledge Base Processor

A comprehensive CLI tool to convert Google Drive content into a unified markdown knowledge base, perfect for chatbot training and knowledge management.

## Features

- **Google Drive Integration**: List and download files from Google Drive, including native Google Docs/Sheets
- **Multiple Format Support**: PDF (with OCR), DOCX, XLSX, CSV, HTML, TXT, Google Docs, Google Sheets, and more
- **Optional LLM Processing**: Enhance markdown conversion and remove PII using OpenAI models
- **Versioning**: Track multiple processing runs of the same files
- **Flexible CLI**: Comprehensive command-line options for fine-grained control
- **Knowledge Base Assembly**: Combine all processed files into a single, well-structured markdown file
- **PII Removal**: Automatic redaction of personally identifiable information
- **Resume Capability**: Resume from interrupted runs
- **Configurable**: YAML configuration file with environment variable support

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Processing Pipeline](#processing-pipeline)
- [CLI Reference](#cli-reference)
- [File Formats](#file-formats)
- [Output Structure](#output-structure)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Cloud project with Drive API enabled
- OpenAI API key (if using LLM processing)
- Tesseract OCR (for PDF processing)

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils pandoc
```

**macOS:**
```bash
brew install tesseract poppler pandoc
```

**Windows:**
- Install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- Install [Poppler](https://blog.alivate.com.au/poppler-windows/)
- Install [Pandoc](https://pandoc.org/installing.html)

### Python Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd sxe-parse-1a
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Google Drive API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials and save as `credentials.json` in the project root

### Environment Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-api-key-here
```

## Quick Start

### Basic Usage (Full Pipeline)

```bash
# Process entire Google Drive with LLM
python src/main.py

# Process without LLM (programmatic conversion only)
python src/main.py --no-llm

# Process specific folder
python src/main.py --folder-id YOUR_FOLDER_ID
```

### First Run

On your first run, you'll be prompted to authenticate with Google Drive. This will open a browser window to authorize the application.

## Configuration

The system is configured via `config.yaml`. Key sections:

### Google Drive Settings

```yaml
google_drive:
  folder_id: ""  # Leave empty for entire drive
  credentials_path: "credentials.json"
  include_shared_drives: false
```

### File Type Handling

```yaml
file_types:
  skip_extensions:
    - jpg
    - png
    - mp3
    - mp4
  # ... see config.yaml for full list
```

### LLM Settings

```yaml
llm:
  enabled: true
  provider: "openai"
  model: "gpt-4o-mini"
  max_chunk_size: 100000
  enable_pii_removal: true
```

### Output Settings

```yaml
output:
  master_file: "data/output/knowledge_base.md"
  include_toc: true
  include_metadata: true
  folder_separator: " > "
```

See `config.yaml` for all available options.

## Usage

### Processing Pipeline

The tool processes files in 5 stages:

1. **Discovery**: List files from Google Drive and populate inventory
2. **Download**: Download files and export Google native formats
3. **Conversion**: Convert files to markdown programmatically
4. **Processing**: (Optional) Enhance with LLM and remove PII
5. **Assembly**: Combine all files into master markdown

### Running Specific Stages

```bash
# Discovery only
python src/main.py --discovery-only

# Download only (after discovery)
python src/main.py --download-only

# Convert only (after download)
python src/main.py --convert-only

# Process with LLM only (after conversion)
python src/main.py --process-only

# Assemble only (after processing)
python src/main.py --assemble-only
```

### Common Workflows

**Resume interrupted run:**
```bash
python src/main.py --resume
```

**Reprocess all files:**
```bash
python src/main.py --reprocess-all
```

**Process only PDFs and Word docs:**
```bash
python src/main.py --include-types pdf,docx
```

**Skip spreadsheets:**
```bash
python src/main.py --skip-types xlsx,csv
```

**Process first 10 files (testing):**
```bash
python src/main.py --limit 10
```

**Dry run (see what would be processed):**
```bash
python src/main.py --dry-run
```

**View statistics:**
```bash
python src/main.py --stats
```

## CLI Reference

### Pipeline Stages

- `--discovery-only`: Only run discovery
- `--download-only`: Only download files
- `--convert-only`: Only convert to markdown
- `--process-only`: Only process with LLM
- `--assemble-only`: Only assemble master file
- `--skip-discovery`: Skip discovery stage
- `--skip-download`: Skip download stage
- `--skip-convert`: Skip conversion stage
- `--skip-process`: Skip LLM processing
- `--skip-assemble`: Skip assembly stage

### LLM Options

- `--no-llm`: Disable LLM processing
- `--llm-model MODEL`: Override LLM model

### Processing Options

- `--reprocess-all`: Reprocess all files
- `--reprocess-ids ID1,ID2`: Reprocess specific file IDs
- `--resume`: Resume from last run (default)
- `--start-from ID`: Start from specific file ID
- `--limit N`: Limit number of files

### File Filtering

- `--include-types TYPE1,TYPE2`: Only process specific types
- `--skip-types TYPE1,TYPE2`: Skip specific types
- `--folder-id ID`: Process specific folder

### Sorting

- `--sort ORDER`: Sort order (path, name, date, size, type)

### Output Options

- `--output PATH`: Override output file path
- `--no-toc`: Disable table of contents
- `--no-metadata`: Disable metadata headers

### Utility Options

- `--dry-run`: Show what would be processed
- `--stats`: Show processing statistics
- `-v, --verbose`: Enable verbose logging
- `-q, --quiet`: Quiet mode

## File Formats

### Supported Formats

**Documents:**
- PDF (with OCR support)
- Microsoft Word (.docx, .doc)
- Google Docs
- OpenDocument (.odt)
- HTML
- Plain text (.txt)
- Markdown (.md)

**Spreadsheets:**
- Microsoft Excel (.xlsx, .xls)
- Google Sheets
- CSV

**Other:**
- Google Slides (exported as PPTX)

### Skipped Formats (Configurable)

- Images: jpg, png, gif, bmp, svg
- Audio: mp3, wav, ogg, m4a
- Video: mp4, avi, mov, mkv

## Output Structure

### Directory Structure

```
data/
├── inventory.csv          # File tracking with versioning
├── raw/                   # Downloaded files
├── converted/             # Programmatically converted markdown
├── processed/             # LLM-processed markdown
└── output/
    └── knowledge_base.md  # Final master markdown
```

### Inventory CSV

Tracks all files and their processing status:

```csv
file_id,source_path,filename,file_type,size_bytes,drive_file_id,mime_type,version,status,last_processed,error_message
001,/Reports/2024,Q1.pdf,pdf,125000,abc123,application/pdf,1,completed,2025-01-09T10:30:00,
```

**Statuses:**
- `pending`: Not yet processed
- `downloaded`: Downloaded from Google Drive
- `converted`: Converted to markdown
- `processed`: Processed with LLM
- `completed`: Fully processed
- `download_failed`: Download failed
- `conversion_failed`: Conversion failed
- `processing_failed`: LLM processing failed

### Master Markdown Structure

```markdown
# Knowledge Base

Generated: 2025-01-09 10:30:00

## Table of Contents

### Reports > 2024
- [Q1 Report.pdf](#reports-2024-q1-report-pdf)

---

# [Reports > 2024] Q1 Report.pdf

---
file_id: 001
source_path: /Reports/2024
original_filename: Q1 Report.pdf
file_type: pdf
---

[Document content here...]

---
```

## Advanced Usage

### Versioning

The system tracks multiple versions of processed files. When you reprocess a file, a new version is created:

```bash
# Create new versions of all files
python src/main.py --reprocess-all

# Reprocess specific files
python src/main.py --reprocess-ids 001,002,003
```

### Custom Sorting

Control the order of documents in the master file:

```bash
# Sort by folder path (default)
python src/main.py --sort path

# Sort by filename
python src/main.py --sort name

# Sort by processing date
python src/main.py --sort date

# Sort by file size (largest first)
python src/main.py --sort size

# Sort by file type
python src/main.py --sort type
```

### Selective Processing

Process specific folders or file types:

```bash
# Process only a specific folder
python src/main.py --folder-id 1A2B3C4D5E6F

# Process only documents (no spreadsheets)
python src/main.py --include-types pdf,docx,gdoc

# Skip large spreadsheets
python src/main.py --skip-types xlsx
```

### LLM Configuration

Customize LLM behavior in `config.yaml`:

```yaml
llm:
  model: "gpt-4o-mini"      # Or gpt-4o for better quality
  max_chunk_size: 100000    # Adjust for your needs
  temperature: 0.1          # Lower = more deterministic
  enable_pii_removal: true  # Toggle PII removal
```

## Troubleshooting

### Common Issues

**Authentication Issues:**
```bash
# Delete token and re-authenticate
rm token.json
python src/main.py --discovery-only
```

**OCR Not Working:**
- Ensure Tesseract is installed: `tesseract --version`
- Check language pack: `tesseract --list-langs`

**Pandoc Errors:**
- Ensure Pandoc is installed: `pandoc --version`
- Try reinstalling: `pip install --upgrade pypandoc`

**Out of Memory:**
- Reduce `llm.max_chunk_size` in config
- Process files in batches: `--limit 10`

**Rate Limits (OpenAI):**
- Reduce `processing.max_workers`
- Add delays between requests (modify `llm_process.py`)

### Logs

Check logs for detailed error information:

```bash
tail -f logs/gdrive_processor.log
```

Enable verbose logging:

```bash
python src/main.py --verbose
```

## Development

### Project Structure

```
sxe-parse-1a/
├── src/
│   ├── main.py           # CLI entry point
│   ├── discovery.py      # Google Drive file listing
│   ├── download.py       # File download/export
│   ├── convert.py        # Programmatic conversion
│   ├── llm_process.py    # LLM processing
│   ├── assemble.py       # Master markdown assembly
│   └── utils.py          # Utilities and helpers
├── data/                 # Data directories
├── logs/                 # Log files
├── config.yaml           # Configuration
├── .env                  # Environment variables
└── requirements.txt      # Python dependencies
```

### Adding New File Converters

To add support for new file formats:

1. Update `file_types` in `config.yaml`
2. Add converter method in `src/convert.py`
3. Update `DocumentConverter.convert_file()` routing

### Extending LLM Prompts

Modify system prompts in `src/llm_process.py`:

```python
def _build_system_prompt(self) -> str:
    # Customize prompts here
    pass
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review logs in `logs/gdrive_processor.log`
- Open an issue on GitHub

## Acknowledgments

Built with:
- Google Drive API
- OpenAI API
- Pandoc, Tesseract, PyPDF, and many other open-source tools
