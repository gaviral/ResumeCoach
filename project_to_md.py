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
SOURCE_DIRECTORY = "./"
OUTPUT_MARKDOWN_FILE = "./project_code.md"

# --- Comprehensive Ignore Lists ---


# List of wildcard patterns for FILES to ignore
IGNORE_FILES = [
    '.gitignore',
    # --- Environment & Secrets ---
    '.env*',                # Environment variables (e.g., .env, .env.local, .env.development)
    'secrets.*',            # Secret files
    'credentials.*',        # Credential files
    'config.local.*',       # Local configuration overrides

    # --- Logs ---
    '*.log',                # Log files
    'npm-debug.log*',       # NPM debug logs
    'yarn-debug.log*',      # Yarn debug logs
    'yarn-error.log*',      # Yarn error logs

    # --- Dependency Lock Files ---
    'package-lock.json',    # NPM lock file
    'yarn.lock',            # Yarn lock file
    'pnpm-lock.yaml',       # PNPM lock file
    'poetry.lock',          # Poetry lock file
    'Pipfile.lock',         # Pipenv lock file
    'requirements.txt.lock', # Common pattern for locked requirements

    # --- Compiled/Generated Code & Artifacts ---
    '*.pyc',                # Python compiled bytecode
    '*.pyo',                # Python optimized bytecode
    '*.class',              # Java compiled classes
    '*.dll', '*.exe',       # Windows binaries
    '*.so', '*.dylib',      # Linux/macOS shared libraries (will ignore those in .venv too)
    '*.o', '*.a', '*.obj',  # Object files, archives
    '*.jar', '*.war', '*.ear', # Java archives
    '*.wasm',               # WebAssembly binaries
    '*generated.*',         # Files often marked as generated
    '*auto_generated.*',    # Files often marked as auto-generated
    # ADDED: Ignore JS and TS definition files globally per request
    '*.js',
    '*.d.ts',

    # --- Build Output & Packages ---
    '*.zip', '*.tar', '*.gz', '*.bz2', '*.rar', '*.7z', # Archives
    '*.msi', '*.dmg', '*.pkg', '*.deb', '*.rpm',      # Installers/Packages
    '*.iso', '*.img',       # Disk images

    # --- Editor/IDE Specific ---
    '*.swp', '*.swo',       # Vim swap files
    '*~',                   # Common backup file pattern
    '*.bak', '*.tmp',       # Backup/temporary files
    '*.sublime-project',    # Sublime Text project files
    '*.sublime-workspace',
    '*.iml',                # IntelliJ module files
    '.DS_Store',            # macOS Finder data
    'Thumbs.db',            # Windows thumbnail cache
    'ehthumbs.db',

    # --- OS Specific ---
    '._*',                  # macOS resource fork files

    # --- Test Reports & Coverage ---
    'junit.xml',            # JUnit XML reports
    'coverage.xml',         # Coverage reports
    '.coverage',            # Coverage data file
    'nosetests.xml',

    # --- Databases ---
    '*.db', '*.sqlite', '*.sqlite3', # Local database files
    '*.sqlitedb',

    # --- Media & Assets ---
    '*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp', '*.ico', '*.bmp',
    '*.svg',
    '*.woff', '*.woff2', '*.ttf', '*.otf', '*.eot',
    '*.mp3', '*.wav', '*.ogg', '*.aac',
    '*.mp4', '*.avi', '*.mov', '*.wmv', '*.flv',

    # --- Specific Generated/Helper Files from Your Example ---
    'frontend_code.md',
    'project_to_md.py',       # The script itself (if inside SOURCE_DIRECTORY)
    'extract_commits.py',     # Tooling script not part of runtime code
    'RECENT_COMMIT_LOG.md',   # Auto-generated commit log
    'version_1_setup.md',
    'version_2_setup.md',
    Path(OUTPUT_MARKDOWN_FILE).name, # Ignore the output file itself
    '.npmignore',             # Packaging ignore not relevant to code context
    'errors_in_readme.md',
    'codex_output.md',

    # --- Cloud Provider/Tooling Cache/State ---
    'cdk.context.json',     # AWS CDK context cache

    # --- Other ---
    '.python-version',      # pyenv version file
]

# List of wildcard patterns for FOLDERS to ignore
IGNORE_FOLDERS = [
    # --- Dependency Management ---
    'node_modules',         # Node.js dependencies
    'bower_components',     # Bower dependencies (less common now)
    'vendor',               # Common directory for PHP/Ruby/Go dependencies
    'jspm_packages',        # JSPM packages

    # --- Build Output / Distribution ---
    'dist',                 # Common distribution folder
    'build',                # Common build folder
    'out',                  # Common output folder
    'target',               # Common build folder (Java/Rust)
    # 'bin', # REMOVED: To allow infrastructure/bin (and potentially others)
    # 'obj', # REMOVED: To potentially allow obj if needed, add back if too noisy
    'public',               # Often contains built frontend assets (NextJS, Vite, etc.)
    '.next',                # Next.js build output
    '.nuxt',                # Nuxt.js build output
    '.svelte-kit',          # SvelteKit build output
    'generated',            # Common generated code folder
    'auto_generated',       # Common auto-generated code folder

    # --- Python Specific ---
    '__pycache__',          # Python bytecode cache
    '*.egg-info',           # Python package build metadata
    '.venv',                # Specific venv names take precedence
    'venv',
    'env',
    '.env',
    # 'lib', 'lib64',   # REMOVED: To allow infrastructure/lib. Venvs caught by .venv/venv/env patterns.
    'include',              # Often part of venvs, keep for now unless needed
    'Scripts',              # Windows virtual environment scripts folder
    'site-packages',        # Usually inside a venv, keep ignored

    # --- Version Control ---
    '.git',                 # Git repository data
    '.svn',                 # Subversion repository data
    '.hg',                  # Mercurial repository data

    # --- Editor/IDE Specific ---
    '.vscode',              # VS Code settings
    '.idea',                # JetBrains IDEs settings
    '.vs',                  # Visual Studio settings

    # --- Testing & Coverage ---
    'coverage',             # Coverage reports folder
    'htmlcov',              # HTML coverage report folder
    '.pytest_cache',        # Pytest cache
    '.hypothesis',          # Hypothesis cache

    # --- Caching ---
    '.cache',               # General cache directory (includes infrastructure/.cache)
    '.mypy_cache',          # Mypy cache
    '.ruff_cache',          # Ruff cache

    # --- Cloud Provider/Tooling Output ---
    '.serverless',          # Serverless Framework output
    '.terraform',           # Terraform state/modules
    'cdk.out',              # AWS CDK synthesis output (keep ignoring top-level)

    # --- Logs & Temporary Files ---
    'logs',                 # Common logs directory
    'temp', 'tmp',          # Temporary file directories

    # --- Documentation Output ---
    '_build',               # Common Sphinx build output
    '_site',                # Common Jekyll/static site generator output
    'docs/build',           # Common documentation build output

    # --- OS Specific ---
    '.Trash-*',             # Linux trash directories

    # --- Jupyter Notebook ---
    '.ipynb_checkpoints',   # Jupyter checkpoint directories
    # --- AWS CDK Output ---
    'cdk.out',              # CDK synthesized CloudFormation artifacts
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