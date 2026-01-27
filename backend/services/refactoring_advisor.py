"""
Refactoring Strategy Generator Service

Generates incremental refactoring suggestions based on code smells and issues.
Important: Does NOT rewrite code, only suggests actionable steps.
"""

import json
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from .code_smell_detector import CodeSmellDetector
from .llm_reasoner import LLMReasoner


class RefactoringStep(BaseModel):
    """A single refactoring step."""

    step_number: int = Field(description="Ordered step number")
    description: str = Field(description="What to do in this step")
    rationale: str = Field(description="Why this step is important")
    code_example: Optional[str] = Field(
        default=None, description="Optional code example or pattern to follow"
    )


class RefactoringStrategy(BaseModel):
    """Complete refactoring strategy for an issue."""

    issue_description: str = Field(description="Description of the issue being addressed")
    severity: str = Field(description="Severity level: high, medium, or low")
    suggested_steps: List[RefactoringStep] = Field(
        description="Ordered list of refactoring steps"
    )
    risk_assessment: str = Field(
        description="Assessment of risks involved in this refactoring"
    )
    estimated_effort: str = Field(
        description="Estimated effort (e.g., '2-4 hours', '1 day', '1 week')"
    )
    prerequisites: List[str] = Field(
        default=[],
        description="Prerequisites or dependencies for this refactoring"
    )
    testing_considerations: List[str] = Field(
        default=[],
        description="Testing considerations and recommendations"
    )


