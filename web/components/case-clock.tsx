"use client";

import { useLayoutEffect, useRef, useState } from "react";

import { NOT_RECORDED, duration } from "@/lib/format";

// Label widths are estimated on the wide side, so a doubtful fit falls back to the legend.
const CHAR_PX = 7;
const LABEL_GAP_PX = 12;
const ORIGIN_PX = 16;
// The widest the axis gets. Used for the server render, until the real width is measured.
const WIDE_PX = 992;

type Tone = "missed" | "met" | "plain";

type Stage = {
  done: number | null;
  target: number | null;
  tone: Tone;
  doneText: string;
  targetText: string;
  verdict: string | null;
  summary: string;
};

type Label = { key: string; at: number; title: string; note?: string; tone?: Tone };
type Placed = Label & { align: "" | "is-start" | "is-end"; left: number };

const toHours = (value: string | null) => (value === null ? null : Number(value));

const percent = (at: number) => `${(at * 100).toFixed(1)}%`;

function gapText(hours: number) {
  const text = duration(hours);
  return text === "0m" ? "Under 1m" : text;
}

// The only place late or met is decided, and only with both numbers. On the target counts as met, as in the reports.
function verdictFor(done: number, target: number) {
  if (done === target) return "On target";
  return done > target ? `${gapText(done - target)} late` : `${gapText(target - done)} inside target`;
}

function readStage(name: string, doneLabel: string, waiting: string, doneValue: string | null, targetValue: string | null): Stage {
  const done = toHours(doneValue);
  const target = toHours(targetValue);
  const judged = done !== null && target !== null;
  const tone: Tone = !judged ? "plain" : done > target ? "missed" : "met";
  return {
    done,
    target,
    tone,
    doneText: done === null ? waiting : `${doneLabel} ${duration(done)}`,
    targetText: target === null ? "No target recorded" : `Target ${duration(target)}`,
    verdict: judged ? verdictFor(done, target) : null,
    summary: done === null ? waiting.toLowerCase() : target === null ? `no ${name} target` : `${name} target ${tone}`,
  };
}

function summarise(reply: Stage, resolve: Stage) {
  if (reply.tone !== "plain" && reply.tone === resolve.tone) return `both targets ${reply.tone}`;
  return `${reply.summary}, ${resolve.summary}`;
}

// Puts each label under its mark, kept inside the axis, and says whether any two touch.
function placeRow(labels: Label[], width: number) {
  let fits = true;
  let edge = -Infinity;
  const placed = [...labels].sort((a, b) => a.at - b.at).map((label): Placed => {
    const chars = Math.max(label.title.length, label.note?.length ?? 0);
    const size = chars * CHAR_PX;
    const left = Math.min(Math.max(label.at * width - size / 2, 0), Math.max(width - size, 0));
    if (size > width || left < edge + LABEL_GAP_PX) fits = false;
    edge = left + size;
    const align = left === 0 ? "is-start" : left + size >= width ? "is-end" : "";
    return { ...label, align, left };
  });
  return { placed, fits };
}

function AxisLabel({ label, className }: { label: Placed; className: string }) {
  return (
    <span
      className={`clock-label ${className} ${label.align}`}
      style={label.align ? undefined : { left: percent(label.at) }}
    >
      {label.note === undefined ? label.title : <strong>{label.title}</strong>}
      {label.note !== undefined && <span className={`clock-verdict is-${label.tone}`}>{label.note}</span>}
    </span>
  );
}

