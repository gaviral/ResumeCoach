import os
import fnmatch
import sys
from pathlib import Path

# Attempt to import pygments for language detection
try:
    from pygments import lexers
    from pygments.util import ClassNotFound
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    print("Warning: 'Pygments' library not found. Install it with 'pip install Pygments' for code block language detection.")

# --- Configuration ---

# !!! IMPORTANT: Set these paths before running !!!
# Use the corrected relative paths or your desired absolute paths
SOURCE_DIRECTORY = "./frontend"
OUTPUT_MARKDOWN_FILE = "./frontend_code.md"

# List of wildcard patterns for files to ignore
IGNORE_FILES = [
    '.env*',
    '*.log',
    '*.lock',
    'package-lock.json',
    'yarn.lock',
    '*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp', '*.ico',
    '*.svg',
    '*.woff', '*.woff2', '*.ttf', '*.otf', '*.eot',
    '*.DS_Store',
    # Consider if you want to ignore the output file itself if it's inside the source dir
    Path(OUTPUT_MARKDOWN_FILE).name, # Ignore the output file itself by name
]

# List of wildcard patterns for folders to ignore
IGNORE_FOLDERS = [
    'node_modules',
    'dist',
    'build',
    '.git',
    '.vscode',
    '.idea',
    '__pycache__',
    'coverage',
    'public',
]

# --- End of Configuration ---

# --- Helper Functions ---

def should_ignore(name, is_dir, ignore_files_patterns, ignore_folders_patterns):
    """Checks if a given file or directory name should be ignored."""
    patterns_to_check = ignore_folders_patterns if is_dir else ignore_files_patterns
    for pattern in patterns_to_check:
        if fnmatch.fnmatch(name, pattern):
            return True
    # Specifically check if the name matches the output file name
    # (This check is technically redundant if OUTPUT_MARKDOWN_FILE name matches an IGNORE_FILES pattern)
    # if not is_dir and name == Path(OUTPUT_MARKDOWN_FILE).name:
    #     return True
    return False

def guess_lexer(filename):
    """Guess the Pygments lexer based on filename, return language string."""
    if not PYGMENTS_AVAILABLE:
        return ""
    try:
        lexer = lexers.guess_lexer_for_filename(filename, "")
        return lexer.aliases[0] if lexer.aliases else ""
    except ClassNotFound:
        return ""
    except Exception as e:
        print(f"Warning: Could not guess language for {filename}: {e}")
        return ""

# --- Core Logic ---

def generate_project_markdown(src_dir, output_file, ignore_files, ignore_folders):
    """
    Generates a single Markdown file containing the project structure tree
    and the content of non-ignored files. Handles .md files specially.
    """
    src_path = Path(src_dir).resolve()
    output_path = Path(output_file).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Prevent reading the output file if it's inside the source directory
    # Add its name to ignore_files dynamically if it's within src_path
    effective_ignore_files = list(ignore_files) # Create a copy
    try:
        if output_path.relative_to(src_path):
             # Check if output is inside source *after* resolving paths
             if output_path.name not in effective_ignore_files:
                 print(f"Info: Adding output file '{output_path.name}' to ignore list as it's inside the source directory.")
                 effective_ignore_files.append(output_path.name)
    except ValueError:
        # output_path is not inside src_path, no need to add it to ignores
        pass


    if not src_path.is_dir():
        print(f"Error: Source directory '{src_path}' not found or is not a directory.")
        sys.exit(1)

    print(f"Scanning directory: {src_path}")
    print(f"Ignoring Files: {effective_ignore_files}") # Use the potentially updated list
    print(f"Ignoring Folders: {ignore_folders}")
    print("-" * 30)

    tree_lines = []
    files_to_include = []

    print("Generating directory tree and collecting files...")
    # Use the resolved absolute path for walking
    for root, dirs, files in os.walk(src_path, topdown=True):
        root_path = Path(root)
        relative_root = root_path.relative_to(src_path)

        # Filter ignored directories using the original ignore_folders list
        dirs[:] = [d for d in dirs if not should_ignore(d, True, effective_ignore_files, ignore_folders)]

        level = len(relative_root.parts)
        indent = '    ' * level

        if relative_root != Path('.'):
            tree_lines.append(f"{indent}*   {root_path.name}{os.sep}")
            indent += '    '

        files.sort()
        for filename in files:
             # Use the effective_ignore_files list here
            if not should_ignore(filename, False, effective_ignore_files, ignore_folders):
                abs_file_path = root_path / filename
                rel_file_path = relative_root / filename
                files_to_include.append((abs_file_path, rel_file_path))
                tree_lines.append(f"{indent}-   {filename}")

    print(f"Found {len(files_to_include)} files to include.")
    print("-" * 30)

    print(f"Writing content to Markdown file: {output_path}")
    all_markdown_content = []

    all_markdown_content.append("# Project Structure")
    all_markdown_content.append("```")
    all_markdown_content.append(f".{os.sep} ({src_path.name})")
    all_markdown_content.extend(tree_lines)
    all_markdown_content.append("```")
    all_markdown_content.append("\n# File Contents")

    for abs_path, rel_path in files_to_include:
        try:
            # Add separator and file path heading (common to all files)
            all_markdown_content.append("\n" + ("-" * 80)) # Visual separator line
            all_markdown_content.append(f"## `{rel_path}`") # Use heading for file path

            # Try reading content
            try:
                content = abs_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                print(f"Warning: Could not decode {rel_path} as UTF-8. Reading with errors ignored.")
                content = abs_path.read_text(encoding='utf-8', errors='ignore')
            except Exception as read_err:
                print(f"Error reading file {rel_path}: {read_err}")
                content = f"Error reading file: {read_err}"
                # Decide how to handle read errors - here we put the error in a code block
                all_markdown_content.append(f"```\n{content}\n```")
                continue # Skip to the next file

            # <<< CHANGE IS HERE >>>
            # Check if the file extension is .md (case-insensitive)
            if rel_path.suffix.lower() == '.md':
                print(f"Processing (Markdown): {rel_path}")
                # Append raw Markdown content directly
                all_markdown_content.append(content)
            else:
                print(f"Processing (Code):   {rel_path}")
                # Process other files as code blocks
                lang = guess_lexer(rel_path.name)
                all_markdown_content.append(f"```{lang}")
                all_markdown_content.append(content.strip()) # Strip whitespace for code blocks
                all_markdown_content.append("```")
            # <<< END OF CHANGE >>>

        except Exception as e:
            # Catch unexpected errors during processing of a single file
            print(f"Error processing file {rel_path}: {e}")
            # Add error message to the markdown output for context
            all_markdown_content.append("\n" + ("-" * 80))
            all_markdown_content.append(f"## `{rel_path}`")
            all_markdown_content.append(f"\n```\nError processing file: {e}\n```")

    # --- Write to Output File ---
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(all_markdown_content))
        print("-" * 30)
        print(f"Successfully created Markdown file: {output_path}")
    except Exception as e:
        print(f"Error writing to output file {output_path}: {e}")
        sys.exit(1)

# --- Main Execution ---
if __name__ == "__main__":
    # Optional: Add more robust argument parsing if needed (e.g., using argparse)

    # Run the generation process
    generate_project_markdown(
        SOURCE_DIRECTORY,
        OUTPUT_MARKDOWN_FILE,
        IGNORE_FILES,
        IGNORE_FOLDERS
    )