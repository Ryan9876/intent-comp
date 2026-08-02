from pathlib import Path

from intent_compiler.demo import run_demo


def test_demo_executes_and_verifies(tmp_path):
    result = run_demo(tmp_path)
    assert str(result["verification_outcome"]) == "pass"
    assert str(result["verification_status"]) == "verified"
    output = Path(result["changed_targets"][0])
    assert output.exists()
    assert "Intent Compilation" in output.read_text(encoding="utf-8")
    assert (tmp_path / ".intent-compiler" / "audit.jsonl").exists()
