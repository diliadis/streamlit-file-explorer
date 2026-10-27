export type Entry = {
  name: string;
  path: string;
  kind: "file" | "directory" | "symlink" | "other" | "unavailable";
  size: number | null;
  modified: number | null;
  error: string | null;
};
export type Preview =
  | { kind: "text"; text: string; truncated: boolean }
  | { kind: "table"; rows: string[][]; truncated: boolean }
  | { kind: "image"; src: string }
  | { kind: "metadata" | "directory" | "error"; message: string };
export type Sort = "name" | "size" | "modified" | "type";
export type ExplorerData = {
  instance_id: string;
  label: string;
  environment: string;
  height: number;
  locations: { id: string; label: string }[];
  root: string;
  path: string;
  display_path: string;
  entries: Entry[];
  total: number;
  page: number;
  pages: number;
  page_size: number;
  truncated: boolean;
  max_entries: number;
  selected: string[];
  selected_entries: Entry[];
  query: string;
  sort: Sort;
  descending: boolean;
  show_hidden: boolean;
  show_preview: boolean;
  preview: Preview | null;
  multiple: boolean;
  selection_mode: "file" | "directory" | "any";
  can_confirm: boolean;
  error: string | null;
  ack: string;
  revision: number;
};
export type Action =
  | { type: "navigate"; root: string; path: string }
  | { type: "select" | "confirm"; paths: string[] }
  | { type: "search"; query: string }
  | { type: "sort"; sort: Sort; descending: boolean }
  | { type: "page"; page: number }
  | { type: "hidden" | "preview" | "refresh" };
export type ActionEvent = Action & {
  id: string;
  context: { root: string; path: string };
};
export type ExplorerState = { action: ActionEvent };
