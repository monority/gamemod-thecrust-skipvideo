#!/usr/bin/env python3
"""Rend les cinematiques video (baked) skippables, sans casser les assets.

Constat (bytecode vanilla) :

  * GodPlayer_PC.InpAxisEvt_SkipSequence (axe Espace) n'incremente
    "Time for Skip Cinematic" que si CrustGI.Cinematic is Active, puis
    broadcast "On Stop Cinematic" quand Time >= Target Time.
  * W_Cinematic affiche la jauge avec
    PB_SetPercent(Time for Skip / Target Time for Skip).
  * S_StartBakedCinematic, au demarrage de la video, appelle
    PlayerController.DisableInput(PC) lorsque sa propriete "Disable Input"
    est vraie. L'axe SkipSequence n'arrive alors jamais au PlayerController :
    pas de jauge, pas de skip, quelle que soit la cinematique video.

POURQUOI PAS UN PATCH DES QSM :
  Les QSM de campagne (QSM_RescueOperation 1,1 Mo de bytecode, etc.) ne se
  re-encodent pas a l'identique via UAssetGUI : le jeu plante avec
  "Serial size mismatch: Got 389857, Expected 1159113".

STRATEGIE RETENUE (modification strictement de meme taille) :
  Dans ExecuteUbergraph_S_StartBakedCinematic, remplacer l'appel virtuel
  "DisableInput" par "EnableInput". Les deux noms existent deja dans la
  table des noms du package :
    - la table des noms ne change pas,
    - le bytecode garde exactement la meme taille (un FName = 2 x int32),
    - les CodeOffset des sauts restent donc valides.
  Resultat : l'input du joueur reste actif pendant la video, l'axe
  SkipSequence arrive au PlayerController, la jauge se remplit et Espace
  coupe la cinematique.

Usage :
  python tools/fix_skip_baked.py            # patche le JSON
  python tools/fix_skip_baked.py --rebuild  # + reconstruit le .uasset
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = (
    ROOT
    / "sources/TheCrust/Content/Shared/Graph"
    / "States/NewStates/CinematicStates/S_StartBakedCinematic.json"
)
UASSETGUI = ROOT / "UAssetGUI.exe"
if not UASSETGUI.exists():
    UASSETGUI = ROOT.parent / "UAssetGUI.exe"

VIRTUAL_FUNCTION = "UAssetAPI.Kismet.Bytecode.Expressions.EX_VirtualFunction, UAssetAPI"
BYTE_CONST = "UAssetAPI.Kismet.Bytecode.Expressions.EX_ByteConst, UAssetAPI"
TARGET_GRAPH = "ExecuteUbergraph_S_StartBakedCinematic"

VISIBLE_SELF_HITTEST_INVISIBLE = 4


def walk(node, hits):
    """Collecte les EX_VirtualFunction dont le nom vaut DisableInput."""
    if isinstance(node, dict):
        if (
            node.get("$type") == VIRTUAL_FUNCTION
            and node.get("VirtualFunctionName") == "DisableInput"
        ):
            hits.append(node)
        for value in node.values():
            walk(value, hits)
    elif isinstance(node, list):
        for value in node:
            walk(value, hits)


def patch() -> int:
    try:
        data = json.loads(JSON_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        print(f"Erreur lecture : {exc}")
        return 1

    names = data.get("NameMap") or []
    for required in ("EnableInput", "DisableInput"):
        if required not in names:
            print(f"Erreur : '{required}' absent de la table des noms")
            return 1

    graph = next(
        (e for e in data.get("Exports") or [] if e.get("ObjectName") == TARGET_GRAPH),
        None,
    )
    if graph is None:
        print(f"Erreur : {TARGET_GRAPH} introuvable")
        return 1

    hits = []
    walk(graph.get("ScriptBytecode") or [], hits)
    for node in hits:
        node["VirtualFunctionName"] = "EnableInput"
    if hits:
        print(f"{TARGET_GRAPH} : {len(hits)} appel(s) DisableInput -> EnableInput")

    shown = 0
    for stmt in graph.get("ScriptBytecode") or []:
        ctx = stmt.get("ContextExpression") or {}
        if ctx.get("VirtualFunctionName") != "SetVisibility":
            continue
        obj = stmt.get("ObjectExpression") or {}
        path = ((obj.get("RValuePointer") or {}).get("New") or {}).get("Path") or []
        if "Overlay_1" not in path:
            continue
        for param in ctx.get("Parameters") or []:
            if param.get("$type") == BYTE_CONST and param.get("Value") == 1:
                param["Value"] = VISIBLE_SELF_HITTEST_INVISIBLE
                shown += 1
    if shown:
        print(f"{TARGET_GRAPH} : {shown} Overlay_1 SetVisibility -> affiche")

    if not hits and not shown:
        print("Rien a patcher (deja fait ?)")
        return 0

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"JSON ecrit : {JSON_PATH}")
    return 0


def rebuild() -> int:
    uasset = JSON_PATH.with_suffix(".uasset")
    uexp = JSON_PATH.with_suffix(".uexp")
    before = uexp.stat().st_size if uexp.exists() else None

    res = subprocess.run(
        [str(UASSETGUI), "fromjson", str(JSON_PATH), str(uasset)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if res.returncode != 0:
        print(f"UAssetGUI a echoue : {res.stderr[-400:]}")
        return 1

    after = uexp.stat().st_size if uexp.exists() else None
    print(f"uexp : {before} -> {after}")
    if before is not None and after != before:
        print("ATTENTION : la taille du bytecode a change, offsets a risque")
        return 1
    print("OK : taille du .uexp inchangee (patch sur)")
    return 0


def main(argv: list[str]) -> int:
    code = patch()
    if code == 0 and "--rebuild" in argv:
        code = rebuild()
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
