# Benchmark Protocol

## Objective

Determine when Intent Compilation creates enough measurable value to justify its additional effort, latency, and cost.

## Conditions

1. Direct prompt
2. Structured single prompt
3. Simple prompt chain
4. Intent Compilation workflow

## Minimum experiment

- Six domains
- Four scenarios per domain
- Identical source material and success criteria
- Blind domain review where possible
- Complete trajectory capture
- No changing the scoring rubric after reviewing results

## Measures

- Outcome quality
- Factual error rate
- Requirement coverage
- Execution success
- Rework minutes
- Traceability
- Human effort
- Latency
- Cost
- Verification burden

## Failure analysis

For every material error, record:

- stage where it entered
- evidence available at that stage
- validation gate that should have detected it
- whether it propagated
- correction cost
- recommended control change

## Interpretation

The methodology need not win every task. The benchmark should identify the consequence, ambiguity, complexity, reuse, and evidence thresholds at which each stage becomes economically justified.
