from __future__ import annotations

from typing import Iterable, List


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def try_float(text: str, default: float = 0.0) -> float:
    try:
        return float(text)
    except Exception:
        return default


def pulses_to_mm(pulses: float, counts_per_mm: float) -> float:
    return pulses / counts_per_mm if counts_per_mm else 0.0


def mm_to_pulses(mm: float, counts_per_mm: float) -> float:
    return mm * counts_per_mm


def format_units(value: float, unit: str) -> str:
    if unit == "mm":
        return f"{value:.3f} mm"
    if unit == "deg":
        return f"{value:.3f}°"
    return f"{value:.3f}"


def bit_is_set(bits: int, index: int) -> bool:
    return bool(bits & (1 << index))


def parse_number_list(s: str) -> List[float]:
    parts = s.replace("\r", " ").replace("\n", " ").split()
    out: List[float] = []
    for p in parts:
        try:
            out.append(float(p))
        except Exception:
            continue
    return out

