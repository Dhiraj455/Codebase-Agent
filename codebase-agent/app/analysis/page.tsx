"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface AnalysisData {
  success: boolean;
  repo_name: string;
  analysis_id: string;
  file_count: number;
  architecture_summary: {
    architecture_summary?: {
      architecture_type?: string;
      key_modules?: string[];
      data_flow?: string;
      risks?: Array<{ severity: string; description: string }>;
      strengths?: string[];
      recommendations?: string[];
      project_description?: string;
    };
    project_description?: string;
    error?: string;
  };
  code_smells: Array<{
    issue: string;
    severity: string;
    description: string;
    location: string;
    impact: string;
    suggestion?: string;
  }>;
  refactoring_strategies: Array<{
    issue_description: string;
    severity: string;
    suggested_steps: Array<{
      step_number: number;
      description: string;
      rationale: string;
      code_example?: string;
    }>;
    risk_assessment: string;
    estimated_effort: string;
    prerequisites?: string[];
    testing_considerations?: string[];
  }>;
  statistics: {
    files_analyzed: number;
    total_classes: number;
    total_functions: number;
    code_smells_count: number;
    refactoring_strategies_count: number;
    has_python_files?: boolean;
    languages?: string[];
  };
}

export default function AnalysisPage() {
  const router = useRouter();
  
  // Initialize state as null to ensure server/client match
  const [data, setData] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Load data from sessionStorage only on client side
    const storedData = sessionStorage.getItem("analysis_data");
    if (storedData) {
      try {
        const parsedData = JSON.parse(storedData) as AnalysisData;
        setData(parsedData);
        setLoading(false);
      } catch (e) {
        console.error("Failed to parse stored data", e);
        setError("Failed to load analysis data");
        setLoading(false);
      }
    } else {
      // Check if we have analysis_id, redirect if not
      const analysisId = sessionStorage.getItem("analysis_id");
      if (!analysisId) {
        router.push("/");
      } else {
        setLoading(false);
      }
    }
  }, [router]);

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "high":
        return "bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300 border-red-300 dark:border-red-700";
      case "medium":
        return "bg-yellow-100 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-300 border-yellow-300 dark:border-yellow-700";
      case "low":
        return "bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-700";
      default:
        return "bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-300 border-zinc-300 dark:border-zinc-700";
    }
  };

  const getSeverityBadge = (severity: string) => {
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(
          severity
        )}`}
      >
        {severity.toUpperCase()}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-zinc-600 dark:text-zinc-400">Loading analysis...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="text-center">
          <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
          <Link href="/" className="text-blue-600 hover:underline">
            Go back to home
          </Link>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="text-center">
          <p className="text-zinc-600 dark:text-zinc-400 mb-4">No analysis data found</p>
          <Link href="/" className="text-blue-600 hover:underline">
            Start a new analysis
          </Link>
        </div>
      </div>
    );
  }

  const archSummary = data.architecture_summary?.architecture_summary;
  
  // Extract project description from various possible locations
  const projectDescription = 
    archSummary?.project_description || 
    data.architecture_summary?.project_description ||
    "";
  
  // Get languages from statistics
  const languages = data.statistics?.languages || [];

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/"
            className="text-blue-600 hover:underline mb-4 inline-block"
          >
            ← Back to Home
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">
                Analysis Results
              </h1>
              <p className="text-zinc-600 dark:text-zinc-400 mt-2">
                {data.repo_name} • {data.file_count} files analyzed
              </p>
            </div>
            <div className="flex gap-3">
              <Link
                href="/chat"
                className="px-4 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-50 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              >
                Ask Questions
              </Link>
            </div>
          </div>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white dark:bg-zinc-800 rounded-lg p-4 border border-zinc-200 dark:border-zinc-700">
            <p className="text-sm text-zinc-600 dark:text-zinc-400">Files</p>
            <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              {data.statistics?.files_analyzed ?? data.file_count ?? 0}
            </p>
          </div>
          <div className="bg-white dark:bg-zinc-800 rounded-lg p-4 border border-zinc-200 dark:border-zinc-700">
            <div className="flex items-center gap-1">
              <p className="text-sm text-zinc-600 dark:text-zinc-400">Classes</p>
              <span 
                className="text-xs text-zinc-400 dark:text-zinc-500 cursor-help" 
                title="Classes detected from all supported languages (Python, JavaScript, TypeScript, Java, C#, Go, etc.). Classes are object-oriented programming constructs that define blueprints for creating objects."
              >
                ⓘ
              </span>
            </div>
            <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              {data.statistics.total_classes}
            </p>
            {data.statistics.total_classes === 0 && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                No classes found in analyzed code files
              </p>
            )}
          </div>
          <div className="bg-white dark:bg-zinc-800 rounded-lg p-4 border border-zinc-200 dark:border-zinc-700">
            <p className="text-sm text-zinc-600 dark:text-zinc-400">Code Smells</p>
            <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              {data.statistics.code_smells_count}
            </p>
          </div>
          <div className="bg-white dark:bg-zinc-800 rounded-lg p-4 border border-zinc-200 dark:border-zinc-700">
            <p className="text-sm text-zinc-600 dark:text-zinc-400">Refactoring Strategies</p>
            <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              {data.statistics.refactoring_strategies_count}
            </p>
          </div>
        </div>

        {/* Project Description - Always show this section */}
        <div className="bg-white dark:bg-zinc-800 rounded-lg p-6 border border-zinc-200 dark:border-zinc-700 mb-6">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-4">
            Project Description
          </h2>
          {projectDescription ? (
            <p className="text-zinc-900 dark:text-zinc-50 whitespace-pre-wrap mb-4">
              {projectDescription}
            </p>
          ) : (
            <p className="text-zinc-500 dark:text-zinc-400 italic mb-4">
              Project description is being generated or is not available. This section provides a brief explanation of what the repository is about, including its main purpose, technologies used, and architectural approach.
            </p>
          )}
          {languages.length > 0 && (
            <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-700">
              <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
                Languages Used:
              </p>
              <div className="flex flex-wrap gap-2">
                {languages.map((lang: string, idx: number) => (
                  <span
                    key={idx}
                    className="px-3 py-1.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 text-xs font-medium border border-blue-200 dark:border-blue-800 hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                  >
                    {lang}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Architecture Summary */}
        {archSummary && (
          <div className="bg-white dark:bg-zinc-800 rounded-lg p-6 border border-zinc-200 dark:border-zinc-700 mb-6">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-4">
              Architecture Summary
            </h2>
            <div className="space-y-4">
              {archSummary.architecture_type && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                    Architecture Type
                  </h3>
                  <p className="text-zinc-900 dark:text-zinc-50">
                    {archSummary.architecture_type}
                  </p>
                </div>
              )}

              {archSummary.key_modules && archSummary.key_modules.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
                    Key Modules
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {archSummary.key_modules.map((module, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300 text-sm"
                      >
                        {module}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {archSummary.data_flow && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                    Data Flow
                  </h3>
                  <p className="text-zinc-900 dark:text-zinc-50 whitespace-pre-wrap">
                    {archSummary.data_flow}
                  </p>
                </div>
              )}

              {archSummary.risks && archSummary.risks.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
                    Risks
                  </h3>
                  <div className="space-y-2">
                    {archSummary.risks.map((risk, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-2 p-2 rounded border border-zinc-200 dark:border-zinc-700"
                      >
                        {getSeverityBadge(risk.severity)}
                        <p className="text-sm text-zinc-900 dark:text-zinc-50 flex-1">
                          {risk.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {archSummary.strengths && archSummary.strengths.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
                    Strengths
                  </h3>
                  <ul className="list-disc list-inside space-y-1 text-zinc-900 dark:text-zinc-50">
                    {archSummary.strengths.map((strength, idx) => (
                      <li key={idx}>{strength}</li>
                    ))}
                  </ul>
                </div>
              )}

              {archSummary.recommendations && archSummary.recommendations.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
                    Recommendations
                  </h3>
                  <ul className="list-disc list-inside space-y-1 text-zinc-900 dark:text-zinc-50">
                    {archSummary.recommendations.map((rec, idx) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {!archSummary && data.architecture_summary?.error && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6">
            <p className="text-sm text-yellow-800 dark:text-yellow-300">
              Architecture summary unavailable: {data.architecture_summary.error}
            </p>
          </div>
        )}

        {/* Code Smells */}
        <div className="bg-white dark:bg-zinc-800 rounded-lg p-6 border border-zinc-200 dark:border-zinc-700 mb-6">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-4">
            Code Smells ({data.code_smells.length})
          </h2>
          {data.code_smells.length === 0 ? (
            <p className="text-zinc-600 dark:text-zinc-400">
              No code smells detected. Great job! 🎉
            </p>
          ) : (
            <div className="space-y-4">
              {data.code_smells.map((smell, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-zinc-900 dark:text-zinc-50">
                        {smell.issue}
                      </h3>
                      {getSeverityBadge(smell.severity)}
                    </div>
                  </div>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-2">
                    {smell.description}
                  </p>
                  <div className="text-xs text-zinc-500 dark:text-zinc-500 mb-2">
                    <span className="font-medium">Location:</span> {smell.location || "Not specified"}
                  </div>
                  <div className="text-xs text-zinc-500 dark:text-zinc-500 mb-2">
                    <span className="font-medium">Impact:</span> {smell.impact || "Not specified"}
                  </div>
                  {smell.suggestion && (
                    <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-xs text-blue-800 dark:text-blue-300">
                      <span className="font-medium">Suggestion:</span> {smell.suggestion}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Refactoring Strategies */}
        <div className="bg-white dark:bg-zinc-800 rounded-lg p-6 border border-zinc-200 dark:border-zinc-700">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-4">
            Refactoring Strategies ({data.refactoring_strategies.length})
          </h2>
          {data.refactoring_strategies.length === 0 ? (
            <p className="text-zinc-600 dark:text-zinc-400">
              No refactoring strategies available
            </p>
          ) : (
            <div className="space-y-6">
              {data.refactoring_strategies.map((strategy, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-lg border border-zinc-200 dark:border-zinc-700"
                >
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 flex-1">
                      {strategy.issue_description}
                    </h3>
                    {getSeverityBadge(strategy.severity)}
                  </div>

                  <div className="mb-3">
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                      <span className="font-medium">Estimated Effort:</span>{" "}
                      {strategy.estimated_effort}
                    </p>
                  </div>

                  <div className="mb-3">
                    <h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
                      Suggested Steps:
                    </h4>
                    <ol className="list-decimal list-inside space-y-2 ml-2">
                      {strategy.suggested_steps.map((step, stepIdx) => (
                        <li key={stepIdx} className="text-sm text-zinc-900 dark:text-zinc-50">
                          <span className="font-medium">{step.description}</span>
                          <p className="text-xs text-zinc-600 dark:text-zinc-400 ml-6 mt-1">
                            {step.rationale}
                          </p>
                          {step.code_example && (
                            <pre className="text-xs bg-zinc-100 dark:bg-zinc-900 p-2 rounded mt-1 ml-6 overflow-x-auto">
                              {step.code_example}
                            </pre>
                          )}
                        </li>
                      ))}
                    </ol>
                  </div>

                  <div className="mb-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-800">
                    <p className="text-xs font-medium text-yellow-800 dark:text-yellow-300 mb-1">
                      Risk Assessment:
                    </p>
                    <p className="text-xs text-yellow-700 dark:text-yellow-400">
                      {strategy.risk_assessment}
                    </p>
                  </div>

                  {strategy.prerequisites && strategy.prerequisites.length > 0 && (
                    <div className="mb-3">
                      <h4 className="text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                        Prerequisites:
                      </h4>
                      <ul className="list-disc list-inside text-xs text-zinc-600 dark:text-zinc-400 ml-2">
                        {strategy.prerequisites.map((prereq, prereqIdx) => (
                          <li key={prereqIdx}>{prereq}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {strategy.testing_considerations &&
                    strategy.testing_considerations.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                          Testing Considerations:
                        </h4>
                        <ul className="list-disc list-inside text-xs text-zinc-600 dark:text-zinc-400 ml-2">
                          {strategy.testing_considerations.map((consideration, consIdx) => (
                            <li key={consIdx}>{consideration}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
