import { describe, expect, it } from "vitest";

import { type AllowedModel, firstRunnable, modelLabel, modelOption } from "@/lib/models";

const FREE: AllowedModel = { id: "free", label: "Nemotron 3 Ultra", provider: "OpenRouter", model: "n:free", paid: false, run: true };
const LUNA: AllowedModel = { id: "luna-high", label: "GPT-6 Luna, high effort", provider: "OpenRouter", model: "l", paid: true, run: true };
const CLAUDE: AllowedModel = { id: "anthropic", label: "Claude Sonnet 5.5", provider: "Anthropic", model: "c", paid: true, run: false };

describe("firstRunnable", () => {
  it("starts on the first line the API will call", () => {
    expect(firstRunnable([FREE, LUNA, CLAUDE])).toBe("free");
  });

  it("skips a line that has not been run", () => {
    expect(firstRunnable([CLAUDE, LUNA])).toBe("luna-high");
  });

  it("has nothing to start on when no line can run, or the list did not load", () => {
    expect(firstRunnable([CLAUDE])).toBeNull();
    expect(firstRunnable([])).toBeNull();
  });
});

describe("modelOption", () => {
  it("says what a line costs", () => {
    expect(modelOption(FREE)).toBe("Nemotron 3 Ultra · OpenRouter · Free");
    expect(modelOption(LUNA)).toBe("GPT-6 Luna, high effort · OpenRouter · Paid");
  });

  it("marks a line that has not been run instead of its price", () => {
    expect(modelOption(CLAUDE)).toBe("Claude Sonnet 5.5 · Anthropic · Not run");
  });
});

describe("modelLabel", () => {
  it("names the line, and nothing when the line is unknown", () => {
    expect(modelLabel([FREE, LUNA], "luna-high")).toBe("GPT-6 Luna, high effort");
    expect(modelLabel([FREE], "luna-high")).toBeNull();
    expect(modelLabel([FREE], null)).toBeNull();
  });
});
