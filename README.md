# Meko

Versioned KSP mod selections and independent Mac game installations. Inspired by MECO / “Main Engine Kut Off.”

Meko keeps a stock reference, a standard template, and playable Blue/Green copies. CKAN installs mods; Meko prepares instances and records what changed. Git stores text records, never the game, saves, mod archives, or personal flag images.

| Instance | Role |
| --- | --- |
| Core | Read-only stock KSP + DLCs, copied only from Steam depot manifest entries and checked against their hashes |
| Base | Writable template: stock + DLCs + local custom flags; standard mods can be added deliberately |
| Blue | Current playable copy |
| Green | Independent copy of Blue for changes and experiments |
| Debug | Existing copy, retained and registered separately |

Base updates affect future clones. They do not propagate into existing instances. Blue and Green have independent saves: switching copies does not merge campaign progress.

## On the configured Mac

From this repository:

```sh
bin/meko status
bin/meko clone Blue GreenNext
bin/meko register GreenNext
bin/meko select GreenNext
bin/meko launch GreenNext
```

Close CKAN and KSP before cloning, recording, registering, or using `select`. With CKAN already open, switch using **File → Manage Game Instances** instead. Use `launch` or the Mac `KSP.app` to play; CKAN's Windows game-launch button is not configured for the Mac game.

`clone` preserves saves, settings, craft, flags and CKAN metadata. It uses independent macOS copy-on-write files, refuses an existing destination, and adds the relative `KSP_x64.exe` compatibility link needed by the Windows CKAN GUI. The link identifies the Mac instance; it does not turn KSP into a Windows executable. Core cannot be registered, selected, or launched through Meko.

## Record and compare a change

```sh
bin/meko snapshot Blue records/blue-before
# Make deliberate mod changes in the Green candidate using CKAN, then quit it.
bin/meko snapshot Green records/green-candidate
bin/meko compare records/blue-before records/green-candidate
```

Each record contains:

- `selection.ckan`: explicitly selected mods, without version pins.
- `exact.ckan`: every installed CKAN mod and dependency pinned to its recorded version.
- `state.json`: package metadata, game version, DLC information, and GameData/settings hashes.

These records are evidence, not complete backups. They do not contain saves, craft, configuration contents, game binaries, or downloadable mod archives. Keep a full local clone for exact rollback. Availability of an old archive and compatibility of an old mod remain separate checks.

## Mod selections

- [Base](profiles/base.ckan) has no third-party CKAN mods yet. Custom flags are a local asset addition.
- [Meko](profiles/meko.ckan) is a **candidate**, recovered from the 70 selected mods in Kranston-02. It has not been installed or qualified on Mac.
- [Historical exact state](records/kranston-2024-06-06) records 82 mods, including 12 automatic dependencies, plus both DLCs. The original Windows registry supplied the metadata; the old download cache was empty.
- [Original imports](imports/kranston) preserve four standalone exports, 35 history exports, and the installed export unchanged.

Keep complete selections for each line. Record explicit exclusions and reasons in [decisions.json](profiles/decisions.json). Editing or importing a recipe is not a full reconciliation: review additions, removals, dependencies, and versions in CKAN before applying them. Never assume that deleting a name from a recipe removes it from an existing installation.

See [the workflow](docs/workflow.md) for upgrades, flags, recovery and setup on another Mac, and [the setup receipt](docs/setup-2026-09-20.md) for what was actually verified.

## Development

Python 3.9+ for records; macOS and a clonefile-capable filesystem for instance copies. CrossOver and CKAN must already be installed for GUI integration.

```sh
python3 -m unittest discover -s tests -v
```

Use `git` and `gh`, not Graphite. Work on a branch and review the exact changes before integrating them.
