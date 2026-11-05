"""Headless battle-royale simulation for repeatable strategy experiments."""

import argparse
import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

STRATEGIES = ("aggressive", "normal", "cautious")
PLAYER_COUNT = 30
MAP_RADIUS = 500.0
STARTING_HEALTH = 100
MOVEMENT_SPEED = 4.0
ATTACK_RANGE = 35.0
ATTACK_ACCURACY = 0.75
DAMAGE_RANGE = (10, 20)
ZONE_SHRINK_INTERVAL = 150
ZONE_SHRINK_FACTOR = 0.85
FINAL_ZONE_RADIUS = 20.0
STORM_DAMAGE = 5
MAX_TICKS = 3000
ATTACK_PROBABILITY = {
    "aggressive": 0.8,
    "normal": 0.45,
    "cautious": 0.2,
}


@dataclass
class Player:
    player_id: int
    strategy: str
    x: float
    y: float
    health: int = STARTING_HEALTH
    eliminations: int = 0

    @property
    def alive(self) -> bool:
        return self.health > 0


def _make_players(strategy_counts: dict[str, int], rng: random.Random) -> list[Player]:
    strategies = [
        strategy
        for strategy in STRATEGIES
        for _ in range(strategy_counts[strategy])
    ]
    rng.shuffle(strategies)

    players = []
    for player_id, strategy in enumerate(strategies):
        distance = MAP_RADIUS * math.sqrt(rng.random())
        angle = rng.uniform(0.0, math.tau)
        players.append(
            Player(
                player_id=player_id,
                strategy=strategy,
                x=distance * math.cos(angle),
                y=distance * math.sin(angle),
            )
        )
    return players


def _nearest_opponent(player: Player, living: list[Player]) -> tuple[Player, float] | None:
    opponents = (other for other in living if other.player_id != player.player_id)
    nearest = min(
        opponents,
        key=lambda other: (other.x - player.x) ** 2 + (other.y - player.y) ** 2,
        default=None,
    )
    if nearest is None:
        return None
    return nearest, math.hypot(nearest.x - player.x, nearest.y - player.y)


def _move_players(living: list[Player], rng: random.Random) -> None:
    next_positions: dict[int, tuple[float, float]] = {}
    for player in living:
        nearest = _nearest_opponent(player, living)
        destination_x, destination_y = 0.0, 0.0

        if nearest is not None:
            opponent, distance = nearest
            if player.strategy == "aggressive":
                destination_x, destination_y = opponent.x, opponent.y
            elif player.strategy == "normal" and distance <= 160.0:
                destination_x, destination_y = opponent.x, opponent.y
            elif player.strategy == "cautious" and distance <= 110.0:
                destination_x = 2.0 * player.x - opponent.x
                destination_y = 2.0 * player.y - opponent.y

        dx = destination_x - player.x
        dy = destination_y - player.y
        distance = math.hypot(dx, dy)
        if distance == 0.0:
            angle = rng.uniform(0.0, math.tau)
            dx, dy, distance = math.cos(angle), math.sin(angle), 1.0

        x = player.x + dx / distance * MOVEMENT_SPEED
        y = player.y + dy / distance * MOVEMENT_SPEED
        next_positions[player.player_id] = (
            max(-MAP_RADIUS, min(MAP_RADIUS, x)),
            max(-MAP_RADIUS, min(MAP_RADIUS, y)),
        )

    for player in living:
        player.x, player.y = next_positions[player.player_id]


