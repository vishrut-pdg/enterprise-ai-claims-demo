from app.evaluation.run import run_evaluation


async def test_evaluation():
    results = await run_evaluation()
    assert len(results) == 6 and all(r["passed"] for r in results)
