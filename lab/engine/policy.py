"""Politique effective : plancher monotone ⊕ overrides, clé par clé (design ADR-13).

Les profils sont des données (``policy_profiles.toml``). Une instance choisit un plancher
(``profile``) et peut le durcir, jamais l'assouplir (INV-2) ; les clés libres sont réglables.
``[overrides.routes]`` valide R1..R7 (INV-3) mais n'est appliqué qu'à partir de l'itération 3.
Aucune clé ne concerne le merge (INV-5).
"""

from __future__ import annotations

import math
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROFILES_TOML = Path(__file__).resolve().parent / "policy_profiles.toml"
PROFILE_NAMES = ("solo", "squad", "regulated")
ROUTES = ("R1", "R2", "R3", "R4", "R5", "R6", "R7")
ROUTE_MODES = ("auto", "proposal", "human")
NO_AUTO_ROUTES = ("R2", "R3", "R4", "R5")  # INV-3
ROUTES_NOTE = "applied from iteration 3"

FLOOR = "floor"
OVERRIDE = "override"
OVERRIDE_FREE = "override (free key)"


class PolicyError(Exception):
    """Invalid policy: the command ends rc 1."""


def load_profiles() -> dict[str, dict]:
    try:
        data = tomllib.loads(PROFILES_TOML.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise PolicyError(f"cannot read {PROFILES_TOML}: {e}") from None
    if data.pop("schema_version", None) != 1:
        raise PolicyError(f"{PROFILES_TOML}: unsupported schema_version")
    return data


def show(value) -> str:
    if value is None:
        return "undeclared"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_type(key: str, value, spec: dict) -> None:
    sample = next((spec[p] for p in PROFILE_NAMES if p in spec), None)
    ok = isinstance(value, bool) if isinstance(sample, bool) else _is_number(value)
    if not ok:
        raise PolicyError(f"{key}={show(value)} has the wrong type")


# BHV-3d: free-key bounds — key -> (integer only, minimum)
BOUNDS = {
    "max_task_attempts": (True, 1),
    "max_parallel": (True, 1),
    "max_cp_rejects": (True, 1),
    "budget_usd": (False, 0),
}


def _check_bounds(key: str, value) -> None:
    if key not in BOUNDS:
        return
    integer, minimum = BOUNDS[key]
    kind = "an integer " if integer else "a finite number "
    bound = f"must be {kind}>= {minimum}"
    if integer and not isinstance(value, int):
        raise PolicyError(f"{key}={show(value)} is out of bounds ({bound})")
    if not integer and not math.isfinite(value):  # nan < 0 is False: test explicitly
        raise PolicyError(f"{key}={show(value)} is out of bounds ({bound})")
    if value < minimum:
        raise PolicyError(f"{key}={show(value)} is out of bounds ({bound})")


def _looser(strict: str, value, floor) -> bool:
    if floor is None:  # undeclared floor: nothing to be looser than
        return False
    if strict == "true":  # looser only if the floor demands true and the value is false
        return floor is True and value is False
    if strict == "false":
        return floor is False and value is True
    if strict == "up":
        return value < floor
    if strict == "down":
        return value > floor
    raise PolicyError(f"unknown strict direction {strict!r}")


def effective_policy(lab_toml: dict) -> dict[str, tuple[object, str]]:
    """``{key: (value, origin)}``, origin ∈ {floor, override, override (free key)}.

    Overridden routes appear as ``routes.Rn`` (origin ``override``): validated, not applied yet.
    """
    profiles = load_profiles()
    profile = lab_toml.get("profile")
    if profile not in PROFILE_NAMES:
        raise PolicyError(f"profile {profile!r} not in {', '.join(PROFILE_NAMES)}")
    overrides = lab_toml.get("overrides", {})
    if not isinstance(overrides, dict):
        raise PolicyError("[overrides] must be a table")
    overrides = dict(overrides)
    routes = overrides.pop("routes", {})
    if not isinstance(routes, dict):
        raise PolicyError("[overrides.routes] must be a table")

    for key in overrides:
        if key not in profiles:
            raise PolicyError(f"unknown policy key {key!r}")
    for route in routes:
        if route not in ROUTES:
            raise PolicyError(f"unknown route {route!r} in [overrides.routes]")

    result: dict[str, tuple[object, str]] = {}
    for key, spec in profiles.items():
        floor = spec.get(profile)
        if key not in overrides:
            result[key] = (floor, FLOOR)
            continue
        value = overrides[key]
        _check_type(key, value, spec)
        if spec["kind"] == "free":
            _check_bounds(key, value)
            result[key] = (value, OVERRIDE_FREE)
            continue
        if _looser(spec["strict"], value, floor):
            raise PolicyError(
                f"{key}={show(value)} is looser than floor '{profile}' ({show(floor)})"
            )
        result[key] = (value, OVERRIDE)

    for route, mode in routes.items():
        if mode not in ROUTE_MODES:
            raise PolicyError(
                f"route {route}={mode!r}: mode must be one of {', '.join(ROUTE_MODES)}"
            )
        if mode == "auto" and route in NO_AUTO_ROUTES:
            raise PolicyError(
                f"route {route}=auto is refused: {route} is never automatic (INV-3)"
            )
        result[f"routes.{route}"] = (mode, OVERRIDE)
    return result


def format_policy(policy: dict[str, tuple[object, str]]) -> list[str]:
    lines = []
    for key, (value, origin) in policy.items():
        note = f" [{ROUTES_NOTE}]" if key.startswith("routes.") else ""
        lines.append(f"{key} = {show(value)}  ({origin}){note}")
    return lines
