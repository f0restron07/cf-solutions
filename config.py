# ---------------------------------------------------------------------------
# cf-solutions configuration  --  edit these to taste
# ---------------------------------------------------------------------------
import os
import shutil

# Root of your solutions repo. Defaults to the folder this file lives in,
# so you normally don't need to touch it.
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# Where solutions are written. Each problem gets its own folder and the class
# is always `Main` (no package): <SRC_DIR>/cf/r800/ProblemName/Main.java
SRC_DIR = os.path.join(REPO_DIR, "src")
BASE_PACKAGE = "cf"          # top folder under src/ (a plain dir now, not a java package)

# --- git / GitHub ----------------------------------------------------------
GIT_REMOTE = "origin"        # name of your github remote
AUTO_PUSH = True             # watcher pushes after each commit (set False = commit only)
COMMIT_PREFIX = "solve:"     # prepended to auto commit messages

# --- web server ------------------------------------------------------------
HOST = "127.0.0.1"
PORT = 5757                  # open http://127.0.0.1:5757 in your browser
SERVE_RUNS_WATCHER = True    # `cf serve` also auto-pushes on save

# --- watcher ---------------------------------------------------------------
WATCH_DEBOUNCE_SECONDS = 6   # wait this long after your last save before committing
WATCH_POLL_SECONDS = 2       # how often to check for changes

# --- IntelliJ launcher -----------------------------------------------------
# Leave as None to auto-detect. Or hard-code, e.g. "idea" or
# 'open -a "IntelliJ IDEA"' (mac)  /  "idea64.exe" (windows).
IDEA_CMD = None


def detect_idea_cmd():
    """Return a shell command prefix that opens a path in IntelliJ, or None."""
    if IDEA_CMD:
        return IDEA_CMD
    # 1) the `idea` command-line launcher (best option, all platforms)
    for name in ("idea", "idea.sh", "idea64.exe"):
        if shutil.which(name):
            return name
    # 2) macOS application bundles
    for app in ("IntelliJ IDEA", "IntelliJ IDEA CE",
                "IntelliJ IDEA Ultimate", "IntelliJ IDEA Community Edition"):
        if os.path.isdir(f"/Applications/{app}.app"):
            return f'open -a "{app}"'
    return None
