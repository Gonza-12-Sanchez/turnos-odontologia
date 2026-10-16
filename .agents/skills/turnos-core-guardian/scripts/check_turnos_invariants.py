"""Check determinista de invariantes C-02 (sin DB).
Uso: python check_turnos_invariants.py [dir_modelos] [dir_migraciones]
Sale 0 + OK si pasa; 1 + lista de violaciones si falla.
No lee secretos ni toca la DB.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

FAIL: list[str] = []

def scan(path: Path, pattern: str, label: str, allow: bool = False) -> None:
    if not path.exists():
        return
    files = [path] if path.is_file() else list(path.rglob("*.py"))
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(pattern, line):
                FAIL.append(f"{label}: {f}:{i}: {line.strip()[:160]}")
                if not allow:
                    pass

def main() -> int:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("backend/app/models")
    mig = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("backend/alembic/versions")
    # 1. Fechas naive: DateTime( sin timezone=True
    scan(base, r"DateTime\s*\(\s*\)", "FECHA-NAIVE DateTime() sin timezone=True")
    scan(mig, r"sa\.DateTime\s*\(\s*\)", "FECHA-NAIVE sa.DateTime() sin timezone")
    # 2. Dinero en float / money
    scan(base, r"Column\s*\(\s*Float", "DINERO-FLOAT prohibido, usar centavos INTEGER")
    scan(base, r"\bMONEY\b", "DINERO-MONEY prohibido")
    scan(mig, r"sa\.Float", "DINERO-FLOAT en migracion")
    scan(mig, r"\bMONEY\b", "DINERO-MONEY en migracion")
    # 3. EXCLUDE sin btree_gist (si hay ExcludeConstraint, exigir extension en migraciones)
    has_exclude = False
    for root in (base, mig):
        if not root.exists():
            continue
        for f in root.rglob("*.py"):
            t = f.read_text(encoding="utf-8", errors="ignore")
            if "ExcludeConstraint" in t or "EXCLUDE USING GIST" in t:
                has_exclude = True
    if has_exclude:
        found = False
        if mig.exists():
            for f in mig.rglob("*.py"):
                if "btree_gist" in f.read_text(encoding="utf-8", errors="ignore"):
                    found = True
        if not found:
            FAIL.append("EXCLUDE sin btree_gist: hay ExcludeConstraint pero ninguna migracion crea la extension")
    # 4. Datos reales sospechosos en seeds/fixtures (heuristica simple)
    for extra in ("backend/app/db", "backend/alembic"):
        p = Path(extra)
        if not p.exists():
            continue
        for f in p.rglob("*.py"):
            t = f.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"@gmail\.com|@hotmail\.com|DNI\s*\d{7,8}", t):
                FAIL.append(f"SEED-SOSPECHOSO dato posiblemente real en {f} (usar @example.com ficticio)")
    if FAIL:
        print("BLOQUEADO por turnos-core-guardian:")
        for x in FAIL:
            print(" -", x)
        return 1
    if not has_exclude:
        print("OK parcial turnos-core-guardian: sin fechas naive, sin float/money, seeds OK; EXCLUDE aún no presente (C-02 pendiente)")
        return 0
    print("OK turnos-core-guardian: sin fechas naive, sin float/money, EXCLUDE con btree_gist, seeds OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
