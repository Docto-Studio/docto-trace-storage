import sys
from unittest.mock import MagicMock, patch, AsyncMock
sys.modules['litellm'] = MagicMock()

from docto_trace.engine.ai_readiness import (
    _categorize_file,
    _score_naming_entropy,
    build_ai_readiness_summary,
)
from docto_trace.schemas.report import FileTypeCategory
from docto_trace.schemas.storage import FileNode, FolderNode, StorageTree


def test_categorize_file():
    # Structured by mimtype
    f1 = FileNode(id="1", name="data", mime_type="text/csv")
    assert _categorize_file(f1) == FileTypeCategory.STRUCTURED
    
    # Structured by extension
    f2 = FileNode(id="2", name="data.json", mime_type="application/octet-stream")
    assert _categorize_file(f2) == FileTypeCategory.STRUCTURED
    
    # Unstructured
    f3 = FileNode(id="3", name="image.jpg", mime_type="image/jpeg")
    assert _categorize_file(f3) == FileTypeCategory.UNSTRUCTURED


def test_score_naming_entropy():
    # Bad names
    assert _score_naming_entropy("IMG_1234.jpg") == 10.0
    assert _score_naming_entropy("DSC001.png") == 10.0
    assert _score_naming_entropy("Untitled document") == 10.0
    assert _score_naming_entropy("1234") == 10.0
    assert _score_naming_entropy("cat") == 20.0
    
    # Okay names (1 word)
    assert _score_naming_entropy("Receipts.pdf") == 30.0
    assert _score_naming_entropy("Project") == 30.0
    
    # Good names (2 words)
    assert _score_naming_entropy("Financial Report.xlsx") == 60.0
    
    # Great names (3+ words)
    assert _score_naming_entropy("Q1 Financial Report.pdf") == 80.0
    assert _score_naming_entropy("My Vacation Photos Italy.zip") == 80.0
    
    # Excellent names (words + date)
    assert _score_naming_entropy("2023_Financial_Report.pdf") == 100.0  # 80 + 20
    assert _score_naming_entropy("Meeting_Notes_2024-03-15.docx") == 100.0


def test_build_ai_readiness_summary_no_llm():
    root = FolderNode(id="root", name="Root Folder")
    f1 = FileNode(id="f1", name="2023_Financial_Report.pdf", mime_type="application/pdf", size_bytes=100)
    f2 = FileNode(id="f2", name="data.csv", mime_type="text/csv", size_bytes=200)
    root.add_child(f1)
    root.add_child(f2)
    
    tree = StorageTree(root_id="root", root_name="Root Folder", tree=root)
    
    summary = build_ai_readiness_summary(tree, llm_model=None)
    
    assert summary.structured_files_count == 1
    assert summary.unstructured_files_count == 1
    assert summary.structured_bytes == 200
    assert summary.unstructured_bytes == 100
    
    # f1 score is 100, f2 ("data") score is 20 => avg 60.0
    assert summary.naming_entropy_score == 60.0
    assert summary.ai_analysis_report is None


@patch("litellm.acompletion", new_callable=AsyncMock)
def test_build_ai_readiness_summary_with_llm(mock_acompletion):
    # Mock Litellm completion response to use a tool call immediately
    mock_response = MagicMock()
    
    mock_msg = MagicMock()
    mock_msg.content = None
    
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_xyz123"
    mock_tool_call.function.name = "finalize_report"
    mock_tool_call.function.arguments = '{"qualitative_review": "Great chaos.", "tactical_plan": ["Buy folders."]}'
    
    # `dict(tc)` won't directly work out of the box for MagicMocks natively if called in dict
    # We supply a special mock object that provides __iter__ for dict()
    class DictMockTool:
        def __init__(self, id, name, args):
            self.id = id
            self.function = MagicMock()
            self.function.name = name
            self.function.arguments = args
            
        def __iter__(self):
            yield "id", self.id
            yield "type", "function"
            yield "function", {"name": self.function.name, "arguments": self.function.arguments}
            
    mock_msg.tool_calls = [DictMockTool("c1", "finalize_report", '{"qualitative_review": "Great chaos.", "tactical_plan": ["Buy folders."]}')]
    
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = mock_msg
    
    mock_acompletion.return_value = mock_response

    root = FolderNode(id="root", name="Root Folder")
    f1 = FileNode(id="f1", name="2023_Financial_Report.pdf", mime_type="application/pdf", size_bytes=100)
    root.add_child(f1)
    tree = StorageTree(root_id="root", root_name="Root Folder", tree=root)
    
    summary = build_ai_readiness_summary(tree, llm_model="fake/model")
    
    assert "Great chaos." in summary.ai_analysis_report
    assert "Buy folders." in summary.ai_analysis_report
    assert mock_acompletion.call_count == 1
