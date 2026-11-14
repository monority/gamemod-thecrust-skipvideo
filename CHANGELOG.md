# Changelog

All notable changes to this mod are documented here.
This project follows [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-11-13

### Added

* `packaging/build_release.py` — builds the distribution archive and the Nexus
  upload folder in one command.
* Double installation path: the same archive works through the **Vortex** mod
  manager (The Crust extension copies only the `.pak` into `~mods`) and as a
  manual copy. Documented in `README.md`, `packaging/README_ARCHIVE.md` and
  `packaging/MODPAGE.md`.
* Ready-to-publish archive in `dist/`, with `SHA256SUMS.txt` and the mod page copy
  in `packaging/MODPAGE.md`.

### Fixed

* Pre-rendered video cinematics can now be skipped. The shared state
  `S_StartBakedCinematic` called `PlayerController.DisableInput()` for the whole
  playback, so the `SkipSequence` axis never reached the controller: the gauge
  stayed at 0 and `Space` had no effect.
* The on-screen skip overlay is now drawn during videos. The same branch that
  disabled input also hid the overlay with `SetVisibility(1)` (`Collapsed`);
  the constant is now `4` (`SelfHitTestInvisible`), matching the normal path.
* In-engine cinematics are skippable in `QSM_AfterExplosion`,
  `QSM_RandomPOIStart`, `QSM_SandboxMode` and the four in `QSM_Tutorial`
  (`Have Skip Option` → `true`, 7 instances).

### Notes

* Every patch is byte-size neutral: the resulting `.uexp` is the same length as
  the vanilla file, so no serialized offset is invalidated. This was a hard
  requirement — see `docs/SKIP_CINEMATICS.md` for the crashes caused by
  size-changing edits.

### Dropped before release

* An "instant skip" variant was prototyped: `Target Time for Skip Cinematic` set
  to `0.0` in `GodPlayer_PC`, so the gauge threshold is met on the very first
  frame. It was dropped because it still requires a key press — the skip timer is
  only advanced from `InpAxisEvt_SkipSequence`, which the engine calls on an
  input-axis event — so it added a patched `GodPlayer_PC` for a marginal gain.
  Making the skip truly automatic would require redirecting a jump in
  `S_StartBakedCinematic`, which needs a byte-accurate Kismet assembler that this
  project does not have. The investigation is documented in
  `docs/SKIP_CINEMATICS.md`, section 6.

### Known limitations

* Quest state machines outside this release are not covered; the base game pak
  uses a frozen index and cannot be enumerated with these tools.
* No zero-input auto-skip, by design (see above).
