"""Create CPU stage notebooks and an explicitly unsealed v2 execution lock."""
import json
from pathlib import Path

V2 = Path(__file__).resolve().parents[1]


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    lock = json.loads((V2.parent / "execution_lock.json").read_text())
    lock.update(protocol_id="iclr-2027-v2", v2_readiness=None, scorer_conformance=None,
                ruler_source=None, reference_tokenizer=None, identifier_contract=None,
                input_materialization=None, paired_coverage_thresholds=None, implementation_inventory=None)
    lock["note"] = "Unsealed. CPU implementation tests do not establish model/processor readiness or authorize GPU inference."
    write_new(V2 / "execution_lock.json", lock)
    directory = V2 / "colab"
    directory.mkdir(exist_ok=False)
    stages = ["cpu-preflight", "processor-calibration", "smoke", "locomo", "ruler", "identifier", "validate"]
    for i, stage in enumerate(stages):
        explanation = ("This stage inventories the installed CPU environment and verifies frozen input hashes. It makes no installs, downloads or GPU calls."
            if stage == "cpu-preflight" else
            "This is a checkpoint scaffold. It reports unresolved prerequisites and stops. The target processor/inference stage adapter is not yet implemented or calibrated; this notebook cannot run an experiment.")
        setup = "from pathlib import Path\nimport os, sys\nROOT = Path('/content/SLM-agents') if Path('/content/SLM-agents').exists() else Path.cwd()\nassert (ROOT / 'iclr/v2/runtime').is_dir(), 'Set ROOT to the prepared repository'\nos.chdir(ROOT)\nsys.path.insert(0, str(ROOT))\nos.environ['PYTHONDONTWRITEBYTECODE'] = '1'\n"
        code = f"import subprocess\nsubprocess.run([sys.executable, '-B', '-m', 'iclr.v2.runtime.stages', '{stage}'], cwd=ROOT, check=True)\n"
        notebook = {"nbformat": 4, "nbformat_minor": 5,
                    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
                    "cells": [{"id": "purpose", "cell_type": "markdown", "metadata": {}, "source": [f"# {stage}\n\n{explanation}\n\nAll scientific results remain planned. GPU and external-operation approval are separate gates.\n"]},
                              {"id": "setup", "cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": setup.splitlines(True)},
                              {"id": "stage", "cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": code.splitlines(True)}]}
        write_new(directory / f"{i:02d}_{stage.replace('-', '_')}.ipynb", notebook)
    print("Created one CPU preflight and six blocked checkpoint scaffolds; execution remains unsealed.")


if __name__ == "__main__":
    main()
