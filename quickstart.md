# Quickstart — iPhone & Apple Podcasts

## The feed URL

Your podcast RSS feed is committed directly to this repo. The permanent URL is:

```
https://raw.githubusercontent.com/johnsirmon/relevant/main/podcast.xml
```

Every time the pipeline runs, it updates this file and pushes the commit. Apple Podcasts polls it automatically.

---

## Step 1 — Add to Apple Podcasts (iPhone)

1. Open the **Podcasts** app on your iPhone
2. Tap **Search** (bottom bar) → scroll down and tap **"Add a Show by URL"** (at the very bottom of the search screen, under Browse Categories)
3. Paste the feed URL above and tap **Subscribe**

That's it. New episodes appear in your library each week automatically.

> **Alternative:** If you can't find "Add a Show by URL" in Podcasts, try [Overcast](https://overcast.fm) or [Pocket Casts](https://pocketcasts.com) — both support RSS URLs directly in the Add Podcast screen.

---

## Step 2 — Trigger an episode from GitHub Mobile (iPhone)

The pipeline runs automatically every **Monday at 9 AM UTC**, but you can kick it off manually at any time from your phone.

1. Install **[GitHub Mobile](https://apps.apple.com/app/github/id1477376905)** and sign in
2. Open this repository: **johnsirmon/relevant**
3. Tap **Actions** (from the repo screen, tap the ⋯ menu → Actions, or tap the Actions tab if visible)
4. Tap **🎙️ Update Radar Podcast**
5. Tap **Run workflow**
6. Choose a mode:
   - **full** — discovers new repos, writes briefing, generates audio *(default)*
   - **podcast-only** — skips discovery; re-narrates the existing README as audio
   - **dry-run** — updates the feed file only, no audio generated (good for testing)
7. Tap **Run workflow** to confirm

The run takes roughly 5–10 minutes. When it finishes, a new episode is live in your feed.

---

## How it all fits together

```
GitHub Actions (Monday 9am UTC, or manual)
        │
        ▼
  Discover repos → Research → Write README.md
        │
        ▼
  Narrate → TTS (audio) → GitHub Release (MP3)
        │
        ▼
  Update podcast.xml  ←── committed to this repo
        │
        ▼
  Apple Podcasts polls the raw URL → new episode appears
```

---

## Listening to the latest episode without waiting

If a new run just finished and the episode hasn't appeared in Apple Podcasts yet:

1. Open Apple Podcasts → your library → **Weekly Developer Radar**
2. Pull down to refresh, or tap the episode list and wait a few minutes — Apple Podcasts typically picks up feed changes within 1–5 minutes

You can also open the MP3 directly from the **Releases** tab of this repo in GitHub Mobile.
