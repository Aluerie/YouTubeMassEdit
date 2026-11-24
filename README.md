# 📝 YouTube Mass Edit

Replaces the shared parts of every video description in a playlist, leaving each video's own intro
and timestamps alone. Each playlist (Sekiro, Elden Ring, ...) has its own shared text and hashtags.

A description is expected to look like this:

```text
[unique intro]
# 😘Chosen Playlist Restrictions   ┐
...                                │ replaced with for_editing/<name>.md
# 🤔Extra                          │
...                                ┘
# ⏰Timestamps                      ← kept
...
#hitless #sekiro                   ← replaced with the playlist's `hashtags`
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

Each playlist is a `[playlists.<name>]` table in `config.toml` with its link, its shared-text file in
`for_editing/` and its hashtags. The name is what you type in the commands, e.g. `sekiro` or
`elden_ring`. To add a playlist, copy a table, give it a new name and point it at a new `.md` file.

1. Edit the playlist's file in `for_editing/` (the shared block), and its hashtags in `config.toml`.
2. Preview. Nothing is saved, and each video's diff is printed (`-` removed, `+` added):

   ```sh
   uv run youtube-mass-edit update sekiro
   ```

3. If only the shared sections show up in the diffs, save the changes:

   ```sh
   uv run youtube-mass-edit update sekiro --apply
   ```

Before saving, the original snippets of the videos being changed are written to
`backups/<name>_<date>_<time>.json`. To undo a run, preview and then apply a restore:

```sh
uv run youtube-mass-edit restore sekiro backups/sekiro_2026-11-23_163000.json
```

```sh
uv run youtube-mass-edit restore sekiro backups/sekiro_2026-11-23_163000.json --apply
```

Only videos in the named playlist are ever changed, and `restore` skips backed-up videos that aren't in
it.

## 💡 Good to know

- **The headings are the markers.** Videos where either heading can't be found are listed as
  `skipped` and left unchanged. The emoji in a heading can change; only the words set in
  `config.toml` have to stay.
- **Renaming a heading:** put the new heading in the playlist's `.md` file, run once with the *old* words in
  `start_heading` / `end_heading`, then switch `config.toml` to the new words. A playlist can set its
  own `start_heading` / `end_heading` if its headings differ from the others.
- **Daily quota:** each saved video costs 50 of the 10,000 free daily units, so about 190 videos a day.
  If the quota runs out, the tool stops. Run the same command the next day; videos already up to date
  are skipped.
- **Limits:** YouTube rejects descriptions over 5000 *bytes* (an emoji counts as 4) or containing
  `<` or `>`. Videos like that are reported and not saved.

## 🛠️ Development

```sh
uv run ruff format . && uv run ruff check . && uv run ty check && uv run pytest
```
