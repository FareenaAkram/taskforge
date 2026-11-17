"""graphkit: classic graph algorithms on plain dicts."""

import heapq
from collections import deque


def bfs_path(graph, start, goal):
    """Shortest path (fewest edges) from start to goal as a list of nodes, or None."""
    if start == goal:
        return [start]
    parents = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in graph.get(node, []):
            if nxt in parents:
                continue
            parents[nxt] = node
            if nxt == goal:
                path = [nxt]
                while parents[path[-1]] is not None:
                    path.append(parents[path[-1]])
                return path[::-1]
            queue.append(nxt)
    return None


def topological_sort(graph):
    """Kahn's algorithm with alphabetical tie-breaking; raises ValueError on a cycle."""
    indegree = {}
    for node, targets in graph.items():
        indegree.setdefault(node, 0)
        for t in targets:
            indegree[t] = indegree.get(t, 0) + 1
    ready = sorted(n for n, d in indegree.items() if d == 0)
    order = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for t in graph.get(node, []):
            indegree[t] -= 1
            if indegree[t] == 0:
                ready.append(t)
        ready.sort()
    if len(order) != len(indegree):
        raise ValueError("graph has a cycle")
    return order


def connected_components(edges):
    """Components of an undirected graph given as (u, v) pairs; each sorted, ordered by first node."""
    adj = {}
    for u, v in edges:
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)
    seen = set()
    comps = []
    for start in sorted(adj):
        if start in seen:
            continue
        stack = [start]
        comp = []
        seen.add(start)
        while stack:
            node = stack.pop()
            comp.append(node)
            for nxt in adj[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        comps.append(sorted(comp))
    return comps


def dijkstra(graph, source):
    """Shortest distances from source; graph maps node -> {neighbour: weight}."""
    dist = {source: 0}
    heap = [(0, source)]
    while heap:
        d, node = heapq.heappop(heap)
        if d > dist.get(node, float("inf")):
            continue
        for nxt, w in graph.get(node, {}).items():
            nd = d + w
            if nd < dist.get(nxt, float("inf")):
                dist[nxt] = nd
                heapq.heappush(heap, (nd, nxt))
    return dist


def has_cycle(graph):
    """Detect a cycle in a directed graph using an iterative three-colour DFS."""
    white, gray, black = 0, 1, 2
    color = {}
    for root in graph:
        if color.get(root, white) != white:
            continue
        stack = [(root, iter(graph.get(root, [])))]
        color[root] = gray
        while stack:
            node, it = stack[-1]
            for nxt in it:
                state = color.get(nxt, white)
                if state == gray:
                    return True
                if state == white:
                    color[nxt] = gray
                    stack.append((nxt, iter(graph.get(nxt, []))))
                    break
            else:
                color[node] = black
                stack.pop()
    return False
