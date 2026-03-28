"""End-to-end redesign plan pipeline.

Loads a plan from plans/, resolves all entity references via FieldlinkResolver,
validates against schema, runs geometric coherence checks, and produces a
structured execution report.

Usage:
    from src.pipeline import Pipeline
    p = Pipeline(clone_base="/tmp")
    report = p.run("plans/energy_grid.example.json")
    p.print_report(report)
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
from typing import Any

from src.resolver import FieldlinkResolver

ROOT = pathlib.Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Golden ratio constants (stdlib-only, no numpy dependency)
# ---------------------------------------------------------------------------

PHI = (math.sqrt(5) - 1) / 2  # ~0.618
PHI_INV = (math.sqrt(5) + 1) / 2  # ~1.618
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]


def _phi_coherence(values: list[float], tolerance: float = 0.1) -> dict:
    """Stdlib-only geometric coherence check on a list of values.

    Mirrors Shadow-Hunting's detect_phi_ratios + detect_geometric_coherence
    but without numpy dependency.
    """
    if len(values) < 2:
        return {"coherence": 0.0, "phi_matches": 0, "total_ratios": 0,
                "enrichment": 0.0, "interpretation": "INSUFFICIENT_DATA"}

    ratios = []
    phi_matches = 0
    for i in range(len(values) - 1):
        if abs(values[i]) > 1e-10:
            ratio = values[i + 1] / values[i]
            ratios.append(ratio)
            if abs(ratio - PHI) < tolerance or abs(ratio - PHI_INV) < tolerance:
                phi_matches += 1

    if not ratios:
        return {"coherence": 0.0, "phi_matches": 0, "total_ratios": 0,
                "enrichment": 0.0, "interpretation": "NO_RATIOS"}

    # Enrichment vs random expectation
    random_prob = 2 * tolerance
    expected = len(ratios) * random_prob
    enrichment = phi_matches / expected if expected > 0 else 0.0

    # Shannon entropy (simplified, on ratio distribution)
    n = len(ratios)
    # Bin ratios into 10 buckets for entropy calculation
    bins = [0] * 10
    for r in ratios:
        idx = min(int(abs(r) * 2), 9)  # crude binning
        bins[idx] += 1

    entropy = 0.0
    for count in bins:
        if count > 0:
            p = count / n
            entropy -= p * math.log2(p)
    max_entropy = math.log2(10)
    norm_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

    coherence = (1 - norm_entropy) * (1 + enrichment)
    if coherence > 1.5:
        interp = "HIGH"
    elif coherence > 0.8:
        interp = "MODERATE"
    else:
        interp = "LOW"

    return {
        "coherence": round(coherence, 4),
        "phi_matches": phi_matches,
        "total_ratios": len(ratios),
        "enrichment": round(enrichment, 4),
        "interpretation": interp,
    }


# ---------------------------------------------------------------------------
# Decay functions (from the spin engine spec)
# ---------------------------------------------------------------------------

def _decay(policy: str, initial: float, pass_idx: int, total_passes: int) -> float:
    """Apply a decay policy to a signal weight."""
    t = pass_idx / max(total_passes - 1, 1)  # normalized 0→1
    if policy == "exponential":
        return initial * math.exp(-3 * t)
    elif policy == "linear":
        return initial * (1 - t)
    elif policy == "resonate":
        # Damped sinusoidal — signal pulses but decays
        return initial * math.cos(2 * math.pi * t) * math.exp(-t)
    return initial


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class Pipeline:
    """End-to-end plan execution pipeline."""

    def __init__(
        self,
        fieldlink_path: str | pathlib.Path | None = None,
        clone_base: str | pathlib.Path | None = None,
    ):
        fieldlink_path = pathlib.Path(
            fieldlink_path or ROOT / ".fieldlink.json"
        )
        self.resolver = FieldlinkResolver(
            fieldlink_path, clone_base=clone_base
        )

    def run(self, plan_path: str | pathlib.Path) -> dict:
        """Execute the full pipeline on a plan file. Returns a report dict."""
        plan_path = pathlib.Path(plan_path)
        if not plan_path.is_absolute():
            plan_path = ROOT / plan_path

        # 1. Load plan
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        report: dict[str, Any] = {
            "plan_id": plan.get("id", "unknown"),
            "goal": plan.get("goal", ""),
            "phases": [],
            "resolution": {},
            "bridges": {},
            "coherence": {},
            "spin": {},
            "guardrails": plan.get("guardrails", []),
            "status": "OK",
            "errors": [],
        }

        # 2. Validate structure
        errors = self._validate_structure(plan)
        if errors:
            report["errors"].extend(errors)
            report["status"] = "VALIDATION_FAILED"
            return report

        # 3. Resolve all entity references
        inputs = plan.get("inputs", {})
        all_ids = (
            inputs.get("shapes", [])
            + inputs.get("sensors", [])
            + inputs.get("defenses", [])
            + inputs.get("protocols", [])
        )

        resolved = {}
        unresolved = []
        for eid in all_ids:
            data = self.resolver.resolve(eid)
            if data:
                resolved[eid] = data
            else:
                unresolved.append(eid)

        report["resolution"] = {
            "total": len(all_ids),
            "resolved": len(resolved),
            "unresolved": unresolved,
            "entities": {eid: _summarize(data) for eid, data in resolved.items()},
        }

        # 4. Resolve bridges for shapes
        for shape_id in inputs.get("shapes", []):
            bridge = self.resolver.resolve_bridge(shape_id)
            if bridge:
                report["bridges"][shape_id] = {
                    "families": bridge.get("families", []),
                    "sensors": bridge.get("sensors", []),
                    "defenses": bridge.get("defense_names", []),
                    "protocols": bridge.get("protocols", []),
                    "polyhedral": bridge.get("polyhedral", {}),
                }

        # 5. Geometric coherence check on resolved shapes
        shape_data = [resolved[s] for s in inputs.get("shapes", []) if s in resolved]
        if shape_data:
            # Build a numeric vector from shape properties for coherence check
            values = []
            for s in shape_data:
                values.extend([
                    float(s.get("faces", 0)),
                    float(s.get("edges", 0)),
                    float(s.get("vertices", 0)),
                ])
            report["coherence"] = _phi_coherence(values)
        else:
            report["coherence"] = {"interpretation": "NO_SHAPES_RESOLVED"}

        # 6. Simulate spin passes with decay
        spin = plan.get("spin", {})
        passes = spin.get("passes", 1)
        decay_policy = spin.get("decay_policy", {})
        sequence = spin.get("sequence", [f"pass_{i}" for i in range(passes)])

        spin_log = []
        for i in range(passes):
            pass_entry = {
                "pass": i + 1,
                "label": sequence[i] if i < len(sequence) else f"pass_{i}",
                "signal_weights": {},
            }
            for signal, policy in decay_policy.items():
                weight = _decay(policy, 1.0, i, passes)
                pass_entry["signal_weights"][signal] = round(weight, 4)
            spin_log.append(pass_entry)

        report["spin"] = {
            "total_passes": passes,
            "sequence": sequence,
            "passes": spin_log,
        }

        # 7. Walk phases (actions)
        for action in plan.get("actions", []):
            phase = {
                "type": action.get("type"),
                "action": action.get("do"),
                "metric": action.get("metric"),
                "status": "READY",
            }
            report["phases"].append(phase)

        # 8. Final status
        if unresolved:
            report["status"] = "PARTIAL"
            report["errors"].append(
                f"{len(unresolved)} entity ref(s) could not be resolved: "
                + ", ".join(unresolved)
            )

        return report

    def print_report(self, report: dict, file=None):
        """Print a human-readable execution report."""
        out = file or sys.stdout
        w = lambda s: print(s, file=out)

        w(f"{'=' * 60}")
        w(f"REDESIGN PLAN EXECUTION REPORT")
        w(f"{'=' * 60}")
        w(f"Plan:       {report['plan_id']}")
        w(f"Goal:       {report['goal']}")
        w(f"Status:     {report['status']}")
        w("")

        # Resolution
        res = report.get("resolution", {})
        w(f"--- Entity Resolution ({res.get('resolved', 0)}/{res.get('total', 0)}) ---")
        for eid, summary in res.get("entities", {}).items():
            w(f"  {eid}: {summary}")
        if res.get("unresolved"):
            w(f"  UNRESOLVED: {', '.join(res['unresolved'])}")
        w("")

        # Bridges
        if report.get("bridges"):
            w("--- Shape Bridges ---")
            for shape_id, bridge in report["bridges"].items():
                w(f"  {shape_id}:")
                w(f"    families:  {bridge['families']}")
                w(f"    sensors:   {bridge['sensors']}")
                w(f"    defenses:  {bridge['defenses']}")
                w(f"    protocols: {bridge['protocols']}")
                poly = bridge.get("polyhedral", {})
                if poly:
                    w(f"    polyhedral: {poly.get('maps_to', 'N/A')}")
            w("")

        # Coherence
        coh = report.get("coherence", {})
        w(f"--- Geometric Coherence ---")
        w(f"  Score:          {coh.get('coherence', 'N/A')}")
        w(f"  Interpretation: {coh.get('interpretation', 'N/A')}")
        w(f"  Phi matches:    {coh.get('phi_matches', 'N/A')}/{coh.get('total_ratios', 'N/A')} ratios")
        w(f"  Enrichment:     {coh.get('enrichment', 'N/A')}x vs random")
        w("")

        # Spin
        spin = report.get("spin", {})
        w(f"--- Spin Engine ({spin.get('total_passes', 0)} passes) ---")
        for p in spin.get("passes", []):
            weights = ", ".join(f"{k}={v}" for k, v in p.get("signal_weights", {}).items())
            w(f"  Pass {p['pass']} [{p['label']}]: {weights}")
        w("")

        # Phases
        w("--- 7-Phase Algorithm ---")
        for i, phase in enumerate(report.get("phases", []), 1):
            w(f"  {i}. [{phase['type']}] {phase['action']}")
            w(f"     metric: {phase['metric']}  status: {phase['status']}")
        w("")

        # Guardrails
        w("--- Guardrails ---")
        for g in report.get("guardrails", []):
            w(f"  - {g}")
        w("")

        # Errors
        if report.get("errors"):
            w("--- Errors ---")
            for e in report["errors"]:
                w(f"  ! {e}")
            w("")

        w(f"{'=' * 60}")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate_structure(self, plan: dict) -> list[str]:
        """Basic structural validation (stdlib-only, no jsonschema dep)."""
        errors = []
        for field in ("id", "goal", "inputs", "spin", "actions", "guardrails", "provenance"):
            if field not in plan:
                errors.append(f"Missing required field: {field}")

        inputs = plan.get("inputs", {})
        if "shapes" not in inputs:
            errors.append("inputs.shapes is required")
        if "sensors" not in inputs:
            errors.append("inputs.sensors is required")

        # Validate dot-notation IDs
        import re
        patterns = {
            "shapes": r"^SHAPE\.[A-Z0-9_]+$",
            "sensors": r"^EMOTION\.[A-Z0-9_]+$",
            "defenses": r"^DEFENSE\.[A-Z0-9_]+$",
            "protocols": r"^AUDIT\.[A-Z0-9_]+$",
        }
        for key, pattern in patterns.items():
            for eid in inputs.get(key, []):
                if not re.match(pattern, eid):
                    errors.append(f"Invalid {key} ID format: {eid} (expected {pattern})")

        return errors


def _summarize(data: dict) -> str:
    """One-line summary of a resolved entity."""
    if "faces" in data:
        return f"{data.get('name', '?')} ({data.get('faces')}F/{data.get('edges')}E/{data.get('vertices')}V)"
    via = data.get("resolved_via")
    kind = data.get("kind", "")
    name = data.get("name", data.get("label", data.get("id", "?")))
    if via == "bridge":
        shape = data.get("shape", "")
        extra = f" via {shape}" if shape else ""
        if kind == "DEFENSE":
            code = data.get("code", "")
            return f"{name} [{code}]{extra}"
        return f"{name}{extra}"
    return str(name)
