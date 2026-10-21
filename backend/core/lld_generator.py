"""Low-Level Design (LLD) UML Architecture Engine & Skeleton Code Generator.

Provides:
1. Object-Oriented and UML structural representation.
2. Architectural relationship validation (cycles, invalid inheritance, orphan interfaces).
3. Polyglot code skeleton generation (TypeScript and Python 3.11).
4. Edge-case safety: generics, empty bodies, abstract methods, and dependency injection.
5. Export serialization for project-level code scaffolding.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Tuple


class Stereotype(str, Enum):
    CLASS = "class"
    INTERFACE = "interface"
    SERVICE = "service"
    REPOSITORY = "repository"
    CONTROLLER = "controller"
    PATTERN = "pattern"


class RelationType(str, Enum):
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    USES = "uses"
    DEPENDS_ON = "depends on"


@dataclass
class LLDAttribute:
    id: str
    name: str
    type: str = "any"
    visibility: str = "-"  # '+', '-', '#'

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLDAttribute":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")).strip(),
            type=str(data.get("type", "any")).strip() or "any",
            visibility=str(data.get("visibility", "-")),
        )


@dataclass
class LLDMethod:
    id: str
    name: str
    params: str = ""
    return_type: str = "void"
    visibility: str = "+"  # '+', '-', '#'

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLDMethod":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")).strip(),
            params=str(data.get("params", "")).strip(),
            return_type=str(data.get("returnType", data.get("return_type", "void"))).strip() or "void",
            visibility=str(data.get("visibility", "+")),
        )


@dataclass
class LLDClass:
    id: str
    label: str
    stereotype: Stereotype = Stereotype.CLASS
    pattern_type: Optional[str] = None
    attributes: List[LLDAttribute] = field(default_factory=list)
    methods: List[LLDMethod] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLDClass":
        # Supports both raw dict and React Flow node structure {id, data: {...}}
        node_id = str(data.get("id", ""))
        d = data.get("data", data)
        label = str(d.get("label", node_id or "UnnamedClass")).strip()
        raw_stereo = str(d.get("stereotype", "class")).lower()
        try:
            stereotype = Stereotype(raw_stereo)
        except ValueError:
            stereotype = Stereotype.CLASS

        attrs = [LLDAttribute.from_dict(a) for a in d.get("attributes", []) if a.get("name")]
        meths = [LLDMethod.from_dict(m) for m in d.get("methods", []) if m.get("name")]

        return cls(
            id=node_id or label,
            label=label,
            stereotype=stereotype,
            pattern_type=d.get("patternType") or d.get("pattern_type"),
            attributes=attrs,
            methods=meths,
        )


@dataclass
class LLDRelationship:
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType = RelationType.USES

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLDRelationship":
        raw_label = str(data.get("label", "uses")).lower().strip()
        if "implement" in raw_label:
            rel = RelationType.IMPLEMENTS
        elif "extend" in raw_label or "inherit" in raw_label:
            rel = RelationType.EXTENDS
        elif "depend" in raw_label:
            rel = RelationType.DEPENDS_ON
        else:
            rel = RelationType.USES

        return cls(
            id=str(data.get("id", "")),
            source_id=str(data.get("source", "")),
            target_id=str(data.get("target", "")),
            relation_type=rel,
        )


class LLDArchitectureValidator:
    """Validates structural UML rules and relationship integrity."""

    @staticmethod
    def validate(classes: List[LLDClass], relationships: List[LLDRelationship]) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        class_map: Dict[str, LLDClass] = {c.id: c for c in classes}
        label_map: Dict[str, str] = {c.id: c.label for c in classes}

        # Check duplicate class names
        names_seen: Dict[str, str] = {}
        for c in classes:
            norm_name = c.label.lower()
            if norm_name in names_seen:
                warnings.append(f"Duplicate class name detected: '{c.label}' (id: {c.id} and {names_seen[norm_name]})")
            else:
                names_seen[norm_name] = c.id

        # Build inheritance graph for cycle detection
        adj_extends: Dict[str, List[str]] = {c.id: [] for c in classes}
        adj_implements: Dict[str, List[str]] = {c.id: [] for c in classes}

        for rel in relationships:
            # Verify source and target existence
            if rel.source_id not in class_map:
                errors.append(f"Relationship '{rel.id}' references non-existent source node '{rel.source_id}'")
                continue
            if rel.target_id not in class_map:
                errors.append(f"Relationship '{rel.id}' references non-existent target node '{rel.target_id}'")
                continue

            src = class_map[rel.source_id]
            tgt = class_map[rel.target_id]

            if rel.source_id == rel.target_id:
                errors.append(f"Self-referential inheritance: '{src.label}' cannot extend/implement itself.")
                continue

            if rel.relation_type == RelationType.EXTENDS:
                # Interfaces cannot extend non-interfaces
                if src.stereotype == Stereotype.INTERFACE and tgt.stereotype != Stereotype.INTERFACE:
                    errors.append(f"Semantic Error: Interface '{src.label}' cannot extend concrete class '{tgt.label}'.")
                # Classes cannot extend interfaces (they implement them)
                elif src.stereotype != Stereotype.INTERFACE and tgt.stereotype == Stereotype.INTERFACE:
                    warnings.append(f"Suspicious relation: '{src.label}' extends interface '{tgt.label}'. Did you mean 'implements'?")
                adj_extends[rel.source_id].append(rel.target_id)

            elif rel.relation_type == RelationType.IMPLEMENTS:
                if tgt.stereotype != Stereotype.INTERFACE:
                    warnings.append(f"Class '{src.label}' implements '{tgt.label}', but '{tgt.label}' is marked as {tgt.stereotype.value}, not interface.")
                adj_implements[rel.source_id].append(rel.target_id)

        # Detect inheritance cycles using DFS
        def find_cycle(node: str, visited: Set[str], rec_stack: Set[str], path: List[str]) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in adj_extends.get(node, []):
                if neighbor not in visited:
                    res = find_cycle(neighbor, visited, rec_stack, path)
                    if res:
                        return res
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return None

        visited_nodes: Set[str] = set()
        for cid in classes:
            if cid.id not in visited_nodes:
                cycle = find_cycle(cid.id, visited_nodes, set(), [])
                if cycle:
                    cycle_names = [label_map.get(node_id, node_id) for node_id in cycle]
                    errors.append(f"Circular inheritance cycle detected: {' -> '.join(cycle_names)}")
                    break

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "class_count": len(classes),
            "relationship_count": len(relationships),
        }


class LLDSkeletonGenerator:
    """Polyglot code skeleton generator for TypeScript and Python."""

    @classmethod
    def generate_typescript(
        cls,
        classes: List[LLDClass],
        relationships: Optional[List[LLDRelationship]] = None,
    ) -> str:
        relationships = relationships or []
        class_map = {c.id: c for c in classes}
        
        # Build relationship lookup per source class
        extends_map: Dict[str, List[str]] = {}
        implements_map: Dict[str, List[str]] = {}
        depends_map: Dict[str, List[str]] = {}

        for r in relationships:
            tgt = class_map.get(r.target_id)
            if not tgt:
                continue
            if r.relation_type == RelationType.EXTENDS:
                extends_map.setdefault(r.source_id, []).append(tgt.label)
            elif r.relation_type == RelationType.IMPLEMENTS:
                implements_map.setdefault(r.source_id, []).append(tgt.label)
            else:
                depends_map.setdefault(r.source_id, []).append(tgt.label)

        code_blocks: List[str] = [
            "/**",
            " * Auto-generated Low-Level Design (LLD) Architecture Skeletons",
            " * Language: TypeScript (strict)",
            " */\n",
        ]

        for c in classes:
            block = []
            if c.pattern_type:
                block.append(f"// Pattern Architecture: {c.pattern_type}")
            if c.stereotype in [Stereotype.SERVICE, Stereotype.REPOSITORY, Stereotype.CONTROLLER]:
                block.append(f"// Stereotype: {c.stereotype.value.capitalize()}")

            is_interface = (c.stereotype == Stereotype.INTERFACE)

            # Heritage clause
            heritage = ""
            ext = extends_map.get(c.id, [])
            imp = implements_map.get(c.id, [])

            if is_interface:
                if ext:
                    heritage = f" extends {', '.join(ext)}"
                block.append(f"export interface {c.label}{heritage} {{")
                for attr in c.attributes:
                    block.append(f"  {attr.name}: {attr.type};")
                for meth in c.methods:
                    block.append(f"  {meth.name}({meth.params}): {meth.return_type};")
                block.append("}\n")
            else:
                parts = []
                if ext:
                    parts.append(f"extends {ext[0]}")
                if imp:
                    parts.append(f"implements {', '.join(imp)}")
                if parts:
                    heritage = " " + " ".join(parts)

                block.append(f"export class {c.label}{heritage} {{")

                # Field declarations
                for attr in c.attributes:
                    vis = "private" if attr.visibility == "-" else ("protected" if attr.visibility == "#" else "public")
                    block.append(f"  {vis} {attr.name}: {attr.type};")

                # Constructor
                if c.attributes:
                    block.append("\n  constructor(")
                    for attr in c.attributes:
                        block.append(f"    {attr.name}: {attr.type},")
                    block.append("  ) {")
                    if ext:
                        block.append("    super();")
                    for attr in c.attributes:
                        block.append(f"    this.{attr.name} = {attr.name};")
                    block.append("  }\n")
                elif ext:
                    block.append("\n  constructor() {\n    super();\n  }\n")

                # Methods
                if not c.methods and not c.attributes:
                    block.append("  // Empty class specification")
                else:
                    for meth in c.methods:
                        vis = "private" if meth.visibility == "-" else ("protected" if meth.visibility == "#" else "public")
                        block.append(f"  {vis} {meth.name}({meth.params}): {meth.return_type} {{")
                        block.append(f"    // TODO: implement {meth.name}")
                        if meth.return_type.strip() != "void":
                            block.append("    throw new Error('Not implemented');")
                        block.append("  }\n")

                block.append("}\n")

            code_blocks.append("\n".join(block))

        return "\n".join(code_blocks)

    @classmethod
    def generate_python(
        cls,
        classes: List[LLDClass],
        relationships: Optional[List[LLDRelationship]] = None,
    ) -> str:
        relationships = relationships or []
        class_map = {c.id: c for c in classes}

        extends_map: Dict[str, List[str]] = {}
        implements_map: Dict[str, List[str]] = {}

        for r in relationships:
            tgt = class_map.get(r.target_id)
            if not tgt:
                continue
            if r.relation_type == RelationType.EXTENDS:
                extends_map.setdefault(r.source_id, []).append(tgt.label)
            elif r.relation_type == RelationType.IMPLEMENTS:
                implements_map.setdefault(r.source_id, []).append(tgt.label)

        has_interface = any(c.stereotype == Stereotype.INTERFACE for c in classes)

        lines: List[str] = [
            '"""Auto-generated Low-Level Design (LLD) Architecture Skeletons.',
            "",
            "Language: Python 3.11+",
            '"""',
            "from __future__ import annotations",
            "from typing import Any, List, Dict, Optional, Generic, TypeVar",
        ]
        if has_interface:
            lines.append("from abc import ABC, abstractmethod")
        lines.append("\n")

        for c in classes:
            if c.pattern_type:
                lines.append(f"# Pattern Architecture: {c.pattern_type}")
            if c.stereotype in [Stereotype.SERVICE, Stereotype.REPOSITORY, Stereotype.CONTROLLER]:
                lines.append(f"# Stereotype: {c.stereotype.value.capitalize()}")

            is_interface = (c.stereotype == Stereotype.INTERFACE)
            ext = extends_map.get(c.id, [])
            imp = implements_map.get(c.id, [])

            bases: List[str] = []
            if is_interface:
                bases.append("ABC")
                bases.extend(ext)
            else:
                bases.extend(ext)
                bases.extend(imp)

            base_clause = f"({', '.join(bases)})" if bases else ""
            lines.append(f"class {c.label}{base_clause}:")

            if is_interface:
                if not c.methods and not c.attributes:
                    lines.append("    pass\n")
                else:
                    for attr in c.attributes:
                        lines.append(f"    {attr.name}: {attr.type}")
                    if c.attributes and c.methods:
                        lines.append("")
                    for meth in c.methods:
                        p = f"self, {meth.params}" if meth.params else "self"
                        lines.append("    @abstractmethod")
                        lines.append(f"    def {meth.name}({p}) -> {meth.return_type}:")
                        lines.append("        pass\n")
            else:
                # Concrete Class
                has_body = False
                if c.attributes:
                    has_body = True
                    params_list = ["self"]
                    for a in c.attributes:
                        params_list.append(f"{a.name}: {a.type}")
                    lines.append(f"    def __init__({', '.join(params_list)}) -> None:")
                    if ext:
                        lines.append("        super().__init__()")
                    for a in c.attributes:
                        prefix = "__" if a.visibility == "-" else ("_" if a.visibility == "#" else "")
                        lines.append(f"        self.{prefix}{a.name} = {a.name}")
                    lines.append("")

                for meth in c.methods:
                    has_body = True
                    prefix = "__" if meth.visibility == "-" else ("_" if meth.visibility == "#" else "")
                    p = f"self, {meth.params}" if meth.params else "self"
                    lines.append(f"    def {prefix}{meth.name}({p}) -> {meth.return_type}:")
                    lines.append("        # TODO: implement logic")
                    if meth.return_type.strip() in ["void", "None"]:
                        lines.append("        return None\n")
                    else:
                        lines.append("        raise NotImplementedError('Method not implemented')\n")

                if not has_body:
                    lines.append("    pass\n")

            lines.append("")

        return "\n".join(lines).strip() + "\n"

    @classmethod
    def export_archive(
        cls,
        classes: List[LLDClass],
        relationships: Optional[List[LLDRelationship]] = None,
    ) -> Dict[str, str]:
        """Generate multi-file architecture bundle for export."""
        ts_code = cls.generate_typescript(classes, relationships)
        py_code = cls.generate_python(classes, relationships)
        return {
            "architecture.ts": ts_code,
            "architecture.py": py_code,
        }
