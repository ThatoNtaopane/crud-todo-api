# GitHub Publishing & Integration Guide: Week 5 · Assignment A9 (The Polite Scraper)

This repository contains the complete, verified solution for **FlyRank Internship · Backend Track · Week 5 · Assignment A9: The polite scraper** (Python Lane).

All stages (`Stage 0` through `Stage 6`, plus `Extras` and `Bonus: AI vs me`) are committed with a clean, verifiable Git history on top of your `crud-todo-api` repository.

---

## Option 1: Pushing `crud-todo-api-scraper.zip` to Your Existing GitHub Repo (`crud-todo-api`)

Because Stage 0 Step 1 specifies *"Create a `scraper/` folder in your internship repo, with a `README.md`, a `.gitignore`, and one entry file (`src/main.py`)"*, `crud-todo-api-scraper.zip` contains your full `crud-todo-api` repository with the new `scraper/` folder and 8 sequential Week 5 commits added cleanly to `main`.

```bash
# 1. Unzip the archive into a local folder
unzip crud-todo-api-scraper.zip -d crud-todo-api-w5
cd crud-todo-api-w5

# 2. Verify the commit history (shows all Week 5 stage commits + earlier weeks)
git log --oneline -n 12

# 3. Point to your GitHub remote and push
git remote set-url origin https://github.com/ThatoNtaopane/crud-todo-api.git || git remote add origin https://github.com/ThatoNtaopane/crud-todo-api.git
git branch -M main
git push -u origin main
```

---

## Option 2: Pushing `polite-scraper-python.zip` as a Standalone Branch or Repository

If you prefer a standalone branch or dedicated repository containing only the scraper files at the root:

```bash
unzip polite-scraper-python.zip -d polite-scraper
cd polite-scraper
git log --oneline
```

---

## Verification Checklist (Under 1 Minute)

1. **Commit History (`git log --oneline -n 9`)**:
   - `Bonus: AI vs me (the AI code stays isolated)`
   - `Extras: CSV export, change detection, HTML dashboard, selector fixtures, and exponential backoff`
   - `Stage 6: publish scraper evidence`
   - `Stage 5: survive failures, report the run`
   - `Stage 4: validate normalized records`
   - `Stage 3: extract book details`
   - `Stage 2: discover three catalogue pages`
   - `Stage 1: fetch and cache HTML`
   - `Stage 0: classify scraping target`

2. **Cache Exclusion Check**:
   Verify `cache/` is ignored and never committed to Git:
   ```bash
   git status --ignored
   git log --all --full-history -- "scraper/cache/*"
   # Returns empty output!
   ```

3. **Run the Scraper & Unit Tests**:
   ```bash
   cd scraper
   python3 src/main.py
   python3 tests/test_scraper.py
   ```
