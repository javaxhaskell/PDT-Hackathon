/**
 * Required frontend happy-path test (spec section 10).
 *
 * Mocks global fetch with the schema-validated example payloads from
 * docs/example_api_response.json and walks the demo route: fill the form,
 * submit, see the loading state, read the verdict and the correctly signed
 * trade quantities, change the risk profile (which must re-analyse), and
 * see the fixture Narrative Lens result with a cited headline.
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import example from "../../../docs/example_api_response.json";
import Home from "@/app/page";
import type {
  AnalyseRequest,
  AnalyseResponse,
  NarrativeRequest,
  NarrativeResponse,
} from "@/lib/types";

const fixture = example as unknown as {
  analyse: AnalyseResponse;
  narrative: NarrativeResponse;
};

let analyseBodies: AnalyseRequest[] = [];
let narrativeBodies: NarrativeRequest[] = [];

// A manual gate so the test can observe the loading state before the first
// analyse response resolves.
let analyseGate: Promise<void> | null = null;
let openAnalyseGate: () => void = () => {};
function armAnalyseGate() {
  analyseGate = new Promise<void>((resolve) => {
    openAnalyseGate = resolve;
  });
}

function jsonResponse(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  analyseBodies = [];
  narrativeBodies = [];
  analyseGate = null;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url;
      if (url.includes("/api/analyse")) {
        const body = JSON.parse(String(init?.body)) as AnalyseRequest;
        analyseBodies.push(body);
        if (analyseGate) {
          const gate = analyseGate;
          analyseGate = null;
          await gate;
        }
        return jsonResponse({
          ...fixture.analyse,
          request: { ...fixture.analyse.request, ...body },
        });
      }
      if (url.includes("/api/narrative")) {
        narrativeBodies.push(JSON.parse(String(init?.body)) as NarrativeRequest);
        return jsonResponse(fixture.narrative);
      }
      if (url.includes("/api/symbols/search")) {
        return jsonResponse({ results: [] });
      }
      throw new Error(`Unexpected fetch in test: ${url}`);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PairScope happy path", () => {
  it("submits the form, shows loading, verdict, signed quantities, re-analyses on risk change and renders the narrative fixture", async () => {
    const user = userEvent.setup();
    render(<Home />);

    // --- fill the form -----------------------------------------------------
    await user.type(screen.getByLabelText(/ticker a/i), "ALL");
    await user.type(screen.getByLabelText(/ticker b/i), "TRV");

    // --- submit and observe the loading state ------------------------------
    armAnalyseGate();
    await user.click(screen.getByRole("button", { name: /^analyse$/i }));
    const loadingButton = await screen.findByRole("button", {
      name: /analysing/i,
    });
    expect(loadingButton).toBeDisabled();
    openAnalyseGate();

    // --- verdict: SELL_A_BUY_B maps to "sell KO, buy PEP" -------------------
    expect(
      await screen.findByRole("heading", {
        name: /candidate setup — sell ALL, buy TRV/i,
      }),
    ).toBeInTheDocument();
    expect(analyseBodies).toHaveLength(1);
    expect(analyseBodies[0]).toMatchObject({
      ticker_a: "ALL",
      ticker_b: "TRV",
      starting_capital: 10000,
      risk_profile: "balanced",
      lookback: "2y",
      whole_shares: true,
      cost_bps: 10,
      data_mode: "live",
    });

    // The fixture banner is shown because the response data is a fixture.
    expect(screen.getByRole("status")).toHaveTextContent(
      /recorded market snapshot/i,
    );

    // All four evidence cards render with their status labels.
    expect(screen.getByText("Move together")).toBeInTheDocument();
    expect(screen.getByText("Stable enough relationship")).toBeInTheDocument();
    expect(screen.getByText("Unusual today")).toBeInTheDocument();
    expect(screen.getByText("Worked historically")).toBeInTheDocument();

    // --- correctly signed quantities from the sizing legs -------------------
    const legAll = screen.getByTestId("leg-ALL");
    expect(within(legAll).getByText("SELL")).toBeInTheDocument();
    expect(legAll).toHaveTextContent(/6 ALL shares/);
    expect(legAll).not.toHaveTextContent(/BUY/);

    const legTrv = screen.getByTestId("leg-TRV");
    expect(within(legTrv).getByText("BUY")).toBeInTheDocument();
    expect(legTrv).toHaveTextContent(/3 TRV shares/);
    expect(legTrv).not.toHaveTextContent(/SELL/);

    // --- changing the risk profile triggers a new analyse call --------------
    await user.selectOptions(
      screen.getByLabelText(/risk profile/i),
      "aggressive",
    );
    await waitFor(() => expect(analyseBodies).toHaveLength(2));
    expect(analyseBodies[1].risk_profile).toBe("aggressive");
    expect(analyseBodies[1].ticker_a).toBe("ALL");
    expect(analyseBodies[1].ticker_b).toBe("TRV");

    // --- narrative fixture result: classification + a cited headline --------
    expect(
      await screen.findByText(/no obvious news explanation/i),
    ).toBeInTheDocument();
    expect(screen.getByText("AI-generated")).toBeInTheDocument();
    const citedLinks = screen.getAllByRole("link", {
      name: /Allstate \(ALL\) Stock Slides as Market Rises/i,
    });
    expect(citedLinks.length).toBeGreaterThan(0);
    expect(citedLinks[0]).toHaveAttribute(
      "href",
      "https://finance.yahoo.com/markets/stocks/articles/allstate-stock-slides-market-rises-215002229.html",
    );

    // The narrative depends only on the pair and data mode, so the
    // risk-profile re-analysis must not refetch it.
    expect(narrativeBodies).toHaveLength(1);
    expect(narrativeBodies[0]).toMatchObject({
      ticker_a: "ALL",
      ticker_b: "TRV",
      data_mode: "live",
    });
  });
});
