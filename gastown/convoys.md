# Autolab Convoys

Convoys should represent research campaigns, not random batches.

## Naming Pattern

Use:

`<theme>: <specific branch of inquiry>`

Examples:

- `optimizer: lower beta2 without architecture change`
- `throughput: smaller model for more tokens in 5 minutes`
- `attention: simplify attention path while preserving context length`
- `recent-master: follow-ups after new winning patch`

Avoid:

- `random ideas`
- `misc experiments`
- `new stuff`

## Convoy Rules

- A convoy should have one theme.
- Each bead inside a convoy should test one hypothesis only.
- Do not mix optimizer, architecture, and throughput experiments in one convoy unless the convoy is explicitly comparative.
- Close or archive convoys that have stopped producing useful follow-ups.

## When To Start A New Convoy

Start a new convoy when:

- master changed materially
- the current theme is exhausted
- a winning result opens a new branch of inquiry
- a regression cluster suggests a distinct failure mode worth isolating

## Planner Checklist For Convoys

Before dispatching from a convoy, confirm:

1. The convoy theme is still relevant to current master.
2. Each bead is non-duplicative.
3. Validated comparable runner slots are available.
4. The expected upside is worth the slot.
