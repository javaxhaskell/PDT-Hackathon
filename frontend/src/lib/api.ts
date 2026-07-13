/**
 * Thin fetch client for the PairScope backend. No quant logic lives here:
 * the frontend renders backend-computed values only.
 */

import type {
  AnalyseRequest,
  AnalyseResponse,
  NarrativeRequest,
  NarrativeResponse,
  SymbolSearchResponse,
} from "@/lib/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function toError(res: Response): Promise<Error> {
  try {
    const body = (await res.json()) as { message?: string; error?: string };
    if (body && typeof body.message === "string" && body.message.length > 0) {
      return new Error(body.message);
    }
    if (body && typeof body.error === "string" && body.error.length > 0) {
      return new Error(body.error);
    }
  } catch {
    // fall through to the generic message
  }
  return new Error(`The analysis service returned an error (HTTP ${res.status}).`);
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw await toError(res);
  }
  return (await res.json()) as T;
}

export function analyse(req: AnalyseRequest): Promise<AnalyseResponse> {
  return postJson<AnalyseResponse>("/api/analyse", req);
}

export function fetchNarrative(
  req: NarrativeRequest,
): Promise<NarrativeResponse> {
  return postJson<NarrativeResponse>("/api/narrative", req);
}

export async function searchSymbols(q: string): Promise<SymbolSearchResponse> {
  const res = await fetch(
    `${BASE_URL}/api/symbols/search?q=${encodeURIComponent(q)}`,
  );
  if (!res.ok) {
    throw await toError(res);
  }
  return (await res.json()) as SymbolSearchResponse;
}
