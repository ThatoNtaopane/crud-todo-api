# GitHub Publishing & Integration Guide: Assignment A4 (Auth · Login & Protect)

This repository contains the complete, production-structured solution for **FlyRank Internship · Backend Track · Week 2 · Assignment A4: Auth · Login & Protect**.

All stages from Stage 0 to Stage 7 (including Bonus AI Rematch and Stretch Goals) are committed with a clean, verifiable git history.

---

## Option 1: Pushing as a New Branch to Your Existing Repo

To keep all assignments organized under your repository (`crud-todo-api`):

```bash
# 1. Unzip the deliverables into a clean folder
unzip crud-todo-api-auth.zip -d auth-assignment
cd auth-assignment

# 2. Add your existing GitHub remote
git remote add origin https://github.com/ThatoNtaopane/crud-todo-api.git

# 3. Create and push a dedicated auth branch
git checkout -b feature/supabase-auth
git push -u origin feature/supabase-auth
```

---

## Option 2: Merging or Pushing Directly to Main

If you prefer `main` to showcase the authenticated stack:

```bash
# 1. Add remote
git remote add origin https://github.com/ThatoNtaopane/crud-todo-api.git

# 2. Push main branch
git branch -M main
git push -u origin main --force
```

---

## Verification Checklist

1. **Commit History**:
   Verify with `git log --oneline`:
   - `Stage 0: setup server and supabase client`
   - `Stage 1: signup and login routes working`
   - `Stage 2: public route and unverified protected route`
   - `Stage 3: profile route token verification`
   - `Stage 4: auth middleware and logout endpoint`
   - `Stage 5: Swagger UI documentation with bearer auth`
   - `Extras: 403 authorization, refresh token, rate limiting, and JWT analysis`
   - `Stage 6: publish to GitHub and write README — then push everything.`
   - `Stage 7: AI vs me (AI code stays in its own folder/branch).`

2. **Secrets Protection**:
   Ensure `.env` was never tracked:
   ```bash
   git log --all --full-history -- .env
   # Must return empty output!
   ```

3. **Running the Automated Test Suite**:
   ```bash
   python3 -m pytest test_api.py -v
   ```
