"""Export application trajectories to Google ADK EvalSet format.

ADK evaluation can consume the function names/arguments in these cases; business
assertions remain in run.py because trajectory similarity alone cannot prove safety.
"""

import json
from pathlib import Path


def build_evalset():
    cases = json.loads((Path(__file__).parents[1] / "datasets/cases.json").read_text())
    tools = [
        "get_claim",
        "get_policy",
        "get_evidence",
        "calculate_policy_checks",
        "get_previous_outcomes",
    ]
    return {
        "eval_set_id": "claims_week2",
        "name": "Claims tool trajectories",
        "eval_cases": [
            {
                "eval_id": case["id"],
                "session_input": {
                    "app_name": "claims",
                    "user_id": "analyst",
                    "state": {"claim_id": case["claim_id"], "expected_version": 1},
                },
                "conversation": [
                    {
                        "invocation_id": case["id"],
                        "user_content": {
                            "role": "user",
                            "parts": [{"text": "Process claim " + case["claim_id"]}],
                        },
                        "final_response": {
                            "role": "model",
                            "parts": [{"text": case["expected"]}],
                        },
                        "intermediate_data": {
                            "tool_uses": [
                                {"name": name, "args": {"claim_id": case["claim_id"]}}
                                for name in tools + [case["action"]]
                            ]
                        },
                    }
                ],
            }
            for case in cases
            if case.get("action")
        ],
    }


if __name__ == "__main__":
    print(json.dumps(build_evalset(), indent=2))
