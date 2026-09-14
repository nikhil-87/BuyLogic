import pytest
from backend.database import AsyncSessionLocal
from backend.routers.evaluation import run_evaluation_suite

@pytest.mark.asyncio
async def test_full_evaluation_matrix():
    async with AsyncSessionLocal() as session:
        report = await run_evaluation_suite(db=session)
        print("\n--- EVALUATION BREAKDOWN ---")
        for sc in report["scenario_results"]:
            print(f"Scenario {sc['scenario_number']}: {sc['title']} -> {sc['points_earned']}/25 pts")
            for r in sc["rubric_breakdown"]:
                print(f"  - [{ 'PASS' if r['passed'] else 'FAIL' }] {r['name']}: {r['notes']} ({r['score']}/{r['max']} pts)")
        print(f"Total Score: {report['evaluation_summary']['total_score']}/100")
        assert report["evaluation_summary"]["total_score"] >= 85
