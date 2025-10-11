# ===== IMPORTS & DEPENDENCIES =====
import subprocess
import re
from datetime import datetime

# ===== CONFIGURATION & CONSTANTS =====
REPO_PATH = '.'  # یا path repo
AUTO_COMMITS = ['Auto-update', 'بروزرسانی ابتدای']  # pattern برای clean

# ===== UTILITY FUNCTIONS =====
def run_git(cmd: str) -> str:
    """Run git command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=REPO_PATH)
    if result.returncode != 0:
        raise ValueError(f"Git error: {result.stderr}")
    return result.stdout.strip()

def standardize_messages():
    """Rebase and standardize commit messages."""
    log = run_git('git log --oneline -n 20')
    commits = re.findall(r'([a-f0-9]{7}) (.+)', log)
    for short_hash, msg in commits:
        if any(auto in msg for auto in AUTO_COMMITS):
            # Example: rebase -i و edit
            print(f"Standardize {short_hash}: {msg} -> 'chore: auto clean v{datetime.now().strftime('%Y%m%d')}'")
            # Manual: git rebase -i HEAD~20, then replace
    print("Run 'git rebase -i HEAD~20' and edit messages.")

def clean_ignored():
    """Remove ignored files from cache."""
    run_git('git rm -r --cached .')
    run_git('git add .')
    run_git('git commit -m "chore: clean ignored files from cache"')

# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    print("Git Log Summary:")
    print(run_git('git log --oneline -n 5'))
    clean_ignored()
    standardize_messages()
    print("Done! Push with 'git push --force-with-lease' (careful!).")