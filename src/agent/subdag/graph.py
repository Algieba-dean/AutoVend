"""
Workflow Graph topology and routing for Sub-DAG.
"""

from collections import deque
from typing import Any, Dict, List, Optional, Set


class SubDAGGraph:
    """Represents a Directed Acyclic Graph topology for local stage workflows."""

    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        self.nodes = {n["id"]: n for n in nodes}
        self.edges = edges
        self.adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
        self.rev_adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
        self.out_edges: Dict[str, List[Dict[str, Any]]] = {n["id"]: [] for n in nodes}

        for edge in edges:
            u, v = edge["source"], edge["target"]
            if u in self.adj and v in self.adj:
                self.adj[u].append(v)
                self.rev_adj[v].append(u)
                self.out_edges[u].append(edge)

    def get_topo_sort(self) -> List[str]:
        """Get topological sort order of node IDs in the DAG."""
        in_degree = {n_id: len(parents) for n_id, parents in self.rev_adj.items()}
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            curr = queue.popleft()
            result.append(curr)
            for neighbor in self.adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def get_next_nodes(self, node_id: str, handle_id: Optional[str] = None) -> List[str]:
        """Get target node IDs following an executed node, optionally filtered by handle."""
        if handle_id:
            targets = [
                edge["target"]
                for edge in self.out_edges.get(node_id, [])
                if edge.get("sourceHandle") == handle_id or edge.get("handle") == handle_id
            ]
            if targets:
                return targets
        return self.adj.get(node_id, [])

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self.nodes.get(node_id)
