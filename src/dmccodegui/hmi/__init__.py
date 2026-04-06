"""HMI-controller integration package.

This package provides the single source of truth for all DMC variable names
and state encoding constants used by Python code that communicates with the
Galil DMC controller.
"""
from . import dmc_vars

__all__ = ["dmc_vars"]
