# Gate 20 blind judge instructions

You are grading two condition-blind candidate legal work products for each benchmark task. You must not infer or discuss which candidate used which protocol.

For each group:
1. Read the task title and instructions.
2. Grade every provided Harvey LAB rubric criterion independently against each candidate's `final_answer` using the criterion's `match_criteria` exactly as written.
3. Do not award a criterion because the answer is generally sophisticated; the specific criterion must be satisfied.
4. Do not penalize a candidate merely for style, brevity, or formatting unless the rubric requires it.
5. Record whether each failure is primarily an omission, incorrect proposition, unsupported/incorrect citation, reconciliation error, or other.
6. Separately give holistic diagnostics: central conclusion correct, material omission present, unsafe hallucination present.
7. Audit materially relied legal citations when they are explicit enough to evaluate. If you have browsing/research tools, verify source existence, proposition support, jurisdiction/scope, and temporal validity. If a citation cannot reasonably be checked, mark it `unverifiable` rather than guessing.

Return exactly one JSON object:
{
  "judge_model": "ACTUAL MODEL NAME",
  "groups": [
    {
      "judge_id": "...",
      "candidates": {
        "A": {
          "criteria": [{"criterion_id":"C-001","pass":true,"failure_type":"none|omission|incorrect|citation|reconciliation|other","reason":"..."}],
          "central_conclusion_correct": true,
          "material_omission": false,
          "unsafe_hallucination": false,
          "citations": [{"citation":"...","source_exists":true,"supports_claim":true,"correct_jurisdiction_scope":true,"temporally_valid":true,"verifiability":"verified|unverifiable"}],
          "primary_failure_stage": "none|issue_mapping|document_recall|legal_retrieval|authority_selection|authority_reading|reconciliation|citation|final_output_omission|other"
        },
        "B": {"criteria": [], "central_conclusion_correct": true, "material_omission": false, "unsafe_hallucination": false, "citations": [], "primary_failure_stage": "none"}
      }
    }
  ]
}
