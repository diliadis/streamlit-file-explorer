import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import Explorer from "./Explorer";
import type { ExplorerData } from "./types";
import { PreviewPane } from "./PreviewPane";

const data: ExplorerData = {
  instance_id: "instance-one",
  label: "Files",
  environment: "Local",
  height: 300,
  locations: [
    { id: "Projects", label: "Projects" },
    { id: "Scratch", label: "Scratch" },
  ],
  root: "Projects",
  path: "",
  display_path: "/projects",
  entries: [
    {
      name: "results",
      path: "results",
      kind: "directory",
      size: null,
      modified: 1700000000,
      error: null,
    },
    {
      name: "scores.csv",
      path: "scores.csv",
      kind: "file",
      size: 24000,
      modified: 1700000000,
      error: null,
    },
    {
      name: "external",
      path: "external",
      kind: "symlink",
      size: null,
      modified: null,
      error: "Symbolic links are not followed.",
    },
  ],
  total: 3,
  page: 0,
  pages: 1,
  page_size: 100,
  truncated: false,
  max_entries: 10000,
  selected: [],
  selected_entries: [],
  query: "",
  sort: "name",
  descending: false,
  show_hidden: false,
  show_preview: true,
  preview: null,
  multiple: false,
  selection_mode: "file",
  can_confirm: false,
  error: null,
  ack: "",
  revision: 0,
};

describe("File explorer", () => {
  it("emits contextual navigation events", () => {
    const send = vi.fn();
    render(<Explorer data={data} send={send} />);
    fireEvent.click(
      screen.getByRole("button", { name: "Open folder results" }),
    );
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "navigate",
        root: "Projects",
        path: "results",
        context: { root: "Projects", path: "" },
      }),
    );
  });
  it("selects without implicitly confirming", () => {
    const send = vi.fn();
    render(<Explorer data={data} send={send} />);
    fireEvent.click(screen.getByRole("button", { name: "File scores.csv" }));
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({ type: "select", paths: ["scores.csv"] }),
    );
    expect(
      screen.getByRole("button", { name: "Use selection" }),
    ).toBeDisabled();
  });
  it("hydrates updated Python selection and confirms explicitly", () => {
    const send = vi.fn();
    const selected = {
      ...data,
      selected: ["scores.csv"],
      selected_entries: [data.entries[1]],
      can_confirm: true,
    };
    const view = render(<Explorer data={data} send={send} />);
    view.rerender(<Explorer data={selected} send={send} />);
    fireEvent.click(screen.getByRole("button", { name: "Use selection" }));
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({ type: "confirm", paths: ["scores.csv"] }),
    );
  });
  it("supports directory confirmation including the root", () => {
    const send = vi.fn();
    render(
      <Explorer data={{ ...data, selection_mode: "directory" }} send={send} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Use this folder" }));
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({ type: "confirm", paths: [""] }),
    );
  });
  it("debounces search and cancels it on unmount", () => {
    vi.useFakeTimers();
    const send = vi.fn();
    const view = render(<Explorer data={data} send={send} />);
    const input = screen.getByRole("searchbox", { name: "Search this folder" });
    fireEvent.change(input, { target: { value: "s" } });
    fireEvent.change(input, { target: { value: "scores" } });
    vi.advanceTimersByTime(300);
    expect(send).toHaveBeenCalledTimes(1);
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({ type: "search", query: "scores" }),
    );
    fireEvent.change(input, { target: { value: "later" } });
    view.unmount();
    vi.runAllTimers();
    expect(send).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
  it("never turns filenames or text into HTML", () => {
    const entry = { ...data.entries[1], name: "<img src=x onerror=alert(1)>" };
    render(
      <PreviewPane
        entry={entry}
        preview={{
          kind: "text",
          text: "<script>alert(1)</script>",
          truncated: false,
        }}
      />,
    );
    expect(screen.getByText("<script>alert(1)</script>")).toBeVisible();
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("img")).toBeNull();
  });
  it("makes links unavailable and supports keyboard navigation", () => {
    render(<Explorer data={data} send={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: "File external" }),
    ).toBeDisabled();
    const folder = screen.getByRole("button", { name: "Folder results" });
    folder.focus();
    fireEvent.keyDown(folder, { key: "ArrowDown" });
    expect(
      screen.getByRole("button", { name: "File scores.csv" }),
    ).toHaveFocus();
  });
  it("keeps errors and partial-list warnings visible", () => {
    render(
      <Explorer
        data={{ ...data, error: "Permission denied", truncated: true }}
        send={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Permission denied");
    expect(screen.getByText(/Search and sorting cover only/)).toBeVisible();
  });
  it("isolates the state of multiple instances", () => {
    const a = vi.fn(),
      b = vi.fn();
    render(
      <>
        <Explorer data={{ ...data, label: "First" }} send={a} />
        <Explorer data={{ ...data, label: "Second" }} send={b} />
      </>,
    );
    const buttons = screen.getAllByRole("button", { name: "File scores.csv" });
    fireEvent.click(buttons[0]);
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).not.toHaveBeenCalled();
    expect(buttons[1]).toHaveAttribute("aria-pressed", "false");
  });
});

it("does not let an older response undo a newer multiselection", () => {
  const send = vi.fn();
  const props = { ...data, multiple: true };
  const view = render(<Explorer data={props} send={send} />);
  fireEvent.click(screen.getByRole("checkbox", { name: "Select results" }));
  const first = send.mock.calls[0][0];
  fireEvent.click(screen.getByRole("checkbox", { name: "Select scores.csv" }));
  const second = send.mock.calls[1][0];
  view.rerender(
    <Explorer
      data={{ ...props, ack: first.id, revision: 1, selected: ["results"] }}
      send={send}
    />,
  );
  expect(
    screen.getByRole("checkbox", { name: "Select scores.csv" }),
  ).toBeChecked();
  view.rerender(
    <Explorer
      data={{
        ...props,
        ack: second.id,
        revision: 2,
        selected: ["results", "scores.csv"],
      }}
      send={send}
    />,
  );
  expect(
    screen.getByRole("checkbox", { name: "Select scores.csv" }),
  ).toBeChecked();
});
