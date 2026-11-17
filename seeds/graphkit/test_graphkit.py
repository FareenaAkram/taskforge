import pytest

from graphkit import bfs_path, connected_components, dijkstra, has_cycle, topological_sort


def test_bfs_simple_path():
    """BFS returns the path from start to goal inclusive"""
    g = {"a": ["b"], "b": ["c"], "c": []}
    assert bfs_path(g, "a", "c") == ["a", "b", "c"]


def test_bfs_prefers_fewest_edges():
    """BFS picks the route with the fewest edges"""
    g = {"a": ["b", "e"], "b": ["c"], "c": ["d"], "e": ["d"], "d": []}
    assert bfs_path(g, "a", "d") == ["a", "e", "d"]


def test_bfs_start_equals_goal():
    """The path from a node to itself is just that node"""
    assert bfs_path({"a": ["b"]}, "a", "a") == ["a"]


def test_bfs_unreachable_returns_none():
    """Unreachable goals give None"""
    g = {"a": ["b"], "b": [], "c": []}
    assert bfs_path(g, "a", "c") is None
    assert bfs_path(g, "a", "zzz") is None


def test_bfs_unknown_start():
    """A start node missing from the graph reaches nothing"""
    assert bfs_path({"a": ["b"]}, "x", "b") is None


def test_bfs_respects_edge_direction():
    """Edges are directed"""
    g = {"a": ["b"], "b": []}
    assert bfs_path(g, "b", "a") is None


def test_bfs_handles_cycles():
    """BFS terminates on cyclic graphs"""
    g = {"a": ["b"], "b": ["a", "c"], "c": ["a"]}
    assert bfs_path(g, "a", "c") == ["a", "b", "c"]


def test_bfs_deterministic_among_equal_paths():
    """With equal-length routes the first-discovered one wins"""
    g = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}
    assert bfs_path(g, "a", "d") == ["a", "b", "d"]


def test_bfs_long_chain_order():
    """The returned path is ordered from start to goal"""
    g = {i: [i + 1] for i in range(6)}
    assert bfs_path(g, 0, 6) == [0, 1, 2, 3, 4, 5, 6]


def test_topological_sort_basic():
    """Dependencies come before dependents, ties broken alphabetically"""
    assert topological_sort({"a": ["c"], "b": ["c"], "c": []}) == ["a", "b", "c"]
    assert topological_sort({"b": ["a"], "a": []}) == ["b", "a"]


def test_topological_sort_includes_target_only_nodes():
    """Nodes that only appear as edge targets are included"""
    assert topological_sort({"a": ["b"]}) == ["a", "b"]


def test_topological_sort_diamond():
    """A diamond-shaped dependency graph sorts correctly"""
    g = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}
    assert topological_sort(g) == ["a", "b", "c", "d"]


def test_topological_sort_independent_nodes_sorted():
    """Independent nodes come out alphabetically"""
    assert topological_sort({"z": [], "m": [], "a": []}) == ["a", "m", "z"]


def test_topological_sort_tie_breaking_with_newly_ready_nodes():
    """Newly unblocked nodes are merged into the alphabetical ready queue"""
    assert topological_sort({"a": ["d"], "b": [], "c": []}) == ["a", "b", "c", "d"]


def test_topological_sort_empty():
    """An empty graph sorts to an empty list"""
    assert topological_sort({}) == []


def test_topological_sort_detects_cycles():
    """Cycles, including self-loops, raise ValueError"""
    with pytest.raises(ValueError):
        topological_sort({"a": ["b"], "b": ["a"]})
    with pytest.raises(ValueError):
        topological_sort({"a": ["a"]})
    with pytest.raises(ValueError):
        topological_sort({"a": ["b"], "b": ["c"], "c": ["b"]})


def test_components_basic():
    """Connected nodes are grouped, groups sorted"""
    assert connected_components([(1, 2), (2, 3), (4, 5)]) == [[1, 2, 3], [4, 5]]


def test_components_empty():
    """No edges means no components"""
    assert connected_components([]) == []


