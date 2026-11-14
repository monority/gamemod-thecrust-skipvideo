# Skip cinematics — technical investigation

Everything below was derived by disassembling the game's Kismet bytecode and
diffing rebuilt packages byte-for-byte against the vanilla files.

## 1. How the game implements skipping

| Component | Role |
| --- | --- |
| `Config/DefaultInput.ini` | `+AxisMappings=(AxisName="SkipSequence",Scale=1,Key=SpaceBar)` |
| `GodPlayer_PC.InpAxisEvt_SkipSequence` | if `AxisValue > 0` **and** `CrustGI.Cinematic is Active`: `Time for Skip Cinematic += WorldDeltaSeconds`; if `Time >= Target Time for Skip Cinematic` then broadcast `On Stop Cinematic` |
| `W_Cinematic` | gauge = `PB_SetPercent(Time for Skip / Target Time for Skip)` |
| `S_StartBakedCinematic` | pre-rendered videos: sets `CinematicIsActive = true`, and **if its `Disable Input` property is true, calls `PlayerController.DisableInput()`** |
| `S_StartInGameCinematic` | in-engine cinematics: has a real skip path (`Have Skip Option`, `Skip Sequence Widget`, `EnableInput`) |

The chain is therefore: axis event → `Time` accumulates → threshold reached →
`On Stop Cinematic` → the state machine leaves the cinematic state.

`DisableInput()` breaks the first link, so `Time` never moves.

## 2. Control flow of the video state

`ExecuteUbergraph_S_StartBakedCinematic` (statements, simplified):

```text
 6  JumpIfNot(->1023, IsValid(Video))        ; no video -> leave
 9  JumpIfNot(->15,   cast to MediaSource)   ; cast failed -> leave
11  JumpIfNot(->1038, OpenSource ok)         ; source failed -> leave
...
26  JumpIfNot(->1108, Disable Input)         ; if false: skip the block below
28  PlayerController.DisableInput            ; <-- blocks the skip axis
31  Overlay_1.SetVisibility(1)                ; <-- also hides the skip hint
...
41  Overlay_1.SetVisibility(4)                ; normal path: hint visible
45  JumpIfNot(->1304, is Loading)
46  CallMulticastDelegate(On Cinematic Finished)
```

Both symptoms — "the skip does not work" and "the gauge never appears" — come
from the same branch (26 → 31).

## 3. Rejected approaches, and the crashes they caused

| Attempt | Result |
| --- | --- |
| Replace the `Disable Input` assignment expression with `EX_False` in `QSM_StartVideo` | `Unknown code token 49` at `084D` of `ExecuteUbergraph_QSM_StartVideo` |
| Same on `QSM_StartVideoExplosion` plus `S_StartBakedCinematic` | crash again |
| `Have Skip Option` / `Disable Input` rewritten in `QSM_MeteoriteFall`, `QSM_RescueOperation`, `QSM_PlotFinal` | `Serial size mismatch: Got 389857, Expected 1159113` on `QSM_RescueOperation` |

Root cause: `UAssetGUI fromjson` re-serializes the JSON tree but **does not
recompute the absolute `CodeOffset` values** stored in jump expressions. Every
change that alters the bytecode length therefore shifts all subsequent code and
desynchronises the jump table, and every change that alters an export's
serialized size breaks the package summary.

> Rule: on these assets, never change the bytecode length.

## 4. The patches that were kept

Both are size-neutral by construction.

### `S_StartBakedCinematic`

1. `EX_VirtualFunction` `DisableInput` → `EnableInput`.
   A virtual function name is an `FName` reference (2 × `int32`), so the length
   of the *string* does not affect the bytecode size, and both names already
   exist in the package `NameMap` — the name table does not even change.
2. `Overlay_1.SetVisibility` argument `EX_ByteConst` `1` → `4`.
   A `ByteConst` operand is one byte regardless of value.

### Quest state machines

`Have Skip Option` boolean property → `true`. A bool value is 1 byte; on
`QSM_Tutorial` the diff against vanilla is **4 bytes for 4 instances**, and the
`.uasset` is byte-identical.

### `GodPlayer_PC` (prototyped, not shipped)

`Target Time for Skip Cinematic` `1.0` → `0.0`, a single float: the comparison
`Time >= Target` then becomes true on the first frame of axis input. This was
built as an "instant skip" variant and dropped: the comparison only runs inside
`InpAxisEvt_SkipSequence`, so a key press is still required and the patch bought
nothing over the normal variant. See section 6.

## 5. Verification performed on every build

```text
S_StartBakedCinematic.uexp   8367 -> 8367 bytes   (2 changes, size identical)
QSM_Tutorial.uexp        1486702 -> same          (4 bytes differ, uasset identical)
GodPlayer_PC.uexp         900018 -> 900018        (1 float, prototype)
```

`work/fix_skip_baked.py` refuses to write the asset if the `.uexp` size moved,
and it is idempotent (a second run reports "nothing to patch").

## 6. Measuring the bytecode layout (unfinished)

To place a *new* jump target one needs an exact statement → byte-offset map.
`ScriptBytecodeSize` is **not** the bytecode length (the measured span of
statements 6→118 is 4246 bytes against a declared 3354), so the map had to be
measured.

Method used: stamp every `CodeOffset` with a unique sentinel, rebuild, then locate
each sentinel in the `.uexp`. The bytecode base offset was anchored with
`PushingAddress = 3351`, a value that occurs exactly once in the file
(bytecode starts at 2900). This yielded 17 exact anchors:

```text
stmt 6 -> 116    stmt 26 -> 1113   stmt 56 -> 2020   stmt 100 -> 3770
stmt 9 -> 231    stmt 45 -> 1650   stmt 61 -> 2202   stmt 105 -> 3956
stmt 11 -> 332   stmt 51 -> 1814   stmt 65 -> 2347   stmt 112 -> 4162
                                   stmt 84 -> 3013   stmt 118 -> 4362
```

A hand-written serialization model reproduces these anchors only within
+24…+178 bytes per interval, which is not good enough to retarget a jump safely.
Two facts rule out the obvious shortcut:

* the "no video" targets (`1023`, `1038`) and the `Disable Input` target (`1108`)
  all land **before** the end-of-video block (offset ≥ 1650), so nulling the
  `Video` property to reach the `IsValid` failure path would never emit
  `On Cinematic Finished` — it would soft-lock;
* there is no unconditional early jump to retarget, and the conditional guards
  are all false in the normal case.

A true zero-input auto-skip therefore requires either a byte-accurate Kismet
assembler or authoring a new state asset in the Unreal editor. It was left out of
1.0.0 rather than shipped with a soft-lock risk.

## 7. Why the base pak cannot be enumerated

```text
pakchunk0-WindowsNoEditor.pak   5.31 GiB   pak version 11
footer at -204 bytes, index at 5 699 137 148 (1 520 530 bytes)
occurrences of 'QSM_' / '.uasset' / 'NewStateMAchine' in the index: 0
```

The index is a frozen (memory-image) index, so filenames are not stored as
strings; reading it requires reimplementing UE4's `FMemoryImage` serialization.
Consequently the quest state machines shipped here are exactly those that had
already been extracted, and no claim is made about the rest of the game.
