#!/usr/bin/env python3
"""
Google Drive to Markdown Knowledge Base Processor

Main CLI entry point for processing Google Drive content into a unified markdown knowledge base.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from utils import Config, InventoryManager, setup_logging, load_env
from discovery import discover_files
from download import download_files
from convert import convert_files
from llm_process import process_files_with_llm
from assemble import assemble_markdown

logger = logging.getLogger('gdrive_processor.main')


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Process Google Drive content into a unified markdown knowledge base.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline with default settings
  python src/main.py

  # Discovery only
  python src/main.py --discovery-only

  # Skip LLM processing (programmatic conversion only)
  python src/main.py --no-llm

  # Reprocess all files
  python src/main.py --reprocess-all

  # Process only specific file types
  python src/main.py --include-types pdf,docx

  # Resume from last run
  python src/main.py --resume

  # Dry run (show what would be processed)
  python src/main.py --dry-run

For more information, see README.md
        """
    )

    # Configuration
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    # Pipeline stages
    stage_group = parser.add_argument_group('Pipeline Stages')
    stage_group.add_argument(
        '--discovery-only',
        action='store_true',
        help='Only run discovery (list files from Google Drive)'
    )
    stage_group.add_argument(
        '--download-only',
        action='store_true',
        help='Only download files (requires prior discovery)'
    )
    stage_group.add_argument(
        '--convert-only',
        action='store_true',
        help='Only convert files to markdown (requires prior download)'
    )
    stage_group.add_argument(
        '--process-only',
        action='store_true',
        help='Only process with LLM (requires prior conversion)'
    )
    stage_group.add_argument(
        '--assemble-only',
        action='store_true',
        help='Only assemble master markdown (requires processed files)'
    )
    stage_group.add_argument(
        '--skip-discovery',
        action='store_true',
        help='Skip discovery stage'
    )
    stage_group.add_argument(
        '--skip-download',
        action='store_true',
        help='Skip download stage'
    )
    stage_group.add_argument(
        '--skip-convert',
        action='store_true',
        help='Skip conversion stage'
    )
    stage_group.add_argument(
        '--skip-process',
        action='store_true',
        help='Skip LLM processing stage'
    )
    stage_group.add_argument(
        '--skip-assemble',
        action='store_true',
        help='Skip assembly stage'
    )

    # LLM options
    llm_group = parser.add_argument_group('LLM Options')
    llm_group.add_argument(
        '--no-llm',
        action='store_true',
        help='Disable LLM processing (use only programmatic conversion)'
    )
    llm_group.add_argument(
        '--llm-model',
        help='Override LLM model from config'
    )

    # Processing options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument(
        '--reprocess-all',
        action='store_true',
        help='Reprocess all files (including completed ones)'
    )
    proc_group.add_argument(
        '--reprocess-ids',
        help='Comma-separated list of file IDs to reprocess (e.g., 001,002,003)'
    )
    proc_group.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last run (skip completed files) - default behavior'
    )
    proc_group.add_argument(
        '--start-from',
        help='Start processing from specific file ID (e.g., 050)'
    )
    proc_group.add_argument(
        '--limit',
        type=int,
        help='Limit number of files to process'
    )

    # File filtering
    filter_group = parser.add_argument_group('File Filtering')
    filter_group.add_argument(
        '--include-types',
        help='Only process specific file types (comma-separated, e.g., pdf,docx,gdoc)'
    )
    filter_group.add_argument(
        '--skip-types',
        help='Skip specific file types (comma-separated, e.g., xlsx,csv)'
    )
    filter_group.add_argument(
        '--folder-id',
        help='Process only specific Google Drive folder ID'
    )

    # Sorting
    sort_group = parser.add_argument_group('Sorting Options')
    sort_group.add_argument(
        '--sort',
        choices=['path', 'name', 'date', 'size', 'type'],
        default='path',
        help='Sort order for processing and assembly (default: path)'
    )

    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        '--output',
        help='Override output file path for master markdown'
    )
    output_group.add_argument(
        '--no-toc',
        action='store_true',
        help='Disable table of contents in master markdown'
    )
    output_group.add_argument(
        '--no-metadata',
        action='store_true',
        help='Disable metadata headers in master markdown'
    )

    # Utility options
    util_group = parser.add_argument_group('Utility Options')
    util_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without actually processing'
    )
    util_group.add_argument(
        '--stats',
        action='store_true',
        help='Show processing statistics and exit'
    )
    util_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    util_group.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (WARNING level only)'
    )

    return parser.parse_args()


