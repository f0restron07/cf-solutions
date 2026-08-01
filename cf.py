#!/usr/bin/env python3
"""
cf.py -- Codeforces -> IntelliJ -> GitHub, one paste.

Commands:
    python3 cf.py new  <url>     create the Java class + open it in IntelliJ
    python3 cf.py serve          run the web page (paste box) + auto-push watcher
    python3 cf.py watch          only run the auto-push-on-save watcher
    python3 cf.py push [-m msg]   commit + push right now
    python3 cf.py test <url>     compile + run against the problem's sample I/O
    python3 cf.py setup          init the git repo and print detected settings

No third-party packages required -- standard library only.
"""
import os
import re
import sys
import json
import time
import html
import argparse
import subprocess
import threading
import urllib.request
from datetime import date, datetime

# make sure `import config` works no matter where we're run from
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CACHE_FILE = os.path.join(config.REPO_DIR, ".cache", "problems.json")
INDEX_FILE = os.path.join(config.REPO_DIR, ".cache", "index.json")
CACHE_TTL = 24 * 3600  # refresh the problem list once a day


def _load_index():
    """url -> repo-relative .java path. Keeps `new`/`test` pointing at one file."""
    try:
        with open(INDEX_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_index(idx):
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(idx, f, indent=0)


# --------------------------------------------------------------------------- #
#  small helpers                                                              #
# --------------------------------------------------------------------------- #
def run(cmd, cwd=None, check=False, capture=True):
    """Run a command (list or str). Returns CompletedProcess."""
    shell = isinstance(cmd, str)
    return subprocess.run(
        cmd, cwd=cwd or config.REPO_DIR, shell=shell, check=check,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        text=True,
    )


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def log(msg):
    print(f"[cf] {msg}")


# --------------------------------------------------------------------------- #
#  parsing the problem URL                                                    #
# --------------------------------------------------------------------------- #
def parse_url(url):
    """
    Accepts any of:
        https://codeforces.com/problemset/problem/4/A
        https://codeforces.com/contest/1850/problem/A
        https://codeforces.com/gym/104555/problem/B
        4/A          (bare contestId/index shorthand)
    Returns (contestId:int, index:str, is_gym:bool).
    """
    url = url.strip()
    m = re.search(r"/(problemset/problem|contest|gym)/(\d+)/(?:problem/)?([A-Za-z]\d*|\d+)", url)
    if m:
        return int(m.group(2)), m.group(3).upper(), m.group(1) == "gym"
    m = re.fullmatch(r"(\d+)[/ ]([A-Za-z]\d*|\d+)", url)
    if m:
        return int(m.group(1)), m.group(2).upper(), False
    raise ValueError(f"Could not parse a Codeforces problem from: {url!r}")


def canonical_url(contest_id, index, is_gym=False):
    kind = "gym" if is_gym else "problemset/problem"
    if is_gym:
        return f"https://codeforces.com/gym/{contest_id}/problem/{index}"
    return f"https://codeforces.com/{kind}/{contest_id}/{index}"


# --------------------------------------------------------------------------- #
#  problem metadata (name + rating) via the official API, cached              #
# --------------------------------------------------------------------------- #
def _load_cache():
    try:
        with open(CACHE_FILE) as f:
            blob = json.load(f)
        if time.time() - blob.get("fetched", 0) < CACHE_TTL:
            return blob["problems"]
    except (OSError, ValueError, KeyError):
        pass
    return None


def _refresh_cache():
    log("refreshing problem list from codeforces API ...")
    data = json.loads(http_get("https://codeforces.com/api/problemset.problems"))
    if data.get("status") != "OK":
        raise RuntimeError("codeforces API did not return OK")
    problems = data["result"]["problems"]
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({"fetched": time.time(), "problems": problems}, f)
    return problems


def get_meta(contest_id, index, is_gym=False):
    """Return {'name', 'rating'(int|None), 'tags'}. Falls back to scraping."""
    if not is_gym:
        problems = _load_cache()
        for source in (problems, None):
            pool = source if source is not None else _refresh_cache()
            for p in pool:
                if p.get("contestId") == contest_id and p.get("index") == index:
                    return {"name": p.get("name", index),
                            "rating": p.get("rating"),
                            "tags": p.get("tags", [])}
            if source is None:
                break  # already refreshed, still not found -> fall through
    # fallback: scrape the title off the problem page (gym / brand-new problems)
    try:
        htmltext = http_get(canonical_url(contest_id, index, is_gym))
        m = re.search(r'<div class="title">\s*([A-Z]\d*\.\s*)?([^<]+?)\s*</div>', htmltext)
        name = html.unescape(m.group(2)).strip() if m else index
    except Exception:
        name = index
    return {"name": name, "rating": None, "tags": []}


# --------------------------------------------------------------------------- #
#  turning a problem into a package + class                                   #
# --------------------------------------------------------------------------- #
def package_for_rating(rating):
    return f"r{rating}" if rating else "runrated"


def sanitize_class(name):
    """'A. Theatre Square' -> 'TheatreSquare' (a valid Java identifier)."""
    tokens = re.split(r"[^0-9A-Za-z]+", name)
    cls = "".join(t[:1].upper() + t[1:] for t in tokens if t)
    if not cls:
        cls = "Problem"
    if cls[0].isdigit():
        cls = "P" + cls
    return cls


JAVA_TEMPLATE = """/*
 *  {name}
 *  rating {rating}{tagline}
 *  {url}
 *  created {today}
 */

import java.io.*;
import java.util.*;

public class Main {{
    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        StringBuilder sb = new StringBuilder();

        // TODO: read input and solve
        // int n = Integer.parseInt(br.readLine().trim());

        System.out.print(sb);
    }}
}}
"""


def resolve_paths(contest_id, index, meta, is_gym=False):
    """Work out the problem folder and file path. Each problem gets its own
    folder, and the class is always `Main` (no package) so every file runs
    standalone -- right-click Run, `java Main.java`, or paste straight into the
    Codeforces submit box. Returns (label, prob_dir, cls, path, url) where
    `label` is a human tag like "r800/NearlyLuckyNumber" for logs/commits.
    Idempotent (same problem always maps to the same file) via a url->path
    index that does not depend on the file's contents."""
    url = canonical_url(contest_id, index, is_gym)
    idx = _load_index()
    if url in idx:  # we've seen this problem before -> reuse that exact folder
        path = os.path.join(config.REPO_DIR, idx[url])
        prob_dir = os.path.dirname(path)
        leaf = os.path.basename(os.path.dirname(prob_dir))
        prob = os.path.basename(prob_dir)
        return f"{leaf}/{prob}", prob_dir, "Main", path, url

    leaf = package_for_rating(meta["rating"])          # e.g. r800
    prob = sanitize_class(meta["name"])                # e.g. NearlyLuckyNumber
    prob_dir = os.path.join(config.SRC_DIR, config.BASE_PACKAGE, leaf, prob)
    path = os.path.join(prob_dir, "Main.java")
    rel = os.path.relpath(path, config.REPO_DIR)
    clash = rel in set(idx.values()) or (
        os.path.exists(path) and url not in open(path, encoding="utf-8").read(600))
    if clash:  # a different problem already claimed this folder -> disambiguate
        prob = f"{prob}_{contest_id}{index}"
        prob_dir = os.path.join(config.SRC_DIR, config.BASE_PACKAGE, leaf, prob)
        path = os.path.join(prob_dir, "Main.java")
    return f"{leaf}/{prob}", prob_dir, "Main", path, url


def create_problem(url, open_ide=True):
    contest_id, index, is_gym = parse_url(url)
    meta = get_meta(contest_id, index, is_gym)
    label, prob_dir, cls, path, canon = resolve_paths(contest_id, index, meta, is_gym)

    created = not os.path.exists(path)
    if created:
        os.makedirs(prob_dir, exist_ok=True)
        tagline = ("  |  tags: " + ", ".join(meta["tags"])) if meta["tags"] else ""
        with open(path, "w", encoding="utf-8") as f:
            f.write(JAVA_TEMPLATE.format(
                name=meta["name"],
                rating=meta["rating"] if meta["rating"] else "unrated",
                tagline=tagline, url=canon, today=date.today().isoformat()))

    # remember url -> file so `test` and repeat `new` always hit the same class
    idx = _load_index()
    idx[canon] = os.path.relpath(path, config.REPO_DIR)
    _save_index(idx)

    if open_ide:
        open_in_idea(path)

    return {"ok": True, "created": created, "name": meta["name"],
            "rating": meta["rating"], "package": label, "className": cls,
            "path": path, "url": canon}


# --------------------------------------------------------------------------- #
#  IntelliJ                                                                    #
# --------------------------------------------------------------------------- #
def open_in_idea(path):
    cmd = config.detect_idea_cmd()
    if not cmd:
        log("IntelliJ launcher not found -- open the repo manually "
            "(see README: 'Create Command-line Launcher').")
        return
    try:
        subprocess.Popen(f'{cmd} "{path}"', shell=True)
        log(f"opening in IntelliJ: {os.path.relpath(path, config.REPO_DIR)}")
    except Exception as e:
        log(f"could not launch IntelliJ: {e}")


# --------------------------------------------------------------------------- #
#  git                                                                         #
# --------------------------------------------------------------------------- #
def ensure_repo():
    if not os.path.isdir(os.path.join(config.REPO_DIR, ".git")):
        log("initialising git repo ...")
        run(["git", "init", "-b", "main"])
    gi = os.path.join(config.REPO_DIR, ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w") as f:
            f.write(".cache/\n.out/\nout/\n*.class\n.idea/\n*.iml\n")
    # so commits never fail for users who haven't set a global git identity;
    # a real global identity (once you've set up GitHub) takes precedence.
    if not run(["git", "config", "user.email"]).stdout.strip():
        run(["git", "config", "user.email", "cf-bot@local"])
        run(["git", "config", "user.name", "cf-bot"])


def has_remote():
    return config.GIT_REMOTE in run(["git", "remote"]).stdout.split()


def current_branch():
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip() or "main"


def _porcelain():
    # -uall lists individual untracked files (not just the parent dir) so the
    # very first commit's message can still name the problems.
    return run(["git", "status", "--porcelain", "--untracked-files=all"]).stdout


def _message_from_status(status):
    names = []
    for line in status.splitlines():
        m = re.search(r"src/%s/(r\w+)/(\w+)/Main\.java" % re.escape(config.BASE_PACKAGE), line)
        if m:
            names.append(f"{m.group(1)}/{m.group(2)}")
    if names:
        uniq = list(dict.fromkeys(names))
        return f"{config.COMMIT_PREFIX} " + ", ".join(uniq[:6]) + (" ..." if len(uniq) > 6 else "")
    return f"{config.COMMIT_PREFIX} update {datetime.now():%Y-%m-%d %H:%M}"


def commit_and_push(message=None, push=None):
    ensure_repo()
    status = _porcelain()
    if not status.strip():
        return {"ok": True, "committed": False, "pushed": False, "detail": "nothing to commit"}
    run(["git", "add", "-A"])
    msg = message or _message_from_status(status)
    c = run(["git", "commit", "-m", msg])
    committed = c.returncode == 0
    if not committed:
        tail = c.stdout.strip().splitlines()[-1] if c.stdout.strip() else "unknown error"
        return {"ok": False, "committed": False, "pushed": False,
                "message": msg, "detail": "commit failed: " + tail}
    pushed, detail = False, msg
    do_push = config.AUTO_PUSH if push is None else push
    if committed and do_push:
        if has_remote():
            p = run(["git", "push", "-u", config.GIT_REMOTE, current_branch()])
            pushed = p.returncode == 0
            if not pushed:
                detail = "commit ok, push failed: " + p.stdout.strip().splitlines()[-1:][0] \
                    if p.stdout.strip() else "commit ok, push failed"
        else:
            detail = f"commit ok, no '{config.GIT_REMOTE}' remote set -- push skipped"
    return {"ok": True, "committed": committed, "pushed": pushed, "message": msg, "detail": detail}


# --------------------------------------------------------------------------- #
#  the auto-push-on-save watcher                                              #
# --------------------------------------------------------------------------- #
def watch_loop(stop=None):
    ensure_repo()
    log(f"watching {config.SRC_DIR} -- auto-commit "
        f"{'+ push ' if config.AUTO_PUSH else ''}"
        f"{config.WATCH_DEBOUNCE_SECONDS}s after you stop typing. Ctrl-C to stop.")
    prev, last_change = None, 0.0
    while not (stop and stop.is_set()):
        status = _porcelain()
        if status != prev:
            prev, last_change = status, time.time()
        if status.strip() and (time.time() - last_change) >= config.WATCH_DEBOUNCE_SECONDS:
            res = commit_and_push()
            if res["committed"]:
                log(("pushed: " if res["pushed"] else "committed: ") + res.get("message", ""))
                if not res["pushed"]:
                    log("  " + res.get("detail", ""))
            prev = _porcelain()
            last_change = time.time()
        time.sleep(config.WATCH_POLL_SECONDS)


# --------------------------------------------------------------------------- #
#  sample tests  (compile + run against the problem's example I/O)            #
# --------------------------------------------------------------------------- #
def _clean_pre(fragment):
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?i)</div>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    text = html.unescape(fragment)
    lines = [ln.rstrip() for ln in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")


def scrape_samples(contest_id, index, is_gym=False):
    page = http_get(canonical_url(contest_id, index, is_gym))
    ins, outs = [], []
    for kind, m in ((k, mm) for k in ("input", "output")
                    for mm in re.finditer(r'class="%s"' % kind, page)):
        pre = re.search(r"<pre[^>]*>(.*?)</pre>", page[m.end():], re.S)
        if pre:
            (ins if kind == "input" else outs).append(_clean_pre(pre.group(1)))
    return list(zip(ins, outs))


def cmd_test(url):
    contest_id, index, is_gym = parse_url(url)
    meta = get_meta(contest_id, index, is_gym)
    pkg, _, cls, path, _ = resolve_paths(contest_id, index, meta, is_gym)
    if not os.path.exists(path):
        log("no file yet -- run `cf.py new <url>` first."); return 1
    out_dir = os.path.join(config.REPO_DIR, ".out")
    os.makedirs(out_dir, exist_ok=True)
    log("compiling ...")
    jc = run(["javac", "-d", out_dir, path])
    if jc.returncode != 0:
        print(jc.stdout); log("compilation failed."); return 1
    fqcn = f"{pkg}.{cls}"
    try:
        samples = scrape_samples(contest_id, index, is_gym)
    except Exception as e:
        log(f"couldn't fetch samples ({e}); compiled OK though."); return 0
    if not samples:
        log("no sample I/O found on the page; compiled OK though."); return 0
    passed = 0
    for i, (inp, exp) in enumerate(samples, 1):
        try:
            got = subprocess.run(["java", "-cp", out_dir, fqcn], input=inp,
                                 text=True, capture_output=True, timeout=10).stdout
        except subprocess.TimeoutExpired:
            print(f"  sample {i}: TIMEOUT"); continue
        if got.strip().split() == exp.strip().split():
            print(f"  sample {i}: PASS"); passed += 1
        else:
            print(f"  sample {i}: FAIL\n    expected: {exp.strip()!r}\n    got:      {got.strip()!r}")
    log(f"{passed}/{len(samples)} samples passed.")
    return 0 if passed == len(samples) else 1


# --------------------------------------------------------------------------- #
#  the local web page                                                         #
# --------------------------------------------------------------------------- #
def serve(run_watcher=None):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    ensure_repo()
    index_html = open(os.path.join(config.REPO_DIR, "web", "index.html"),
                      encoding="utf-8").read()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json_body(self):
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n).decode() if n else "{}"
            try:
                return json.loads(raw)
            except ValueError:
                return {}

        def log_message(self, *a):  # quiet
            pass

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, index_html, "text/html; charset=utf-8")
            elif self.path == "/health":
                self._send(200, json.dumps({"ok": True}))
            else:
                self._send(404, json.dumps({"ok": False, "error": "not found"}))

        def do_POST(self):
            try:
                if self.path == "/api/new":
                    url = self._json_body().get("url", "").strip()
                    res = create_problem(url)
                    self._send(200, json.dumps(res))
                elif self.path == "/api/push":
                    self._send(200, json.dumps(commit_and_push()))
                else:
                    self._send(404, json.dumps({"ok": False, "error": "not found"}))
            except Exception as e:
                self._send(200, json.dumps({"ok": False, "error": str(e)}))

    if run_watcher is None:
        run_watcher = config.SERVE_RUNS_WATCHER
    if run_watcher:
        threading.Thread(target=watch_loop, args=(threading.Event(),), daemon=True).start()

    httpd = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    log(f"open  http://{config.HOST}:{config.PORT}  in your browser  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("bye")


# --------------------------------------------------------------------------- #
#  CLI                                                                         #
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(prog="cf", description="Codeforces -> IntelliJ -> GitHub")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("new", help="create the java class + open in IntelliJ")
    p.add_argument("url")
    p.add_argument("--no-open", action="store_true", help="don't launch IntelliJ")

    sub.add_parser("serve", help="web paste-box + auto-push watcher")
    sub.add_parser("watch", help="only the auto-push-on-save watcher")

    p = sub.add_parser("push", help="commit + push now")
    p.add_argument("-m", "--message", default=None)

    p = sub.add_parser("test", help="compile + run against sample I/O")
    p.add_argument("url")

    sub.add_parser("setup", help="init git repo + show detected settings")

    args = ap.parse_args(argv)

    if args.cmd == "new":
        res = create_problem(args.url, open_ide=not args.no_open)
        rating = res["rating"] if res["rating"] else "unrated"
        verb = "created" if res["created"] else "exists"
        log(f"{verb}: {res['package']}.{res['className']}  "
            f"({res['name']}, rating {rating})")
        log(res["path"])
    elif args.cmd == "serve":
        serve()
    elif args.cmd == "watch":
        watch_loop(threading.Event())
    elif args.cmd == "push":
        print(json.dumps(commit_and_push(message=args.message), indent=2))
    elif args.cmd == "test":
        sys.exit(cmd_test(args.url))
    elif args.cmd == "setup":
        ensure_repo()
        log(f"repo dir     : {config.REPO_DIR}")
        log(f"src dir      : {config.SRC_DIR}")
        log(f"idea launcher: {config.detect_idea_cmd() or 'NOT FOUND'}")
        log(f"git remote   : {'set' if has_remote() else 'NOT set (push will be skipped)'}")
        log("ready. Try:  python3 cf.py new https://codeforces.com/problemset/problem/4/A")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
