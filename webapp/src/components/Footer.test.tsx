import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Footer } from "./Footer";

describe("Footer", () => {
  it("renders a 'Report a problem' link to the issue tracker", () => {
    render(<Footer />);

    const link = screen.getByRole("link", { name: "Report a problem" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "https://github.com/edonahue/Discogs_Spinner/issues");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer");
  });

  it("is labelled as a support region", () => {
    render(<Footer />);
    expect(screen.getByRole("contentinfo", { name: "Support" })).toBeInTheDocument();
  });
});
