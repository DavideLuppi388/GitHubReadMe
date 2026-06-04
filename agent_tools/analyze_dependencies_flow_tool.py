from langchain_core.tools import tool
from typing import Annotated, List
import ast
import re
from collections import defaultdict
import json

@tool
def analyze_dependencies_flow(
    files_metadata: Annotated[
        str,
        "JSON str containing a List of dicts with 'file_path' and 'metadata' (output of extract_code_metadata). "
        "Example: [{'file_path': 'src/auth.py', 'metadata': {...}, ...]"
    ],
    only_internal: Annotated[bool, "If True, exclude third-party/stdlib imports, keep only intra-repo dependencies"] = True,
) -> str:
    """
    Analyzes the import graph across multiple files in a repository.
    Returns a dependency graph, reverse graph, orphan modules, hub modules,
    and circular dependency chains.
    """

    if isinstance(files_metadata, str):
        try:
            files_metadata = json.loads(files_metadata)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input"})
        
    deserialized = []
    for entry in files_metadata:
        if isinstance(entry, str):
            try:
                entry = json.loads(entry)
            except json.JSONDecodeError:
                continue
        # fix: metadata potrebbe essere stringa JSON (output di extract_code_metadata)
        metadata = entry.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        deserialized.append({
            "file_path": entry["file_path"],
            "metadata": metadata
        })
    files_metadata = deserialized

    # ── 1. Indice dei moduli noti ─────────────────────────────────────────────

    def path_to_module(path: str) -> str:
        """'src/auth/service.py' → 'src.auth.service'"""
        return path.replace("/", ".").replace("\\", ".").removesuffix(".py")

    def module_variants(module: str) -> set[str]:
        """
        Genera tutte le varianti possibili di un nome modulo.
        'src.auth.service' → {'src.auth.service', 'auth.service', 'service'}
        Copre import relativi, import flat e import con prefisso parziale.
        """
        parts = module.split(".")
        return {".".join(parts[i:]) for i in range(len(parts))}

    # mappa: ogni variante → modulo canonico
    # es. 'service' → 'src.auth.service', 'auth.service' → 'src.auth.service'
    variant_to_canonical: dict[str, str] = {}
    known_modules: set[str] = set()

    for entry in files_metadata:
        canonical = path_to_module(entry["file_path"])
        known_modules.add(canonical)
        for variant in module_variants(canonical):
            # in caso di collisione preferisce il modulo con path più lungo (più specifico)
            if variant not in variant_to_canonical or \
               len(canonical) > len(variant_to_canonical[variant]):
                variant_to_canonical[variant] = canonical

    def resolve(module: str) -> str | None:
        """
        Risolve un import al suo modulo canonico nella repo.
        Prova match esatto, poi tutte le varianti suffisso.
        Ritorna None se non è un modulo interno.
        """
        # match esatto
        if module in variant_to_canonical:
            return variant_to_canonical[module]

        # prova suffissi crescenti: 'a.b.c' → 'b.c' → 'c'
        parts = module.split(".")
        for i in range(1, len(parts)):
            suffix = ".".join(parts[i:])
            if suffix in variant_to_canonical:
                return variant_to_canonical[suffix]

        return None

    # ── 2. Costruisce il grafo ────────────────────────────────────────────────

    graph: dict[str, set] = defaultdict(set)
    reverse_graph: dict[str, set] = defaultdict(set)
    raw_imports: dict[str, list] = {}
    unresolved_imports: dict[str, list] = {}  # import non risolti per debug

    for entry in files_metadata:
        file_path = entry["file_path"]
        metadata  = entry["metadata"]
        source    = path_to_module(file_path)
        imports   = metadata.get("imports", [])

        graph[source]  # assicura nodo anche senza uscite
        raw_list, unresolved_list = [], []

        for imp in imports:
            # ricostruisce il nome completo
            full = imp["from"] if imp.get("from") else imp["module"]
            raw_list.append(full)

            canonical = resolve(full)

            if canonical is None:
                if not only_internal:
                    graph[source].add(full)
                    reverse_graph[full].add(source)
                else:
                    unresolved_list.append(full)
                continue

            # evita self-loop
            if canonical == source:
                continue

            graph[source].add(canonical)
            reverse_graph[canonical].add(source)

        raw_imports[file_path]      = raw_list
        unresolved_imports[file_path] = unresolved_list

    # ── 3. Metriche ──────────────────────────────────────────────────────────

    all_nodes = set(graph.keys()) | set(reverse_graph.keys())

    # nodi senza dipendenze uscenti (utility pure, nessun import interno)
    source_modules = sorted(m for m in graph if len(graph[m]) == 0)

    # nodi non importati da nessuno (entry point / script top-level)
    leaf_modules = sorted(m for m in all_nodes if m not in reverse_graph or len(reverse_graph[m]) == 0)

    # hub: moduli più importati
    hubs = sorted(
        [(m, len(importers)) for m, importers in reverse_graph.items()],
        key=lambda x: x[1], reverse=True
    )[:5]

    # ── 4. Cicli (DFS) ───────────────────────────────────────────────────────

    def find_cycles(g: dict) -> list:
        visited, rec_stack, cycles = set(), set(), []

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in g.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
                elif neighbor in rec_stack and neighbor in path:
                    cycles.append(path[path.index(neighbor):] + [neighbor])

        for node in list(g.keys()):
            if node not in visited:
                dfs(node, [node])

        # deduplica per frozenset
        seen, unique = set(), []
        for c in cycles:
            key = frozenset(c)
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    cycles = find_cycles({k: list(v) for k, v in graph.items()})

    # ── 5. Output ────────────────────────────────────────────────────────────

    return json.dumps({
        "graph": {k: sorted(v) for k, v in graph.items()},
        "reverse_graph": {k: sorted(v) for k, v in reverse_graph.items()},
        "metrics": {
            "total_modules": len(all_nodes),
            "total_edges": sum(len(v) for v in graph.values()),
            "source_modules": source_modules,
            "leaf_modules": leaf_modules,
            "hub_modules": [{"module": m, "imported_by": n} for m, n in hubs],
            "circular_dependencies": cycles,
        },
        "raw_imports": raw_imports,
        "unresolved_imports": unresolved_imports,
    })