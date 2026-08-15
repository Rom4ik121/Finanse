"""Enable Android core library desugaring for flutter_local_notifications.

Idempotent. Supports Groovy ``build.gradle`` and Kotlin ``build.gradle.kts``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DESUGAR_DEP_GROOVY = (
    "coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.4'"
)
DESUGAR_DEP_KTS = (
    'coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")'
)


def _patch_kts(text: str) -> str:
    if "isCoreLibraryDesugaringEnabled" not in text:
        text = re.sub(
            r"(compileOptions\s*\{)",
            r"\1\n        isCoreLibraryDesugaringEnabled = true",
            text,
            count=1,
        )
    if "multiDexEnabled" not in text:
        text = re.sub(
            r"(defaultConfig\s*\{)",
            r"\1\n        multiDexEnabled = true",
            text,
            count=1,
        )
    if "desugar_jdk_libs" not in text:
        if re.search(r"dependencies\s*\{\s*\}", text):
            text = re.sub(
                r"dependencies\s*\{\s*\}",
                "dependencies {\n    " + DESUGAR_DEP_KTS + "\n}",
                text,
                count=1,
            )
        elif re.search(r"dependencies\s*\{", text):
            text = re.sub(
                r"(dependencies\s*\{)",
                r"\1\n    " + DESUGAR_DEP_KTS,
                text,
                count=1,
            )
        else:
            text = text.rstrip() + "\n\ndependencies {\n    " + DESUGAR_DEP_KTS + "\n}\n"
    return text


def _patch_groovy(text: str) -> str:
    if "coreLibraryDesugaringEnabled" not in text:
        text = re.sub(
            r"(compileOptions\s*\{)",
            r"\1\n        coreLibraryDesugaringEnabled true",
            text,
            count=1,
        )
    if "multiDexEnabled" not in text:
        text = re.sub(
            r"(defaultConfig\s*\{)",
            r"\1\n        multiDexEnabled true",
            text,
            count=1,
        )
    if "desugar_jdk_libs" not in text:
        if re.search(r"dependencies\s*\{\s*\}", text):
            text = re.sub(
                r"dependencies\s*\{\s*\}",
                "dependencies {\n    " + DESUGAR_DEP_GROOVY + "\n}",
                text,
                count=1,
            )
        elif re.search(r"dependencies\s*\{", text):
            text = re.sub(
                r"(dependencies\s*\{)",
                r"\1\n    " + DESUGAR_DEP_GROOVY,
                text,
                count=1,
            )
        else:
            text = text.rstrip() + "\n\ndependencies {\n    " + DESUGAR_DEP_GROOVY + "\n}\n"
    return text


def patch_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    if path.name.endswith(".kts"):
        updated = _patch_kts(original)
    else:
        updated = _patch_groovy(original)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        default="build/flutter",
        help="Flet Flutter project root (default: build/flutter)",
    )
    args = parser.parse_args()
    root = Path(args.project_root)
    candidates = [
        root / "android" / "app" / "build.gradle.kts",
        root / "android" / "app" / "build.gradle",
    ]
    target = next((p for p in candidates if p.is_file()), None)
    if target is None:
        print(f"No app build.gradle(.kts) under {root}", file=sys.stderr)
        return 1
    changed = patch_file(target)
    print(("Patched" if changed else "Already patched") + f": {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
