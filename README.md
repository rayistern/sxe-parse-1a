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

Follow these steps to set up Google Drive API access:

#### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Click the project dropdown at the top (next to "Google Cloud")
4. Click "NEW PROJECT"
5. Enter a project name (e.g., "Google Drive Parser")
6. Click "CREATE"
7. Wait for the project to be created, then select it from the project dropdown

#### 2. Enable the Google Drive API

1. In your project, go to the **Navigation Menu** (≡) → **APIs & Services** → **Library**
2. Search for "Google Drive API"
3. Click on "Google Drive API" from the results
4. Click the blue **"ENABLE"** button
5. Wait for the API to be enabled

#### 3. Configure OAuth Consent Screen

Before creating credentials, you need to configure the OAuth consent screen:

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **"External"** user type (unless you have a Google Workspace account)
3. Click **"CREATE"**
4. Fill in the required fields:
   - **App name**: "Google Drive Parser" (or your preferred name)
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
5. Click **"SAVE AND CONTINUE"**
6. On the "Scopes" page, click **"SAVE AND CONTINUE"** (no need to add scopes manually)
7. On the "Test users" page:
   - Click **"+ ADD USERS"**
   - Enter your Google email address (the one that has access to the Drive files)
   - Click **"ADD"**
   - Click **"SAVE AND CONTINUE"**
8. Review the summary and click **"BACK TO DASHBOARD"**

#### 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **"+ CREATE CREDENTIALS"** at the top
3. Select **"OAuth client ID"**
4. For "Application type", select **"Desktop app"**
5. Enter a name (e.g., "Desktop Client")
6. Click **"CREATE"**
7. A dialog will appear with your credentials - click **"OK"**

#### 5. Download Credentials File

1. In the **Credentials** page, find your newly created OAuth 2.0 Client ID
2. Click the **download icon** (⬇) on the right side of the credential
3. Save the downloaded JSON file as `credentials.json` in your project root directory:
   ```
   /home/user/sxe-parse-1a/credentials.json
   ```

**Important Notes:**
- Keep `credentials.json` secure and **never commit it to version control** (it's already in `.gitignore`)
- The first time you run the tool, it will open a browser for authentication
- After authentication, a `token.json` file will be created to store your access token
- You only need to authenticate once (unless you delete `token.json`)

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

  # Customize prompts (all configurable in config.yaml)
  system_prompt: |
    You are a document processing assistant...
  pii_removal_prompt: |
    PII Removal instructions...
  user_prompt_template: |
    Process the following document...
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
- PDF (with OCR support - automatically detects if OCR is needed)
  - For digital PDFs: Extracts text directly (fast, no OCR needed)
  - For scanned PDFs: Automatically runs OCR on pages without extractable text
  - Configurable OCR language and DPI settings in `config.yaml`
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

  # Customize all prompts - edit in config.yaml
  system_prompt: |
    You are a document processing assistant. Your task is to convert documents to well-structured markdown.

    Guidelines:
    - Preserve all meaningful content and structure
    - Use proper markdown formatting (headers, lists, tables, bold, italic, code blocks)
    - Use ATX-style headers (# ## ###)
    - Maintain document hierarchy and organization
    - For tables, use proper markdown table syntax
    - For code snippets, use fenced code blocks with language identifiers
    - Remove any OCR artifacts or formatting errors
    - Improve readability while preserving original meaning

  pii_removal_prompt: |

    PII Removal:
    - Identify and REDACT all personally identifiable information (PII)
    - Replace PII with [REDACTED-TYPE] placeholders:
      - Names: [REDACTED-NAME]
      - Email addresses: [REDACTED-EMAIL]
      - Phone numbers: [REDACTED-PHONE]
      - Street addresses: [REDACTED-ADDRESS]
      - Social Security Numbers: [REDACTED-SSN]
      - Credit card numbers: [REDACTED-CCN]
      - Dates of birth: [REDACTED-DOB]
      - Other sensitive data: [REDACTED-PII]
    - Preserve generic company names, organizations, and public entities
    - Keep job titles, departments, and roles if not tied to specific individuals

  user_prompt_template: |
    Process the following document and convert it to clean, well-structured markdown.

    Filename: {filename}

    Content:
    {content}
```

**Note:** All three prompts are fully configurable in `config.yaml`. Edit them to customize LLM behavior for your specific use case.

## Troubleshooting

### Common Issues

**Google Drive Authentication Issues:**

*Problem: "Access blocked: This app's request is invalid"*
- Make sure you configured the OAuth consent screen (step 3 above)
- Add yourself as a test user in the OAuth consent screen

*Problem: "Error: invalid_grant" or "Token has been expired or revoked"*
```bash
# Delete token and re-authenticate
rm token.json
python src/main.py --discovery-only
```

*Problem: Browser doesn't open during authentication*
- The tool will print a URL in the terminal
- Copy and paste it into your browser manually
- Complete the authentication flow
- The tool will detect the authorization automatically

*Problem: "Credentials file not found"*
- Make sure `credentials.json` is in the project root directory
- Check the filename is exactly `credentials.json` (not `client_secret_xxx.json`)
- You can rename the downloaded file to `credentials.json`

*Problem: "Access denied" or "Insufficient permissions"*
- Make sure the Google account you authenticate with has access to the shared folder
- If using a shared folder, verify it's shared with your account
- Check that the Google Drive API is enabled in your Google Cloud project

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
