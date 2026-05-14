"""
agent_h — the meta-package that re-exports every \\agenth{} subsystem
under a single Python namespace.

Usage
-----
    >>> from agent_h import lapidary, homer, shell, bankroll
    >>> from agent_h import Task, finetune_agent, cometh_rollout
    >>> from agent_h import LLMClient, Agent, Ledger

Each sub-package is loaded lazily on first attribute access, so importing
``agent_h`` itself is cheap and does NOT require every subsystem to be
installed. If you reference ``agent_h.foo`` and ``foo`` is not installed,
you get a clear ``AgentHMissingDependency`` error naming the pip target.

The full list of subsystems is :data:`SUBSYSTEMS`. The convenience
re-exports (``Task``, ``Agent``, ``LLMClient``, ``Ledger``, ``Searcher``,
``finetune_agent``, ``cometh_rollout``, ``replay``, ...) are listed in
:data:`__all__`.
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any

__version__ = "0.1.0"

# --- registry of subsystems ---------------------------------------------------

#: All 19 \agenth{} subsystems and the pip target that installs each.
SUBSYSTEMS: dict[str, str] = {
    # Production tier
    "shell":      "git+https://github.com/thehalleyyoung/shell",
    "homer":      "git+https://github.com/thehalleyyoung/homer",
    "looper":     "git+https://github.com/thehalleyyoung/looper",
    "bankroll":   "git+https://github.com/thehalleyyoung/bankroll",
    "mnemos":     "git+https://github.com/thehalleyyoung/mnemos",
    "stepback":   "git+https://github.com/thehalleyyoung/stepback",
    "flowwarden": "git+https://github.com/thehalleyyoung/flowwarden",
    "toolforge":  "git+https://github.com/thehalleyyoung/toolforge",
    "adversary":  "git+https://github.com/thehalleyyoung/adversary",
    "rerun":      "git+https://github.com/thehalleyyoung/rerun",
    "ragdoctor":  "git+https://github.com/thehalleyyoung/ragdoctor",
    "cartograph": "git+https://github.com/thehalleyyoung/cartograph",
    "manyworlds": "git+https://github.com/thehalleyyoung/manyworlds",
    "distill":    "git+https://github.com/thehalleyyoung/distill",
    "atelier":    "git+https://github.com/thehalleyyoung/atelier",
    "kiln":       "git+https://github.com/thehalleyyoung/kiln",
    "crucible":   "git+https://github.com/thehalleyyoung/crucible",
    # Comet-H tier
    "coevo":      "git+https://github.com/thehalleyyoung/coevo",
    "groundwork": "git+https://github.com/thehalleyyoung/groundwork",
    # Finetuning tier (the contract)
    "lapidary":   "git+https://github.com/thehalleyyoung/lapidary",
}


class AgentHMissingDependency(ImportError):
    """Raised when a subsystem the user accessed is not installed."""

    def __init__(self, name: str, pip_target: str | None = None):
        target = pip_target or SUBSYSTEMS.get(name, name)
        msg = (
            f"agent-h subsystem `{name}` is not installed.\n"
            f"  pip install {target}\n"
            f"or install the whole stack with `make install-all` from the agent-h repo."
        )
        super().__init__(msg)
        self.name = name
        self.pip_target = target


# --- lazy loader --------------------------------------------------------------

_loaded: dict[str, ModuleType] = {}


def _load(name: str) -> ModuleType:
    if name in _loaded:
        return _loaded[name]
    if name not in SUBSYSTEMS:
        raise AttributeError(f"agent_h has no attribute {name!r}")
    try:
        mod = importlib.import_module(name)
    except ImportError as e:
        raise AgentHMissingDependency(name) from e
    _loaded[name] = mod
    return mod


def __getattr__(name: str) -> Any:
    # Sub-package access: agent_h.lapidary, agent_h.homer, ...
    if name in SUBSYSTEMS:
        return _load(name)
    # Convenience symbol re-exports: agent_h.Task, agent_h.finetune_agent, ...
    if name in _CONVENIENCE_MAP:
        sub, attr = _CONVENIENCE_MAP[name]
        return getattr(_load(sub), attr)
    raise AttributeError(f"module 'agent_h' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(SUBSYSTEMS) | set(_CONVENIENCE_MAP))


# --- convenience symbol map ---------------------------------------------------
#
# The most commonly-used public symbols from each subsystem, surfaced at the
# top level so a user can write `from agent_h import Task, Agent, LLMClient`
# without remembering which subsystem owns each one.
#
# Format: top-level name -> (subsystem, attr-in-subsystem)
_CONVENIENCE_MAP: dict[str, tuple[str, str]] = {
    # --- lapidary (the contract) ---
    "Task":                  ("lapidary", "Task"),
    "Searcher":              ("lapidary", "Searcher"),
    "Reasoner":              ("lapidary", "Reasoner"),
    "Store":                 ("lapidary", "Store"),
    "ChoiceParam":           ("lapidary", "ChoiceParam"),
    "NumberParam":           ("lapidary", "NumberParam"),
    "BoolParam":             ("lapidary", "BoolParam"),
    "TextParam":             ("lapidary", "TextParam"),
    "FilenameParam":         ("lapidary", "FilenameParam"),
    "PromptParam":           ("lapidary", "PromptParam"),
    "Preferences":           ("lapidary", "Preferences"),
    "compile_preferences":   ("lapidary", "compile_preferences"),
    "apply_preferences":     ("lapidary", "apply_preferences"),
    # finetuning surface
    "AgentPolicy":           ("lapidary", "AgentPolicy"),
    "cometh_policy_schema":  ("lapidary", "cometh_policy_schema"),
    "Trajectory":            ("lapidary", "Trajectory"),
    "TrajectoryStep":        ("lapidary", "TrajectoryStep"),
    "TrajectoryOutcome":     ("lapidary", "TrajectoryOutcome"),
    "CurriculumRunner":      ("lapidary", "CurriculumRunner"),
    "Stage":                 ("lapidary", "Stage"),
    "default_curriculum":    ("lapidary", "default_curriculum"),
    "find_neighbours":       ("lapidary", "find_neighbours"),
    "transferred_defaults":  ("lapidary", "transferred_defaults"),
    "BootstrapMutator":      ("lapidary", "BootstrapMutator"),
    "auto_distill":          ("lapidary", "auto_distill"),
    "FinetuneReport":        ("lapidary", "FinetuneReport"),
    "finetune_agent":        ("lapidary", "finetune_agent"),
    "cometh_rollout":        ("lapidary", "cometh_rollout"),
    "join_schemas":          ("lapidary", "join_schemas"),

    # --- shell ---
    "LLMClient":             ("shell",   "LLMClient"),

    # --- homer ---
    "Agent":                 ("homer",   "Agent"),

    # --- bankroll ---
    "Ledger":                ("bankroll", "Ledger"),
    "BankrollExceeded":      ("bankroll", "BankrollExceeded"),

    # --- mnemos ---
    "recall":                ("mnemos",  "recall"),
    "remember":              ("mnemos",  "remember"),

    # --- stepback ---
    "replay":                ("stepback", "replay"),
    "recorder":              ("stepback", "recorder"),

    # --- flowwarden ---
    "TaintLabel":            ("flowwarden", "TaintLabel"),

    # --- toolforge ---
    "ToolRegistry":          ("toolforge", "Registry"),
    "tool":                  ("toolforge", "tool"),

    # --- looper ---
    "durable_session":       ("looper",  "durable_session"),

    # --- crucible ---
    "grade_codebase":        ("crucible", "grade_codebase"),

    # --- coevo ---
    "intent_hash":           ("coevo",   "intent_hash"),
    "PromptFamily":          ("coevo",   "PromptFamily"),
    "EcosystemScorer":       ("coevo",   "EcosystemScorer"),

    # --- groundwork ---
    "record_claim":          ("groundwork", "record_claim"),

    # --- manyworlds ---
    "fork":                  ("manyworlds", "fork"),

    # --- distill (sibling, not lapidary.distill) ---
    "HierarchicalCompactor": ("distill", "HierarchicalCompactor"),

    # --- cartograph ---
    "symbol_graph":          ("cartograph", "symbol_graph"),
}


__all__ = [
    "__version__",
    "SUBSYSTEMS",
    "AgentHMissingDependency",
    *sorted(_CONVENIENCE_MAP),
]
