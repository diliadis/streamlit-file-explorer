import { FileSearch, FolderOpen, Info } from "lucide-react";
import type { Entry, Preview } from "./types";
import { formatDate, formatSize } from "./format";

export function PreviewPane({
  entry,
  preview,
}: {
  entry?: Entry;
  preview: Preview | null;
}) {
  return (
    <aside className="fe-preview" aria-label="File preview">
      <div className="fe-section-label">Preview</div>
      {!entry ? (
        <div className="fe-preview-empty">
          <FileSearch aria-hidden="true" size={32} />
          <strong>A closer look</strong>
          <span>Select a file to see its contents and details.</span>
        </div>
      ) : (
        <>
          <div className="fe-preview-content">
            {preview?.kind === "image" && (
              <img
                className="fe-image"
                src={preview.src}
                alt={`Preview of ${entry.name}`}
              />
            )}
            {preview?.kind === "text" && (
              <pre className="fe-code">{preview.text || "(Empty file)"}</pre>
            )}
            {preview?.kind === "table" &&
              (preview.rows.length ? (
                <div className="fe-table-preview">
                  <table aria-label="File contents">
                    <thead>
                      <tr>
                        {preview.rows[0].map((cell, i) => (
                          <th key={i} scope="col">
                            {cell}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.slice(1).map((row, i) => (
                        <tr key={i}>
                          {row.map((cell, j) => (
                            <td key={j}>{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="fe-preview-message">Empty file</p>
              ))}
            {preview && "message" in preview && (
              <div
                className="fe-preview-message"
                role={preview.kind === "error" ? "alert" : undefined}
              >
                {preview.kind === "directory" ? (
                  <FolderOpen size={32} aria-hidden="true" />
                ) : (
                  <Info size={24} aria-hidden="true" />
                )}
                <span>{preview.message}</span>
              </div>
            )}
            {preview && "truncated" in preview && preview.truncated && (
              <p className="fe-preview-limit">
                Partial preview · content limit reached
              </p>
            )}
          </div>
          <div className="fe-file-details">
            <strong>{entry.name}</strong>
            <span>
              {entry.kind === "directory"
                ? "Folder"
                : entry.name.includes(".")
                  ? `${entry.name.split(".").pop()?.toUpperCase()} file`
                  : "File"}
            </span>
            <dl>
              <dt>Size</dt>
              <dd>{formatSize(entry.size)}</dd>
              <dt>Modified</dt>
              <dd>{formatDate(entry.modified)}</dd>
            </dl>
          </div>
        </>
      )}
    </aside>
  );
}