def run_match(
    strategy_counts: dict[str, int],
    seed: int,
    max_ticks: int = MAX_TICKS,
) -> dict[str, int | float | str]:
    """Run one match and return its outcome and final player counts."""
    if set(strategy_counts) != set(STRATEGIES):
        raise ValueError(f"strategy_counts must contain exactly {STRATEGIES}")
    if any(count < 0 for count in strategy_counts.values()):
        raise ValueError("Strategy counts cannot be negative.")
    if sum(strategy_counts.values()) < 2:
        raise ValueError("A match requires at least two players.")
    if max_ticks < 1:
        raise ValueError("max_ticks must be at least 1.")

    rng = random.Random(seed)
    players = _make_players(strategy_counts, rng)
    zone_radius = MAP_RADIUS
    ticks = 0

    for ticks in range(1, max_ticks + 1):
        if ticks % ZONE_SHRINK_INTERVAL == 0:
            zone_radius = max(FINAL_ZONE_RADIUS, zone_radius * ZONE_SHRINK_FACTOR)

        living = [player for player in players if player.alive]
        if len(living) <= 1:
            break

        _move_players(living, rng)
        attack_order = living.copy()
        rng.shuffle(attack_order)
        for attacker in attack_order:
            if not attacker.alive:
                continue
            current_living = [player for player in living if player.alive]
            nearest = _nearest_opponent(attacker, current_living)
            if nearest is None:
                continue
            target, distance = nearest
            if (
                distance <= ATTACK_RANGE
                and rng.random() < ATTACK_PROBABILITY[attacker.strategy]
                and rng.random() < ATTACK_ACCURACY
            ):
                target.health -= rng.randint(*DAMAGE_RANGE)
                if not target.alive:
                    attacker.eliminations += 1

        for player in living:
            if player.alive and math.hypot(player.x, player.y) > zone_radius:
                player.health -= STORM_DAMAGE

    remaining = [player for player in players if player.alive]
    winner = remaining[0] if len(remaining) == 1 else None
    result: dict[str, int | float | str] = {
        "seed": seed,
        "ticks": ticks,
        "winner_id": winner.player_id if winner else -1,
        "winner_strategy": winner.strategy if winner else "no_winner",
        "final_zone_radius": round(zone_radius, 2),
    }
    for strategy in STRATEGIES:
        result[f"{strategy}_players"] = strategy_counts[strategy]
        result[f"{strategy}_alive"] = sum(
            player.alive and player.strategy == strategy for player in players
        )
        result[f"{strategy}_eliminations"] = sum(
            player.eliminations for player in players if player.strategy == strategy
        )
    return result


def build_scenarios(player_count: int) -> list[dict[str, int]]:
    """Create five mixes from 0% to 100% aggressive players."""
    if player_count < 2:
        raise ValueError("player_count must be at least 2.")

    scenarios = []
    for aggressive_quarters in range(5):
        aggressive = player_count * aggressive_quarters // 4
        others = player_count - aggressive
        normal = others // 2
        cautious = others - normal
        scenarios.append(
            {"aggressive": aggressive, "normal": normal, "cautious": cautious}
        )
    return scenarios


def run_experiment(
    player_count: int,
    matches_per_scenario: int,
    base_seed: int,
    max_ticks: int = MAX_TICKS,
) -> list[dict[str, int | float | str]]:
    """Run each strategy mix using the same seed sequence for fairer comparison."""
    if matches_per_scenario < 1:
        raise ValueError("matches_per_scenario must be at least 1.")

    results = []
    for scenario_id, strategy_counts in enumerate(build_scenarios(player_count), start=1):
        for match_number in range(1, matches_per_scenario + 1):
            seed = base_seed + match_number - 1
            result = run_match(strategy_counts, seed, max_ticks)
            result["scenario_id"] = scenario_id
            result["match_number"] = match_number
            results.append(result)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", type=int, default=PLAYER_COUNT)
    parser.add_argument("--matches", type=int, default=100, help="matches per strategy mix")
    parser.add_argument("--seed", type=int, default=2026, help="starting random seed")
    parser.add_argument("--max-ticks", type=int, default=MAX_TICKS)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("battle_royale_results.csv"),
        help="CSV output path",
    )
    args = parser.parse_args()

    results = run_experiment(args.players, args.matches, args.seed, args.max_ticks)
    fieldnames = list(results[0])
    with args.output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Saved {len(results)} matches to {args.output}")
    for scenario_id, counts in enumerate(build_scenarios(args.players), start=1):
        scenario_results = [
            result for result in results if result["scenario_id"] == scenario_id
        ]
        print(
            f"Scenario {scenario_id}: {counts}; "
            f"winner counts: "
            + ", ".join(
                f"{strategy}={sum(result['winner_strategy'] == strategy for result in scenario_results)}"
                for strategy in (*STRATEGIES, "no_winner")
            )
        )


if __name__ == "__main__":
    main()
