import { useEffect, useRef, useState } from "react";
import type { CSSProperties, KeyboardEvent } from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Check,
  ChevronLeft,
  ChevronRight,
  Eye,
  File,
  FileCode2,
  FileImage,
  FileText,
  Folder,
  FolderOpen,
  HardDrive,
  Link,
  LoaderCircle,
  PanelRight,
  RefreshCw,
  Search,
  Table2,
  Terminal,
  X,
} from "lucide-react";
import type { Action, ActionEvent, Entry, ExplorerData, Sort } from "./types";
import { formatDate, formatSize, parentPath } from "./format";
import { PreviewPane } from "./PreviewPane";

export type ExplorerProps = {
  data: ExplorerData;
  send: (event: ActionEvent) => void;
};

function FileIcon({ entry }: { entry: Entry }) {
  if (entry.kind === "directory")
    return <Folder className="fe-folder-icon" aria-hidden="true" />;
  if (entry.kind === "symlink") return <Link aria-hidden="true" />;
  const extension = entry.name.split(".").pop()?.toLowerCase();
  const Icon = ["csv", "tsv", "xlsx"].includes(extension ?? "")
    ? Table2
    : ["png", "jpg", "jpeg", "webp", "gif"].includes(extension ?? "")
      ? FileImage
      : ["sh", "sbatch"].includes(extension ?? "")
        ? Terminal
        : ["json", "yaml", "yml", "py", "js"].includes(extension ?? "")
          ? FileCode2
          : ["txt", "md", "log"].includes(extension ?? "")
            ? FileText
            : File;
  return <Icon aria-hidden="true" />;
}

