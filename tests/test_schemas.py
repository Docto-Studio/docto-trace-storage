"""Unit tests for storage and report Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

import pytest

from docto_trace.schemas.storage import FileNode, FolderNode, StorageTree
from docto_trace.schemas.report import (
    ActionSeverity,
    DuplicateGroup,
    FolderInsight,
    HealthReport,
    InsightSummary,
    ZombieFile,
    ZombieStatus,
)


# ---------------------------------------------------------------------------
# FileNode
# ---------------------------------------------------------------------------


class TestFileNode:
    def test_minimal_construction(self):
        f = FileNode(id="abc", name="report.pdf", mime_type="application/pdf")
        assert f.size_bytes == 0
        assert f.owners == []
        assert f.depth == 0

    def test_full_construction(self):
        f = FileNode(
            id="xyz",
            name="invoice.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            created_at=datetime(2024, 1, 1),
            modified_at=datetime(2024, 6, 1),
            owners=["owner@example.com"],
            parents=["folder_123"],
            depth=3,
        )
        assert f.size_bytes == 1024
        assert f.depth == 3

    def test_json_roundtrip(self):
        f = FileNode(id="abc", name="test.txt", mime_type="text/plain", size_bytes=42)
        restored = FileNode.model_validate_json(f.model_dump_json())
        assert restored == f


# ---------------------------------------------------------------------------
# FolderNode
# ---------------------------------------------------------------------------


class TestFolderNode:
    def _make_file(self, name: str, size: int, depth: int = 1) -> FileNode:
        return FileNode(
            id=name, name=name, mime_type="application/pdf", size_bytes=size, depth=depth
        )

    def test_empty_folder(self):
        folder = FolderNode(id="f1", name="Empty")
        assert folder.total_size_bytes == 0
        assert folder.total_file_count == 0
        assert folder.children == []

    def test_add_file_children_accumulates_stats(self):
        folder = FolderNode(id="f1", name="Docs")
        folder.add_child(self._make_file("a.pdf", 1000))
        folder.add_child(self._make_file("b.pdf", 2000))
        assert folder.total_size_bytes == 3000
        assert folder.total_file_count == 2

    def test_add_nested_folder_accumulates_stats(self):
        child_folder = FolderNode(
            id="child",
            name="Child",
            total_size_bytes=5000,
            total_file_count=3,
            depth=1,
        )
        parent = FolderNode(id="parent", name="Parent")
        parent.add_child(child_folder)
        assert parent.total_size_bytes == 5000
        assert parent.total_file_count == 3

    def test_mixed_children(self):
        folder = FolderNode(id="root", name="Root")
        folder.add_child(self._make_file("a.pdf", 500))
        sub = FolderNode(
            id="sub", name="Sub", total_size_bytes=1500, total_file_count=2, depth=1
        )
        folder.add_child(sub)
        assert folder.total_size_bytes == 2000
        assert folder.total_file_count == 3  # 1 direct + 2 from sub

    def test_json_roundtrip(self):
        folder = FolderNode(id="f1", name="Docs")
        folder.add_child(self._make_file("x.pdf", 100))
        restored = FolderNode.model_validate_json(folder.model_dump_json())
        assert restored.total_size_bytes == folder.total_size_bytes


# ---------------------------------------------------------------------------
# StorageTree
# ---------------------------------------------------------------------------


class TestStorageTree:
    def test_stats_sync_from_tree(self):
        root = FolderNode(id="root", name="My Drive")
        root.add_child(
            FileNode(id="f1", name="a.pdf", mime_type="application/pdf", size_bytes=2048)
        )
        tree = StorageTree(root_id="root", root_name="My Drive", tree=root)
        # Validator should have populated these from the tree.
        assert tree.total_files == 1
        assert tree.total_size_bytes == 2048

    def test_explicit_stats_not_overwritten(self):
        root = FolderNode(id="root", name="My Drive")
        root.add_child(
            FileNode(id="f1", name="a.pdf", mime_type="application/pdf", size_bytes=100)
        )
        # Provide explicit stats (non-zero) — validator should NOT overwrite them.
        tree = StorageTree(
            root_id="root",
            root_name="My Drive",
            tree=root,
            total_files=99,
            total_size_bytes=99999,
        )
        assert tree.total_files == 99
        assert tree.total_size_bytes == 99999


# ---------------------------------------------------------------------------
# HealthReport
# ---------------------------------------------------------------------------


class TestHealthReport:
    def _make_basic_report(self) -> HealthReport:
        root = FolderNode(id="root", name="My Drive")
        root.add_child(
            FileNode(id="f1", name="a.pdf", mime_type="application/pdf", size_bytes=1024)
        )
        tree = StorageTree(root_id="root", root_name="My Drive", tree=root)
        insight = FolderInsight(
            folder_id="root",
            name="My Drive",
            path="My Drive",
            depth=0,
            total_size_bytes=1024,
            total_size_human="1.0 KB",
            file_count=1,
        )
        insights = InsightSummary(
            top_folders=[insight],
            deep_folders=[],
            top_n=10,
            deep_folder_threshold=5,
        )
        return HealthReport(storage_tree=tree, insights=insights)

    def test_construction(self):
        report = self._make_basic_report()
        assert report.schema_version == "0.2.1"
        assert len(report.zombies) == 0
        assert len(report.duplicates) == 0
        assert len(report.action_plan) == 0

    def test_json_roundtrip(self):
        report = self._make_basic_report()
        restored = HealthReport.model_validate_json(report.model_dump_json())
        assert restored.schema_version == report.schema_version
        assert restored.storage_tree.total_size_bytes == 1024

    def test_schema_version_is_string(self):
        report = self._make_basic_report()
        data = report.model_dump()
        assert isinstance(data["schema_version"], str)
