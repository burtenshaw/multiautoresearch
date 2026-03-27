## Autolab Polecat Policy

This rig is an experiment rig, not a general coding rig.

Your job is to execute one benchmark experiment cleanly and report the result.

### Hard Rules

- Edit `train.py` only unless the assigned bead explicitly says otherwise.
- Never modify `prepare.py`.
- Start from current master, not from your prior local branch.
- Make exactly one hypothesis change per experiment bead.
- Do not bundle multiple ideas into one patch.
- If master changed materially while you were working, record that fact and ask for replanning instead of improvising.

### Completion Standard

Your work is not done when code looks good.
Your work is done when you have:

1. Launched exactly one managed benchmark job for the experiment bead.
2. Recorded the HF job id plus the resulting `val_bpb`.
3. Written a short interpretation of the result.
4. Submitted only if the result beats current master.

### Result Persistence

After every run, persist:
- parent master hash
- HF job id and flavor
- observed `val_bpb`
- hypothesis tested
- whether the patch was submitted
- one short note on what likely happened

If the run regressed or failed before a metric appeared, persist the HF job id
and failure clearly so other workers do not repeat it.

### Duplicate Avoidance

Before editing, check whether your bead notes or convoy context show that the same idea
was just tried. If yes, do not retry it unless the bead explicitly says the retry is intentional.

### Scope Discipline

Do not:
- redesign the whole model
- refactor unrelated code
- investigate side issues
- run your own research program

If you discover a promising adjacent idea, file it as follow-up research instead of adding it now.
