import React, { useEffect, useMemo, useState } from "react";

import {
  createMeeting,
  deleteMeeting,
  exportMeeting,
  getMeeting,
  getMeetingActionItems,
  getMeetings,
  updateActionItem,
} from "./api";


const sampleTranscript = `Meeting Title: Smart Docs Weekly Sync

Neha: Thanks everyone. The main goal today is to finalize the approach for advanced Azure OpenAI monitoring through the gateway.

Abhishek: I reviewed the Microsoft gateway pattern. My recommendation is to place API Management in front of Azure OpenAI so we can track usage by client, deployment, and model.

Jeevan: That makes sense. We also need audit logs because Smart Docs may handle sensitive documents.

Aditya: What about cost tracking? Leadership wants to know which teams are consuming the most tokens.

Abhishek: We can capture prompt tokens, completion tokens, total tokens, client ID, and request timestamp in Azure Monitor. Later we can build KQL dashboards.

Neha: Good. Abhishek, please create the first working POC by Friday. Jeevan, please validate the logging fields by Wednesday.

Jeevan: Sure. One concern is that we should not log sensitive user content directly.

Abhishek: Agreed. We can start with metadata logging only and add redaction before storing any payload.

Aditya: The biggest risk is latency. If APIM adds too much overhead, teams may push back.

Neha: Then let us measure baseline latency and gateway latency separately. We will review results next week.

Abhishek: I will also document the tradeoff between observability and performance.

Neha: Perfect. Let us close here.`;

const initialForm = {
  title: "Smart Docs Weekly Sync",
  participants: "Neha, Abhishek, Jeevan, Aditya",
  transcript_text: sampleTranscript,
};


function createExportFileName(meeting, extension) {
  const safeTitle = (meeting?.title || "meeting-notes")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

  return `${safeTitle || "meeting-notes"}.${extension}`;
}


function downloadTextFile(content, fileName, mimeType) {
  const file = new Blob([content], { type: mimeType });
  const fileUrl = URL.createObjectURL(file);
  const link = document.createElement("a");

  link.href = fileUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(fileUrl);
}


function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


