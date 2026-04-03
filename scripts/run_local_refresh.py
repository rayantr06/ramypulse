"""CLI entrypoint to refresh the local RamyPulse pipeline end to end."""

from __future__ import annotations

from core.runtime.diagnostics import collect_runtime_diagnostics
from core.runtime.refresh_pipeline import run_local_refresh_pipeline


def main() -> dict:
    """Run the local refresh pipeline and print a concise summary."""
    diagnostics = collect_runtime_diagnostics()
    summary = run_local_refresh_pipeline()

    print(f"MODE={diagnostics['mode']}")
    print(f"ANNOTATION={diagnostics['annotation']['backend_label']}")
    print(f"RAG={diagnostics['rag']['provider']}:{diagnostics['rag']['model']}")
    print(f"RECO={diagnostics['recommendation']['provider']}:{diagnostics['recommendation']['model']}")
    print(f"RAW={summary['artifacts']['raw']}")
    print(f"CLEAN={summary['artifacts']['clean']}")
    print(f"ANNOTATED={summary['artifacts']['annotated']}")
    print(f"INDEX={summary['artifacts']['index']}")
    print(f"ROWS_CLEAN={summary['rows']['clean']}")
    print(f"ROWS_ANNOTATED={summary['rows']['annotated']}")
    return summary


if __name__ == "__main__":
    main()
