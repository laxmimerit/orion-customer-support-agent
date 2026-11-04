import { describe, expect, it } from "vitest";

import { askProblem, askReader } from "@/lib/ask";

const bytes = (text: string) => new TextEncoder().encode(text);
const delta = (text: string) => `event: delta\ndata: ${JSON.stringify({ text })}\n\n`;

describe("askReader", () => {
  it("reads each event in order", () => {
    const read = askReader();
    expect(read(bytes(delta("Not ") + delta("recorded.") + 'event: done\ndata: {"complete": true}\n\n'))).toEqual([
      { type: "delta", text: "Not " },
      { type: "delta", text: "recorded." },
      { type: "done", complete: true },
    ]);
  });

  it("keeps an unfinished event for the next read", () => {
    const read = askReader();
    const frame = delta("Paris");
    expect(read(bytes(frame.slice(0, 12)))).toEqual([]);
    expect(read(bytes(frame.slice(12)))).toEqual([{ type: "delta", text: "Paris" }]);
  });

  it("joins a character split across two reads", () => {
    const read = askReader();
    const frame = bytes(delta("7–8 hours"));
    const split = frame.indexOf(0xe2) + 1;
    expect(read(frame.slice(0, split))).toEqual([]);
    expect(read(frame.slice(split))).toEqual([{ type: "delta", text: "7–8 hours" }]);
  });

  it("keeps newlines inside the text", () => {
    expect(askReader()(bytes(delta("one\n\ntwo")))).toEqual([{ type: "delta", text: "one\n\ntwo" }]);
  });

  it("reads frames with CRLF line endings", () => {
    expect(askReader()(bytes('event: delta\r\ndata: {"text": "Yes"}\r\n\r\n'))).toEqual([{ type: "delta", text: "Yes" }]);
  });

  it("reports an answer that was cut short", () => {
    expect(askReader()(bytes('event: done\ndata: {"complete": false}\n\n'))).toEqual([{ type: "done", complete: false }]);
  });

  it("passes on the API's error body", () => {
    const body = { error: { status: 429, code: "model_busy", message: "Try again in a minute." } };
    expect(askReader()(bytes(`event: error\ndata: ${JSON.stringify(body)}\n\n`))).toEqual([
      { type: "error", problem: body.error },
    ]);
  });

  it.each([
    ["an unknown event", 'event: ping\ndata: {}\n\n'],
    ["a comment", ": keep-alive\n\n"],
    ["a broken body", "event: delta\ndata: {not json\n\n"],
    ["a delta with no text", "event: delta\ndata: {}\n\n"],
  ])("skips %s", (_, frame) => {
    expect(askReader()(bytes(frame))).toEqual([]);
  });
});

describe("askProblem", () => {
  it("reads the desk's error body", () => {
    expect(askProblem({ error: { status: 404, code: "ticket_not_found", message: "No ticket." } }, 500))
      .toEqual({ status: 404, code: "ticket_not_found", message: "No ticket." });
  });

  it("falls back to the response status when the body has none", () => {
    expect(askProblem({ error: { code: "x", message: "y" } }, 503)).toEqual({ status: 503, code: "x", message: "y" });
  });

  it.each([[null], ["<html>"], [{}]])("names an unknown failure for %j", (body) => {
    expect(askProblem(body, 500)).toEqual({ status: 500, code: "unexpected_response",
      message: "The desk did not return an answer. Try again." });
  });
});
