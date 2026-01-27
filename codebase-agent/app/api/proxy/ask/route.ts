import { NextRequest, NextResponse } from "next/server";
import type { QuestionRequest, QuestionResponse, ApiError } from "../types";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

/**
 * POST /api/proxy/ask
 * 
 * Proxies question requests to the FastAPI backend for RAG-based answers.
 * Handles CORS, error handling, and type safety.
 */
export async function POST(request: NextRequest): Promise<NextResponse<QuestionResponse | ApiError>> {
  try {
    // Parse and validate request body
    let body: QuestionRequest;
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
    if (!body.question || typeof body.question !== "string" || body.question.trim().length === 0) {
      return NextResponse.json<ApiError>(
        {
          error: true,
          detail: "question is required and must be a non-empty string",
          status_code: 400,
        },
        { status: 400 }
      );
    }

    // Validate that either analysis_id or repo_name is provided
    if (!body.analysis_id && !body.repo_name) {
      return NextResponse.json<ApiError>(
        {
          error: true,
          detail: "Either analysis_id or repo_name must be provided",
          status_code: 400,
        },
        { status: 400 }
      );
    }

    // Proxy request to FastAPI backend
    let response: Response;
    try {
      response = await fetch(`${BACKEND_URL}/api/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify(body),
        // Timeout after 2 minutes
        signal: AbortSignal.timeout(120000),
      });
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return NextResponse.json<ApiError>(
          {
            error: true,
            detail: "Request timeout - question processing took too long",
            status_code: 504,
          },
          { status: 504 }
        );
      }
      throw error;
    }

    // Parse response
    let data: QuestionResponse | ApiError;
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
          detail: errorData.detail || "Failed to get answer",
          status_code: response.status,
        },
        { status: response.status }
      );
    }

    // Validate response structure
    const responseData = data as QuestionResponse;
    if (!responseData.answer || typeof responseData.answer !== "string") {
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
    return NextResponse.json<QuestionResponse>(responseData, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    // Handle unexpected errors
    console.error("Error in ask proxy:", error);
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
