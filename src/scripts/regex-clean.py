
import os
import re
import argparse

def clean_file(file_path):
    """
    Cleans a single file by removing extra spaces and fixing punctuation spacing.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove space before punctuation
    content = re.sub(r'\s+([.,])', r'\1', content)
    
    # Replace multiple spaces with a single space
    content = re.sub(r' +', ' ', content)

    # Remove < and > from subway lines like <F>
    content = re.sub(r'<([A-Z0-9]+)>', r'\1', content)

    commute_table = """
---

### Commute Times (optional — if data available)
| Destination | Subway | Drive |
|-------------|--------|-------|
| … | … | … |
| … | … | … |

---
"""
    # Insert commute_table before ### Online Resources
    content = re.sub(r'(### Online Resources)', commute_table + r'\n\1', content)

    # Remove leading space from numeric list items (e.g., ZIP codes)
    content = re.sub(r'^- (\d+)', r'-\1', content, flags=re.MULTILINE)

    disclaimer = """
**Disclaimer:** This content was generated in part by an artificial intelligence system. While efforts have been made to ensure accuracy and reliability, AI-generated information may contain errors or omissions. Please verify any critical information.
"""
    content += disclaimer

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """
    Main function to parse arguments and clean files.
    """
    parser = argparse.ArgumentParser(description='Clean up markdown files.')
    parser.add_argument('directory', help='The directory to clean.')
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found at {args.directory}")
        return

    for root, _, files in os.walk(args.directory):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                print(f"Cleaning {file_path}...")
                clean_file(file_path)

if __name__ == '__main__':
    main()
