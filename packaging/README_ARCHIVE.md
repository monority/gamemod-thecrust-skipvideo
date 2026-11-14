# Skip Cinematics

Makes every cutscene in The Crust skippable: hold `Space`, a gauge fills, the
cutscene cuts when the gauge is full.

## Install

### With Vortex (mod manager)

1. On the mod page, click **Install with Vortex** (or in Vortex: *Mods → Install
   From File* and pick this archive).
2. Enable the mod and click **Deploy**.

Vortex's The Crust extension only copies `.pak` files, flattened, into
`TheCrust\Content\Paks\~mods`. The `README.md` inside this archive is ignored by
the installer, so nothing but the pak reaches the game folder.

### Manually

1. Extract `zzzzzzzz_SkipCinematics_P.pak` from this archive.
2. Copy it to:

```text
The Crust\TheCrust\Content\Paks\~mods\
```

Default full path: `C:\Games\The Crust\TheCrust\Content\Paks\~mods\`

Create the `~mods` folder if it does not exist. No configuration change needed.

### Pick one method, not both

Vortex deploys the pak into `~mods` as a hard link. If you also copy the file
there by hand, you end up with two entries for the same mod and uninstalling
through Vortex leaves the manual copy behind. Use either Vortex or the manual
copy.

## Uninstall

* Vortex: disable or remove the mod, then **Deploy**. Vortex removes the link.
* Manual: delete the `.pak` from `~mods`.

Nothing else is modified in either case.

## What it covers

**All baked video cinematics.** Every video uses one shared state machine
(`S_StartBakedCinematic`), so patching that state covers the main-menu intro, the
campaign videos (Meteorite Fall, Rescue Operation, Plot Final), POI intros,
explosion sequences and tutorial videos.

**In-engine cinematics**, via the per-instance `Have Skip Option` flag:

| Quest state machine | Cinematics |
| --- | --- |
| `QSM_AfterExplosion` | MeteorPlacement |
| `QSM_RandomPOIStart` | In Game Cinematic |
| `QSM_SandboxMode` | In Game Cinematic |
| `QSM_Tutorial` | TutorialAccum, MeteorPlacement, SolarTutorialCine, Tut_Alice16 |

## Conflicts

This mod replaces these game assets:

```text
TheCrust/Content/Shared/Graph/States/NewStates/CinematicStates/S_StartBakedCinematic
TheCrust/Content/Shared/NewStateMAchine/Quests_2024/Act_1/QSM_AfterExplosion
TheCrust/Content/Shared/NewStateMAchine/Quests_2024/POI/QSM_RandomPOIStart
TheCrust/Content/Shared/NewStateMAchine/Quests_2024/Tutorial/QSM_Tutorial
TheCrust/Content/Shared/NewStateMAchine/Tutorial/QSM_SandboxMode
```

Any other mod editing the same assets will conflict; the pak loaded last wins
(alphabetical order of the file names). The `zzzzzzzz` prefix on this mod's pak
is deliberate: Vortex merges all The Crust mods into the same `~mods` folder, so
the name decides which pak overrides the other.

## Known limitations

* In-engine cinematics that live in quest state machines **not shipped here** are
  not covered. The base game pak is 5.31 GB with a frozen (memory-image) index,
  so its asset list cannot be enumerated with the tools used here.
* A key press is always required. There is no zero-input auto-skip: the skip
  timer is only incremented inside `GodPlayer_PC.InpAxisEvt_SkipSequence`, which
  the engine only calls on an input-axis event.
* A few cutscenes are deliberately flagged non-skippable by the developers. This
  mod overrides that design choice for the assets listed above.

## Technical notes

No bytecode offset is moved by these patches, so the assets stay structurally
identical to the originals:

* `S_StartBakedCinematic` — the virtual call `DisableInput` is retargeted to the
  already-present name `EnableInput` (an `FName` reference, same size), and one
  `SetVisibility` byte constant is changed from `Collapsed` (1) to
  `SelfHitTestInvisible` (4) so the skip overlay is drawn.
* Quest state machines — the boolean `Have Skip Option` is set to `true`
  (4 bytes differ from vanilla, no size change).

Verification performed on each build: the `.uexp` file size is byte-identical to
the vanilla file, so no serialized offset can be invalidated.
