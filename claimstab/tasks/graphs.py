# claimstab/tasks/graphs.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import random

from claimstab.tasks.instances import ProblemInstance

Edge = Tuple[int, int]


@dataclass(frozen=True)
class GraphInstance:
    graph_id: str
    num_nodes: int
    edges: List[Edge]


def ring(n: int) -> GraphInstance:
    edges = [(i, (i + 1) % n) for i in range(n)]
    return GraphInstance(graph_id=f"ring{n}", num_nodes=n, edges=edges)


def erdos_renyi(n: int, p: float, seed: int) -> GraphInstance:
    rnd = random.Random(seed)
    edges: List[Edge] = []
    for i in range(n):
        for j in range(i + 1, n):
            if rnd.random() < p:
                edges.append((i, j))
    return GraphInstance(graph_id=f"er_n{n}_p{p}_seed{seed}", num_nodes=n, edges=edges)


def core_suite() -> List[ProblemInstance]:
    suite: List[ProblemInstance] = []
    graph = GraphInstance(
        graph_id="maxcut_test",
        num_nodes=5,
        edges=[(0, 1), (1, 2), (0, 2), (1, 3), (2, 3), (2, 4), (3, 4)],
    )
    suite.append(ProblemInstance(instance_id=graph.graph_id, payload=graph))
    return suite


def standard_suite() -> List[ProblemInstance]:
    suite: List[ProblemInstance] = []

    g1 = ring(6)
    suite.append(ProblemInstance(instance_id=g1.graph_id, payload=g1))

    g2 = ring(8)
    suite.append(ProblemInstance(instance_id=g2.graph_id, payload=g2))

    g3 = erdos_renyi(8, 0.3, seed=0)
    suite.append(ProblemInstance(instance_id=g3.graph_id, payload=g3))

    g4 = erdos_renyi(8, 0.3, seed=1)
    suite.append(ProblemInstance(instance_id=g4.graph_id, payload=g4))

    g5 = erdos_renyi(10, 0.25, seed=0)
    suite.append(ProblemInstance(instance_id=g5.graph_id, payload=g5))

    return suite


def large_suite() -> List[ProblemInstance]:
    """
    Deterministic larger benchmark suite (30 instances).

    Mixes structured (ring) and random (Erdos-Renyi with fixed seeds) graphs
    across multiple sizes and densities for stronger external validity.
    """
    suite: List[ProblemInstance] = []

    for n in [6, 8, 10, 12, 14, 16]:
        g = ring(n)
        suite.append(ProblemInstance(instance_id=g.graph_id, payload=g))

    for n in [8, 10, 12]:
        for p in [0.2, 0.3]:
            for seed in [0, 1, 2, 3]:
                g = erdos_renyi(n, p, seed=seed)
                suite.append(ProblemInstance(instance_id=g.graph_id, payload=g))

    return suite


# Backward-compatible aliases.
def day1_suite() -> List[ProblemInstance]:
    return core_suite()


def day2_suite() -> List[ProblemInstance]:
    return standard_suite()


def day2_large_suite() -> List[ProblemInstance]:
    return large_suite()
