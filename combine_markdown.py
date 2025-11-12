#!/usr/bin/env python3
"""
Script to combine all markdown files from data/processed into one large markdown file.
Preserves original files and creates a comprehensive combined document.
"""

import os
import glob
from datetime import datetime

def combine_markdown_files(input_dir='data/processed', output_file='data/processed/COMBINED_ALL_DOCUMENTS.md'):
    """
    Combine all .md files from input_dir into one large markdown file.

    Args:
        input_dir: Directory containing markdown files
        output_file: Path for the combined output file
    """

    # Get all markdown files except the combined file itself
    md_files = sorted([f for f in glob.glob(f'{input_dir}/*.md')
                      if not f.endswith('COMBINED_ALL_DOCUMENTS.md')])

    if not md_files:
        print(f"No markdown files found in {input_dir}")
        return

    print(f"Found {len(md_files)} markdown files to combine")
    print(f"Output file: {output_file}")
    print()

    # Create combined markdown
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Write header
        outfile.write("---\n")
        outfile.write("file_id: \"combined_all_documents\"\n")
        outfile.write(f"created: \"{datetime.now().isoformat()}\"\n")
        outfile.write(f"source_files: {len(md_files)}\n")
        outfile.write("description: \"Combined markdown document containing all processed files from the Shluchim knowledge base\"\n")
        outfile.write("---\n\n")

        outfile.write("# COMBINED SHLUCHIM KNOWLEDGE BASE\n\n")
        outfile.write("**Total Documents**: {}\n".format(len(md_files)))
        outfile.write("**Generated**: {}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        outfile.write("**Source Directory**: {}\n\n".format(input_dir))

        outfile.write("---\n\n")
        outfile.write("## Table of Contents\n\n")

        # Generate table of contents
        for idx, filepath in enumerate(md_files, 1):
            filename = os.path.basename(filepath)
            file_id = filename.replace('.md', '')
            outfile.write(f"{idx}. [{file_id}](#{file_id.replace('_', '-').lower()})\n")

        outfile.write("\n")
        outfile.write("=" * 80 + "\n\n")

        # Combine all files
        for idx, filepath in enumerate(md_files, 1):
            filename = os.path.basename(filepath)
            file_id = filename.replace('.md', '')

            print(f"Processing [{idx}/{len(md_files)}]: {filename}")

            try:
                with open(filepath, 'r', encoding='utf-8') as infile:
                    content = infile.read()

                # Write document separator
                outfile.write("\n\n")
                outfile.write("=" * 80 + "\n")
                outfile.write(f"# DOCUMENT {idx}: {file_id}\n")
                outfile.write("=" * 80 + "\n\n")
                outfile.write(f"**Source File**: `{filename}`\n")
                outfile.write(f"**Document ID**: `{file_id}`\n\n")
                outfile.write("---\n\n")

                # Write the content
                outfile.write(content)

                # Add page break marker
                outfile.write("\n\n")
                outfile.write("---\n")
                outfile.write("**End of Document {}**\n".format(idx))
                outfile.write("---\n\n")

            except Exception as e:
                print(f"  ERROR processing {filename}: {e}")
                outfile.write(f"\n\n**ERROR**: Could not process {filename}: {e}\n\n")

    # Get file size
    file_size = os.path.getsize(output_file)
    file_size_mb = file_size / (1024 * 1024)

    print()
    print("=" * 60)
    print("COMBINATION COMPLETE!")
    print("=" * 60)
    print(f"Combined file: {output_file}")
    print(f"Total documents combined: {len(md_files)}")
    print(f"Output file size: {file_size:,} bytes ({file_size_mb:.2f} MB)")
    print()

if __name__ == "__main__":
    combine_markdown_files()
