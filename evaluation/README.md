# NeedYield evaluation

These scripts calculate metrics from labeled cases; they do not ask an LLM to grade itself.

## Vision

`vision_test_cases.json` is deliberately empty because the project does not yet have a human-labeled image dataset. Add real labels and saved predictions using the documented schema, then run:

```bash
backend/.venv/bin/python evaluation/vision_eval.py
```

The script reports classification accuracy and quantity mean absolute error only when the corresponding labels exist. Do not report `null` metrics as results.

## RAG retrieval

`rag_test_questions.json` contains five labeled questions tied to the six seeded demo-resource records. Run:

```bash
backend/.venv/bin/python evaluation/rag_eval.py
```

The script queries the actual Chroma collection, checks retrieved resource IDs, and reports Hit Rate@1, Hit Rate@3, and mean Recall@3. It does not score generated answer prose. This tiny, location-explicit set is a pipeline smoke evaluation, not evidence of broad retrieval quality.
