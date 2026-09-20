# KSP management

Use git and gh, never Graphite. Work on a reviewable branch; main is integrated.

This repository is public. Track scripts, mod selection recipes, exact package metadata, and documentation. Never commit game files, saves, downloaded mod archives, credentials, local paths/configuration, or runtime state.

Core is a frozen stock reference. Base is a template. Blue and Green are independent playable copies. Preserve the current playable copy before changes. Never replace an existing instance, silently update pinned mods, share writable save directories, or assume an old Windows mod selection works on Mac.

Use CKAN to install/remove mods. Scripts here provide instance preparation and records, not a replacement dependency resolver. Close CKAN and KSP before cloning or snapshotting. Use APFS copy-on-write copies, not hardlinks or shared stock folders.

Run `python3 -m unittest discover -s tests -v` for manager changes. Verify installed CKAN behavior for registration/selection changes. A package record is not proof of archive availability or gameplay compatibility.
