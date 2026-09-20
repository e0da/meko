# Maintaining a line

## Try a change

1. Quit KSP and CKAN. Record Blue and clone it into a new candidate name. Meko never overwrites an existing instance.
2. Register the candidate and open it in CKAN. Add, remove, or upgrade mods deliberately. Read CKAN's dependency/removal preview before applying.
3. Quit CKAN and record the result. Compare the records, including dependency versions and file changes. Copy the candidate's `selection.ckan` to the intended profile only when it represents the selection you want to maintain. Record deliberate exclusions and reasons.
4. Launch the candidate with `bin/meko launch NAME`. Check the flag picker, load a copy of a representative save, and exercise the mods you changed. A catalog refresh is not a gameplay test.
5. After acceptance, `bin/meko select NAME` makes that candidate CKAN's default. Keep the previous copy as rollback. This does not rename folders, overwrite Blue, or merge saves.
6. Commit the intended selection, exact state and notes. A release tag can mark a tested combination. A Git tag does not preserve missing binary archives; retain the tested game copy and cached downloads separately.

Use Blue and Green as stable names when useful, but make a fresh name such as `GreenNext` when both already exist. Archive a retired copy deliberately before reusing its name. There is no automatic destructive promotion or deletion command.

## Refresh Core and Base

Check Steam for updates and verify the integrity of installed files. Once Steam has finished, create a new reference name:

```sh
bin/meko core "$HOME/Library/Application Support/Steam/steamapps/common/Kerbal Space Program" CoreNext
bin/meko clone CoreNext BaseNext --role template
bin/meko flags BaseNext assets.local/flags
bin/meko register BaseNext
```

The `core` command reads Steam's app manifest and installed depot manifests, checks the listed files against their SHA-1 hashes and sizes, and copies only those entries. User saves, screenshots and other files absent from the depots are not carried forward. It freezes the resulting reference by removing write permission, and records Steam build/depot IDs in local instance configuration. It fails if manifests are missing, hashes mismatch, or Steam is not fully installed and idle. It does not download or authenticate to Steam.

Apply the chosen Base recipe to the new template with CKAN, review the dependency result, and record it. A game upgrade and a mod upgrade are separate choices: don't silently resolve all mods to the latest version during a rebuild. Build the candidate from the new Base and the desired line's complete selection, recording any explicit changes to old version pins.

Do not share mutable directories or use CKAN's “share stock” mode. Meko uses clonefile for data independence and refuses a full-copy fallback if cloning is unsupported. Copy-on-write saves space initially; later changes still consume disk space. Same-disk recovery copies do not protect against disk failure.

## Flags and local overrides

Personal flags live in ignored `assets.local/flags/`. To apply them to a writable instance:

```sh
bin/meko flags Base assets.local/flags
```

Meko copies PNGs unchanged into `GameData/Meko/Flags/`, accepting the recovered 256×160 format and the current stock 512×256 format. It refuses to replace a different file with the same name. Use a new filename for a new flag version; existing saves and craft may refer to the old texture path. Other image dimensions require explicit review rather than automatic resizing.

Existing instances do not receive Base changes automatically. Apply the flags to each desired copy explicitly, then record it. Keep configuration override contents privately with the full instance; the public state record contains hashes only. No custom flags are installed in Core.

## Another Mac

Clone the public repository. Copy `instances.example.json` to `instances.local.json` and set the real instance paths and installed CrossOver/CKAN launcher paths. Restore game copies and personal assets from your own backups, or obtain the game through Steam and use `core` and `clone`. A Git checkout alone is not a game installation.

`register` adds a new CKAN entry; use it once per name. `select` requires that name to be registered. After a CLI change, Meko waits for the dedicated Wine server to exit before reopening the GUI through macOS, preventing a remote terminal desktop from carrying over. If that wait times out, close remaining CKAN windows and retry; do not force a registry lock.

Paths in local configuration are relative to its parent directory, or absolute. This setup uses a dedicated CrossOver bottle named CKAN; `--asroot` is for Wine's simulated Windows account and does not invoke sudo on macOS.

Keep the public Git repository separate from CKAN runtime/account settings. Do not commit Steam account configuration or the CrossOver bottle.

## Recovery

Before this setup, full independent copies of Blue, the previous Core, and Steam's installation were placed in ignored `Snapshots/2026-09-20-before-meko/`. The original Kranston registry and flag-source mapping are retained locally as well. These are local recovery material, not cloud backups.

Quit both programs before restoring a copy. Restore to a new path/name first, register it, inspect its record and launch it before retiring anything. Do not overlay an old registry onto different GameData files. Do not run two CKAN clients against the same instance.

The historical Meko selection originated on Windows. Shader/native plugin support, archive availability, and save compatibility must be checked on Mac before promoting it to a playable line. The repository intentionally records this candidate without installing it into Blue or Green.
