"""Tests for the core pipeline engine."""

import os

import pandas as pd
import pytest

from flowpipe.pipeline import EdgeSpec, NodeSpec, Pipeline


@pytest.fixture
def sample_csv(tmp_path):
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie", "Diana"],
        "age": [30, 25, 35, 28],
        "city": ["NYC", "LA", "NYC", "LA"],
        "salary": [70000, 60000, 90000, 65000],
    })
    path = tmp_path / "test.csv"
    df.to_csv(path, index=False)
    return tmp_path, "test.csv"


class TestPipelineExecution:
    def test_single_source_node(self, sample_csv):
        upload_dir, filename = sample_csv
        nodes = [NodeSpec("n1", "CSVSource", {"filename": filename, "delimiter": ",", "encoding": "utf-8"})]
        edges = []
        pipeline = Pipeline(nodes, edges)
        result = pipeline.run(str(upload_dir))

        assert result.success
        assert len(result.nodes) == 1
        assert result.nodes[0].rows == 4
        assert result.nodes[0].columns == 4

    def test_source_and_filter(self, sample_csv):
        upload_dir, filename = sample_csv
        nodes = [
            NodeSpec("n1", "CSVSource", {"filename": filename, "delimiter": ",", "encoding": "utf-8"}),
            NodeSpec("n2", "FilterRows", {"condition": "age > 27"}),
        ]
        edges = [EdgeSpec("n1", "n2")]
        pipeline = Pipeline(nodes, edges)
        result = pipeline.run(str(upload_dir))

        assert result.success
        assert result.nodes[1].rows == 3  # Alice(30), Charlie(35), Diana(28)

    def test_source_filter_aggregate(self, sample_csv):
        upload_dir, filename = sample_csv
        nodes = [
            NodeSpec("n1", "CSVSource", {"filename": filename, "delimiter": ",", "encoding": "utf-8"}),
            NodeSpec("n2", "GroupAggregate", {"group_by": "city", "aggregations": "salary=mean"}),
        ]
        edges = [EdgeSpec("n1", "n2")]
        pipeline = Pipeline(nodes, edges)
        result = pipeline.run(str(upload_dir))

        assert result.success
        assert result.nodes[1].rows == 2  # NYC, LA

    def test_select_columns(self, sample_csv):
        upload_dir, filename = sample_csv
        nodes = [
            NodeSpec("n1", "CSVSource", {"filename": filename, "delimiter": ",", "encoding": "utf-8"}),
            NodeSpec("n2", "SelectColumns", {"columns": "name, age"}),
        ]
        edges = [EdgeSpec("n1", "n2")]
        pipeline = Pipeline(nodes, edges)
        result = pipeline.run(str(upload_dir))

        assert result.success
        assert result.nodes[1].columns == 2

    def test_sort_rows(self, sample_csv):
        upload_dir, filename = sample_csv
        nodes = [
            NodeSpec("n1", "CSVSource", {"filename": filename, "delimiter": ",", "encoding": "utf-8"}),
            NodeSpec("n2", "SortRows", {"columns": "age", "ascending": "ascending"}),
        ]
        edges = [EdgeSpec("n1", "n2")]
        pipeline = Pipeline(nodes, edges)
        result = pipeline.run(str(upload_dir))

        assert result.success
        assert result.nodes[1].preview[0]["age"] == 25  # Bob is youngest

    def test_add_column(self, sample_csv):
        upload_dir, filename = sample_csv
        nodes = [
            NodeSpec("n1", "CSVSource", {"filename": filename, "delimiter": ",", "encoding": "utf-8"}),
            NodeSpec("n2", "AddColumn", {"name": "bonus", "expression": "df['salary'] * 0.1"}),
        ]
        edges = [EdgeSpec("n1", "n2")]
        pipeline = Pipeline(nodes, edges)
        result = pipeline.run(str(upload_dir))

        assert result.success
        assert result.nodes[1].columns == 5
        assert result.nodes[1].preview[0]["bonus"] == 7000.0

    def test_csv_destination(self, sample_csv):
        upload_dir, filename = sample_csv
        nodes = [
            NodeSpec("n1", "CSVSource", {"filename": filename, "delimiter": ",", "encoding": "utf-8"}),
            NodeSpec("n2", "CSVDestination", {"filename": "output.csv", "delimiter": ",", "index": "no"}),
        ]
        edges = [EdgeSpec("n1", "n2")]
        pipeline = Pipeline(nodes, edges)
        result = pipeline.run(str(upload_dir))

        assert result.success
        assert os.path.exists(os.path.join(str(upload_dir), "output.csv"))

    def test_sample_data_node(self, tmp_path):
        nodes = [NodeSpec("n1", "SampleData", {"dataset": "sales", "rows": 50})]
        pipeline = Pipeline(nodes, [])
        result = pipeline.run(str(tmp_path))

        assert result.success
        assert result.nodes[0].rows == 50

    def test_chain_three_nodes(self, sample_csv):
        upload_dir, filename = sample_csv
        nodes = [
            NodeSpec("n1", "CSVSource", {"filename": filename, "delimiter": ",", "encoding": "utf-8"}),
            NodeSpec("n2", "FilterRows", {"condition": "city == 'NYC'"}),
            NodeSpec("n3", "SortRows", {"columns": "age", "ascending": "descending"}),
        ]
        edges = [EdgeSpec("n1", "n2"), EdgeSpec("n2", "n3")]
        pipeline = Pipeline(nodes, edges)
        result = pipeline.run(str(upload_dir))

        assert result.success
        assert result.nodes[2].rows == 2
        assert result.nodes[2].preview[0]["age"] == 35  # Charlie first (descending)

    def test_unknown_node_type(self, tmp_path):
        nodes = [NodeSpec("n1", "NonexistentNode", {})]
        pipeline = Pipeline(nodes, [])
        result = pipeline.run(str(tmp_path))

        assert not result.success
        assert "Unknown" in result.error

    def test_cycle_detection(self):
        nodes = [
            NodeSpec("n1", "FilterRows", {"condition": "True"}),
            NodeSpec("n2", "FilterRows", {"condition": "True"}),
        ]
        edges = [EdgeSpec("n1", "n2"), EdgeSpec("n2", "n1")]
        pipeline = Pipeline(nodes, edges)

        with pytest.raises(ValueError, match="cycle"):
            pipeline.run(".")


class TestSampleData:
    def test_employees_dataset(self, tmp_path):
        nodes = [NodeSpec("n1", "SampleData", {"dataset": "employees", "rows": 20})]
        pipeline = Pipeline(nodes, [])
        result = pipeline.run(str(tmp_path))
        assert result.success
        assert result.nodes[0].rows == 20

    def test_timeseries_dataset(self, tmp_path):
        nodes = [NodeSpec("n1", "SampleData", {"dataset": "timeseries", "rows": 30})]
        pipeline = Pipeline(nodes, [])
        result = pipeline.run(str(tmp_path))
        assert result.success
        assert result.nodes[0].rows == 30
