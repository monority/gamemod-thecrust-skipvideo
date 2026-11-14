# Skip Cinematics

Skip any cutscene in The Crust. Hold `Space` while it plays: a gauge fills on
screen and the cutscene stops when the gauge is full.

## Install

With Vortex: install the archive from the Releases page, enable the mod, then
deploy.

Manually: copy `zzzzzzzz_SkipCinematics_P.pak` into

```text
The Crust\TheCrust\Content\Paks\~mods\
```

Create the `~mods` folder if it does not exist.

Pick one of the two. If you do both you end up with two copies, and Vortex will
not remove the one you copied by hand.

## Uninstall

Delete the `.pak` from `~mods`, or disable the mod in Vortex and deploy.

## What can be skipped

Every video in the game, plus the in-game cutscenes of these parts: After
Explosion, random POI start, sandbox mode and the tutorial.

## Limits

Some cutscenes are not covered here because their files were not available.

A key press is always needed. Nothing is skipped on its own.

## For modders

The modified game files are in `sources/`. To rebuild the pak:

```bash
python tools/build_pak.py
```

The reasoning behind the fix, including what was tried and rejected, is in
[docs/SKIP_CINEMATICS.md](docs/SKIP_CINEMATICS.md).

## Credits and license

Code is MIT, see [LICENSE](LICENSE). The Crust is made by VEOM Studio. This
repository only ships modified game data, no original content.

JSON conversion uses [UAssetGUI](https://github.com/atenfyr/UAssetGUI).
