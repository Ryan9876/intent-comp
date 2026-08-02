# Live Study Release Candidate

Version 0.4 adds controls needed before a live comparative run:

- an approved model profile with dated official pricing;
- a hard total-study spend limit and per-run reserve;
- credential and network preflight without sending content;
- resumable execution keyed by blinded output ID;
- balanced independent reviewer assignment;
- publication guards that block quality claims for mock, incomplete, unreviewed, over-budget, or usage-incomplete studies.

## Selected model

The example profile selects GPT-5.6 Terra (`gpt-5.6-terra`) because the official OpenAI model catalog describes it as balancing intelligence and cost. The profile records pricing effective 2026-08-02: $2.00 per million input tokens, $0.20 cached input, and $12.00 per million output tokens. Recheck official pricing before every live run.

## Safety boundary

A live run is blocked unless all of the following are true:

1. `OPENAI_API_KEY` is present in the local environment.
2. Network access is explicitly enabled.
3. The scenario schedule fits the maximum run count.
4. The conservative reserved cost fits the approved spend limit.
5. The model and pricing profiles have official sources and an effective date.

The package never stores the API key and does not record prompt content by default.

## Publication boundary

No comparative quality or superiority claim is allowed until:

- every scheduled live run is present;
- exact token and cost data are recorded;
- there are no run errors;
- the total is within the approved spend limit;
- every output has the required number of independent blind reviews.
