"""Tests for the FlowPipe command-line interface."""

import json

import pytest

from flowpipe.__main__ import main


@pytest.fixture
def sample_pipeline(tmp_path):
    pipeline = {
        "nodes": [
            {"id": "src", "type": "SampleData",
             "params": {"dataset": "sales", "rows": 20}},
            {"id": "flt", "type": "FilterRows",
             "params": {"condition": "price > 50"}},
            {"id": "out", "type": "CSVDestination",
             "params": {"filename": "out.csv"}},
        ],
        "edges": [
            {"source": "src", "target": "flt"},
            {"source": "flt", "target": "out"},
        ],
    }
    path = tmp_path / "pipeline.json"
    path.write_text(json.dumps(pipeline), encoding="utf-8")
    return path


def test_nodes_lists_known_types(capsys):
    code = main(["nodes"])
    assert code == 0
    out = capsys.readouterr().out
    assert "CSVSource" in out
    assert "FilterRows" in out


def test_nodes_json(capsys):
    code = main(["nodes", "--json"])
    assert code == 0
    specs = json.loads(capsys.readouterr().out)
    types = {s["type"] for s in specs}
    assert "SampleData" in types


def test_validate_ok(sample_pipeline, capsys):
    code = main(["validate", str(sample_pipeline)])
    assert code == 0
    assert "OK" in capsys.readouterr().out


def test_validate_unknown_node(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"nodes": [{"id": "a", "type": "Nope"}], "edges": []}))
    code = main(["validate", str(bad)])
    assert code == 1
    assert "unknown node" in capsys.readouterr().out.lower()


def test_validate_cycle(tmp_path, capsys):
    cyclic = {
        "nodes": [{"id": "a", "type": "SampleData", "params": {}},
                  {"id": "b", "type": "Deduplicate", "params": {}}],
        "edges": [{"source": "a", "target": "b"},
                  {"source": "b", "target": "a"}],
    }
    path = tmp_path / "cyclic.json"
    path.write_text(json.dumps(cyclic))
    code = main(["validate", str(path)])
    assert code == 1
    assert "cycle" in capsys.readouterr().out.lower()


def test_run_writes_output(sample_pipeline, tmp_path, capsys):
    upload = tmp_path / "uploads"
    upload.mkdir()
    code = main(["run", str(sample_pipeline), "--upload-dir", str(upload)])
    assert code == 0
    assert (upload / "out.csv").exists()
    assert "Pipeline finished" in capsys.readouterr().out


def test_run_json_output(sample_pipeline, tmp_path):
    upload = tmp_path / "uploads"
    upload.mkdir()
    code = main(["run", str(sample_pipeline), "--upload-dir", str(upload), "--json"])
    assert code == 0


def test_run_failure_exit_code(tmp_path, capsys):
    pipeline = {
        "nodes": [
            {"id": "src", "type": "SampleData", "params": {"rows": 5}},
            {"id": "flt", "type": "FilterRows",
             "params": {"condition": "no_such_column > 1"}},
        ],
        "edges": [{"source": "src", "target": "flt"}],
    }
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(pipeline))
    code = main(["run", str(path), "--upload-dir", str(tmp_path)])
    assert code == 1


def test_codegen_outputs_script(sample_pipeline, capsys):
    code = main(["codegen", str(sample_pipeline)])
    assert code == 0
    out = capsys.readouterr().out
    assert "import pandas as pd" in out
    assert "to_csv" in out


def test_codegen_to_file(sample_pipeline, tmp_path, capsys):
    target = tmp_path / "script.py"
    code = main(["codegen", str(sample_pipeline), "-o", str(target)])
    assert code == 0
    assert target.exists()
    assert "import pandas" in target.read_text(encoding="utf-8")
