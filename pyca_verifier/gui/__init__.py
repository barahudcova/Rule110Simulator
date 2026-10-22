"""Bundled visualization kit; graphics dependencies load only when requested.

The renderer, camera, widgets and reservoir simulation are based on PyCA_clean.
Binary evolution, initialization and pattern tables use the verifier's own
frozen backend. No separately installed PyCA package is needed.
"""


def main():
    """Launch the diagnostic viewer with a useful optional-dependency message."""
    try:
        from ..visualization import main as visualize
    except ModuleNotFoundError as exc:
        if exc.name not in {"numpy", "pygame"}:
            raise
        raise SystemExit(
            "Visualization requires numpy and pygame. "
            "Install them with: pip install '.[visualization]'"
        ) from exc
    visualize()
