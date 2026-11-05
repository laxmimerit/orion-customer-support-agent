import { describe, expect, it } from "vitest";

import { askProblem, askReader, plainAnswer, sourceHref } from "@/lib/ask";

const bytes = (text: string) => new TextEncoder().encode(text);
const delta = (text: string) => `event: delta\ndata: ${JSON.stringify({ text })}\n\n`;
const done = (body: unknown) => `event: done\ndata: ${JSON.stringify(body)}\n\n`;
const KB004 = { kind: "article", id: "KB004", title: "Resend an invitation" };
const PAGE = { url: "https://developer.mozilla.org/docs/429", title: "429 Too Many Requests" };

describe("askReader", () => {
  it("reads each event in order", () => {
    const read = askReader();
    const finished = done({ complete: true, found: true, sources: [KB004] });
    expect(read(bytes('event: lookup\ndata: {"label": "Reading an article"}\n\n' + delta("Not ") + delta("recorded.") + finished))).toEqual([
      { type: "lookup", label: "Reading an article" },
      { type: "delta", text: "Not " },
      { type: "delta", text: "recorded." },
      { type: "done", complete: true, found: true, sources: [KB004], pages: [], searches: [], note: null },
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
    expect(askReader()(bytes(done({ complete: false, found: true, sources: [] }))))
      .toEqual([{ type: "done", complete: false, found: true, sources: [], pages: [], searches: [], note: null }]);
  });

  it("reports an answer the records do not hold, with what was checked", () => {
    expect(askReader()(bytes(done({ complete: true, found: false, sources: [KB004] }))))
      .toEqual([{ type: "done", complete: true, found: false, sources: [KB004], pages: [], searches: [], note: null }]);
  });

  it("keeps a source with no title", () => {
    const source = { kind: "customer", id: "C0300", title: null };
    expect(askReader()(bytes(done({ complete: true, found: true, sources: [source] }))))
      .toEqual([{ type: "done", complete: true, found: true, sources: [source], pages: [], searches: [], note: null }]);
  });

  it.each([
    ["no sources field", { complete: true, found: true }],
    ["sources that are not a list", { complete: true, found: true, sources: "KB004" }],
    ["a source of an unknown kind", { complete: true, found: true, sources: [{ kind: "invoice", id: "I1", title: null }] }],
    ["an inherited kind", { complete: true, found: true, sources: [{ kind: "constructor", id: "I1", title: null }] }],
    ["a source with no ID", { complete: true, found: true, sources: [{ kind: "ticket", title: "x" }] }],
    ["a source that is not an object", { complete: true, found: true, sources: [null, 7] }],
    ["a script address", { complete: true, found: true, pages: [{ url: "javascript:alert(1)", title: "x" }] }],
    ["a data address", { complete: true, found: true, pages: [{ url: "data:text/html,x", title: "x" }] }],
    ["a page that is no address", { complete: true, found: true, pages: [{ url: "T00727", title: null }] }],
    ["a page with no address", { complete: true, found: true, pages: [{ title: "x" }] }],
    ["pages that are not a list", { complete: true, found: true, pages: "https://example.com" }],
  ])("lists nothing for %s", (_, body) => {
    expect(askReader()(bytes(done(body)))).toEqual([{ type: "done", complete: true, found: true, sources: [], pages: [], searches: [], note: null }]);
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
    ["a lookup with no label", "event: lookup\ndata: {}\n\n"],
  ])("skips %s", (_, frame) => {
    expect(askReader()(bytes(frame))).toEqual([]);
  });
});

describe("plainAnswer", () => {
  it("drops the marks the model should not have used", () => {
    expect(plainAnswer("**KB004** covers it, via `list_articles`.")).toBe("KB004 covers it, via list_articles.");
  });

  it("leaves a single star and plain text alone", () => {
    expect(plainAnswer("8 seats * $99, one\n\ntwo")).toBe("8 seats * $99, one\n\ntwo");
  });
});

describe("the done event", () => {
  it("keeps a web page, with or without a title", () => {
    const fetched = { url: "http://example.com/a", title: null };
    expect(askReader()(bytes(done({ complete: true, found: true, sources: [], pages: [PAGE, fetched] }))))
      .toEqual([{ type: "done", complete: true, found: true, sources: [], pages: [PAGE, fetched], searches: [], note: null }]);
  });

  it("keeps the words the model searched for, and drops anything that is not text", () => {
    expect(askReader()(bytes(done({ complete: true, found: true, sources: [], searches: ["HTTP 429", 7, null] }))))
      .toEqual([{ type: "done", complete: true, found: true, sources: [], pages: [], searches: ["HTTP 429"], note: null }]);
  });

  it("carries the note for the next question", () => {
    expect(askReader()(bytes(done({ complete: true, found: true, sources: [], note: "Ask about the invite." }))))
      .toEqual([{ type: "done", complete: true, found: true, sources: [], pages: [], searches: [], note: "Ask about the invite." }]);
  });

  it("treats a note that is not text as no note", () => {
    expect(askReader()(bytes(done({ complete: true, found: true, sources: [], note: 7 }))))
      .toEqual([{ type: "done", complete: true, found: true, sources: [], pages: [], searches: [], note: null }]);
  });
});

describe("sourceHref", () => {
  it.each([
    [{ kind: "ticket", id: "T00727", title: null }, "/tickets/T00727"],
    [{ kind: "customer", id: "C0086", title: null }, "/customers/C0086"],
    [{ kind: "article", id: "KB004", title: null }, "/knowledge/KB004"],
    [{ kind: "ticket", id: "a/b c", title: null }, "/tickets/a%2Fb%20c"],
  ] as const)("links %j to its page", (source, href) => {
    expect(sourceHref(source)).toBe(href);
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
