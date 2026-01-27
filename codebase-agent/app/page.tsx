"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/proxy/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ repo_url: repoUrl }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to analyze repository");
      }

      const data = await response.json();
      
      // Store analysis data in sessionStorage for navigation
      if (data.analysis_id) {
        sessionStorage.setItem("analysis_id", data.analysis_id);
        sessionStorage.setItem("repo_name", data.repo_name);
        sessionStorage.setItem("analysis_data", JSON.stringify(data));
      }

      // Navigate to analysis page
      router.push("/analysis");
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-zinc-50 to-zinc-100 dark:from-zinc-900 dark:to-zinc-800">
      <main className="flex min-h-screen w-full max-w-2xl flex-col items-center justify-center px-6 py-16">
        <div className="w-full space-y-8">
          {/* Header */}
          <div className="text-center space-y-4">
            <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
              Codebase Analysis Agent
          </h1>
            <p className="text-lg text-zinc-600 dark:text-zinc-400">
              Analyze your GitHub repository for architecture insights, code smells, and refactoring opportunities
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleAnalyze} className="space-y-4">
            <div className="space-y-2">
              <label
                htmlFor="repo-url"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
              >
                GitHub Repository URL
              </label>
              <input
                id="repo-url"
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/username/repository"
                required
                className="w-full px-4 py-3 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !repoUrl}
              className="w-full py-3 px-6 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-400 disabled:cursor-not-allowed text-white font-medium transition-colors"
            >
              {loading ? "Analyzing..." : "Analyze Repository"}
            </button>
          </form>

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8">
            <div className="p-4 rounded-lg bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 mb-2">
                Architecture Analysis
              </h3>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Understand your codebase structure and design patterns
              </p>
            </div>
            <div className="p-4 rounded-lg bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 mb-2">
                Code Smell Detection
              </h3>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Identify issues and anti-patterns automatically
              </p>
            </div>
            <div className="p-4 rounded-lg bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 mb-2">
                Refactoring Guidance
              </h3>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Get actionable refactoring strategies
          </p>
        </div>
          </div>
        </div>
      </main>
    </div>
  );
}
