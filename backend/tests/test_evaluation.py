from app.evaluation.run import run_evaluation


async def test_evaluation():
    results = await run_evaluation()
    assert len(results) == 6 and all(r["passed"] for r in results)


async def test_demo_eval_suite_covers_workflow_rag_chat_and_controls():
    from app.evaluation.suite import run_suite

    report = await run_suite()
    assert report["total"] == report["passed"] == 20
    assert report["pass_rate"] == 1
    assert report["groups"]["batch_outcomes"]["total"] == 7
    assert report["groups"]["rag"]["total"] == 5
    assert report["groups"]["chat"]["total"] == 3
    assert report["groups"]["guardrails"]["total"] == 3


async def test_demo_eval_reports_failed_expectation_and_continues(
    tmp_path, monkeypatch
):
    import json

    from app.evaluation import suite

    dataset = json.loads(suite.DATA.read_text())
    dataset["claims"][0]["expected"] = "rejected"
    path = tmp_path / "wrong-expectation.json"
    path.write_text(json.dumps(dataset))
    monkeypatch.setattr(suite, "DATA", path)
    report = await suite.run_suite()
    assert report["total"] == 20
    assert report["passed"] == 19
    failure = next(r for r in report["results"] if not r["passed"])
    assert failure["case"] == "CLM-001"
    assert not failure["checks"]["expected_final_status"]
