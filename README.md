# 📝 YouTube Mass Edit

Replaces the shared parts of every video description in a playlist, leaving each video's own intro
and timestamps alone.

A description is expected to look like this:

```text
[unique intro]
# 😘Chosen Playlist Restrictions   ┐
...                                │ replaced with for_editing/shared.md
# 🤔Extra                          │
...                                ┘
# ⏰Timestamps                      ← kept
...
#hitless #sekiro                   ← replaced with `hashtags` from config.toml
```

## 🔑 One-time setup

1. Install [uv](https://docs.astral.sh/uv/), then run `uv sync` in this folder.
2. In [Google Cloud Console](https://console.cloud.google.com):
   1. Create a project.
   2. Go to **APIs & Services → Library**, then find and enable **YouTube Data API v3**.
   3. Go to **OAuth consent screen** (now called **Google Auth Platform**) and click **Get started**.
      Fill in the app name and your email. **External** is chosen at the wizard's **Audience** step,
      not on the first page. If the wizard is already finished, check **Audience → User type** instead.
      Then, under **Audience → Test users**, add the Google account that owns your channel.
   4. Go to **Credentials → Create credentials → OAuth client ID** and choose **Desktop app**. Download
      the JSON file and save it here as `client_secret.json`.

The first run opens your browser to log in. Google warns that the app is "unverified"; that's expected
for your own test app. The login is saved to `token.json`, so later runs don't ask again.
`client_secret.json`, `token.json` and `backups/` are git-ignored. Don't share them.

## 🚀 Usage

1. Edit `for_editing/shared.md` (the shared block) and `config.toml` (playlist, hashtags, optional video tags).
2. Preview. Nothing is saved, and each video's diff is printed (`-` removed, `+` added):

   ```sh
   uv run youtube-mass-edit update
   ```

3. If only the shared sections show up in the diffs, save the changes:

   ```sh
   uv run youtube-mass-edit update --apply
   ```

Before saving, the original snippets of the videos being changed are written to
`backups/<date>_<time>.json`. To undo a run, preview and then apply a restore:

```sh
uv run youtube-mass-edit restore backups/2026-11-23_163000.json
uv run youtube-mass-edit restore backups/2026-11-23_163000.json --apply
```

Only videos in the playlist are ever changed, and `restore` skips backed-up videos that are no longer in
it. To work on a different playlist than the one in `config.toml`, pass its ID or URL before the command:

```sh
uv run youtube-mass-edit --playlist "https://www.youtube.com/playlist?list=PL..." update
```

## 💡 Good to know

- **The headings are the markers.** Videos where either heading can't be found are listed as
  `skipped` and left unchanged. The emoji in a heading can change; only the words set in
  `config.toml` have to stay.
- **Renaming a heading:** put the new heading in `for_editing/shared.md`, run once with the *old* words in
  `start_heading` / `end_heading`, then switch `config.toml` to the new words.
- **Daily quota:** each saved video costs 50 of the 10,000 free daily units, so about 190 videos a day.
  If the quota runs out, the tool stops. Run the same command the next day; videos already up to date
  are skipped.
- **Limits:** YouTube rejects descriptions over 5000 *bytes* (an emoji counts as 4) or containing
  `<` or `>`. Videos like that are reported and not saved.

## 🛠️ Development

```sh
uv run ruff format . && uv run ruff check . && uv run ty check && uv run pytest
```
