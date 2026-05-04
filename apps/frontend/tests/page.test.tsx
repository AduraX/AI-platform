import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import Page from "../app/page";

describe("Chat Page", () => {
  it("renders without crashing", () => {
    render(<Page />);
    expect(document.querySelector("form")).toBeTruthy();
  });

  it("renders the send button", () => {
    render(<Page />);
    const button = document.querySelector("button[type='submit']");
    expect(button).toBeTruthy();
    expect(button?.textContent).toBe("Send");
  });
});