export function CaseClock({ status, replyTarget, reply, resolveTarget, resolved }: {
  status: string | null;
  replyTarget: string | null;
  reply: string | null;
  resolveTarget: string | null;
  resolved: string | null;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(WIDE_PX);

  useLayoutEffect(() => {
    const node = box.current;
    if (!node) return;
    const measure = () => setWidth(node.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  // A closed ticket with no time is a gap in the record; only an open one is still waiting.
  const closed = status === null || status.toLowerCase() === "resolved";
  const replyStage = readStage("first reply", "First reply",
    closed ? `First reply: ${NOT_RECORDED}` : "No first reply yet", reply, replyTarget);
  const resolveStage = readStage("resolution", "Resolved",
    closed ? `Resolution: ${NOT_RECORDED}` : "Not resolved yet", resolved, resolveTarget);
  const stages = [replyStage, resolveStage];

  const present = stages.flatMap((stage) => [stage.done, stage.target]).filter((value) => value !== null);
  const axis = Math.ceil(Math.max(0, ...present) * 1.055 * 10) / 10;
  const at = (value: number) => (axis > 0 ? value / axis : 0);

  const top = placeRow([
    ...(replyStage.target === null ? [] : [{ key: "reply", at: at(replyStage.target), title: `Reply target ${duration(replyStage.target)}` }]),
    ...(resolveStage.target === null ? [] : [{ key: "resolve", at: at(resolveStage.target), title: `Resolve target ${duration(resolveStage.target)}` }]),
  ], width);

  // With no time to mark, the words sit at the end of the axis the stage belongs to.
  const noteFor = (stage: Stage) => stage.verdict ?? (stage.done === null ? "" : stage.targetText);
  const bottom = placeRow([
    { key: "reply", at: replyStage.done === null ? 0 : at(replyStage.done), title: replyStage.doneText, note: noteFor(replyStage), tone: replyStage.tone },
    { key: "resolve", at: resolveStage.done === null ? 1 : at(resolveStage.done), title: resolveStage.doneText, note: noteFor(resolveStage), tone: resolveStage.tone },
  ], width);

  const tight = axis <= 0 || !top.fits || !bottom.fits;
  const showOrigin = bottom.placed[0].left >= ORIGIN_PX + LABEL_GAP_PX;
  const latest = Math.max(replyStage.done ?? 0, resolveStage.done ?? 0);
  const description = stages
    .map((stage) => [stage.doneText, stage.targetText, stage.verdict].filter(Boolean).join(". "))
    .join(". ");

  return (
    <div ref={box} className={`clock${tight ? " is-tight" : ""}`}>
      <div className="clock-head">
        <h2 className="clock-title">Case clock</h2>
        <span className="clock-meta">Hours · {summarise(replyStage, resolveStage)}</span>
      </div>

      {axis > 0 && (
        <div className="clock-axis" role="img" aria-label={`${description}.`}>
          {top.placed.map((label) => <AxisLabel key={label.key} label={label} className="is-target" />)}
          <div className="clock-bar clock-track" />
          {latest > 0 && <div className="clock-bar clock-elapsed" style={{ width: percent(at(latest)) }} />}
          {stages.map((stage, index) => stage.tone === "missed" && (
            <div
              key={index}
              className="clock-bar clock-over"
              style={{ left: percent(at(stage.target!)), width: percent(at(stage.done! - stage.target!)) }}
            />
          ))}
          {stages.map((stage, index) => stage.target !== null && (
            <div key={index} className="clock-tick" style={{ left: percent(at(stage.target)) }} />
          ))}
          {stages.map((stage, index) => stage.done !== null && (
            <span key={index} className={`clock-marker is-${stage.tone}`} style={{ left: percent(at(stage.done)) }} />
          ))}
          {showOrigin && <span className="clock-origin">0h</span>}
          {bottom.placed.map((label) => <AxisLabel key={label.key} label={label} className="is-actual" />)}
        </div>
      )}

      <ul className="clock-legend">
        {stages.map((stage) => (
          <li key={stage.doneText} className="clock-entry">
            <span className={`clock-dot is-${stage.tone}`} aria-hidden="true" />
            <span className="clock-entry-text">
              <strong>{stage.doneText}</strong>
              <span>{stage.targetText}</span>
            </span>
            {stage.verdict && <span className={`clock-verdict is-${stage.tone}`}>{stage.verdict}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
