from evaluation.run_evaluation import evaluate


def test_bundled_agent_benchmark_is_fully_grounded():
    result = evaluate()
    assert result["cases"] == 30
    assert result["tool_selection_accuracy_pct"] == 100.0
    assert result["grounded_completion_pct"] == 100.0