# Graphify experiment: can it suggest joints across courses?

Question: given only course syllabi, does [Graphify](https://pypi.org/project/graphifyy/)
find the big ideas that run through several subjects (the Locker's *joints*)? If it does,
teachers could use it on real syllabi and long-range plans to propose joints.

Rules (`docs/plan.md`): curriculum files only, never a Locker, rosters or student work.
This run uses **four fictional syllabi** (`syllabi/`), so nothing real leaves the machine.
Graphify sends document text to an AI model for its semantic pass; we name the backend
(`--backend claude-cli`, Claude through the `claude` CLI) so it can't pick one from
whatever API keys happen to be set.

`answer-key.md` lists the four joints planted in the syllabi (worded differently in each
course) and four single-course decoys. It sits outside `syllabi/` so Graphify never sees it.

## Run

```sh
uv tool install graphifyy==0.9.106      # or: pipx install graphifyy==0.9.106
cd experiments/graphify
graphify extract syllabi --backend claude-cli
```

Then score the output against `answer-key.md`: results go in `results.md`.
