import { NextRequest, NextResponse } from "next/server";
import type { GraphQueryParams, GraphResponse, ApiError } from "../types";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

/**
 * GET /api/proxy/graph
 * 
 * Proxies dependency graph requests to the FastAPI backend.
 * Handles CORS, error handling, and type safety.
 */
export async function GET(request: NextRequest): Promise<NextResponse<GraphResponse | ApiError>> {
  try {
    // Extract and validate query parameters
    const searchParams = request.nextUrl.searchParams;
    const repoName = searchParams.get("repo_name");
    const analysisId = searchParams.get("analysis_id");

    // Validate required parameters
    if (!repoName || repoName.trim().length === 0) {
      return NextResponse.json<ApiError>(
        {
          error: true,
          detail: "repo_name query parameter is required",
          status_code: 400,
        },
        { status: 400 }
      );
    }

    // Build backend URL with query parameters
    const url = new URL(`${BACKEND_URL}/api/graph`);
    url.searchParams.set("repo_name", repoName);
    if (analysisId && analysisId.trim().length > 0) {
      url.searchParams.set("analysis_id", analysisId);
    }

    // Proxy request to FastAPI backend
    let response: Response;
    try {
      response = await fetch(url.toString(), {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        // Timeout after 1 minute
        signal: AbortSignal.timeout(60000),
      });
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return NextResponse.json<ApiError>(
          {
            error: true,
            detail: "Request timeout - graph loading took too long",
            status_code: 504,
          },
          { status: 504 }
        );
      }
      throw error;
    }

    // Parse response
    let data: GraphResponse | ApiError;
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
          detail: errorData.detail || "Failed to get graph",
          status_code: response.status,
        },
        { status: response.status }
      );
    }

    // Validate response structure
    const responseData = data as GraphResponse;
    if (!Array.isArray(responseData.nodes) || !Array.isArray(responseData.edges)) {
      return NextResponse.json<ApiError>(
        {
          error: true,
          detail: "Invalid response format from backend",
          status_code: 502,
        },
        { status: 502 }
      );
    }

    // Return successful response
    return NextResponse.json<GraphResponse>(responseData, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    // Handle unexpected errors
    console.error("Error in graph proxy:", error);
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
