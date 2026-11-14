# The Crust — Skip Cinematics

## Short description (Nexus summary field)

Makes every cutscene in The Crust skippable — campaign videos, POI intros,
explosions, tutorial videos and in-engine cinematics. Hold `Space` to fill the
skip gauge.

## Long description

### What this does

The Crust only allows skipping on some in-engine cinematics, and most of those
are flagged non-skippable. Every pre-rendered video calls
`PlayerController.DisableInput()` while it plays, so the skip axis never reaches
the controller: the gauge stays at 0 and `Space` does nothing.

This mod fixes the shared cinematic state and the per-quest flags so that:

* every pre-rendered video is skippable — main-menu intro, campaign videos
  (Meteorite Fall, Rescue Operation, Plot Final), POI intros, explosion
  sequences and tutorial videos;
* the in-engine cinematics in `QSM_AfterExplosion`, `QSM_RandomPOIStart`,
  `QSM_SandboxMode` and the four in `QSM_Tutorial` are skippable;
* the on-screen skip overlay is actually drawn while a video plays.

### Installation

**Vortex (recommended):** click **Install with Vortex** on this page, or in Vortex
use *Mods → Install From File*. Enable the mod, then **Deploy**.

The The Crust Vortex extension only copies `.pak` files, flattened, into
`TheCrust\Content\Paks\~mods`; any other file in the archive is ignored.

**Manual:** extract `zzzzzzzz_SkipCinematics_P.pak` and copy it into
`The Crust\TheCrust\Content\Paks\~mods\` (create `~mods` if it is missing).

Use one method or the other — not both for the same file.

### Uninstallation

* Vortex: disable or remove the mod, then **Deploy**.
* Manual: delete the `.pak` from `~mods`.

### Conflicts

Replaces `S_StartBakedCinematic`, plus `QSM_AfterExplosion`,
`QSM_RandomPOIStart`, `QSM_Tutorial` and `QSM_SandboxMode`. Any mod touching the
same assets will conflict; the pak loaded last wins. The `zzzzzzzz` prefix is
deliberate: Vortex merges all The Crust mods into one `~mods` folder, so the file
name decides which pak overrides the other.

### Technical

Every patch is byte-size neutral: the `.uexp` produced for each asset is exactly
the same length as the vanilla file, so no serialized offset is invalidated. This
is the difference between a working pak and a `Serial size mismatch` crash.
Changes are: a virtual call retargeted from `DisableInput` to the already-present
`EnableInput`, one `SetVisibility` byte constant changed from `Collapsed` to
`SelfHitTestInvisible`, and the boolean `Have Skip Option` set to `true` on seven
in-engine instances.

### Known limitations

* In-engine cinematics living in quest state machines that are not part of this
  release are not covered — the base game pak uses a frozen index, so its full
  asset list cannot be enumerated.
* A key press is always required. There is no zero-input auto-skip: the skip
  timer only advances inside `GodPlayer_PC.InpAxisEvt_SkipSequence`, which the
  engine only calls on an input-axis event.

### Changelog

**1.0.0**
* First release.
* All baked video cinematics skippable, skip overlay restored.
* `Have Skip Option` enabled on 7 in-engine cinematic instances.
