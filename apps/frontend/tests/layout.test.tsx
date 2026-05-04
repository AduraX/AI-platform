import { describe, it, expect } from "vitest";

describe("RootLayout", () => {
  it("exports a default function", async () => {
    const mod = await import("../app/layout");
    expect(typeof mod.default).toBe("function");
  });
});
