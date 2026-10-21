"""Unit tests for the Low-Level Design (LLD) Code Generator and Architecture Validator."""

import pytest
from core.lld_generator import (
    LLDClass,
    LLDAttribute,
    LLDMethod,
    LLDRelationship,
    Stereotype,
    RelationType,
    LLDArchitectureValidator,
    LLDSkeletonGenerator,
)


def test_empty_class_generation():
    """Verify empty classes produce syntactically sound code in Python and TypeScript."""
    empty_cls = LLDClass(
        id="c1",
        label="EmptyNode",
        stereotype=Stereotype.CLASS,
        attributes=[],
        methods=[],
    )

    ts_code = LLDSkeletonGenerator.generate_typescript([empty_cls])
    py_code = LLDSkeletonGenerator.generate_python([empty_cls])

    assert "export class EmptyNode {" in ts_code
    assert "class EmptyNode:" in py_code
    assert "    pass" in py_code


def test_interface_and_abstract_methods():
    """Verify interface generation produces TypeScript interfaces and Python ABC abstract methods."""
    method = LLDMethod(id="m1", name="processPayment", params="amount: float", return_type="bool", visibility="+")
    iface = LLDClass(
        id="i1",
        label="IPaymentProcessor",
        stereotype=Stereotype.INTERFACE,
        attributes=[],
        methods=[method],
    )

    ts = LLDSkeletonGenerator.generate_typescript([iface])
    py = LLDSkeletonGenerator.generate_python([iface])

    # TypeScript
    assert "export interface IPaymentProcessor {" in ts
    assert "processPayment(amount: float): bool;" in ts

    # Python
    assert "from abc import ABC, abstractmethod" in py
    assert "class IPaymentProcessor(ABC):" in py
    assert "@abstractmethod" in py
    assert "def processPayment(self, amount: float) -> bool:" in py


def test_inheritance_and_implements():
    """Verify class extending base class and implementing interface."""
    base = LLDClass(id="b1", label="BaseEntity", attributes=[LLDAttribute("a1", "id", "string", "-")])
    iface = LLDClass(id="i1", label="ISerializable", stereotype=Stereotype.INTERFACE)
    child = LLDClass(
        id="c1",
        label="UserEntity",
        attributes=[LLDAttribute("a2", "email", "string", "+")],
        methods=[LLDMethod("m1", "getEmail", "", "string", "+")],
    )

    rels = [
        LLDRelationship("r1", source_id="c1", target_id="b1", relation_type=RelationType.EXTENDS),
        LLDRelationship("r2", source_id="c1", target_id="i1", relation_type=RelationType.IMPLEMENTS),
    ]

    ts = LLDSkeletonGenerator.generate_typescript([base, iface, child], rels)
    py = LLDSkeletonGenerator.generate_python([base, iface, child], rels)

    assert "export class UserEntity extends BaseEntity implements ISerializable {" in ts
    assert "super();" in ts
    assert "class UserEntity(BaseEntity, ISerializable):" in py
    assert "super().__init__()" in py


def test_visibility_modifiers_mapping():
    """Verify private '-', protected '#', and public '+' modifier translations."""
    cls_def = LLDClass(
        id="c1",
        label="Account",
        attributes=[
            LLDAttribute("a1", "secretKey", "string", "-"),
            LLDAttribute("a2", "balance", "number", "#"),
            LLDAttribute("a3", "username", "string", "+"),
        ],
        methods=[
            LLDMethod("m1", "hashPassword", "", "string", "-"),
            LLDMethod("m2", "logAudit", "", "void", "#"),
            LLDMethod("m3", "getBalance", "", "number", "+"),
        ],
    )

    ts = LLDSkeletonGenerator.generate_typescript([cls_def])
    py = LLDSkeletonGenerator.generate_python([cls_def])

    # TypeScript modifiers
    assert "private secretKey: string;" in ts
    assert "protected balance: number;" in ts
    assert "public username: string;" in ts
    assert "private hashPassword(): string {" in ts
    assert "protected logAudit(): void {" in ts
    assert "public getBalance(): number {" in ts

    # Python mangling and convention
    assert "self.__secretKey = secretKey" in py
    assert "self._balance = balance" in py
    assert "self.username = username" in py
    assert "def __hashPassword(self) -> string:" in py
    assert "def _logAudit(self) -> void:" in py
    assert "def getBalance(self) -> number:" in py


