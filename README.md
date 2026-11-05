# Battle Royale Simulation

A small, headless battle-royale model for testing how player strategy affects
match outcomes. It uses only the Python standard library.

## Run a batch

From the repository folder, run:

```powershell
python Main\simulation.py --matches 100 --output results.csv
```

This runs 100 matches for each of five strategy mixes (500 matches total) and
writes one row per match to `results.csv`. The CSV contains the random seed,
strategy counts, winner, match length, and eliminations by strategy.

Useful options:

```powershell
python Main\simulation.py --help
python Main\simulation.py --players 30 --matches 500 --seed 2026 --output results.csv
```

The same sequence of random seeds is used for each strategy mix. This makes
the mixes easier to compare under similar random starting conditions. Keep the
seed, player count, and rules with any results you use in a paper.

## Current model

- Each match has aggressive, normal, and cautious players; all have identical
  health, movement speed, attack range, attack accuracy, and damage.
- Aggressive players pursue the nearest opponent and attack more often.
- Normal players pursue nearby opponents, otherwise moving toward the center.
- Cautious players flee nearby opponents, otherwise moving toward the center,
  and attack less often.
- Players start randomly inside a circular map. The safe zone shrinks in timed
  stages; players outside it take damage.
- Attacks resolve in a randomized order each tick; an eliminated player cannot
  attack later in that tick.
- The experiment varies the aggressive-player count from zero to all players.
  The remaining players are split as evenly as possible between normal and
  cautious strategies. The exact counts are included in each CSV row.

This is a deliberately simple first model, not a claim that the rules represent
all battle-royale games. Treat the results as outcomes of these specific rules.
If the zone eliminates all remaining players at once, the CSV records
`no_winner`; those matches should be counted and discussed, not silently
discarded.
Before using them in a paper, we should refine the research question, justify
the rules, run enough repetitions, analyze uncertainty, and support the
methodology with real, verified references in IEEE style.
