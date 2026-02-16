

import json
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from .code_smell_detector import CodeSmellDetector
from .llm_reasoner import LLMReasoner


class RefactoringStep(BaseModel):


    step_number: int = Field(description="Ordered step number")
    description: str = Field(description="What to do in this step")
    rationale: str = Field(description="Why this step is important")
    code_example: Optional[str] = Field(
        default=None, description="Optional code example or pattern to follow"
    )


class RefactoringStrategy(BaseModel):


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


    def __init__(
        self,
        code_smell_detector: Optional[CodeSmellDetector] = None,
        llm_reasoner: Optional[LLMReasoner] = None,
    ):

        self.code_smell_detector = code_smell_detector or CodeSmellDetector()
        self.llm_reasoner = llm_reasoner

    def generate_refactoring_strategies(
        self,
        code_smells: List[Dict[str, Any]],
        file_analyses: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:

        strategies = []

        smells_by_issue = {}
        for smell in code_smells:
            issue_type = smell.get("issue", "Unknown")
            if issue_type not in smells_by_issue:
                smells_by_issue[issue_type] = []
            smells_by_issue[issue_type].append(smell)

        for issue_type, smells in smells_by_issue.items():
            primary_smell = max(smells, key=lambda s: self._severity_value(s.get("severity", "low")))

            if self.llm_reasoner:
                strategy = self._generate_llm_strategy(primary_smell, smells, file_analyses)
            else:
                strategy = self._generate_rule_based_strategy(primary_smell, smells)

            if strategy:
                strategies.append(strategy)

        strategies.sort(key=lambda s: self._severity_value(s.get("severity", "low")))

        return strategies

    def _generate_llm_strategy(
        self,
        primary_smell: Dict[str, Any],
        related_smells: List[Dict[str, Any]],
        file_analyses: Optional[List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:

        if not self.llm_reasoner:
            return None

        context = {
            "issue": primary_smell.get("issue", ""),
            "description": primary_smell.get("description", ""),
            "location": primary_smell.get("location", ""),
            "impact": primary_smell.get("impact", ""),
            "suggestion": primary_smell.get("suggestion", ""),
            "severity": primary_smell.get("severity", "medium"),
            "related_occurrences": len(related_smells),
        }

        if file_analyses:
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

        prompt = f

        try:
            import google.generativeai as genai

            full_prompt = f

            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
                response_mime_type="application/json",
            )

            response = self.llm_reasoner.model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            content = response.text

            try:
                json_data = json.loads(content)
            except json.JSONDecodeError:
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

            validated = RefactoringStrategy(**json_data)
            return validated.model_dump()

        except Exception as e:
            print(f"LLM strategy generation failed: {e}")
            return self._generate_rule_based_strategy(primary_smell, related_smells)

    def _generate_rule_based_strategy(
        self, primary_smell: Dict[str, Any], related_smells: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        issue_type = primary_smell.get("issue", "")
        severity = primary_smell.get("severity", "medium")

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

        strategy = strategies.get(issue_type, self._generic_strategy(primary_smell))

        return strategy

    def _god_class_strategy(
        self, smell: Dict[str, Any], related: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

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

        return {
            "issue_description": smell.get("description", ""),
            "severity": smell.get("severity", "low"),
            "suggested_steps": [
                {
                    "step_number": 1,
                    "description": "Add docstring describing the class/function purpose",
                    "rationale": "Improves code documentation and maintainability",
                    "code_example": '',
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

        severity_map = {"high": 0, "medium": 1, "low": 2}
        return severity_map.get(severity.lower(), 2)


if __name__ == "__main__":
    pass