class RefactoringAdvisor:
    """Service for generating refactoring strategies."""

    def __init__(
        self,
        code_smell_detector: Optional[CodeSmellDetector] = None,
        llm_reasoner: Optional[LLMReasoner] = None,
    ):
        """
        Initialize the refactoring advisor.

        Args:
            code_smell_detector: Optional CodeSmellDetector instance
            llm_reasoner: Optional LLMReasoner instance
        """
        self.code_smell_detector = code_smell_detector or CodeSmellDetector()
        self.llm_reasoner = llm_reasoner

    def generate_refactoring_strategies(
        self,
        code_smells: List[Dict[str, Any]],
        file_analyses: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate refactoring strategies for detected code smells.

        Args:
            code_smells: List of detected code smells
            file_analyses: Optional file analyses for additional context

        Returns:
            List of refactoring strategies
        """
        strategies = []

        # Group smells by issue type for batch processing
        smells_by_issue = {}
        for smell in code_smells:
            issue_type = smell.get("issue", "Unknown")
            if issue_type not in smells_by_issue:
                smells_by_issue[issue_type] = []
            smells_by_issue[issue_type].append(smell)

        # Generate strategy for each unique issue type
        for issue_type, smells in smells_by_issue.items():
            # Use the highest severity smell as the primary one
            primary_smell = max(smells, key=lambda s: self._severity_value(s.get("severity", "low")))

            if self.llm_reasoner:
                # Use LLM for nuanced refactoring strategies
                strategy = self._generate_llm_strategy(primary_smell, smells, file_analyses)
            else:
                # Use rule-based strategies
                strategy = self._generate_rule_based_strategy(primary_smell, smells)

            if strategy:
                strategies.append(strategy)

        # Sort by severity (high priority first)
        strategies.sort(key=lambda s: self._severity_value(s.get("severity", "low")))

        return strategies

    def _generate_llm_strategy(
        self,
        primary_smell: Dict[str, Any],
        related_smells: List[Dict[str, Any]],
        file_analyses: Optional[List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """
        Generate refactoring strategy using LLM.

        Args:
            primary_smell: Primary code smell to address
            related_smells: Related smells of the same type
            file_analyses: Optional file analyses for context

        Returns:
            Refactoring strategy dictionary
        """
        if not self.llm_reasoner:
            return None

        # Build context
        context = {
            "issue": primary_smell.get("issue", ""),
            "description": primary_smell.get("description", ""),
            "location": primary_smell.get("location", ""),
            "impact": primary_smell.get("impact", ""),
            "suggestion": primary_smell.get("suggestion", ""),
            "severity": primary_smell.get("severity", "medium"),
            "related_occurrences": len(related_smells),
        }

        # Add file context if available
        if file_analyses:
            # Find relevant file analysis
            location = primary_smell.get("location", "")
            for analysis in file_analyses:
                if analysis.get("file_name", "") in location:
                    context["file_context"] = {
                        "file_name": analysis.get("file_name", ""),
                        "classes": [
                            {
                                "name": cls["name"],
                                "methods": len(cls.get("methods", [])),
                            }
                            for cls in analysis.get("classes", [])[:5]
                        ],
                        "functions": [
                            {
                                "name": func["name"],
                                "parameters": func.get("parameter_count", 0),
                            }
                            for func in analysis.get("functions", [])[:5]
                        ],
                    }
                    break

        # Build prompt
        prompt = f"""You are a senior software engineer providing refactoring guidance.

## Issue to Address:
**Issue Type:** {context['issue']}
**Description:** {context['description']}
**Location:** {context['location']}
**Impact:** {context['impact']}
**Severity:** {context['severity']}
**Occurrences:** {context['related_occurrences']} similar issues found

## Current Suggestion:
{context.get('suggestion', 'None provided')}

## Your Task:
Generate a detailed, incremental refactoring strategy. **IMPORTANT: Do NOT rewrite code. Only provide step-by-step guidance.**

The strategy should include:
1. **Suggested Steps**: Ordered, incremental steps that can be done one at a time
2. **Risk Assessment**: What could go wrong and how to mitigate
3. **Estimated Effort**: Realistic time estimate
4. **Prerequisites**: What needs to be in place first
5. **Testing Considerations**: How to ensure nothing breaks

Each step should:
- Be actionable and specific
- Build on previous steps
- Be testable independently
- Minimize risk

Return a JSON object with this structure:
{{
    "issue_description": "description of the issue",
    "severity": "high|medium|low",
    "suggested_steps": [
        {{
            "step_number": 1,
            "description": "what to do",
            "rationale": "why this step",
            "code_example": "optional example pattern"
        }},
        ...
    ],
    "risk_assessment": "assessment of risks",
    "estimated_effort": "e.g., '2-4 hours'",
    "prerequisites": ["prerequisite1", ...],
    "testing_considerations": ["consideration1", ...]
}}

Focus on incremental, safe refactoring. Do not provide full code rewrites.
"""

        try:
            response = self.llm_reasoner.client.chat.completions.create(
                model=self.llm_reasoner.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior software engineer. Always respond with valid JSON only. Never rewrite entire code, only provide guidance.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            content = response.choices[0].message.content

            # Parse JSON
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract from markdown
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_data = json.loads(content[json_start:json_end].strip())
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    json_data = json.loads(content[json_start:json_end].strip())
                else:
                    raise ValueError("Failed to parse JSON from LLM response")

            # Validate with Pydantic
            validated = RefactoringStrategy(**json_data)
            return validated.model_dump()

        except Exception as e:
            print(f"LLM strategy generation failed: {e}")
            # Fallback to rule-based
            return self._generate_rule_based_strategy(primary_smell, related_smells)

    def _generate_rule_based_strategy(
        self, primary_smell: Dict[str, Any], related_smells: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate refactoring strategy using rule-based approach.

        Args:
            primary_smell: Primary code smell
            related_smells: Related smells

        Returns:
            Refactoring strategy dictionary
        """
        issue_type = primary_smell.get("issue", "")
        severity = primary_smell.get("severity", "medium")

        # Rule-based strategies for common issues
        strategies = {
            "God Class": self._god_class_strategy(primary_smell, related_smells),
            "High Cyclomatic Complexity": self._complexity_strategy(
                primary_smell, related_smells
            ),
            "Circular Dependency": self._circular_dependency_strategy(
                primary_smell, related_smells
            ),
            "Tight Coupling": self._tight_coupling_strategy(primary_smell, related_smells),
            "Missing Docstring": self._docstring_strategy(primary_smell, related_smells),
            "Large Function": self._large_function_strategy(primary_smell, related_smells),
            "Too Many Parameters": self._many_parameters_strategy(
                primary_smell, related_smells
            ),
        }

        # Get strategy or use generic one
        strategy = strategies.get(issue_type, self._generic_strategy(primary_smell))

        return strategy

    def _god_class_strategy(
        self, smell: Dict[str, Any], related: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate strategy for God Class refactoring."""
        return {
            "issue_description": smell.get("description", ""),
            "severity": smell.get("severity", "high"),
            "suggested_steps": [
                {
                    "step_number": 1,
                    "description": "Identify distinct responsibilities within the class",
                    "rationale": "Understanding responsibilities helps determine how to split",
                    "code_example": "List all methods and group them by responsibility",
                },
                {
                    "step_number": 2,
                    "description": "Extract one responsibility into a new class",
                    "rationale": "Start with the most independent responsibility to minimize risk",
                    "code_example": "Create NewClass with related methods, keep original class as composition",
                },
                {
                    "step_number": 3,
                    "description": "Update original class to use the new class",
                    "rationale": "Maintain functionality while reducing complexity",
                    "code_example": "Replace direct method calls with delegation to new class",
                },
                {
                    "step_number": 4,
                    "description": "Run tests to ensure behavior is unchanged",
                    "rationale": "Verify refactoring didn't break anything",
                },
                {
                    "step_number": 5,
                    "description": "Repeat steps 2-4 for remaining responsibilities",
                    "rationale": "Incremental approach reduces risk",
                },
            ],
            "risk_assessment": "Medium risk. Breaking a large class can affect many parts of the system. Ensure comprehensive test coverage before starting.",
            "estimated_effort": "1-3 days depending on class size and test coverage",
            "prerequisites": [
                "Comprehensive test suite",
                "Understanding of class responsibilities",
                "Clear separation of concerns identified",
            ],
            "testing_considerations": [
                "Ensure all existing tests pass before refactoring",
                "Add tests for new classes",
                "Test integration between original and new classes",
            ],
        }

    def _complexity_strategy(
        self, smell: Dict[str, Any], related: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate strategy for high complexity refactoring."""
        return {
            "issue_description": smell.get("description", ""),
            "severity": smell.get("severity", "medium"),
            "suggested_steps": [
                {
                    "step_number": 1,
                    "description": "Identify complex conditional logic or nested structures",
                    "rationale": "Understanding complexity sources guides extraction",
                },
                {
                    "step_number": 2,
                    "description": "Extract complex conditions into well-named boolean methods",
                    "rationale": "Improves readability and reduces nesting",
                    "code_example": "if complex_condition: -> if is_valid_and_ready():",
                },
                {
                    "step_number": 3,
                    "description": "Extract repeated logic into helper functions",
                    "rationale": "Reduces duplication and complexity",
                },
                {
                    "step_number": 4,
                    "description": "Use early returns to reduce nesting",
                    "rationale": "Flattens control flow",
                    "code_example": "if not condition: return early",
                },
                {
                    "step_number": 5,
                    "description": "Test each extracted function independently",
                    "rationale": "Ensures correctness of refactored code",
                },
            ],
            "risk_assessment": "Low to medium risk. Complexity reduction improves maintainability but requires careful testing.",
            "estimated_effort": "2-6 hours per function",
            "prerequisites": ["Function-level tests", "Understanding of function logic"],
            "testing_considerations": [
                "Test extracted functions in isolation",
                "Ensure original function behavior is preserved",
                "Test edge cases for extracted conditions",
            ],
        }

    def _circular_dependency_strategy(
        self, smell: Dict[str, Any], related: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate strategy for circular dependency refactoring."""
        return {
            "issue_description": smell.get("description", ""),
            "severity": smell.get("severity", "high"),
            "suggested_steps": [
                {
                    "step_number": 1,
                    "description": "Identify shared dependencies or common abstractions",
                    "rationale": "Finding common ground helps break the cycle",
                },
                {
                    "step_number": 2,
                    "description": "Extract shared code into a new module or interface",
                    "rationale": "Creates a dependency that both modules can use",
                    "code_example": "Create interfaces.py or common.py",
                },
                {
                    "step_number": 3,
                    "description": "Refactor one module to depend on the abstraction instead",
                    "rationale": "Breaks the direct dependency",
                },
                {
                    "step_number": 4,
                    "description": "Refactor the other module similarly",
                    "rationale": "Completes the cycle break",
                },
                {
                    "step_number": 5,
                    "description": "Verify no circular dependencies remain",
                    "rationale": "Ensures the issue is resolved",
                },
            ],
            "risk_assessment": "High risk. Circular dependencies often indicate architectural issues. Requires careful analysis and may need broader refactoring.",
            "estimated_effort": "1-2 days",
            "prerequisites": [
                "Clear understanding of module dependencies",
                "Architectural review",
                "Test coverage for affected modules",
            ],
            "testing_considerations": [
                "Test both modules independently",
                "Test integration between modules",
                "Verify no functionality is lost",
            ],
        }

    def _tight_coupling_strategy(
        self, smell: Dict[str, Any], related: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate strategy for tight coupling refactoring."""
        return {
            "issue_description": smell.get("description", ""),
            "severity": smell.get("severity", "medium"),
            "suggested_steps": [
                {
                    "step_number": 1,
                    "description": "Identify which dependencies are actually needed",
                    "rationale": "Understanding true dependencies guides decoupling",
                },
                {
                    "step_number": 2,
                    "description": "Introduce interfaces or abstract base classes for dependencies",
                    "rationale": "Allows dependency inversion",
                    "code_example": "Create IDataStore interface instead of direct DB dependency",
                },
                {
                    "step_number": 3,
                    "description": "Refactor to depend on interfaces instead of concrete classes",
                    "rationale": "Reduces coupling to specific implementations",
                },
                {
                    "step_number": 4,
                    "description": "Use dependency injection to provide implementations",
                    "rationale": "Makes dependencies explicit and testable",
                },
                {
                    "step_number": 5,
                    "description": "Test with mock implementations",
                    "rationale": "Verifies decoupling and improves testability",
                },
            ],
            "risk_assessment": "Medium risk. Decoupling improves testability but requires careful interface design.",
            "estimated_effort": "1-2 days",
            "prerequisites": [
                "Understanding of dependency injection patterns",
                "Interface design knowledge",
            ],
            "testing_considerations": [
                "Create mock implementations for testing",
                "Test with different implementations",
                "Verify behavior is unchanged",
            ],
        }

    def _docstring_strategy(
        self, smell: Dict[str, Any], related: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate strategy for missing docstring refactoring."""
        return {
            "issue_description": smell.get("description", ""),
            "severity": smell.get("severity", "low"),
            "suggested_steps": [
                {
                    "step_number": 1,
                    "description": "Add docstring describing the class/function purpose",
                    "rationale": "Improves code documentation and maintainability",
                    "code_example": '"""Brief description of what this does."""',
                },
                {
                    "step_number": 2,
                    "description": "Document parameters and return values (for functions)",
                    "rationale": "Helps users understand the API",
                },
                {
                    "step_number": 3,
                    "description": "Add usage examples if complex",
                    "rationale": "Examples clarify usage",
                },
            ],
            "risk_assessment": "Very low risk. Adding documentation doesn't change behavior.",
            "estimated_effort": "15-30 minutes per item",
            "prerequisites": ["Understanding of the code being documented"],
            "testing_considerations": [
                "No testing needed for documentation",
                "Consider adding doctests for examples",
            ],
        }

    def _large_function_strategy(
        self, smell: Dict[str, Any], related: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate strategy for large function refactoring."""
        return {
            "issue_description": smell.get("description", ""),
            "severity": smell.get("severity", "medium"),
            "suggested_steps": [
                {
                    "step_number": 1,
                    "description": "Identify logical sections within the function",
                    "rationale": "Understanding structure guides extraction",
                },
                {
                    "step_number": 2,
                    "description": "Extract one section into a helper function",
                    "rationale": "Reduces function size incrementally",
                },
                {
                    "step_number": 3,
                    "description": "Test the extracted function",
                    "rationale": "Ensures correctness",
                },
                {
                    "step_number": 4,
                    "description": "Update original function to call helper",
                    "rationale": "Maintains functionality",
                },
                {
                    "step_number": 5,
                    "description": "Repeat for remaining sections",
                    "rationale": "Incremental approach",
                },
            ],
            "risk_assessment": "Low to medium risk. Function extraction is generally safe with good tests.",
            "estimated_effort": "2-4 hours per function",
            "prerequisites": ["Function-level tests"],
            "testing_considerations": [
                "Test extracted functions independently",
                "Test original function still works correctly",
            ],
        }

    def _many_parameters_strategy(
        self, smell: Dict[str, Any], related: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate strategy for too many parameters refactoring."""
        return {
            "issue_description": smell.get("description", ""),
            "severity": smell.get("severity", "medium"),
            "suggested_steps": [
                {
                    "step_number": 1,
                    "description": "Identify related parameters that can be grouped",
                    "rationale": "Grouping reduces parameter count",
                },
                {
                    "step_number": 2,
                    "description": "Create a data class or configuration object for related parameters",
                    "rationale": "Encapsulates related data",
                    "code_example": "@dataclass class UserConfig: name: str, email: str",
                },
                {
                    "step_number": 3,
                    "description": "Refactor function to accept the data class",
                    "rationale": "Reduces parameter count",
                },
                {
                    "step_number": 4,
                    "description": "Update all call sites",
                    "rationale": "Maintains compatibility",
                },
                {
                    "step_number": 5,
                    "description": "Test function with new signature",
                    "rationale": "Ensures correctness",
                },
            ],
            "risk_assessment": "Low risk. Parameter grouping is straightforward but requires updating call sites.",
            "estimated_effort": "1-3 hours",
            "prerequisites": ["Understanding of all call sites"],
            "testing_considerations": [
                "Test function with new parameter structure",
                "Verify all call sites are updated",
            ],
        }

    def _generic_strategy(self, smell: Dict[str, Any]) -> Dict[str, Any]:
        """Generic strategy for unknown issue types."""
        return {
            "issue_description": smell.get("description", ""),
            "severity": smell.get("severity", "medium"),
            "suggested_steps": [
                {
                    "step_number": 1,
                    "description": "Analyze the issue and understand its root cause",
                    "rationale": "Understanding is essential for effective refactoring",
                },
                {
                    "step_number": 2,
                    "description": "Design a solution that addresses the root cause",
                    "rationale": "Addressing symptoms doesn't solve the problem",
                },
                {
                    "step_number": 3,
                    "description": "Implement the solution incrementally",
                    "rationale": "Incremental changes reduce risk",
                },
                {
                    "step_number": 4,
                    "description": "Test thoroughly after each change",
                    "rationale": "Ensures correctness",
                },
            ],
            "risk_assessment": "Risk depends on the specific issue. Analyze carefully before proceeding.",
            "estimated_effort": "Varies by issue complexity",
            "prerequisites": ["Understanding of the issue", "Test coverage"],
            "testing_considerations": [
                "Ensure comprehensive test coverage",
                "Test incrementally",
            ],
        }

    def _severity_value(self, severity: str) -> int:
        """Convert severity string to numeric value for sorting."""
        severity_map = {"high": 0, "medium": 1, "low": 2}
        return severity_map.get(severity.lower(), 2)


# Example usage
if __name__ == "__main__":
    # Example: Generate refactoring strategies
    # advisor = RefactoringAdvisor()
    #
    # code_smells = [...]  # From code_smell_detector
    # file_analyses = [...]  # From code_analyzer
    #
    # strategies = advisor.generate_refactoring_strategies(code_smells, file_analyses)
    #
    # for strategy in strategies:
    #     print(f"\n{strategy['severity'].upper()}: {strategy['issue_description']}")
    #     print(f"Effort: {strategy['estimated_effort']}")
    #     print("Steps:")
    #     for step in strategy['suggested_steps']:
    #         print(f"  {step['step_number']}. {step['description']}")
    pass  # Placeholder for example code
