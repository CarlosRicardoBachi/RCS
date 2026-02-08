#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probar.py — Runner + depurador de log con IA (OpenAI) para RCS

Objetivo:
- Ejecuta RCS (python -m rcs.app) con el Python actual.
- Espera a que cierres la app (o a que termine).
- Lee scs.log (o fallback: stdout/stderr del proceso).
- Detecta y carga el checklist/objetivos del último hotfix en docs/patches/**.
- Llama a OpenAI (Responses API) para:
    - depurar el log (sin “ruido”),
    - etiquetar el error (causa / mecanismo),
    - resumir acciones sugeridas,
    - mapear resultado contra objetivos.
- Reemplaza scs.log por un JSON compacto y limpio (1 run = 1 log depurado).
- Guarda una copia cruda *solo del último run* en scs.raw.last.log (se sobreescribe).

Credenciales:
- Poner la API key en un archivo "credenciales.ia" (y excluirlo por git).
  En .gitignore:
      credenciales.ia

Formato de credenciales.ia (cualquiera de estos):
1) Solo la key en una línea:
   sk-....
2) JSON:
   {"OPENAI_API_KEY":"sk-...."}

Uso típico:
    python probar.py --verbose
Opcional:
    python probar.py --model gpt-4o-mini --max-runtime 0 --log scs.log --verbose
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------
# Config por defecto
# -----------------------------
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_LOG_NAME = "scs.log"
CRED_FILE_NAME = "credenciales.ia"

# Si el log es enorme, no lo mandamos entero a la IA.
MAX_CHARS_TO_AI = 45_000

# Cantidad de líneas finales si no hay traceback.
FALLBACK_TAIL_LINES = 350

# Copia cruda (solo la última) — se sobreescribe.
RAW_LAST_NAME = "scs.raw.last.log"

APP_CMD = [sys.executable, "-m", "rcs.app"]  # usa el Python actual


# -----------------------------
# Utils
# -----------------------------
def now_local_iso() -> str:
    # ISO sin tz explícita (Windows-friendly), pero con precisión de segundos.
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return path.read_text(errors="ignore")
        except Exception:
            return ""


def safe_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="ignore")


def truncate_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", errors="ignore") as f:
        f.write("")


def strip_ansi(s: str) -> str:
    ansi = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")
    return ansi.sub("", s)


def tail_lines(text: str, n: int) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def clamp_text_for_ai(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    # conservar el final (suele estar el error)
    return text[-max_chars:]


def parse_int_tuple_from_version(s: str) -> Optional[Tuple[int, ...]]:
    """
    Acepta:
      - "0.3"
      - "0.3.10.2.77"
      - "0.3.10.2.77_HOTFIX_..." (agarra el prefijo numérico)
    """
    m = re.match(r"^\s*(\d+(?:\.\d+)*)", s.strip())
    if not m:
        return None
    parts = m.group(1).split(".")
    try:
        return tuple(int(p) for p in parts)
    except Exception:
        return None


def max_version_dir(dirs: List[Path]) -> Optional[Path]:
    best: Optional[Path] = None
    best_v: Optional[Tuple[int, ...]] = None
    for p in dirs:
        v = parse_int_tuple_from_version(p.name)
        if v is None:
            continue
        if best_v is None or v > best_v:
            best_v = v
            best = p
    return best


# -----------------------------
# Objetivos / checklist del último hotfix (docs/patches/**)
# -----------------------------
@dataclass
class HotfixObjectives:
    found: bool
    base_path: str
    version_folder: str
    checklist_path: str
    objectives: List[str]
    raw_text: str


def extract_objectives_from_checklist(text: str) -> List[str]:
    """
    Intenta extraer objetivos tipo:
      1) ...
      2) ...
    o bullets.
    """
    out: List[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        # 1) 1. 1- 1:
        m = re.match(r"^(\d+)\s*[\)\.\:\-]\s*(.+)$", s)
        if m:
            out.append(m.group(2).strip())
            continue
        # bullets
        if s.startswith(("-", "*", "•")) and len(s) > 2:
            out.append(s.lstrip("-*•").strip())
            continue
    # de-dup conservando orden
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def find_latest_hotfix_objectives(repo_root: Path) -> HotfixObjectives:
    """
    Busca en:
      repo_root/docs/patches/<major_minor>/<full_version>/checklist_*.txt|.md
    """
    patches_root = repo_root / "docs" / "patches"
    if not patches_root.exists():
        return HotfixObjectives(False, str(patches_root), "", "", [], "")

    # Ej: docs/patches/0.3
    lvl1_dirs = [p for p in patches_root.iterdir() if p.is_dir()]
    major_minor_dir = max_version_dir(lvl1_dirs)
    if not major_minor_dir:
        return HotfixObjectives(False, str(patches_root), "", "", [], "")

    # Ej: docs/patches/0.3/0.3.10.2.77
    lvl2_dirs = [p for p in major_minor_dir.iterdir() if p.is_dir()]
    version_dir = max_version_dir(lvl2_dirs)
    if not version_dir:
        return HotfixObjectives(False, str(major_minor_dir), "", "", [], "")

    # checklist preferido .txt, fallback .md
    checklist_candidates = []
    checklist_candidates += sorted(version_dir.glob("checklist_*.txt"))
    checklist_candidates += sorted(version_dir.glob("checklist_*.md"))
    checklist_path = checklist_candidates[0] if checklist_candidates else None

    if not checklist_path or not checklist_path.exists():
        return HotfixObjectives(
            False, str(major_minor_dir), version_dir.name, "", [], ""
        )

    raw = safe_read_text(checklist_path)
    objectives = extract_objectives_from_checklist(raw)

    return HotfixObjectives(
        True,
        base_path=str(major_minor_dir),
        version_folder=version_dir.name,
        checklist_path=str(checklist_path),
        objectives=objectives,
        raw_text=raw,
    )


# -----------------------------
# Extracción “sin ruido” (local) + evidencia clave
# -----------------------------
def extract_traceback_block(text: str) -> str:
    """
    Devuelve el último traceback (si existe) desde "Traceback (most recent call last):"
    hasta el final. Si no existe, devuelve "".
    """
    needle = "Traceback (most recent call last):"
    idx = text.rfind(needle)
    if idx == -1:
        return ""
    return text[idx:].strip()


def extract_key_lines(text: str) -> List[str]:
    """
    Recoge líneas útiles: ERROR, Exception, Traceback, NameError, KeyError, etc.
    """
    patterns = [
        r"\bERROR\b",
        r"\bException\b",
        r"\bTraceback\b",
        r"\bNameError\b",
        r"\bKeyError\b",
        r"\bTypeError\b",
        r"\bValueError\b",
        r"\bAttributeError\b",
        r"\bImportError\b",
        r"\bModuleNotFoundError\b",
        r"\bAssertionError\b",
        r"\bCRITICAL\b",
    ]
    rx = re.compile("|".join(patterns))
    lines = []
    for ln in text.splitlines():
        if rx.search(ln):
            lines.append(ln.strip())
    # de-dup conservando orden y limitando
    seen = set()
    uniq = []
    for x in lines:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq[:80]


def local_clean(payload: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """
    Fallback si no hay cuota / no hay internet / key mala.
    Genera un JSON limpio “suficiente” con heurística básica.
    """
    raw = payload.get("raw_log_excerpt", "") or ""
    tb = extract_traceback_block(raw)
    key_lines = extract_key_lines(raw)

    status = "unknown"
    if tb:
        status = "fail"
    else:
        # si no hay señales de error, asumimos OK
        if not any("ERROR" in (k.upper()) for k in key_lines):
            status = "ok"

    tags = ["LOCAL_FALLBACK"]
    if "NameError" in (tb or ""):
        tags.append("PY_NAMEERROR")
    if "ModuleNotFoundError" in (tb or ""):
        tags.append("PY_MISSING_MODULE")
    if "KeyError" in (tb or ""):
        tags.append("PY_KEYERROR")
    if "TypeError" in (tb or ""):
        tags.append("PY_TYPEERROR")

    objectives_items = payload.get("objectives", {}).get("items", [])
    verdicts = []
    for obj in objectives_items:
        verdicts.append({"objective": obj, "result": "unknown", "notes": ""})

    return {
        "run": payload.get("run", {}),
        "hotfix_context": payload.get("hotfix_context", {}),
        "status": status,
        "tags": tags,
        "summary": "Depuración local (sin IA). " + (reason or "").strip(),
        "root_cause": "",
        "mechanism": "",
        "likely_fix": "",
        "confidence": 0.15,
        "objectives": {"items": objectives_items, "verdicts": verdicts},
        "evidence": {
            "traceback": tb,
            "key_lines": key_lines,
        },
        "meta": {"fallback_reason": reason},
    }


# -----------------------------
# OpenAI client + llamada (Responses API, Structured Outputs)
# -----------------------------
def load_openai_key(repo_root: Path, cred_path: Optional[Path] = None) -> str:
    """
    Lee credenciales.ia en repo_root (o cred_path).
    """
    p = cred_path if cred_path else (repo_root / CRED_FILE_NAME)
    if not p.exists():
        return ""
    raw = safe_read_text(p).strip()
    if not raw:
        return ""
    # JSON?
    if raw.startswith("{") and raw.endswith("}"):
        try:
            obj = json.loads(raw)
            for k in ("OPENAI_API_KEY", "openai_api_key", "api_key", "key"):
                if k in obj and isinstance(obj[k], str) and obj[k].strip():
                    return obj[k].strip()
        except Exception:
            pass
    # 1 línea
    return raw.splitlines()[0].strip()


def build_clean_schema() -> Dict[str, Any]:
    """
    JSON Schema para Structured Outputs.
    """
    return {
        "name": "rcs_clean_log",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "run",
                "hotfix_context",
                "status",
                "tags",
                "summary",
                "root_cause",
                "mechanism",
                "likely_fix",
                "confidence",
                "objectives",
                "evidence",
            ],
            "properties": {
                "run": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["start", "end", "duration_s", "rcs_exit_code"],
                    "properties": {
                        "start": {"type": "string"},
                        "end": {"type": "string"},
                        "duration_s": {"type": "number"},
                        "rcs_exit_code": {"type": "integer"},
                    },
                },
                "hotfix_context": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["latest_patch_version", "checklist_path"],
                    "properties": {
                        "latest_patch_version": {"type": "string"},
                        "checklist_path": {"type": "string"},
                    },
                },
                "status": {
                    "type": "string",
                    "enum": ["ok", "fail", "unknown"],
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "summary": {"type": "string"},
                "root_cause": {"type": "string"},
                "mechanism": {"type": "string"},
                "likely_fix": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "objectives": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["items", "verdicts"],
                    "properties": {
                        "items": {"type": "array", "items": {"type": "string"}},
                        "verdicts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["objective", "result", "notes"],
                                "properties": {
                                    "objective": {"type": "string"},
                                    "result": {
                                        "type": "string",
                                        "enum": ["pass", "fail", "unknown"],
                                    },
                                    "notes": {"type": "string"},
                                },
                            },
                        },
                    },
                },
                "evidence": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["traceback", "key_lines"],
                    "properties": {
                        "traceback": {"type": "string"},
                        "key_lines": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        },
    }


def call_openai_clean(payload: Dict[str, Any], model: str, api_key: str, verbose: bool) -> Dict[str, Any]:
    """
    Usa Responses API con Structured Outputs.
    """
    # Import diferido para que el script funcione aunque no esté instalado openai.
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=api_key)

    schema = build_clean_schema()

    system = (
        "Sos un depurador de logs de Python para un proyecto llamado RCS. "
        "Tu trabajo: eliminar ruido, extraer el error real, etiquetar causa/mecanismo, "
        "y mapear el resultado contra los objetivos del hotfix (checklist). "
        "No inventes hechos: si falta info, ponelo en 'unknown'. "
        "Salida estricta: JSON que cumpla el schema."
    )

    user = json.dumps(payload, ensure_ascii=False)

    if verbose:
        print(f"[{now_local_iso()}] IA: enviando payload (chars={len(user)}) al modelo {model}...")

    # Structured Outputs
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        text={
            "format": {
                "type": "json_schema",
                "strict": True,
                "schema": schema,
            }
        },
    )

    # En SDK moderno existe resp.output_text; si no, fallback best-effort.
    out_text = getattr(resp, "output_text", None)
    if not out_text:
        # Fallback: intentar extraer del primer bloque
        try:
            # resp.output[0].content[0].text (según estructura típica)
            out_text = resp.output[0].content[0].text  # type: ignore
        except Exception:
            out_text = ""

    if not out_text:
        raise RuntimeError("OpenAI devolvió respuesta vacía (sin output_text).")

    try:
        return json.loads(out_text)
    except Exception:
        # Si por alguna razón no viene puro JSON, intentar rescatar el bloque JSON.
        m = re.search(r"\{.*\}\s*$", out_text, flags=re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


# -----------------------------
# Runner principal
# -----------------------------
def run_rcs_app(repo_root: Path, max_runtime_s: int, verbose: bool) -> Tuple[int, str]:
    """
    Ejecuta la app y devuelve (exit_code, combined_stdout_stderr).
    Para GUI, normalmente stdout es poco, pero igual lo capturamos.
    """
    start = time.time()
    if verbose:
        print(f"[{now_local_iso()}] Ejecutando: {' '.join(APP_CMD)}  (cwd={repo_root})")

    # Popen para poder mostrar “sigue corriendo…”
    p = subprocess.Popen(
        APP_CMD,
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        bufsize=1,
        universal_newlines=True,
    )

    output_lines: List[str] = []
    last_ping = 0.0

    try:
        while True:
            line = p.stdout.readline() if p.stdout else ""
            if line:
                output_lines.append(line.rstrip("\n"))
            rc = p.poll()

            elapsed = time.time() - start
            if verbose and (time.time() - last_ping) > 3.0:
                last_ping = time.time()
                state = "RUNNING" if rc is None else f"EXIT({rc})"
                print(f"[{now_local_iso()}] RCS: {state}  elapsed={elapsed:.1f}s")

            if rc is not None:
                break

            if max_runtime_s > 0 and elapsed > max_runtime_s:
                if verbose:
                    print(f"[{now_local_iso()}] RCS: max-runtime alcanzado ({max_runtime_s}s). Terminando proceso…")
                p.terminate()
                try:
                    p.wait(timeout=10)
                except Exception:
                    p.kill()
                break

            time.sleep(0.05)

    except KeyboardInterrupt:
        if verbose:
            print(f"[{now_local_iso()}] Interrumpido por usuario. Terminando RCS…")
        p.terminate()
        try:
            p.wait(timeout=10)
        except Exception:
            p.kill()

    # Consumir lo que quede
    try:
        if p.stdout:
            rest = p.stdout.read()
            if rest:
                output_lines.extend(rest.splitlines())
    except Exception:
        pass

    rc = p.returncode if p.returncode is not None else -1
    combined = "\n".join(output_lines).strip()
    return rc, combined


def build_payload(
    run_start: str,
    run_end: str,
    duration_s: float,
    rcs_exit_code: int,
    objectives: HotfixObjectives,
    raw_log_excerpt: str,
    console_excerpt: str,
) -> Dict[str, Any]:
    return {
        "run": {
            "start": run_start,
            "end": run_end,
            "duration_s": round(duration_s, 3),
            "rcs_exit_code": int(rcs_exit_code),
        },
        "hotfix_context": {
            "latest_patch_version": objectives.version_folder if objectives.found else "",
            "checklist_path": objectives.checklist_path if objectives.found else "",
            "patch_base_path": objectives.base_path if objectives.found else "",
        },
        "objectives": {
            "items": objectives.objectives if objectives.found else [],
            "raw_checklist": objectives.raw_text if objectives.found else "",
        },
        "raw_log_excerpt": raw_log_excerpt,
        "console_excerpt": console_excerpt,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Runner + depurador IA de scs.log para RCS.")
    ap.add_argument("--repo-root", default=".", help="Raíz del repo (default: .)")
    ap.add_argument("--log", default=DEFAULT_LOG_NAME, help="Nombre del log de la app (default: scs.log)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Modelo OpenAI (default: {DEFAULT_MODEL})")
    ap.add_argument("--no-ai", action="store_true", help="No llamar a OpenAI; usar fallback local.")
    ap.add_argument("--max-runtime", type=int, default=0, help="Segundos máx. para RCS (0 = sin límite).")
    ap.add_argument("--verbose", action="store_true", help="Verbose.")
    ap.add_argument("--compact", action="store_true", help="JSON compacto (sin indent).")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    scs_log_path = repo_root / args.log
    raw_last_path = repo_root / RAW_LAST_NAME
    console_path = repo_root / ".probar.console.last.log"

    if args.verbose:
        print(f"[{now_local_iso()}] repo_root={repo_root}")
        print(f"[{now_local_iso()}] scs_log={scs_log_path}")

    # 1) Limpiar log actual ANTES de correr (para que el run sea “puro”).
    truncate_file(scs_log_path)

    # 2) Ejecutar app
    run_start_iso = now_local_iso()
    t0 = time.time()
    rcs_exit, console_out = run_rcs_app(repo_root, args.max_runtime, args.verbose)
    t1 = time.time()
    run_end_iso = now_local_iso()

    safe_write_text(console_path, console_out + ("\n" if console_out else ""))

    # 3) Leer log crudo
    raw_log = safe_read_text(scs_log_path)
    raw_log = strip_ansi(raw_log)

    # Guardar copia cruda del último run (sobre-escribe)
    safe_write_text(raw_last_path, raw_log + ("\n" if raw_log else ""))

    # 4) Preparar excerpt para IA (traceback si existe; si no, tail)
    if raw_log.strip():
        tb = extract_traceback_block(raw_log)
        raw_excerpt = tb if tb else tail_lines(raw_log, FALLBACK_TAIL_LINES)
    else:
        # fallback: si no hubo archivo, usar consola
        tb = extract_traceback_block(console_out)
        raw_excerpt = tb if tb else tail_lines(console_out, FALLBACK_TAIL_LINES)

    raw_excerpt = clamp_text_for_ai(raw_excerpt, MAX_CHARS_TO_AI)
    console_excerpt = clamp_text_for_ai(console_out, 15_000)

    # 5) Levantar objetivos del último hotfix
    objectives = find_latest_hotfix_objectives(repo_root)

    if args.verbose:
        print(f"[{now_local_iso()}] objectives.found={objectives.found}")
        if objectives.found:
            print(f"[{now_local_iso()}] latest_patch_version={objectives.version_folder}")
            print(f"[{now_local_iso()}] checklist={objectives.checklist_path}")
            print(f"[{now_local_iso()}] objectives_count={len(objectives.objectives)}")

    # 6) Payload
    payload = build_payload(
        run_start=run_start_iso,
        run_end=run_end_iso,
        duration_s=(t1 - t0),
        rcs_exit_code=rcs_exit,
        objectives=objectives,
        raw_log_excerpt=raw_excerpt,
        console_excerpt=console_excerpt,
    )

    # 7) IA / fallback
    cleaned: Dict[str, Any]
    if args.no_ai:
        cleaned = local_clean(payload, reason="--no-ai habilitado.")
    else:
        api_key = load_openai_key(repo_root)
        if not api_key:
            cleaned = local_clean(payload, reason=f"No se encontró {CRED_FILE_NAME} o está vacío.")
        else:
            try:
                if args.verbose:
                    print(f"[{now_local_iso()}] IA: iniciando llamada…")
                cleaned = call_openai_clean(payload, model=args.model, api_key=api_key, verbose=args.verbose)
            except Exception as e:
                # Si no hay cuota / 429 / etc, caemos a fallback pero NO dejamos el script “colgado”.
                err = f"{type(e).__name__}: {str(e)}"
                if args.verbose:
                    print(f"[{now_local_iso()}] IA: FALLÓ -> {err}")
                    print(traceback.format_exc())
                cleaned = local_clean(payload, reason=err)

    # 8) Reemplazar scs.log por el JSON limpio (lo que pediste: “reemplaza y depure”)
    if args.compact:
        out_json = json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))
    else:
        out_json = json.dumps(cleaned, ensure_ascii=False, indent=2)

    safe_write_text(scs_log_path, out_json + "\n")

    # 9) Resumen mínimo por consola (solo si verbose)
    if args.verbose:
        print(f"[{now_local_iso()}] Listo ✅ scs.log reemplazado por log depurado (JSON).")
        print(f"[{now_local_iso()}] status={cleaned.get('status')} tags={cleaned.get('tags')}")
        if cleaned.get("evidence", {}).get("traceback"):
            print(f"[{now_local_iso()}] traceback_detectado=SI")
        else:
            print(f"[{now_local_iso()}] traceback_detectado=NO")

    # exit code razonable:
    # - 0 si status ok
    # - 1 si fail/unknown
    return 0 if cleaned.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