def test_components_edge_direction_is_ignored():
    """Edges are undirected and each component is sorted"""
    assert connected_components([(3, 1)]) == [[1, 3]]


def test_components_ordered_by_smallest_node():
    """Components are ordered by their smallest node"""
    assert connected_components([(9, 8), (1, 2)]) == [[1, 2], [8, 9]]


def test_components_self_loop():
    """A self-loop forms a component of one node"""
    assert connected_components([(1, 1)]) == [[1]]


def test_components_late_bridge_merges_groups():
    """An edge added last can join two earlier groups"""
    assert connected_components([(1, 2), (3, 4), (2, 3)]) == [[1, 2, 3, 4]]


def test_components_star_and_duplicates():
    """Duplicate edges are harmless and stars form one component"""
    edges = [(0, 1), (0, 2), (0, 3), (0, 1), (1, 0)]
    assert connected_components(edges) == [[0, 1, 2, 3]]


def test_dijkstra_prefers_cheaper_multi_hop_route():
    """Dijkstra finds cheaper multi-edge routes over a direct heavy edge"""
    g = {"a": {"b": 1, "c": 4}, "b": {"c": 2, "d": 5}, "c": {"d": 1}, "d": {}}
    assert dijkstra(g, "a") == {"a": 0, "b": 1, "c": 3, "d": 4}


def test_dijkstra_unreachable_nodes_are_absent():
    """Unreachable nodes do not appear in the result"""
    g = {"a": {"b": 2}, "b": {}, "c": {"a": 1}}
    assert dijkstra(g, "a") == {"a": 0, "b": 2}


def test_dijkstra_source_only():
    """A source with no edges has distance zero to itself"""
    assert dijkstra({"a": {}}, "a") == {"a": 0}
    assert dijkstra({}, "a") == {"a": 0}


def test_dijkstra_is_directed():
    """Edge direction is respected"""
    g = {"a": {"b": 1}, "b": {}}
    assert dijkstra(g, "b") == {"b": 0}


def test_dijkstra_zero_and_fractional_weights():
    """Zero and fractional weights are allowed"""
    g = {"a": {"b": 0, "c": 0.5}, "b": {"c": 0.25}, "c": {}}
    assert dijkstra(g, "a") == {"a": 0, "b": 0, "c": 0.25}


def test_dijkstra_equal_cost_alternatives():
    """Equal-cost alternatives give the same distance"""
    g = {"s": {"a": 1, "b": 1}, "a": {"t": 2}, "b": {"t": 2}, "t": {}}
    assert dijkstra(g, "s")["t"] == 3


def test_dijkstra_stale_heap_entries():
    """A node reached first by a worse route is correctly improved later"""
    g = {"a": {"b": 10, "c": 1}, "c": {"b": 1}, "b": {"d": 1}, "d": {}}
    assert dijkstra(g, "a") == {"a": 0, "b": 2, "c": 1, "d": 3}


def test_has_cycle_acyclic():
    """A DAG has no cycle, including a diamond where a node is reached twice"""
    assert has_cycle({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}) is False
    assert has_cycle({"a": ["b"]}) is False
    assert has_cycle({}) is False


def test_has_cycle_self_loop_and_two_cycle():
    """Self-loops and two-node cycles are cycles"""
    assert has_cycle({"a": ["a"]}) is True
    assert has_cycle({"a": ["b"], "b": ["a"]}) is True


def test_has_cycle_longer_cycle():
    """A three-node cycle is detected"""
    assert has_cycle({"a": ["b"], "b": ["c"], "c": ["a"]}) is True


def test_has_cycle_in_later_component():
    """A cycle in a later component is still found"""
    g = {"a": ["b"], "b": [], "x": ["y"], "y": ["x"]}
    assert has_cycle(g) is True


def test_has_cycle_reachable_but_not_through_root():
    """A cycle that the root only leads into is still a cycle"""
    assert has_cycle({"a": ["b"], "b": ["c"], "c": ["b"]}) is True


def test_has_cycle_long_chain():
    """A long acyclic chain is not a cycle"""
    g = {i: [i + 1] for i in range(20)}
    assert has_cycle(g) is False
