from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):

    repo_url: str = Field(..., description="GitHub repository URL to analyze")
    store_name: Optional[str] = Field(
        None, description="Optional name for storing analysis results"
    )


class AnalyzeResponse(BaseModel):

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
    statistics: Dict[str, Any] = Field(..., description="Analysis statistics")


class QuestionRequest(BaseModel):

    question: str = Field(..., description="Question about the codebase")
    analysis_id: Optional[str] = Field(
        None, description="Analysis ID to use for context"
    )
    repo_name: Optional[str] = Field(
        None, description="Repository name to search"
    )


class QuestionResponse(BaseModel):

    answer: str = Field(..., description="LLM-generated answer")
    sources: List[Dict[str, Any]] = Field(
        default=[], description="Source chunks used for answer"
    )


class CodeSmell(BaseModel):

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

    step_number: int = Field(..., description="Ordered step number")
    description: str = Field(..., description="What to do in this step")
    rationale: str = Field(..., description="Why this step is important")
    code_example: Optional[str] = Field(
        default=None, description="Optional code example or pattern to follow"
    )


class RefactoringSuggestion(BaseModel):

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

    step_number: int = Field(..., description="Ordered step number")
    description: str = Field(..., description="What to do in this step")
    rationale: str = Field(..., description="Why this step is important")
    code_example: Optional[str] = Field(
        default=None, description="Optional code example or pattern to follow"
    )


class RefactoringSuggestion(BaseModel):

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
