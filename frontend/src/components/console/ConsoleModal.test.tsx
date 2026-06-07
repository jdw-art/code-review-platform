import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { ConsoleModal } from "./ConsoleModal";

test("renders accessible dialog semantics with title and description", () => {
  render(
    <ConsoleModal
      open
      title="创建项目"
      description="填写项目基础信息后继续。"
    >
      <div>表单内容</div>
    </ConsoleModal>
  );

  const dialog = screen.getByRole("dialog", { name: "创建项目" });

  expect(dialog).toHaveAttribute("aria-modal", "true");
  expect(dialog).toHaveAttribute("aria-labelledby");
  expect(dialog).toHaveAttribute("aria-describedby");
  expect(screen.getByText("填写项目基础信息后继续。")).toBeInTheDocument();
});

test("dismisses the modal with Escape when onClose is provided", () => {
  const onClose = vi.fn();

  render(
    <ConsoleModal open title="创建项目" onClose={onClose}>
      <div>表单内容</div>
    </ConsoleModal>
  );

  fireEvent.keyDown(document, { key: "Escape" });

  expect(onClose).toHaveBeenCalledTimes(1);
});
