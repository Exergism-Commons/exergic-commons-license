#!/usr/bin/env python3
"""Isolated bootstrap for the content-addressed Schedule renderer.

The executable renderer is intentionally fail-closed.  It must be launched as
``python -I -S tools/render_schedule.py`` so repository paths, ``PYTHONPATH``,
user-site packages, ``sitecustomize`` and ``.pth`` processing cannot run before
the reviewed renderer imports are resolved.  Internal regression tests may
import this bootstrap only from an already isolated (``-I``) interpreter.
"""

from __future__ import annotations

import sys

_WRAPPER_PATH = __file__.replace("\\", "/")
_WRAPPER_DIR = _WRAPPER_PATH.rsplit("/", 1)[0]
_IMPL_PATH = f"{_WRAPPER_DIR}/render_schedule_impl.py"
_ORIGINAL_NAME = globals().get("__name__", "render_schedule")
_ORIGINAL_SPEC = globals().get("__spec__")
_ORIGINAL_SYS_PATH = list(sys.path)


def _fail_bootstrap(message: str) -> None:
    raise RuntimeError(message)


def _normalise_absolute_path(entry: str) -> str | None:
    """Lexically normalise an absolute import path without importing path code."""

    if not isinstance(entry, str) or not entry:
        return None
    value = entry.replace("\\", "/")
    drive = ""
    if sys.platform == "win32":
        if len(value) < 3 or value[1] != ":" or value[2] != "/":
            return None
        drive = value[:2].lower()
        value = value[2:]
    elif not value.startswith("/"):
        return None

    parts: list[str] = []
    for part in value.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
            continue
        parts.append(part.lower() if sys.platform == "win32" else part)
    suffix = "/".join(parts)
    return f"{drive}/{suffix}" if drive else f"/{suffix}"


def _is_within(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix.rstrip("/") + "/")


# No shadowable import is permitted before these gates.  Non-isolated script,
# package/module (``python -m``), PYTHONPATH-driven, and ordinary host imports
# fail before the renderer implementation can import argparse/hashlib/pathlib,
# PyYAML, or any of their dependencies.
if not sys.flags.isolated:
    _fail_bootstrap(
        "Schedule renderer requires isolated Python; run executable mode as "
        "`python -I -S tools/render_schedule.py ...`"
    )
if _ORIGINAL_NAME == "__main__" and not sys.flags.no_site:
    _fail_bootstrap(
        "Schedule renderer executable mode requires site-disabled isolation; run "
        "`python -I -S tools/render_schedule.py ...`"
    )

# Keep only interpreter-owned import roots.  Under -I this excludes cwd,
# PYTHONPATH, the script directory, and user-site paths.  The lexical collapse
# also rejects ``..`` aliases that would otherwise appear to live below an
# interpreter prefix.  A repository cannot create a symlink inside an
# interpreter-owned prefix without already controlling the trusted runtime.
_trusted_prefixes: list[str] = []
for _prefix in (
    sys.prefix,
    sys.base_prefix,
    sys.exec_prefix,
    sys.base_exec_prefix,
):
    _normalised = _normalise_absolute_path(_prefix)
    if _normalised and _normalised not in _trusted_prefixes:
        _trusted_prefixes.append(_normalised)

_sanitised_path: list[str] = []
for _entry in sys.path:
    _normalised = _normalise_absolute_path(_entry)
    if _normalised and any(
        _is_within(_normalised, _prefix) for _prefix in _trusted_prefixes
    ):
        _sanitised_path.append(_entry)
sys.path[:] = _sanitised_path

# ``-S`` deliberately omits site-packages.  Add exactly the interpreter's own
# site-packages directory so the separately pinned PyYAML dependency remains
# available without processing site.py, .pth files, user-site, or repository
# paths.  The renderer later verifies PyYAML == 6.0.3 and hash-binds its pin.
if _ORIGINAL_NAME == "__main__":
    if sys.platform == "win32":
        _site_packages = f"{sys.prefix.replace(chr(92), '/')}/Lib/site-packages"
    else:
        _site_packages = (
            f"{sys.prefix.replace(chr(92), '/')}/lib/"
            f"python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
        )
    _site_normalised = _normalise_absolute_path(_site_packages)
    if not _site_normalised or not any(
        _is_within(_site_normalised, _prefix) for _prefix in _trusted_prefixes
    ):
        _fail_bootstrap("Schedule renderer derived an untrusted site-packages path")
    sys.path.append(_site_packages)

_globals = globals()
_globals["__file__"] = _IMPL_PATH
_globals["__name__"] = "_ecl_render_schedule_impl"
_globals["__spec__"] = None
try:
    with open(_IMPL_PATH, "r", encoding="utf-8") as _handle:
        _source = _handle.read()
    exec(compile(_source, _IMPL_PATH, "exec"), _globals)
finally:
    _globals["__name__"] = _ORIGINAL_NAME
    _globals["__spec__"] = _ORIGINAL_SPEC

_impl_control_paths = schedule_renderer_control_paths
_impl_validate_environment = validate_renderer_environment


def _repository_local_module(label, module) -> None:
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str) or not origin:
        raise ValueError(f"Schedule renderer cannot verify imported {label} origin")
    origin_path = Path(origin).resolve()
    try:
        origin_path.relative_to(ROOT)
    except ValueError:
        return
    raise ValueError(
        f"Schedule renderer refuses repository-local shadowing of imported {label}: {origin_path}"
    )


def validate_renderer_environment() -> None:
    """Fail closed if a supported isolated run still resolves local shadows."""

    _repository_local_module("argparse", argparse)
    _repository_local_module("hashlib", hashlib)
    _repository_local_module("re", re)
    _repository_local_module("yaml", yaml)
    _impl_validate_environment()


def schedule_renderer_control_paths() -> list[Path]:
    """Bind both the bootstrap and implementation as material renderer code."""

    paths = list(_impl_control_paths())
    wrapper = Path(_WRAPPER_PATH).resolve()
    if wrapper not in {path.resolve() for path in paths}:
        paths.append(wrapper)
    return paths


if _ORIGINAL_NAME == "__main__":
    main()