def test_generics_and_complex_types():
    """Verify generic types such as List[T], Repository<T>, Promise<UserDTO>."""
    cls_def = LLDClass(
        id="repo",
        label="UserRepository",
        attributes=[
            LLDAttribute("a1", "cache", "Map<string, UserDTO>", "-"),
        ],
        methods=[
            LLDMethod("m1", "findAll", "limit: int = 10", "List[UserDTO]", "+"),
            LLDMethod("m2", "findById", "id: str", "Optional[UserDTO]", "+"),
        ],
    )

    ts = LLDSkeletonGenerator.generate_typescript([cls_def])
    py = LLDSkeletonGenerator.generate_python([cls_def])

    assert "private cache: Map<string, UserDTO>;" in ts
    assert "findAll(limit: int = 10): List[UserDTO] {" in ts
    assert "self.__cache = cache" in py
    assert "def findAll(self, limit: int = 10) -> List[UserDTO]:" in py
    assert "def findById(self, id: str) -> Optional[UserDTO]:" in py


def test_validator_cycle_detection():
    """Verify that circular inheritance (A -> B -> C -> A) is flagged as an error."""
    a = LLDClass(id="a", label="ClassA")
    b = LLDClass(id="b", label="ClassB")
    c = LLDClass(id="c", label="ClassC")

    # A extends B, B extends C, C extends A
    cycle_rels = [
        LLDRelationship("r1", source_id="a", target_id="b", relation_type=RelationType.EXTENDS),
        LLDRelationship("r2", source_id="b", target_id="c", relation_type=RelationType.EXTENDS),
        LLDRelationship("r3", source_id="c", target_id="a", relation_type=RelationType.EXTENDS),
    ]

    res = LLDArchitectureValidator.validate([a, b, c], cycle_rels)
    assert res["valid"] is False
    assert any("Circular inheritance cycle detected" in err for err in res["errors"])


def test_validator_semantic_rules():
    """Verify semantic integrity: interface extending concrete class, missing nodes, self-extension."""
    concrete = LLDClass(id="c1", label="ConcreteClass", stereotype=Stereotype.CLASS)
    iface = LLDClass(id="i1", label="BadInterface", stereotype=Stereotype.INTERFACE)

    # Interface extending class
    rels = [
        LLDRelationship("r1", source_id="i1", target_id="c1", relation_type=RelationType.EXTENDS),
        LLDRelationship("r2", source_id="c1", target_id="non_existent", relation_type=RelationType.USES),
        LLDRelationship("r3", source_id="c1", target_id="c1", relation_type=RelationType.EXTENDS),
    ]

    res = LLDArchitectureValidator.validate([concrete, iface], rels)
    assert res["valid"] is False
    assert any("Interface 'BadInterface' cannot extend concrete class" in err for err in res["errors"])
    assert any("non-existent target node" in err for err in res["errors"])
    assert any("Self-referential inheritance" in err for err in res["errors"])


def test_export_archive():
    """Verify export_archive returns full code dictionaries for TypeScript and Python."""
    c = LLDClass(id="order", label="OrderService", stereotype=Stereotype.SERVICE)
    bundle = LLDSkeletonGenerator.export_archive([c])

    assert "architecture.ts" in bundle
    assert "architecture.py" in bundle
    assert "export class OrderService" in bundle["architecture.ts"]
    assert "class OrderService:" in bundle["architecture.py"]
