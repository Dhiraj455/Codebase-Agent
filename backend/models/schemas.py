"""
Pydantic models for API request/response schemas.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request model for repository analysis."""

    repo_url: str = Field(..., description="GitHub repository URL to analyze")
    store_name: Optional[str] = Field(
        None, description="Optional name for storing analysis results"
    )


class AnalyzeResponse(BaseModel):
    """Response model for repository analysis."""

    success: bool = Field(..., description="Whether analysis was successful")
    repo_name: str = Field(..., description="Name of the analyzed repository")
    analysis_id: str = Field(..., description="Unique identifier for this analysis")
    file_count: int = Field(..., description="Number of Python files analyzed")
    architecture_summary: Dict[str, Any] = Field(
        ..., description="Architecture analysis summary"
    )
    code_smells: List[Dict[str, Any]] = Field(
        ..., description="List of detected code smells"
    )
    refactoring_strategies: List[Dict[str, Any]] = Field(
        ..., description="List of refactoring strategies"
    )
    dependency_graph: Dict[str, Any] = Field(
        ..., description="Dependency graph data"
    )
    statistics: Dict[str, Any] = Field(..., description="Analysis statistics")


class QuestionRequest(BaseModel):
    """Request model for asking questions."""

    question: str = Field(..., description="Question about the codebase")
    analysis_id: Optional[str] = Field(
        None, description="Analysis ID to use for context"
    )
    repo_name: Optional[str] = Field(
        None, description="Repository name to search"
    )


class QuestionResponse(BaseModel):
    """Response model for questions."""

    answer: str = Field(..., description="LLM-generated answer")
    sources: List[Dict[str, Any]] = Field(
        default=[], description="Source chunks used for answer"
    )


class GraphRequest(BaseModel):
    """Request model for getting dependency graph."""

    repo_name: str = Field(..., description="Repository name")
    analysis_id: Optional[str] = Field(
        None, description="Analysis ID (optional)"
    )


class GraphResponse(BaseModel):
    """Response model for dependency graph."""

    nodes: List[Dict[str, Any]] = Field(..., description="Graph nodes")
    edges: List[Dict[str, Any]] = Field(..., description="Graph edges")
    cycles: List[List[str]] = Field(..., description="Detected cycles")
    statistics: Dict[str, Any] = Field(..., description="Graph statistics")


class CodeSmell(BaseModel):
    """Model for a code smell/issue."""

    issue: str = Field(..., description="Name of the code smell or issue")
    severity: str = Field(
        ..., description="Severity level: high, medium, or low"
    )
    description: str = Field(..., description="Detailed description of the issue")
    location: str = Field(..., description="File or module where the issue is found")
    impact: str = Field(..., description="Impact of this issue on the codebase")
    suggestion: Optional[str] = Field(
        default=None, description="Suggestion for fixing the issue"
    )


class RefactoringStep(BaseModel):
    """Model for a single refactoring step."""

    step_number: int = Field(..., description="Ordered step number")
    description: str = Field(..., description="What to do in this step")
    rationale: str = Field(..., description="Why this step is important")
    code_example: Optional[str] = Field(
        default=None, description="Optional code example or pattern to follow"
    )


class RefactoringSuggestion(BaseModel):
    """Model for a complete refactoring strategy."""

    issue_description: str = Field(
        ..., description="Description of the issue being addressed"
    )
    severity: str = Field(..., description="Severity level: high, medium, or low")
    suggested_steps: List[RefactoringStep] = Field(
        ..., description="Ordered list of refactoring steps"
    )
    risk_assessment: str = Field(
        ..., description="Assessment of risks involved in this refactoring"
    )
    estimated_effort: str = Field(
        ..., description="Estimated effort (e.g., '2-4 hours', '1 day', '1 week')"
    )
    prerequisites: List[str] = Field(
        default=[],
        description="Prerequisites or dependencies for this refactoring",
    )
    testing_considerations: List[str] = Field(
        default=[],
        description="Testing considerations and recommendations",
    )


class CodeSmell(BaseModel):
    """Model for a code smell/issue."""

    issue: str = Field(..., description="Name of the code smell or issue")
    severity: str = Field(
        ..., description="Severity level: high, medium, or low"
    )
    description: str = Field(..., description="Detailed description of the issue")
    location: str = Field(..., description="File or module where the issue is found")
    impact: str = Field(..., description="Impact of this issue on the codebase")
    suggestion: Optional[str] = Field(
        default=None, description="Suggestion for fixing the issue"
    )


class RefactoringStep(BaseModel):
    """Model for a single refactoring step."""

    step_number: int = Field(..., description="Ordered step number")
    description: str = Field(..., description="What to do in this step")
    rationale: str = Field(..., description="Why this step is important")
    code_example: Optional[str] = Field(
        default=None, description="Optional code example or pattern to follow"
    )


class RefactoringSuggestion(BaseModel):
    """Model for a complete refactoring strategy."""

    issue_description: str = Field(
        ..., description="Description of the issue being addressed"
    )
    severity: str = Field(..., description="Severity level: high, medium, or low")
    suggested_steps: List[RefactoringStep] = Field(
        ..., description="Ordered list of refactoring steps"
    )
    risk_assessment: str = Field(
        ..., description="Assessment of risks involved in this refactoring"
    )
    estimated_effort: str = Field(
        ..., description="Estimated effort (e.g., '2-4 hours', '1 day', '1 week')"
    )
    prerequisites: List[str] = Field(
        default=[],
        description="Prerequisites or dependencies for this refactoring",
    )
    testing_considerations: List[str] = Field(
        default=[],
        description="Testing considerations and recommendations",
    )