def show_statistics(inventory: InventoryManager):
    """Display processing statistics."""
    all_files = inventory.get_all_files()

    if not all_files:
        print("No files in inventory.")
        return

    # Get latest version of each file
    latest_files = {}
    for file in all_files:
        file_id = file['file_id']
        if file_id not in latest_files:
            latest_files[file_id] = file
        else:
            current_version = int(latest_files[file_id].get('version', 0))
            new_version = int(file.get('version', 0))
            if new_version > current_version:
                latest_files[file_id] = file

    # Count by status
    status_counts = {}
    for file in latest_files.values():
        status = file.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    # Display statistics
    print("\n=== Processing Statistics ===")
    print(f"Total unique files: {len(latest_files)}")
    print(f"Total file versions: {len(all_files)}")
    print("\nStatus breakdown:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    # File type breakdown
    type_counts = {}
    for file in latest_files.values():
        file_type = file.get('file_type', 'unknown')
        type_counts[file_type] = type_counts.get(file_type, 0) + 1

    print("\nFile type breakdown:")
    for file_type, count in sorted(type_counts.items()):
        print(f"  {file_type}: {count}")

    print()


def main():
    """Main entry point."""
    args = parse_arguments()

    # Load environment variables
    load_env()

    # Load configuration
    try:
        config = Config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Apply CLI overrides
    if args.verbose:
        config.set('logging.level', 'DEBUG')
    elif args.quiet:
        config.set('logging.level', 'WARNING')

    if args.no_llm:
        config.set('llm.enabled', False)

    if args.llm_model:
        config.set('llm.model', args.llm_model)

    if args.output:
        config.set('output.master_file', args.output)

    if args.no_toc:
        config.set('output.include_toc', False)

    if args.no_metadata:
        config.set('output.include_metadata', False)

    if args.reprocess_all:
        config.set('processing.reprocess_existing', True)

    if args.sort:
        config.set('processing.sort_order', args.sort)

    # Setup logging
    global logger
    logger = setup_logging(config)

    logger.info("Starting Google Drive to Markdown processor")

    # Initialize inventory
    inventory_path = config.get('inventory.path', 'data/inventory.csv')
    enable_versioning = config.get('inventory.enable_versioning', True)
    inventory = InventoryManager(inventory_path, enable_versioning)

    # Show statistics and exit if requested
    if args.stats:
        show_statistics(inventory)
        sys.exit(0)

    # Dry run
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be processed")
        pending = inventory.get_pending_files(reprocess=args.reprocess_all)
        logger.info(f"Would process {len(pending)} files")
        for file_data in pending[:10]:  # Show first 10
            logger.info(f"  {file_data['file_id']}: {file_data['source_path']}/{file_data['filename']}")
        if len(pending) > 10:
            logger.info(f"  ... and {len(pending) - 10} more")
        sys.exit(0)

    # Determine which stages to run
    run_discovery = not args.skip_discovery
    run_download = not args.skip_download
    run_convert = not args.skip_convert
    run_process = not args.skip_process and config.get('llm.enabled', True)
    run_assemble = not args.skip_assemble

    # Handle *-only flags
    if args.discovery_only:
        run_download = run_convert = run_process = run_assemble = False
    elif args.download_only:
        run_discovery = run_convert = run_process = run_assemble = False
    elif args.convert_only:
        run_discovery = run_download = run_process = run_assemble = False
    elif args.process_only:
        run_discovery = run_download = run_convert = run_assemble = False
    elif args.assemble_only:
        run_discovery = run_download = run_convert = run_process = False

    # Run pipeline stages
    try:
        # Stage 1: Discovery
        if run_discovery:
            logger.info("=== Stage 1: Discovery ===")
            new_count = discover_files(config, inventory, folder_id=args.folder_id)
            logger.info(f"Discovered {new_count} new files")

        # Stage 2: Download
        if run_download:
            logger.info("=== Stage 2: Download ===")
            stats = download_files(config, inventory, max_files=args.limit)
            logger.info(f"Downloaded {stats['success']} files")

        # Stage 3: Convert
        if run_convert:
            logger.info("=== Stage 3: Conversion ===")
            stats = convert_files(config, inventory)
            logger.info(f"Converted {stats['success']} files")

        # Stage 4: LLM Processing
        if run_process:
            logger.info("=== Stage 4: LLM Processing ===")
            stats = process_files_with_llm(config, inventory, max_files=args.limit)
            logger.info(f"Processed {stats['success']} files with LLM")

        # Stage 5: Assembly
        if run_assemble:
            logger.info("=== Stage 5: Assembly ===")
            use_llm = config.get('llm.enabled', True) and not args.no_llm
            stats = assemble_markdown(
                config,
                inventory,
                use_llm_processed=use_llm,
                sort_by=args.sort
            )
            logger.info(f"Assembled {stats['included']} files into {stats['output_path']}")

        logger.info("Processing complete!")

    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
