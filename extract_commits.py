#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
import sys
from datetime import datetime # To add a timestamp

# --- Configuration ---
NUM_COMMITS = 10  # Number of latest commits to fetch (change as needed)
OUTPUT_FILE = "RECENT_COMMIT_LOG.md" # Name of the output Markdown file
# --- End Configuration ---

def get_commit_data(num_commits):
    """
    Fetches commit data (hash and full message) for the last 'num_commits'.
    Returns a list of dictionaries, or None on error.
    """
    # Format: Hash<newline>Body<null_byte_separator>
    # Using %B gets the raw body, including subject and multi-line messages.
    # Using %x00 (null byte) as a separator is robust.
    command = ["git", "log", f"-n{num_commits}", "--pretty=format:%H%n%B%x00"]
    try:
        print(f"Running command: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,        # Get output as string
            check=True,       # Raise CalledProcessError on failure
            encoding='utf-8', # Specify encoding
            errors='replace'  # Replace chars that can't be decoded
        )
        raw_output = result.stdout.strip() # Remove leading/trailing whitespace

        if not raw_output:
            print("Warning: No commit history found or 'git log' produced empty output.")
            return [] # Return empty list if no commits

        # Split by the null byte separator. Filter out potential empty strings
        # that might result from trailing null bytes.
        commit_blocks = [block for block in raw_output.split('\x00') if block]

        commits_data = []
        for block in commit_blocks:
            # Each block is "HASH\nMESSAGE_BODY"
            parts = block.strip().split('\n', 1) # Split only on the first newline
            commit_hash = parts[0]
            # Handle commits that might only have a hash (e.g., empty message - unlikely but possible)
            commit_message = parts[1] if len(parts) > 1 else ""
            commits_data.append({
                "hash": commit_hash,
                "message": commit_message.strip() # Clean up message whitespace
            })

        # Git log returns newest first. The list will be [newest, ..., oldest]
        return commits_data

    except FileNotFoundError:
        print("\nError: 'git' command not found.", file=sys.stderr)
        print("Please ensure Git is installed and accessible in your system's PATH.", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"\nError executing git command (Return Code: {e.returncode}):", file=sys.stderr)
        print(f"Command: {' '.join(e.cmd)}", file=sys.stderr)
        print(f"Stderr: {e.stderr.strip()}", file=sys.stderr)
        print("\nHint: Are you running this script inside a valid Git repository?", file=sys.stderr)
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        return None

def write_to_markdown(commits_data, filename, num_requested):
    """
    Writes the collected commit data to a Markdown file.
    Returns True on success, False on failure.
    """
    if commits_data is None:
        print("Skipping Markdown file generation due to previous errors.", file=sys.stderr)
        return False

    actual_commits = len(commits_data)
    if actual_commits == 0:
        print(f"No commits found to write to '{filename}'.")
        # Optionally create an empty file or a file indicating no commits
        try:
            with open(filename, "w", encoding='utf-8') as f:
                f.write(f"# Recent Commit Log (Last {num_requested})\n\n")
                f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write("No commits found in the specified range or repository.\n")
            print(f"Created '{filename}' indicating no commits found.")
            return True
        except IOError as e:
            print(f"Error writing empty log file '{filename}': {e}", file=sys.stderr)
            return False


    title_commits = min(num_requested, actual_commits)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        print(f"\nWriting {actual_commits} commit messages to '{filename}'...")
        with open(filename, "w", encoding='utf-8') as f:
            f.write(f"# Recent Commit Log (Last {title_commits} Commits)\n\n")
            f.write(f"*Generated on: {current_time}*\n")
            # Try to get repo name (directory name) for context
            try:
                repo_name = os.path.basename(os.getcwd())
                f.write(f"*Repository: `{repo_name}`*\n")
            except Exception:
                pass # Ignore if getting cwd fails
            f.write("\n---\n\n")

            # Commits are currently newest first from git log
            for i, commit in enumerate(commits_data):
                short_hash = commit['hash'][:7] # Use the first 7 chars for a short hash
                f.write(f"## {i+1}. Commit `{short_hash}`\n\n")
                # Use a code block to preserve formatting of the commit message
                f.write("```text\n")
                f.write(commit['message'] if commit['message'] else "[No commit message body]")
                f.write("\n```\n\n")
                # Add a separator between commits, except for the last one
                if i < actual_commits - 1:
                    f.write("---\n\n")

        print(f"Successfully wrote commit log to '{filename}'.")
        return True
    except IOError as e:
        print(f"Error writing to file '{filename}': {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred during file writing: {e}", file=sys.stderr)
        return False

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Attempting to fetch the last {NUM_COMMITS} commit messages...")
    commit_info = get_commit_data(NUM_COMMITS)

    if commit_info is not None:
        write_to_markdown(commit_info, OUTPUT_FILE, NUM_COMMITS)
    else:
        print("\nScript finished with errors.", file=sys.stderr)
        sys.exit(1) # Exit with error code

    print("\nScript finished.")
    sys.exit(0) # Exit successfully
# --- End Script ---