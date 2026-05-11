# Deploy Cerna to Streamlit Community Cloud

Total time: ~30 minutes. Produces a persistent public URL like
`https://<your-username>-cerna-<hash>.streamlit.app/` that anyone can hit.

The repo is already Cloud-ready: `requirements.txt` is complete, `.gitignore`
protects your `.env`, and `chroma_store/` (129 MB) is committed so first-boot
is fast (no 2-hour rebuild).

You need to run steps 1, 2, 3, and 4 — Streamlit Cloud requires your
GitHub auth, which I can't do from here.

---

## 1. Create a GitHub repo and push the code

```powershell
# In the project directory:
git init
git branch -m main
git add .
git commit -m "Initial Cerna POV deploy"

# Create the repo on github.com (private is fine on Streamlit Cloud free tier).
# Then push:
git remote add origin https://github.com/<your-username>/cerna.git
git push -u origin main
```

The first push will take ~2-5 min because of `chroma_store/` (129 MB).

If you'd rather keep the repo lean and rebuild embeddings on first boot,
re-add `chroma_store/` to `.gitignore` before committing — but expect
~3 hours of CPU work the first time anyone loads the app. Not recommended
for a demo.

---

## 2. Sign in to Streamlit Community Cloud

Open <https://share.streamlit.io> and sign in with the same GitHub account
you just pushed to.

---

## 3. Connect the repo

In the Streamlit dashboard:

- Click **New app**
- Repository: `<your-username>/cerna`
- Branch: `main`
- Main file path: `app.py`
- Click **Advanced settings...**

In the **Secrets** field, paste this (filling in the `gsk_...` values
from your local `.env` file — DO NOT commit the real keys to git):

```toml
GROQ_API_KEY = "<paste the GROQ_API_KEY value from your .env>"
GROQ_API_KEYS = "<paste the GROQ_API_KEYS value from your .env — comma-separated, no spaces>"
COLLECTION = "cerner_docs_bge"
RERANK_ENABLED = "false"
```

To pull them out of `.env` quickly:

```powershell
# Shows the values so you can copy them into the Streamlit dashboard.
# Run this in your terminal, never paste the output into anything that gets committed.
Get-Content .env
```

(Streamlit Cloud injects these as environment variables at startup, so
the existing `os.getenv()` calls in `config.py` and `groq_pool.py` pick
them up automatically — no code change needed.)

Click **Deploy**.

---

## 4. Wait for the first build

The first boot does:
1. Install `requirements.txt` (~3 min)
2. Download BGE-large embeddings on first retrieve (~2 min, then cached)
3. Build BM25 index (~30 s)

Total ~6 min on cold boot. Subsequent loads are seconds.

Streamlit Cloud will show you the deployed URL — that's the link to share.

---

## Operational notes for the share

- **Groq quota is shared.** Every stakeholder query bills against your
  3-key Groq free-tier pool (~36K TPM total). For a 5-person live demo,
  fine; for an open-link-to-many-strangers situation, plan to upgrade
  Groq or pre-warm a fixed query set.
- **Memory ceiling.** Streamlit Cloud free tier is 1 GB. Cerna at idle is
  ~600 MB (BGE + chroma + streamlit); under load ~800 MB. Tight but works.
  If you see OOM in the Streamlit Cloud logs, drop `RERANK_ENABLED` and
  consider switching to the MiniLM collection (`COLLECTION=cerner_docs`)
  which is smaller — though that loses the +7.3 pp Outcome A win.
- **App sleeps after ~7 days idle.** Next visitor triggers a ~2 min
  reboot. Not a problem for active demos.
- **To rotate Groq keys** (e.g., one gets flagged), update the secrets
  in the dashboard — the app re-reads on the next request.

---

## If you need to redeploy after a code change

```powershell
git add <changed files>
git commit -m "..."
git push
```

Streamlit Cloud watches the repo and auto-redeploys on push — usually
under 2 minutes.

---

## If Step 1 fails because git is blocked or you don't have a GitHub account

- **No git on your machine:** install via `winget install --id Git.Git` (no admin needed on most Accenture builds).
- **No GitHub account:** sign up at <https://github.com/signup> — free, ~2 min.
- **Forcepoint blocks github.com:** unlikely (GitHub is whitelisted on most Accenture configs), but if it does, use the GitHub web UI to upload the repo as a zip via the "uploading an existing file" flow from a `+ Add file` menu. Slower but bypasses git push.
