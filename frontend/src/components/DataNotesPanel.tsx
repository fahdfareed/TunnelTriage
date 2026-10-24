import { useEffect, useState } from "react";
import { api } from "../api";

export function DataNotesPanel() {
  const [notes, setNotes] = useState<any>(null);
  const [constants, setConstants] = useState<any>(null);

  useEffect(() => {
    api.dataNotes().then(setNotes);
    api.constants().then(setConstants);
  }, []);

  if (!notes) return <div className="spinner">Loading…</div>;
  const suspect = notes.suspect_elements ?? {};

  return (
    <div>
      <div className="section-title">Suspect elements (reporting convention)</div>
      <div className="banner info">{suspect.explanation}</div>
      <div>
        Excluded element numbers: <strong>{(suspect.numbers ?? []).join(", ") || "none"}</strong>{" "}
        ({suspect.affected_rows ?? 0} rows affected,{" "}
        {suspect.excluded_by_default ? "excluded by default" : "included"}).
      </div>

      <div className="section-title">Data-quality flag counts</div>
      <table>
        <thead><tr><th>Flag</th><th>Count</th><th>Example row</th></tr></thead>
        <tbody>
          {Object.entries(notes.flag_counts ?? {}).map(([flag, count]) => (
            <tr key={flag}>
              <td>{flag}</td>
              <td>{String(count)}</td>
              <td style={{ color: "var(--muted)" }}>
                {(notes.flag_examples?.[flag] ?? [])[0] ?? "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="section-title">Sources</div>
      <div>Data year: {notes.data_year}</div>
      {constants && (
        <ul style={{ fontSize: 12 }}>
          {Object.entries(constants.sources ?? {}).map(([k, url]) => (
            <li key={k}>
              <a href={url as string} target="_blank" rel="noreferrer">{k}</a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