export default function Explorer({ data, send }: ExplorerProps) {
  const [query, setQuery] = useState(data.query);
  const [pending, setPending] = useState("");
  const [slow, setSlow] = useState(false);
  const [editingPath, setEditingPath] = useState(false);
  const [pathInput, setPathInput] = useState(data.path);
  const [selected, setSelected] = useState(data.selected);
  const [history, setHistory] = useState<{ root: string; path: string }[]>([]);
  const [compact, setCompact] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout>>();
  const rowButtons = useRef<(HTMLButtonElement | null)[]>([]);
  const searchInput = useRef<HTMLInputElement>(null);
  const busy = Boolean(pending && pending !== data.ack);
  const context = `${data.root}/${data.path}`;

  useEffect(() => {
    // An earlier response must not overwrite a newer optimistic selection.
    if (!busy) setSelected(data.selected);
  }, [data.selected, data.revision, busy]);
  useEffect(() => {
    setQuery(data.query);
    setPathInput(data.path);
    setEditingPath(false);
    clearTimeout(searchTimer.current);
  }, [context, data.query]);
  useEffect(() => () => clearTimeout(searchTimer.current), []);
  useEffect(() => {
    setSlow(false);
    if (!busy) return;
    const timeout = setTimeout(() => setSlow(true), 8000);
    return () => clearTimeout(timeout);
  }, [busy, pending]);

  const emit = (action: Action) => {
    // getRandomValues also works on private-network HTTP deployments, where
    // browsers do not expose the secure-context-only randomUUID method.
    const id = Array.from(crypto.getRandomValues(new Uint32Array(4)), (value) =>
      value.toString(16),
    ).join("-");
    setPending(id);
    send({ ...action, id, context: { root: data.root, path: data.path } });
  };
  const navigate = (root: string, path: string, remember = true) => {
    clearTimeout(searchTimer.current);
    if (remember)
      setHistory((previous) => [
        ...previous.slice(-49),
        { root: data.root, path: data.path },
      ]);
    emit({ type: "navigate", root, path });
  };
  const select = (entry: Entry, add = false) => {
    if (entry.error) return;
    const paths =
      data.multiple && add
        ? selected.includes(entry.path)
          ? selected.filter((path) => path !== entry.path)
          : [...selected, entry.path]
        : [entry.path];
    setSelected(paths);
    emit({ type: "select", paths });
  };
  const search = (text: string) => {
    setQuery(text);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(
      () => emit({ type: "search", query: text }),
      300,
    );
  };
  const sort = (field: Sort) =>
    emit({
      type: "sort",
      sort: field,
      descending: data.sort === field ? !data.descending : false,
    });
  const keyboard = (
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
    entry: Entry,
  ) => {
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      const targets = rowButtons.current.filter(
        (button): button is HTMLButtonElement =>
          Boolean(button && !button.disabled),
      );
      const current = targets.indexOf(rowButtons.current[index]!);
      const next =
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? targets.length - 1
            : Math.min(
                targets.length - 1,
                Math.max(0, current + (event.key === "ArrowDown" ? 1 : -1)),
              );
      targets[next]?.focus();
    } else if (
      (event.key === "Enter" || event.key === "ArrowRight") &&
      entry.kind === "directory"
    ) {
      event.preventDefault();
      navigate(data.root, entry.path);
    } else if (event.key === "ArrowLeft" && data.path) {
      event.preventDefault();
      navigate(data.root, parentPath(data.path));
    }
  };
  const breadcrumbs = data.path ? data.path.split("/") : [];
  const highlighted = data.selected_entries.at(-1);
  const sortHeading = (field: Sort, text: string) => (
    <button className="fe-sort" onClick={() => sort(field)}>
      {text}
      {data.sort === field &&
        (data.descending ? (
          <ArrowDown aria-hidden="true" />
        ) : (
          <ArrowUp aria-hidden="true" />
        ))}
    </button>
  );

  return (
    <section
      className={`fe-explorer ${compact ? "fe-compact" : ""}`}
      aria-label={data.label}
      style={{ "--fe-list-height": `${data.height}px` } as CSSProperties}
      onKeyDown={(event) => {
        if ((event.metaKey || event.ctrlKey) && event.key === "f") {
          event.preventDefault();
          searchInput.current?.focus();
        }
        if (event.key === "Escape" && editingPath) setEditingPath(false);
      }}
    >
      <header className="fe-header">
        <div className="fe-title">
          <FolderOpen aria-hidden="true" />
          <h2>{data.label}</h2>
          <span className="fe-mode">
            {data.selection_mode === "directory"
              ? "Choose a folder"
              : data.multiple
                ? data.selection_mode === "file"
                  ? "Select files"
                  : "Select files & folders"
                : "Browse & select"}
          </span>
        </div>
        {data.environment && (
          <span className="fe-environment">
            <HardDrive aria-hidden="true" />
            {data.environment}
          </span>
        )}
      </header>
      <div className="fe-toolbar">
        <div className="fe-nav-buttons">
          <button
            className="fe-icon"
            aria-label="Back"
            title="Back"
            disabled={busy || history.length === 0}
            onClick={() => {
              const target = history.at(-1)!;
              setHistory(history.slice(0, -1));
              navigate(target.root, target.path, false);
            }}
          >
            <ArrowLeft />
          </button>
          <button
            className="fe-icon"
            aria-label="Parent folder"
            title="Parent folder"
            disabled={busy || !data.path}
            onClick={() => navigate(data.root, parentPath(data.path))}
          >
            <ArrowUp />
          </button>
        </div>
        {editingPath ? (
          <form
            className="fe-path-form"
            onSubmit={(event) => {
              event.preventDefault();
              navigate(data.root, pathInput);
            }}
          >
            <input
              autoFocus
              aria-label={`Path within ${data.root}`}
              value={pathInput}
              onChange={(event) => setPathInput(event.target.value)}
              placeholder={`Path within ${data.root}`}
            />
            <button className="fe-icon" aria-label="Open path">
              <ArrowRight />
            </button>
          </form>
        ) : (
          <nav className="fe-breadcrumbs" aria-label="Folder path">
            <button disabled={busy} onClick={() => navigate(data.root, "")}>
              {data.root}
            </button>
            {breadcrumbs.map((part, index) => (
              <span key={index}>
                <ChevronRight aria-hidden="true" />
                <button
                  disabled={busy}
                  aria-current={
                    index === breadcrumbs.length - 1 ? "location" : undefined
                  }
                  onClick={() =>
                    navigate(
                      data.root,
                      breadcrumbs.slice(0, index + 1).join("/"),
                    )
                  }
                >
                  {part}
                </button>
              </span>
            ))}
          </nav>
        )}
        <button
          className="fe-icon"
          title="Enter a relative path"
          aria-label="Edit path"
          aria-pressed={editingPath}
          onClick={() => setEditingPath(!editingPath)}
        >
          <Terminal />
        </button>
        <span className="fe-toolbar-divider" />
        <button
          className="fe-icon"
          aria-label="Refresh folder"
          title="Refresh folder"
          disabled={busy && !slow}
          onClick={() => emit({ type: "refresh" })}
        >
          <RefreshCw className={busy ? "fe-spin" : ""} />
        </button>
        <button
          className="fe-icon"
          aria-label="Show hidden files"
          title="Show hidden files"
          aria-pressed={data.show_hidden}
          disabled={busy}
          onClick={() => emit({ type: "hidden" })}
        >
          <Eye />
        </button>
        <button
          className="fe-icon"
          aria-label="Toggle preview"
          title="Preview pane"
          aria-pressed={data.show_preview}
          disabled={busy}
          onClick={() => emit({ type: "preview" })}
        >
          <PanelRight />
        </button>
      </div>
      {data.error && (
        <div role="alert" className="fe-alert">
          {data.error}
        </div>
      )}
      {data.truncated && (
        <div role="status" className="fe-warning">
          Folder scan limited to {data.max_entries.toLocaleString()} entries.
          Search and sorting cover only the scanned portion.
        </div>
      )}
      <div className={`fe-body ${data.show_preview ? "" : "fe-no-preview"}`}>
        <aside className="fe-locations" aria-label="Locations">
          <div className="fe-section-label">Locations</div>
          {data.locations.map((location) => (
            <button
              key={location.id}
              className="fe-location"
              disabled={busy}
              aria-current={data.root === location.id ? "location" : undefined}
              onClick={() => navigate(location.id, "")}
            >
              <HardDrive aria-hidden="true" />
              <span>{location.label}</span>
            </button>
          ))}
          <div className="fe-sidebar-hint">
            Browsing this host.
            <br />
            Read-only access.
          </div>
        </aside>
        <div className="fe-main">
          <div className="fe-list-tools">
            <label className="fe-search">
              <Search aria-hidden="true" />
              <input
                ref={searchInput}
                type="search"
                aria-label="Search this folder"
                maxLength={1000}
                placeholder="Search this folder"
                value={query}
                onChange={(event) => search(event.target.value)}
              />
              {query && (
                <button
                  aria-label="Clear search"
                  className="fe-icon"
                  onClick={() => search("")}
                >
                  <X />
                </button>
              )}
            </label>
            <button
              className="fe-density"
              aria-pressed={compact}
              onClick={() => setCompact(!compact)}
              title="Toggle compact rows"
            >
              {compact ? "Compact" : "Comfortable"}
            </button>
          </div>
          <div className="fe-list-scroll" aria-busy={busy}>
            <table className="fe-files" aria-label="Files and folders">
              <thead>
                <tr>
                  {data.multiple && (
                    <th className="fe-check-column" scope="col">
                      <span className="fe-sr-only">Select</span>
                    </th>
                  )}
                  <th
                    scope="col"
                    aria-sort={
                      data.sort === "name"
                        ? data.descending
                          ? "descending"
                          : "ascending"
                        : "none"
                    }
                  >
                    {sortHeading("name", "Name")}
                  </th>
                  <th
                    className="fe-size"
                    scope="col"
                    aria-sort={
                      data.sort === "size"
                        ? data.descending
                          ? "descending"
                          : "ascending"
                        : "none"
                    }
                  >
                    {sortHeading("size", "Size")}
                  </th>
                  <th
                    className="fe-modified"
                    scope="col"
                    aria-sort={
                      data.sort === "modified"
                        ? data.descending
                          ? "descending"
                          : "ascending"
                        : "none"
                    }
                  >
                    {sortHeading("modified", "Modified")}
                  </th>
                  <th className="fe-open-column" scope="col">
                    <span className="fe-sr-only">Open</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.entries.map((entry, index) => (
                  <tr
                    key={`${entry.path}:${entry.name}`}
                    data-selected={selected.includes(entry.path)}
                  >
                    {data.multiple && (
                      <td className="fe-check-column">
                        <input
                          type="checkbox"
                          aria-label={`Select ${entry.name}`}
                          checked={selected.includes(entry.path)}
                          disabled={Boolean(entry.error)}
                          onChange={() => select(entry, true)}
                        />
                      </td>
                    )}
                    <td>
                      <button
                        ref={(button) => {
                          rowButtons.current[index] = button;
                        }}
                        className="fe-file"
                        disabled={Boolean(entry.error)}
                        title={entry.error ?? entry.name}
                        aria-label={`${entry.kind === "directory" ? "Folder" : "File"} ${entry.name}`}
                        aria-pressed={selected.includes(entry.path)}
                        onClick={(event) =>
                          select(entry, event.metaKey || event.ctrlKey)
                        }
                        onDoubleClick={() =>
                          entry.kind === "directory" &&
                          navigate(data.root, entry.path)
                        }
                        onKeyDown={(event) => keyboard(event, index, entry)}
                      >
                        <FileIcon entry={entry} />
                        <span>{entry.name}</span>
                        {selected.includes(entry.path) && (
                          <Check
                            className="fe-selected-check"
                            aria-hidden="true"
                          />
                        )}
                      </button>
                      {entry.error && (
                        <span className="fe-entry-error">{entry.error}</span>
                      )}
                    </td>
                    <td className="fe-size">{formatSize(entry.size)}</td>
                    <td
                      className="fe-modified"
                      title={
                        entry.modified
                          ? new Date(entry.modified * 1000).toLocaleString()
                          : undefined
                      }
                    >
                      {formatDate(entry.modified)}
                    </td>
                    <td className="fe-open-column">
                      {entry.kind === "directory" && (
                        <button
                          className="fe-icon"
                          aria-label={`Open folder ${entry.name}`}
                          title={`Open ${entry.name}`}
                          disabled={busy}
                          onClick={() => navigate(data.root, entry.path)}
                        >
                          <ChevronRight />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!data.entries.length && (
              <div className="fe-empty">
                <Search size={28} aria-hidden="true" />
                <strong>
                  {query
                    ? "No matching files"
                    : data.error
                      ? "Folder unavailable"
                      : "This folder is empty"}
                </strong>
                <span>
                  {query
                    ? "Try another name or clear the search."
                    : data.error
                      ? "Choose another location or refresh to try again."
                      : "Files added here will appear after a refresh."}
                </span>
              </div>
            )}
          </div>
          <div className="fe-pagination">
            <span>
              {data.total.toLocaleString()}{" "}
              {data.total === 1 ? "item" : "items"}
              {data.truncated ? " in partial listing" : ""}
            </span>
            {data.pages > 1 && (
              <div>
                <button
                  className="fe-icon"
                  aria-label="Previous page"
                  disabled={busy || data.page === 0}
                  onClick={() => emit({ type: "page", page: data.page - 1 })}
                >
                  <ChevronLeft />
                </button>
                <span>
                  {data.page + 1} / {data.pages}
                </span>
                <button
                  className="fe-icon"
                  aria-label="Next page"
                  disabled={busy || data.page + 1 === data.pages}
                  onClick={() => emit({ type: "page", page: data.page + 1 })}
                >
                  <ChevronRight />
                </button>
              </div>
            )}
          </div>
        </div>
        {data.show_preview && (
          <PreviewPane entry={highlighted} preview={data.preview} />
        )}
      </div>
      <footer className="fe-footer">
        <div className="fe-status" aria-live="polite">
          <strong>
            {busy ? (
              <>
                <LoaderCircle className="fe-spin" aria-hidden="true" />
                {slow ? "Waiting for the filesystem…" : "Loading…"}
              </>
            ) : selected.length ? (
              `${selected.length} ${selected.length === 1 ? "item" : "items"} selected`
            ) : (
              "Choose an item to continue"
            )}
          </strong>
          <span title={data.display_path}>{data.display_path}</span>
        </div>
        <div className="fe-actions">
          {data.selection_mode !== "file" && (
            <button
              className="fe-secondary"
              disabled={busy}
              onClick={() => emit({ type: "confirm", paths: [data.path] })}
            >
              Use this folder
            </button>
          )}
          <button
            className="fe-primary"
            disabled={busy || !data.can_confirm}
            onClick={() => emit({ type: "confirm", paths: selected })}
          >
            Use selection <ArrowRight aria-hidden="true" />
          </button>
        </div>
      </footer>
    </section>
  );
}
