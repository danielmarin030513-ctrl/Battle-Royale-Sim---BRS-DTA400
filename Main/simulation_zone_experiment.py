#compare safe-zone shrinking speeds in 1500 headless matches
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
ZONE_SHRINK_FACTOR = 0.85
FINAL_ZONE_RADIUS = 20.0
STORM_DAMAGE = 5
MAX_TICKS = 3000
ZONE_SCENARIOS = {"fast": 75, "normal": 150, "slow": 300}
ATTACK_PROBABILITY = {"aggressive": 0.8, "normal": 0.45, "cautious": 0.2}

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
    strategies = [s for s in STRATEGIES for _ in range(strategy_counts[s])]
    rng.shuffle(strategies)
    players = []
    for player_id, strategy in enumerate(strategies):
        distance = MAP_RADIUS * math.sqrt(rng.random())
        angle = rng.uniform(0.0, math.tau)
        players.append(Player(player_id, strategy, distance * math.cos(angle), distance * math.sin(angle)))
    return players


def _nearest_opponent(player: Player, living: list[Player]) -> tuple[Player, float] | None:
    opponents = (other for other in living if other.player_id != player.player_id)
    nearest = min(opponents, key=lambda other: (other.x - player.x)**2 + (other.y - player.y)**2, default=None)
    if nearest is None:
        return None
    return nearest, math.hypot(nearest.x - player.x, nearest.y - player.y)


def _move_players(living: list[Player], rng: random.Random) -> None:
    next_positions = {}
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
        dx, dy = destination_x - player.x, destination_y - player.y
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


def run_match(strategy_counts: dict[str, int], seed: int, zone_shrink_interval: int,
              max_ticks: int = MAX_TICKS) -> dict:
    if set(strategy_counts) != set(STRATEGIES) or any(v < 0 for v in strategy_counts.values()):
        raise ValueError("Invalid strategy counts")
    if sum(strategy_counts.values()) < 2 or zone_shrink_interval < 1 or max_ticks < 1:
        raise ValueError("Invalid player count, interval, or max ticks")
    rng = random.Random(seed)
    players = _make_players(strategy_counts, rng)
    zone_radius = MAP_RADIUS
    combat_eliminations = 0
    zone_eliminations = 0
    ticks = 0

    for tick in range(1, max_ticks + 1):
        if sum(p.alive for p in players) <= 1:
            break
        ticks = tick
        if tick % zone_shrink_interval == 0:
            zone_radius = max(FINAL_ZONE_RADIUS, zone_radius * ZONE_SHRINK_FACTOR)
        living = [p for p in players if p.alive]
        _move_players(living, rng)
        attack_order = living.copy()
        rng.shuffle(attack_order)
        for attacker in attack_order:
            if not attacker.alive:
                continue
            current_living = [p for p in living if p.alive]
            nearest = _nearest_opponent(attacker, current_living)
            if nearest is None:
                continue
            target, distance = nearest
            if (distance <= ATTACK_RANGE
                and rng.random() < ATTACK_PROBABILITY[attacker.strategy]
                and rng.random() < ATTACK_ACCURACY):
                target.health -= rng.randint(*DAMAGE_RANGE)
                if not target.alive:
                    attacker.eliminations += 1
                    combat_eliminations += 1
        for player in living:
            if player.alive and math.hypot(player.x, player.y) > zone_radius:
                player.health -= STORM_DAMAGE
                if not player.alive:
                    zone_eliminations += 1

    remaining = [p for p in players if p.alive]
    winner = remaining[0] if len(remaining) == 1 else None
    result = {
        "seed": seed,
        "zone_shrink_interval": zone_shrink_interval,
        "ticks": ticks,
        "combat_eliminations": combat_eliminations,
        "zone_eliminations": zone_eliminations,
        "total_eliminations": combat_eliminations + zone_eliminations,
        "survivors": len(remaining),
        "finished": len(remaining) <= 1,
        "winner_id": winner.player_id if winner else -1,
        "winner_strategy": winner.strategy if winner else "no_winner",
        "final_zone_radius": round(zone_radius, 2),
    }
    for strategy in STRATEGIES:
        result[f"{strategy}_players"] = strategy_counts[strategy]
        result[f"{strategy}_eliminations"] = sum(p.eliminations for p in players if p.strategy == strategy)
    return result


def run_experiment(player_count: int, matches_per_scenario: int, base_seed: int,
                   max_ticks: int = MAX_TICKS) -> list[dict]:
    if player_count < 3 or matches_per_scenario < 1:
        raise ValueError("Need at least 3 players and 1 match")
    # Same AI composition for all zone-speed scenarios.
    base, remainder = divmod(player_count, 3)
    counts = {strategy: base + (i < remainder) for i, strategy in enumerate(STRATEGIES)}
    results = []
    for scenario_id, (name, interval) in enumerate(ZONE_SCENARIOS.items(), start=1):
        for match_number in range(1, matches_per_scenario + 1):
            seed = base_seed + match_number - 1
            result = run_match(counts, seed, interval, max_ticks)
            result.update(scenario_id=scenario_id, zone_speed=name, match_number=match_number)
            results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", type=int, default=PLAYER_COUNT)
    parser.add_argument("--matches", type=int, default=500, help="Matches per zone speed")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--max-ticks", type=int, default=MAX_TICKS)
    parser.add_argument("--output", type=Path, default=Path("zone_results.csv"))
    args = parser.parse_args()
    results = run_experiment(args.players, args.matches, args.seed, args.max_ticks)
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved {len(results)} matches to {args.output}")
    for name in ZONE_SCENARIOS:
        group = [r for r in results if r["zone_speed"] == name]
        avg = lambda key: sum(r[key] for r in group) / len(group)
        print(f"{name}: avg ticks={avg('ticks'):.1f}, combat={avg('combat_eliminations'):.1f}, "
              f"zone={avg('zone_eliminations'):.1f}, finished={sum(r['finished'] for r in group)}/{len(group)}")

if __name__ == "__main__":
    main()
