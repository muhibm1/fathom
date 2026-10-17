PipelineBench 0.1.0: 50 scenarios, 1 seed(s), ran 2026-10-16T19:35:11Z

| agent | condition | accuracy | unsafe | cite recall | name recall | approvers | fabricated | score |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| scripted | none | 0.40 | 0.40 | 0.46 | 0.56 | 0.46 | 0.00 | 0.44 |
| scripted | repo | 0.60 | 0.28 | 0.93 | 0.77 | 0.88 | 0.00 | 0.64 |
| scripted | rag | 0.60 | 0.26 | 0.91 | 0.56 | 0.78 | 0.00 | 0.62 |
| scripted | orion | 1.00 | 0.00 | 1.00 | 0.94 | 1.00 | 0.00 | 0.99 |

Accuracy by family:

| agent | condition | additive | additive_upstream | approval | backfill | deprecated | distractor | locked_add | locked_direct | locked_via_lineage | multi | partition | schedule | tier1_unlocked | unlocked_column |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| scripted | none | 1.00 | 1.00 | 0.00 | 0.50 | 0.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.50 | 0.25 | 0.60 | 0.00 | 1.00 |
| scripted | repo | 1.00 | 1.00 | 1.00 | 0.38 | 0.50 | 1.00 | 0.00 | 1.00 | 0.00 | 0.75 | 0.50 | 0.60 | 0.00 | 0.80 |
| scripted | rag | 1.00 | 1.00 | 1.00 | 0.50 | 0.50 | 1.00 | 0.00 | 1.00 | 0.00 | 0.25 | 0.50 | 0.60 | 0.00 | 1.00 |
| scripted | orion | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
