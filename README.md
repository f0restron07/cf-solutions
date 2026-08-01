# cf-solutions — Codeforces → IntelliJ → GitHub, one paste

Paste a Codeforces problem link. It:

1. looks up the problem's **name** and **rating** from the official API,
2. creates `src/cf/r800/Watermelon/Main.java` (rating decides the folder — `r800`, `r900`, …),
3. opens that file in **IntelliJ**, and
4. **auto-commits + pushes to GitHub** every time you save.

No third-party Python packages. Standard library only.

> Every solution is a **`public class Main` with no package**, in its own folder.
> That means each file runs standalone — right-click *Run*, `java Main.java`, or
> paste straight into the Codeforces submit box (Java needs the class to be `Main`).
> Rating folders are `r800`, `r900`, `r1600`, …; unrated problems go in `runrated`.

---

## One-time setup (≈ 3 minutes)

**1. Put this folder where you want it and make it your repo.**

```bash
cd cf-solutions
python3 cf.py setup
```

This runs `git init`, writes a `.gitignore`, and prints what it detected.

**2. Give IntelliJ a command-line launcher** (so the tool can open files).

In IntelliJ: **Settings → Tools → Command Line Launcher** (or the Toolbox App:
gear icon → *Generate shell scripts*). This creates the `idea` command.
Check it: `idea --version`. If you skip this, on macOS the tool falls back to
`open -a "IntelliJ IDEA"` automatically.

Then open this folder once as a project: **File → Open →** pick `cf-solutions`,
and mark `src` as *Sources Root* (right-click `src` → *Mark Directory as → Sources Root*).
JDK 17+ recommended in Project Structure.

**3. Connect GitHub** (so pushes work).

```bash
# create an empty repo on github.com first, then:
git remote add origin git@github.com:YOUR_USERNAME/cf-solutions.git
git push -u origin main
```

That's it.

---

## Daily use

Start the web page + auto-push watcher (leave it running in a terminal tab):

```bash
python3 cf.py serve
```

Open **http://127.0.0.1:5757**, paste a link, hit **Create & Open**.
IntelliJ opens the class. Solve it. Every save is committed and pushed.

Prefer the terminal? Same thing without the web page:

```bash
python3 cf.py new https://codeforces.com/problemset/problem/4/A
```

### All commands

| Command | What it does |
|---|---|
| `python3 cf.py serve` | Web paste-box **and** auto-push-on-save watcher (recommended). |
| `python3 cf.py new <url>` | Create the class + open IntelliJ. `--no-open` skips launching. |
| `python3 cf.py watch` | Just the auto-push watcher (no web page). |
| `python3 cf.py push -m "msg"` | Commit + push right now. |
| `python3 cf.py test <url>` | Compile and run your code against the problem's **sample I/O**. |
| `python3 cf.py setup` | Init the repo and show detected settings. |

`cf.py test` is the "did I get it right?" check — it scrapes the example
input/output from the problem page, runs your class, and prints PASS/FAIL.

---

## Resulting layout

```
cf-solutions/
├── cf.py            # the tool
├── config.py        # your settings (edit freely)
├── web/index.html   # the paste box
└── src/
    └── cf/
        ├── r800/Watermelon/Main.java
        ├── r900/…
        └── r1600/…
```

---

## Settings (`config.py`)

- `PORT` — web page port (default 5757).
- `AUTO_PUSH` — set `False` to auto-commit but **not** push.
- `WATCH_DEBOUNCE_SECONDS` — how long after your last save it commits (default 6s).
- `IDEA_CMD` — force a launcher, e.g. `"idea"` or `'open -a "IntelliJ IDEA"'`.
- `COMMIT_PREFIX` — text in front of auto commit messages.

---

## Troubleshooting

- **"push skipped / no origin remote"** — you haven't added a GitHub remote yet
  (setup step 3). Commits still happen locally.
- **IntelliJ didn't open** — install the `idea` launcher (setup step 2), or set
  `IDEA_CMD` in `config.py`.
- **Rating shows `unrated`** — very new or gym problems aren't in the API yet;
  the file still gets created under `runrated`. Move it later if you like.
- **Wrong Java version** — set Project SDK to 17+ in *Project Structure*. The
  template uses only standard `java.io` / `java.util`.
- **Windows** — set `IDEA_CMD = "idea64.exe"` (or the full path) in `config.py`;
  everything else is cross-platform.
