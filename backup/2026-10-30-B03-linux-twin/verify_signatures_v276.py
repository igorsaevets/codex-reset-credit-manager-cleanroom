"""Signature provenance + coverage check for the B-03 classifier tables.

Usage:
    python verify_signatures_v276.py <manager.py> <install_linux.py> [--ps1 <install.ps1> ...] [--report <path>]

Gating groups (exit 1 on failure):
  linux-provenance  every _LINUX_INSTALLER_SIGNATURES entry is a substring of
                    at least one real `raise InstallError(...)` message parsed
                    from install_linux.py (AST; f-string fields become {X}).
  linux-ambiguity   no real installer message is matched by signatures from
                    two different code buckets.
Informational:
  linux-coverage    how many distinct installer messages each code receives
                    and which ones still fall back to CHILD_INSTALL_FAILED.
  windows-provenance  each _INSTALLER_SIGNATURES entry found verbatim in every
                    given install.ps1 (v2.7.5 table; reported, not gating).
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib
import sys


def load_manager(path: str):
    spec = importlib.util.spec_from_file_location("mgr_sig_check", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mgr_sig_check"] = mod
    spec.loader.exec_module(mod)
    return mod


def _render(expr: ast.expr) -> str:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    if isinstance(expr, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{X}" for v in expr.values)
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        return _render(expr.left) + _render(expr.right)
    return "{X}"


def installer_messages(path: str) -> list[tuple[int, str]]:
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    found: dict[str, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        func = node.exc.func
        if isinstance(func, ast.Name) and func.id == "InstallError" and node.exc.args:
            text = _render(node.exc.args[0])
            found.setdefault(text, node.lineno)
    return sorted(((line, text) for text, line in found.items()), key=lambda item: item[0])


def main(argv: list[str]) -> int:
    manager_path, installer_path = argv[0], argv[1]
    ps1_paths: list[str] = []
    report_path = None
    rest = argv[2:]
    while rest:
        flag = rest.pop(0)
        if flag == "--ps1":
            ps1_paths.append(rest.pop(0))
        elif flag == "--report":
            report_path = rest.pop(0)
        else:
            raise SystemExit(f"unknown argument {flag}")

    mod = load_manager(manager_path)
    messages = installer_messages(installer_path)
    buckets = [(code, tuple(sigs)) for code, sigs in mod._LINUX_INSTALLER_SIGNATURES]
    failed = False

    dead = [(code, sig) for code, sigs in buckets for sig in sigs
            if not any(sig in text for _, text in messages)]
    print(f"install_linux.py distinct InstallError messages: {len(messages)}")
    print(f"linux signatures: {sum(len(s) for _, s in buckets)}")
    if dead:
        failed = True
        print("  linux-provenance: FAIL")
        for code, sig in dead:
            print(f"    dead signature [{code}]: {sig!r}")
    else:
        print("  linux-provenance: pass (every signature occurs in a real installer message)")

    ambiguous = []
    for line, text in messages:
        hit = {code for code, sigs in buckets if any(sig in text for sig in sigs)}
        if len(hit) > 1:
            ambiguous.append((line, text, sorted(hit)))
    if ambiguous:
        failed = True
        print("  linux-ambiguity: FAIL")
        for line, text, hit in ambiguous:
            print(f"    line {line} matched {hit}: {text!r}")
    else:
        print("  linux-ambiguity: pass (no message matched by two buckets)")

    tally: dict[str, int] = {}
    rows = []
    for line, text in messages:
        code = mod._classify_linux_installer_stderr("error: " + text)
        tally[code] = tally.get(code, 0) + 1
        rows.append(f"{line:5d}  {code:24s}  {text}")
    classified = len(messages) - tally.get("CHILD_INSTALL_FAILED", 0)
    print(f"  linux-coverage: {classified} of {len(messages)} messages get a specific code; "
          + ", ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    if report_path:
        pathlib.Path(report_path).write_text(
            "line   code                      install_linux.py message ({X} = f-string field)\n"
            + "\n".join(rows) + "\n",
            encoding="utf-8",
        )
        print(f"  full mapping written to {report_path}")

    for ps1 in ps1_paths:
        text = pathlib.Path(ps1).read_text(encoding="utf-8-sig")
        missing = [(code, sig) for code, sigs in mod._INSTALLER_SIGNATURES for sig in sigs if sig not in text]
        total = sum(len(s) for _, s in mod._INSTALLER_SIGNATURES)
        print(f"  windows-provenance [{pathlib.Path(ps1).name}]: {total - len(missing)} of {total} found verbatim")
        for code, sig in missing:
            print(f"    not verbatim [{code}]: {sig!r}")

    print("RESULT: FAIL" if failed else "RESULT: PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