function markdownToPrintableHtml(markdown) {
  const htmlBlocks = [];
  let tableRows = [];

  function splitTableRow(line) {
    return line
      .replace(/^\||\|$/g, "")
      .split("|")
      .map((cell) => cell.trim());
  }

  function flushTable() {
    if (tableRows.length === 0) {
      return;
    }

    const [headerRow, ...bodyRows] = tableRows;
    htmlBlocks.push(`
      <table>
        <thead>
          <tr>${headerRow.map((cell) => `<th>${escapeHtml(cell)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${bodyRows
            .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
            .join("")}
        </tbody>
      </table>
    `);
    tableRows = [];
  }

  markdown.split("\n").forEach((line) => {
    const trimmedLine = line.trim();

    if (trimmedLine.startsWith("|") && trimmedLine.endsWith("|")) {
      if (!/^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$/.test(trimmedLine)) {
        tableRows.push(splitTableRow(trimmedLine));
      }
      return;
    }

    flushTable();

    if (trimmedLine.startsWith("# ")) {
      htmlBlocks.push(`<h1>${escapeHtml(trimmedLine.slice(2))}</h1>`);
      return;
    }

    if (trimmedLine.startsWith("## ")) {
      htmlBlocks.push(`<h2>${escapeHtml(trimmedLine.slice(3))}</h2>`);
      return;
    }

    if (trimmedLine.startsWith("- ")) {
      htmlBlocks.push(`<p class="bullet">${escapeHtml(trimmedLine.slice(2))}</p>`);
      return;
    }

    if (trimmedLine.startsWith("> ")) {
      htmlBlocks.push(`<blockquote>${escapeHtml(trimmedLine.slice(2))}</blockquote>`);
      return;
    }

    if (trimmedLine) {
      htmlBlocks.push(`<p>${escapeHtml(trimmedLine)}</p>`);
    }
  });

  flushTable();
  return htmlBlocks.join("");
}


function openPdfPrintPreview(markdown, meeting) {
  const previewWindow = window.open("", "_blank");

  if (!previewWindow) {
    return;
  }

  previewWindow.document.write(`
    <!doctype html>
    <html>
      <head>
        <title>${escapeHtml(createExportFileName(meeting, "pdf"))}</title>
        <style>
          body {
            margin: 40px;
            color: #111827;
            font-family: Arial, sans-serif;
            line-height: 1.55;
          }
          h1 {
            margin: 0 0 24px;
            font-size: 28px;
          }
          h2 {
            margin: 28px 0 10px;
            font-size: 18px;
            border-bottom: 1px solid #d8dee8;
            padding-bottom: 6px;
          }
          p {
            margin: 6px 0;
          }
          .bullet::before {
            content: "• ";
          }
          blockquote {
            margin: 8px 0 14px;
            padding: 8px 12px;
            border-left: 4px solid #2563eb;
            background: #f8fafc;
            color: #475569;
          }
          table {
            width: 100%;
            margin: 12px 0 18px;
            border-collapse: collapse;
            font-size: 13px;
          }
          th, td {
            padding: 8px;
            border: 1px solid #d8dee8;
            text-align: left;
            vertical-align: top;
          }
          th {
            background: #f8fafc;
          }
        </style>
      </head>
      <body>${markdownToPrintableHtml(markdown)}</body>
    </html>
  `);
  previewWindow.document.close();
  previewWindow.focus();
  previewWindow.print();
}


export default function App() {
  const [form, setForm] = useState(initialForm);
  const [meetings, setMeetings] = useState([]);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [visibleActionItems, setVisibleActionItems] = useState([]);
  const [ownerFilter, setOwnerFilter] = useState("");
  const [exportedMarkdown, setExportedMarkdown] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMeeting, setIsLoadingMeeting] = useState(false);
  const [deletingMeetingId, setDeletingMeetingId] = useState(null);

  useEffect(() => {
    loadMeetings();
  }, []);

  const stats = useMemo(() => {
    const actionItems = selectedMeeting?.action_items || [];
    return {
      meetings: meetings.length,
      open: actionItems.filter((item) => item.status !== "done").length,
      done: actionItems.filter((item) => item.status === "done").length,
      evidence: actionItems.filter((item) => item.evidence_quote).length,
    };
  }, [meetings, selectedMeeting]);

  const owners = useMemo(() => {
    const names = new Set((selectedMeeting?.action_items || []).map((item) => item.owner));
    return ["", ...Array.from(names).sort()];
  }, [selectedMeeting]);

  async function loadMeetings() {
    try {
      const meetingList = await getMeetings();
      setMeetings(meetingList);
    } catch (err) {
      setError(err.message);
    }
  }

  function updateFormField(event) {
    const { name, value } = event.target;
    setForm((currentForm) => ({
      ...currentForm,
      [name]: value,
    }));
  }

  function loadSampleTranscript() {
    setForm(initialForm);
    setError("");
  }

  async function submitMeeting(event) {
    event.preventDefault();
    setError("");
    setExportedMarkdown("");
    setOwnerFilter("");
    setIsLoading(true);

    try {
      const createdMeeting = await createMeeting({
        title: form.title,
        participants: form.participants || null,
        transcript_text: form.transcript_text,
      });

      setSelectedMeeting(createdMeeting);
      setVisibleActionItems(createdMeeting.action_items);
      await loadMeetings();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function selectMeeting(meetingId) {
    setError("");
    setExportedMarkdown("");
    setOwnerFilter("");
    setIsLoadingMeeting(true);

    try {
      const meeting = await getMeeting(meetingId);
      setSelectedMeeting(meeting);
      setVisibleActionItems(meeting.action_items);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingMeeting(false);
    }
  }

  async function removeMeeting(meetingId) {
    const meeting = meetings.find((item) => item.id === meetingId);
    const confirmed = window.confirm(
      `Delete "${meeting?.title || "this meeting"}" and its generated notes?`,
    );

    if (!confirmed) {
      return;
    }

    setError("");
    setDeletingMeetingId(meetingId);

    try {
      await deleteMeeting(meetingId);
      await loadMeetings();

      if (selectedMeeting?.id === meetingId) {
        setSelectedMeeting(null);
        setVisibleActionItems([]);
        setExportedMarkdown("");
        setOwnerFilter("");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingMeetingId(null);
    }
  }

  async function filterActionItems(owner) {
    setOwnerFilter(owner);
    setError("");

    if (!selectedMeeting) {
      return;
    }

    try {
      const items = await getMeetingActionItems(selectedMeeting.id, owner);
      setVisibleActionItems(items);
    } catch (err) {
      setError(err.message);
    }
  }

  async function markActionItemDone(actionItemId) {
    if (!selectedMeeting) {
      return;
    }

    setError("");

    try {
      await updateActionItem(actionItemId, { status: "done" });
      const refreshedMeeting = await getMeeting(selectedMeeting.id);
      setSelectedMeeting(refreshedMeeting);
      const filteredItems = ownerFilter
        ? await getMeetingActionItems(refreshedMeeting.id, ownerFilter)
        : refreshedMeeting.action_items;
      setVisibleActionItems(filteredItems);
    } catch (err) {
      setError(err.message);
    }
  }

  async function exportSelectedMeeting() {
    if (!selectedMeeting) {
      return;
    }

    setError("");

    try {
      const exported = await exportMeeting(selectedMeeting.id);
      setExportedMarkdown(exported.markdown);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main style={styles.page}>
      <aside style={styles.sidebar}>
        <div style={styles.brandBlock}>
          <span style={styles.eyebrow}>Meeting intelligence</span>
          <h1 style={styles.title}>AI Meeting Summarizer</h1>
          <p style={styles.subtitle}>
            Turn transcripts into source-backed summaries, decisions, risks, and action items.
          </p>
        </div>

        <form onSubmit={submitMeeting} style={styles.form}>
          <div style={styles.formHeader}>
            <h2 style={styles.sectionTitle}>New Meeting</h2>
            <button type="button" onClick={loadSampleTranscript} style={styles.ghostButton}>
              Load sample
            </button>
          </div>

          <label style={styles.label}>
            Meeting title
            <input
              name="title"
              value={form.title}
              onChange={updateFormField}
              required
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            Participants
            <input
              name="participants"
              value={form.participants}
              onChange={updateFormField}
              placeholder="Neha, Abhishek, Jeevan"
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            Transcript
            <textarea
              name="transcript_text"
              value={form.transcript_text}
              onChange={updateFormField}
              required
              rows={13}
              style={styles.textarea}
            />
          </label>

          <button type="submit" disabled={isLoading} style={styles.primaryButton}>
            {isLoading ? "Generating notes..." : "Generate evidence-backed notes"}
          </button>
        </form>

        <section style={styles.meetingPanel}>
          <div style={styles.formHeader}>
            <h2 style={styles.sectionTitle}>Meetings</h2>
            <span style={styles.countBadge}>{meetings.length}</span>
          </div>

          {meetings.length === 0 ? (
            <p style={styles.emptyText}>No saved meetings yet.</p>
          ) : (
            <div style={styles.meetingList}>
              {meetings.map((meeting) => (
                <div
                  key={meeting.id}
                  style={{
                    ...styles.meetingRow,
                    ...(selectedMeeting?.id === meeting.id ? styles.meetingRowActive : {}),
                  }}
                >
                  <button
                    type="button"
                    onClick={() => selectMeeting(meeting.id)}
                    style={styles.meetingSelectButton}
                  >
                    <span>
                      <strong>{meeting.title}</strong>
                      <small style={styles.meetingMeta}>{meeting.source_type}</small>
                    </span>
                    <StatusBadge status={meeting.status} />
                  </button>
                  <button
                    type="button"
                    onClick={() => removeMeeting(meeting.id)}
                    disabled={deletingMeetingId === meeting.id}
                    aria-label={`Delete ${meeting.title}`}
                    title="Delete meeting"
                    style={styles.deleteMeetingButton}
                  >
                    {deletingMeetingId === meeting.id ? "..." : "Delete"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </aside>

      <section style={styles.workspace}>
        {error ? <p style={styles.error}>{error}</p> : null}

        <section style={styles.statsGrid}>
          <Metric label="Meetings" value={stats.meetings} />
          <Metric label="Open Actions" value={stats.open} />
          <Metric label="Done" value={stats.done} />
          <Metric label="With Evidence" value={stats.evidence} />
        </section>

        {isLoadingMeeting ? (
          <section style={styles.heroPanel}>
            <p style={styles.emptyText}>Loading meeting detail...</p>
          </section>
        ) : selectedMeeting ? (
          <MeetingDetail
            exportedMarkdown={exportedMarkdown}
            filterActionItems={filterActionItems}
            markActionItemDone={markActionItemDone}
            meeting={selectedMeeting}
            onExport={exportSelectedMeeting}
            ownerFilter={ownerFilter}
            owners={owners}
            visibleActionItems={visibleActionItems}
          />
        ) : (
          <section style={styles.heroPanel}>
            <span style={styles.eyebrow}>Ready for a transcript</span>
            <h2 style={styles.heroTitle}>Create or select a meeting to inspect the evidence trail.</h2>
            <p style={styles.subtitle}>
              The dashboard will show summary, decisions, risks, follow-up questions, action items,
              owner filters, and Markdown export.
            </p>
          </section>
        )}
      </section>
    </main>
  );
}


function MeetingDetail({
  exportedMarkdown,
  filterActionItems,
  markActionItemDone,
  meeting,
  onExport,
  ownerFilter,
  owners,
  visibleActionItems,
}) {
  const [exportMode, setExportMode] = useState("normal");

  function downloadMarkdown() {
    downloadTextFile(
      exportedMarkdown,
      createExportFileName(meeting, "md"),
      "text/markdown;charset=utf-8",
    );
  }

  function downloadPreviewPdf() {
    openPdfPrintPreview(exportedMarkdown, meeting);
  }

  return (
    <section style={styles.detailShell}>
      <header style={styles.detailHeader}>
        <div>
          <span style={styles.eyebrow}>Selected meeting</span>
          <h2 style={styles.detailTitle}>{meeting.title}</h2>
          <p style={styles.detailMeta}>
            {meeting.participants || "No participants listed"} · {meeting.source_type}
          </p>
        </div>
        <div style={styles.headerActions}>
          <StatusBadge status={meeting.status} />
          <button type="button" onClick={onExport} style={styles.secondaryButton}>
            Export Markdown
          </button>
        </div>
      </header>

      {meeting.summary ? (
        <section style={styles.insightGrid}>
          <article style={styles.summaryPanel}>
            <span style={styles.eyebrow}>Executive summary</span>
            <p style={styles.summaryText}>{meeting.summary.executive_summary}</p>
          </article>
          <InsightList title="Decisions" items={meeting.summary.key_decisions} textKey="decision" />
          <InsightList title="Risks" items={meeting.summary.risks} textKey="risk" tone="risk" />
          <QuestionList questions={meeting.summary.follow_up_questions} />
        </section>
      ) : (
        <section style={styles.summaryPanel}>
          <p style={styles.emptyText}>No summary available for this meeting.</p>
        </section>
      )}

      <section style={styles.actionsPanel}>
        <div style={styles.actionToolbar}>
          <div>
            <span style={styles.eyebrow}>Workflow</span>
            <h3 style={styles.panelTitle}>Action Items</h3>
          </div>
          <label style={styles.filterLabel}>
            Owner
            <select
              value={ownerFilter}
              onChange={(event) => filterActionItems(event.target.value)}
              style={styles.select}
            >
              {owners.map((owner) => (
                <option key={owner || "all"} value={owner}>
                  {owner || "All owners"}
                </option>
              ))}
            </select>
          </label>
        </div>

        {visibleActionItems.length === 0 ? (
          <p style={styles.emptyText}>No action items match this filter.</p>
        ) : (
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th>Owner</th>
                  <th>Task</th>
                  <th>Due</th>
                  <th>Priority</th>
                  <th>Confidence</th>
                  <th>Status</th>
                  <th>Evidence</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {visibleActionItems.map((item) => (
                  <tr key={item.id}>
                    <td>{item.owner}</td>
                    <td style={styles.taskCell}>{item.task}</td>
                    <td>{item.due_date}</td>
                    <td><span style={styles.priorityBadge}>{item.priority}</span></td>
                    <td>{Math.round(item.confidence * 100)}%</td>
                    <td><StatusBadge status={item.status} /></td>
                    <td style={styles.evidenceCell}>{item.evidence_quote}</td>
                    <td>
                      <button
                        type="button"
                        onClick={() => markActionItemDone(item.id)}
                        disabled={item.status === "done"}
                        style={styles.smallButton}
                      >
                        Mark done
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {exportedMarkdown ? (
        <section style={styles.markdownPanel}>
          <div style={styles.formHeader}>
            <h3 style={styles.panelTitle}>Markdown Export</h3>
            <div style={styles.exportActions}>
              <div style={styles.segmentedControl}>
                <button
                  type="button"
                  onClick={() => setExportMode("normal")}
                  style={{
                    ...styles.segmentButton,
                    ...(exportMode === "normal" ? styles.segmentButtonActive : {}),
                  }}
                >
                  Normal
                </button>
                <button
                  type="button"
                  onClick={() => setExportMode("preview")}
                  style={{
                    ...styles.segmentButton,
                    ...(exportMode === "preview" ? styles.segmentButtonActive : {}),
                  }}
                >
                  Preview
                </button>
              </div>
              <button type="button" onClick={downloadMarkdown} style={styles.secondaryButton}>
                Download Markdown
              </button>
              {exportMode === "preview" ? (
                <button type="button" onClick={downloadPreviewPdf} style={styles.secondaryButton}>
                  Download PDF
                </button>
              ) : null}
            </div>
          </div>
          {exportMode === "preview" ? (
            <MarkdownPreview markdown={exportedMarkdown} />
          ) : (
            <pre style={styles.markdownOutput}>{exportedMarkdown}</pre>
          )}
        </section>
      ) : null}
    </section>
  );
}


function MarkdownPreview({ markdown }) {
  const blocks = [];
  let listItems = [];
  let tableRows = [];

  function splitTableRow(line) {
    return line
      .replace(/^\||\|$/g, "")
      .split("|")
      .map((cell) => cell.trim());
  }

  function flushList() {
    if (listItems.length === 0) {
      return;
    }

    blocks.push(
      <ul key={`list-${blocks.length}`} style={styles.previewList}>
        {listItems.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>,
    );
    listItems = [];
  }

  function flushTable() {
    if (tableRows.length === 0) {
      return;
    }

    const [headerRow, ...bodyRows] = tableRows;

    blocks.push(
      <div key={`table-${blocks.length}`} style={styles.previewTableWrap}>
        <table style={styles.previewTable}>
          <thead>
            <tr>
              {headerRow.map((cell) => (
                <th key={cell} style={styles.previewTableHeader}>{cell}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bodyRows.map((row, rowIndex) => (
              <tr key={`row-${rowIndex}`}>
                {row.map((cell, cellIndex) => (
                  <td key={`${rowIndex}-${cellIndex}`} style={styles.previewTableCell}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>,
    );

    tableRows = [];
  }

  markdown.split("\n").forEach((line, index) => {
    const trimmedLine = line.trim();

    if (!trimmedLine) {
      flushList();
      flushTable();
      return;
    }

    if (trimmedLine.startsWith("|") && trimmedLine.endsWith("|")) {
      flushList();
      if (!/^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$/.test(trimmedLine)) {
        tableRows.push(splitTableRow(trimmedLine));
      }
      return;
    }

    if (trimmedLine.startsWith("# ")) {
      flushList();
      flushTable();
      blocks.push(<h1 key={`h1-${index}`} style={styles.previewTitle}>{trimmedLine.slice(2)}</h1>);
      return;
    }

    if (trimmedLine.startsWith("## ")) {
      flushList();
      flushTable();
      blocks.push(<h2 key={`h2-${index}`} style={styles.previewHeading}>{trimmedLine.slice(3)}</h2>);
      return;
    }

    if (trimmedLine.startsWith("- ")) {
      listItems.push(trimmedLine.slice(2));
      return;
    }

    if (trimmedLine.startsWith("> ")) {
      flushList();
      flushTable();
      blocks.push(
        <blockquote key={`quote-${index}`} style={styles.previewQuote}>
          {trimmedLine.slice(2)}
        </blockquote>,
      );
      return;
    }

    flushList();
    flushTable();
    blocks.push(<p key={`p-${index}`} style={styles.previewParagraph}>{trimmedLine}</p>);
  });

  flushList();
  flushTable();

  return <div style={styles.markdownPreview}>{blocks}</div>;
}


function InsightList({ items, textKey, title, tone = "neutral" }) {
  return (
    <article style={styles.insightPanel}>
      <span style={styles.eyebrow}>{title}</span>
      {items.length === 0 ? (
        <p style={styles.emptyText}>None recorded.</p>
      ) : (
        <ul style={styles.insightList}>
          {items.map((item) => (
            <li key={`${title}-${item[textKey]}-${item.evidence_quote}`} style={styles.insightItem}>
              <span style={tone === "risk" ? styles.riskDot : styles.decisionDot}></span>
              <div>
                <strong>{item[textKey]}</strong>
                <small style={styles.evidenceLine}>Evidence: {item.evidence_quote}</small>
              </div>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}


function QuestionList({ questions }) {
  return (
    <article style={styles.insightPanel}>
      <span style={styles.eyebrow}>Follow-up questions</span>
      {questions.length === 0 ? (
        <p style={styles.emptyText}>None recorded.</p>
      ) : (
        <ul style={styles.questionList}>
          {questions.map((question) => (
            <li key={question}>{question}</li>
          ))}
        </ul>
      )}
    </article>
  );
}


function Metric({ label, value }) {
  return (
    <article style={styles.metricCard}>
      <span style={styles.metricValue}>{value}</span>
      <span style={styles.metricLabel}>{label}</span>
    </article>
  );
}


function StatusBadge({ status }) {
  const isDone = status === "done" || status === "completed";
  const isFailed = status?.includes("failed");
  return (
    <span
      style={{
        ...styles.statusBadge,
        ...(isDone ? styles.statusDone : {}),
        ...(isFailed ? styles.statusFailed : {}),
      }}
    >
      {status}
    </span>
  );
}


const styles = {
  page: {
    minHeight: "100vh",
    display: "grid",
    gridTemplateColumns: "420px minmax(0, 1fr)",
    background: "#eef2f7",
    color: "#111827",
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
  },
  sidebar: {
    display: "flex",
    flexDirection: "column",
    gap: "18px",
    padding: "24px",
    borderRight: "1px solid #d8dee8",
    background: "#f8fafc",
  },
  workspace: {
    padding: "24px",
    display: "flex",
    flexDirection: "column",
    gap: "18px",
  },
  brandBlock: {
    padding: "12px 4px 4px",
  },
  eyebrow: {
    display: "block",
    marginBottom: "6px",
    color: "#64748b",
    fontSize: "12px",
    fontWeight: 800,
    letterSpacing: "0",
    textTransform: "uppercase",
  },
  title: {
    margin: "0 0 8px",
    fontSize: "34px",
    lineHeight: 1.05,
  },
  subtitle: {
    margin: 0,
    color: "#475569",
    lineHeight: 1.55,
  },
  form: {
    padding: "20px",
    border: "1px solid #d8dee8",
    borderRadius: "8px",
    background: "#ffffff",
    boxShadow: "0 12px 30px rgba(15, 23, 42, 0.05)",
  },
  formHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "12px",
    alignItems: "center",
    marginBottom: "14px",
  },
  sectionTitle: {
    margin: 0,
    fontSize: "18px",
  },
  label: {
    display: "grid",
    gap: "7px",
    marginBottom: "14px",
    fontSize: "13px",
    fontWeight: 800,
    color: "#1f2937",
  },
  input: {
    width: "100%",
    boxSizing: "border-box",
    padding: "11px 12px",
    border: "1px solid #cbd5e1",
    borderRadius: "7px",
    background: "#ffffff",
    color: "#111827",
    font: "inherit",
  },
  textarea: {
    width: "100%",
    boxSizing: "border-box",
    padding: "12px",
    border: "1px solid #cbd5e1",
    borderRadius: "7px",
    background: "#ffffff",
    color: "#111827",
    font: "inherit",
    lineHeight: 1.45,
    resize: "vertical",
  },
  primaryButton: {
    width: "100%",
    minHeight: "44px",
    padding: "11px 14px",
    border: 0,
    borderRadius: "7px",
    background: "#2563eb",
    color: "#ffffff",
    fontWeight: 800,
    cursor: "pointer",
  },
  ghostButton: {
    padding: "7px 10px",
    border: "1px solid #cbd5e1",
    borderRadius: "7px",
    background: "#f8fafc",
    color: "#1e40af",
    fontWeight: 800,
    cursor: "pointer",
  },
  meetingPanel: {
    padding: "18px",
    border: "1px solid #d8dee8",
    borderRadius: "8px",
    background: "#ffffff",
  },
  meetingList: {
    display: "grid",
    gap: "10px",
  },
  meetingRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "12px",
    width: "100%",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    background: "#ffffff",
    overflow: "hidden",
  },
  meetingRowActive: {
    borderColor: "#2563eb",
    background: "#eff6ff",
  },
  meetingSelectButton: {
    flex: 1,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "12px",
    minWidth: 0,
    padding: "12px",
    border: 0,
    background: "transparent",
    textAlign: "left",
    color: "#111827",
    cursor: "pointer",
  },
  deleteMeetingButton: {
    alignSelf: "stretch",
    minWidth: "72px",
    padding: "0 12px",
    border: 0,
    borderLeft: "1px solid #e2e8f0",
    background: "#fff7ed",
    color: "#9a3412",
    fontSize: "12px",
    fontWeight: 900,
    cursor: "pointer",
  },
  meetingMeta: {
    display: "block",
    marginTop: "3px",
    color: "#64748b",
  },
  countBadge: {
    display: "inline-flex",
    minWidth: "34px",
    justifyContent: "center",
    padding: "4px 9px",
    borderRadius: "999px",
    background: "#e0f2fe",
    color: "#075985",
    fontSize: "12px",
    fontWeight: 900,
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
    gap: "14px",
  },
  metricCard: {
    padding: "16px",
    border: "1px solid #d8dee8",
    borderRadius: "8px",
    background: "#ffffff",
  },
  metricValue: {
    display: "block",
    fontSize: "28px",
    fontWeight: 900,
    color: "#0f172a",
  },
  metricLabel: {
    color: "#64748b",
    fontSize: "13px",
    fontWeight: 700,
  },
  heroPanel: {
    minHeight: "420px",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    padding: "34px",
    border: "1px solid #d8dee8",
    borderRadius: "8px",
    background: "#ffffff",
  },
  heroTitle: {
    maxWidth: "720px",
    margin: "0 0 10px",
    fontSize: "30px",
    lineHeight: 1.15,
  },
  detailShell: {
    display: "flex",
    flexDirection: "column",
    gap: "18px",
  },
  detailHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "18px",
    alignItems: "start",
    padding: "22px",
    border: "1px solid #d8dee8",
    borderRadius: "8px",
    background: "#ffffff",
  },
  detailTitle: {
    margin: 0,
    fontSize: "28px",
  },
  detailMeta: {
    margin: "8px 0 0",
    color: "#64748b",
  },
  headerActions: {
    display: "flex",
    gap: "10px",
    alignItems: "center",
  },
  secondaryButton: {
    minHeight: "38px",
    padding: "8px 12px",
    border: "1px solid #cbd5e1",
    borderRadius: "7px",
    background: "#ffffff",
    color: "#111827",
    fontWeight: 800,
    cursor: "pointer",
  },
  insightGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    gap: "16px",
  },
  summaryPanel: {
    padding: "20px",
    border: "1px solid #d8dee8",
    borderRadius: "8px",
    background: "#ffffff",
  },
  insightPanel: {
    padding: "20px",
    border: "1px solid #d8dee8",
    borderRadius: "8px",
    background: "#ffffff",
  },
  summaryText: {
    margin: 0,
    color: "#1f2937",
    fontSize: "17px",
    lineHeight: 1.6,
  },
  insightList: {
    display: "grid",
    gap: "12px",
    margin: 0,
    padding: 0,
    listStyle: "none",
  },
  insightItem: {
    display: "grid",
    gridTemplateColumns: "10px minmax(0, 1fr)",
    gap: "10px",
    alignItems: "start",
  },
  decisionDot: {
    width: "8px",
    height: "8px",
    marginTop: "7px",
    borderRadius: "999px",
    background: "#2563eb",
  },
  riskDot: {
    width: "8px",
    height: "8px",
    marginTop: "7px",
    borderRadius: "999px",
    background: "#dc2626",
  },
  evidenceLine: {
    display: "block",
    marginTop: "4px",
    color: "#64748b",
    lineHeight: 1.45,
  },
  questionList: {
    margin: 0,
    paddingLeft: "18px",
    color: "#1f2937",
    lineHeight: 1.55,
  },
  actionsPanel: {
    padding: "20px",
    border: "1px solid #d8dee8",
    borderRadius: "8px",
    background: "#ffffff",
  },
  actionToolbar: {
    display: "flex",
    justifyContent: "space-between",
    gap: "16px",
    alignItems: "end",
    marginBottom: "16px",
  },
  panelTitle: {
    margin: 0,
    fontSize: "20px",
  },
  filterLabel: {
    display: "grid",
    gap: "6px",
    minWidth: "180px",
    color: "#475569",
    fontSize: "12px",
    fontWeight: 900,
    textTransform: "uppercase",
  },
  select: {
    padding: "9px 10px",
    border: "1px solid #cbd5e1",
    borderRadius: "7px",
    background: "#ffffff",
    color: "#111827",
    font: "inherit",
    textTransform: "none",
  },
  tableWrap: {
    overflowX: "auto",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "14px",
  },
  taskCell: {
    minWidth: "220px",
    fontWeight: 800,
  },
  evidenceCell: {
    minWidth: "260px",
    color: "#475569",
    fontStyle: "italic",
  },
  priorityBadge: {
    display: "inline-flex",
    padding: "4px 8px",
    borderRadius: "999px",
    background: "#f1f5f9",
    color: "#334155",
    fontWeight: 800,
  },
  smallButton: {
    minWidth: "92px",
    padding: "7px 9px",
    border: "1px solid #cbd5e1",
    borderRadius: "7px",
    background: "#ffffff",
    color: "#111827",
    fontWeight: 800,
    cursor: "pointer",
  },
  markdownPanel: {
    padding: "20px",
    border: "1px solid #d8dee8",
    borderRadius: "8px",
    background: "#ffffff",
  },
  exportActions: {
    display: "flex",
    flexWrap: "wrap",
    justifyContent: "flex-end",
    gap: "8px",
    alignItems: "center",
  },
  segmentedControl: {
    display: "inline-flex",
    padding: "3px",
    border: "1px solid #cbd5e1",
    borderRadius: "8px",
    background: "#f8fafc",
  },
  segmentButton: {
    minHeight: "32px",
    padding: "6px 10px",
    border: 0,
    borderRadius: "6px",
    background: "transparent",
    color: "#475569",
    fontWeight: 800,
    cursor: "pointer",
  },
  segmentButtonActive: {
    background: "#ffffff",
    color: "#1e40af",
    boxShadow: "0 1px 4px rgba(15, 23, 42, 0.12)",
  },
  markdownOutput: {
    maxHeight: "360px",
    overflow: "auto",
    whiteSpace: "pre-wrap",
    padding: "14px",
    border: "1px solid #d8dee8",
    borderRadius: "7px",
    background: "#0f172a",
    color: "#e2e8f0",
    lineHeight: 1.5,
  },
  markdownPreview: {
    maxHeight: "520px",
    overflow: "auto",
    padding: "22px",
    border: "1px solid #d8dee8",
    borderRadius: "7px",
    background: "#ffffff",
    color: "#111827",
  },
  previewTitle: {
    margin: "0 0 22px",
    fontSize: "28px",
    lineHeight: 1.15,
  },
  previewHeading: {
    margin: "26px 0 10px",
    paddingBottom: "7px",
    borderBottom: "1px solid #e2e8f0",
    fontSize: "18px",
  },
  previewParagraph: {
    margin: "7px 0",
    color: "#1f2937",
    lineHeight: 1.55,
  },
  previewList: {
    display: "grid",
    gap: "7px",
    margin: "8px 0 14px",
    paddingLeft: "22px",
    color: "#1f2937",
    lineHeight: 1.55,
  },
  previewQuote: {
    margin: "8px 0 14px",
    padding: "9px 12px",
    borderLeft: "4px solid #2563eb",
    borderRadius: "0 7px 7px 0",
    background: "#f8fafc",
    color: "#475569",
    lineHeight: 1.5,
  },
  previewTableWrap: {
    overflowX: "auto",
    margin: "10px 0 18px",
  },
  previewTable: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "13px",
  },
  previewTableHeader: {
    padding: "9px",
    border: "1px solid #d8dee8",
    background: "#f8fafc",
    textAlign: "left",
    color: "#1f2937",
  },
  previewTableCell: {
    padding: "9px",
    border: "1px solid #d8dee8",
    color: "#334155",
    verticalAlign: "top",
  },
  statusBadge: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "24px",
    padding: "3px 9px",
    borderRadius: "999px",
    background: "#fef3c7",
    color: "#92400e",
    fontSize: "12px",
    fontWeight: 900,
    whiteSpace: "nowrap",
  },
  statusDone: {
    background: "#dcfce7",
    color: "#166534",
  },
  statusFailed: {
    background: "#fee2e2",
    color: "#991b1b",
  },
  emptyText: {
    margin: 0,
    color: "#64748b",
    lineHeight: 1.5,
  },
  error: {
    margin: 0,
    padding: "12px 14px",
    border: "1px solid #fecaca",
    borderRadius: "8px",
    background: "#fef2f2",
    color: "#991b1b",
    fontWeight: 700,
  },
};
