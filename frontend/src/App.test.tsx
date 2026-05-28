import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import App from "./App";

vi.mock("react-router-dom", async () => {
  const React = await import("react");
  const actual = await import("react-router-dom");

  return {
    ...actual,
    RouterProvider: () =>
      React.createElement(
        "main",
        { className: "min-h-screen" },
        React.createElement("h1", null, "AI Code Review"),
        React.createElement("p", null, "管理后台骨架")
      ),
  };
});

vi.mock("./routes/router", () => {
  return {
    router: {},
  };
});

test("渲染管理后台标题占位内容", () => {
  render(<App />);
  expect(screen.getByRole("main")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { level: 1, name: "AI Code Review" })
  ).toBeInTheDocument();
  expect(screen.getByText("管理后台骨架")).toBeInTheDocument();
});
