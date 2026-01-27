import { NextRequest, NextResponse } from "next/server";
import type { AnalyzeRequest, AnalyzeResponse, ApiError } from "../types";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

/**
 * POST /api/proxy/analyze
 * 
 * Proxies repository analysis requests to the FastAPI backend.
 * Handles CORS, error handling, and type safety.
 */
export async function POST(request: NextRequest): Promise<NextResponse<AnalyzeResponse | ApiError>> {
  try {
    // Parse and validate request body
    let body: AnalyzeRequest;
    try {
      body = await request.json();
    } catch (error) {
      return NextResponse.json<ApiError>(
        {
          error: true,
          detail: "Invalid JSON in request body",
          status_code: 400,
        },
        { status: 400 }
      );
    }

    // Validate required fields
    if (!body.repo_url || typeof body.repo_url !== "string") {
      return NextResponse.json<ApiError>(
        {
          error: true,
          detail: "repo_url is required and must be a string",
          status_code: 400,
        },
        { status: 400 }
      );
    }

    // Validate URL format
    try {
      new URL(body.repo_url);
    } catch {
      return NextResponse.json<ApiError>(
        {
          error: true,
          detail: "repo_url must be a valid URL",
          status_code: 400,
        },
        { status: 400 }
      );
    }

    // Proxy request to FastAPI backend
    let response: Response;
    try {
      response = await fetch(`${BACKEND_URL}/api/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify(body),
        // Timeout after 5 minutes (analysis can take time)
        signal: AbortSignal.timeout(300000),
      });
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return NextResponse.json<ApiError>(
          {
            error: true,
            detail: "Request timeout - analysis took too long",
            status_code: 504,
          },
          { status: 504 }
        );
      }
      throw error;
    }

    // Parse response
    let data: AnalyzeResponse | ApiError;
    try {
      data = await response.json();
    } catch (error) {
      return NextResponse.json<ApiError>(
        {
          error: true,
          detail: "Invalid JSON response from backend",
          status_code: 502,
        },
        { status: 502 }
      );
    }

    // Handle backend errors
    if (!response.ok) {
      const errorData = data as ApiError;
      return NextResponse.json<ApiError>(
        {
          error: true,
          detail: errorData.detail || "Analysis failed",
          status_code: response.status,
        },
        { status: response.status }
      );
    }

    // Return successful response
    return NextResponse.json<AnalyzeResponse>(data as AnalyzeResponse, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    // Handle unexpected errors
    console.error("Error in analyze proxy:", error);
    return NextResponse.json<ApiError>(
      {
        error: true,
        detail:
          error instanceof Error
            ? `Internal server error: ${error.message}`
            : "Failed to connect to backend",
        status_code: 500,
      },
      { status: 500 }
    );
  }
}
