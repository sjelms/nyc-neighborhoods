import argparse
import os
import re


def clean_file(file_path):
    """
    Cleans a single file by removing extra spaces and fixing punctuation spacing.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove space before punctuation
    content = re.sub(r"\s+([.,])", r"\1", content)

    # Replace multiple spaces with a single space
    content = re.sub(r" +", " ", content)

    # Remove < and > from subway lines like <F>
    content = re.sub(r"<([A-Z0-9]+)>", r"\1", content)

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
    content = re.sub(r"(### Online Resources)", commute_table + r"\n\1", content)

    disclaimer = """

> **Disclaimer:** This content was generated in part by an artificial intelligence system. While efforts have been made to ensure accuracy and reliability, AI-generated information may contain errors or omissions. Please verify any critical information.
"""
    content += disclaimer

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    """
    Main function to parse arguments and clean files.
    """
    parser = argparse.ArgumentParser(description="Clean up markdown files.")
    parser.add_argument("path", help="The file or directory to clean.")
    args = parser.parse_args()

    if os.path.isfile(args.path):
        if args.path.endswith(".md"):
            print(f"Cleaning {args.path}...")
            clean_file(args.path)
        else:
            print(f"Error: Provided file is not a markdown file: {args.path}")
    elif os.path.isdir(args.path):
        for root, _, files in os.walk(args.path):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    print(f"Cleaning {file_path}...")
                    clean_file(file_path)
    else:
        print(f"Error: Path not found at {args.path}")
        return


if __name__ == "__main__":
    main()
