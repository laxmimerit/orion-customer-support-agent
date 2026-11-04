"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const ALL = "all";

function searchHref(query: string, priority: string) {
  const text = query.trim();
  if (!text) return "/";
  const params = new URLSearchParams({ q: text });
  if (priority !== ALL) params.set("priority", priority);
  return `/?${params}`;
}

// The search lives in the URL, so results can be reloaded and the page renders on the server.
// Enter runs it; changing the priority reruns a search that has words in the box.
export function SearchToolbar({ query, priority }: { query: string; priority: string | null }) {
  const router = useRouter();
  const [text, setText] = useState(query);
  const [chosen, setChosen] = useState(priority ?? ALL);

  useEffect(() => {
    setText(query);
    setChosen(priority ?? ALL);
  }, [query, priority]);

  return (
    <form
      className="sub toolbar"
      role="search"
      aria-label="Search tickets"
      onSubmit={(event) => {
        event.preventDefault();
        router.push(searchHref(text, chosen));
      }}
    >
      <div className="field c6 tb-search">
        <label htmlFor="q">Search tickets</label>
        <input
          id="q"
          className="input"
          type="search"
          maxLength={500}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="T00727 or invite link expired"
          aria-describedby="q-hint"
        />
      </div>
      <div className="field c2 tb-prio">
        <label htmlFor="prio">Priority</label>
        <select
          id="prio"
          className="select"
          value={chosen}
          onChange={(event) => {
            setChosen(event.target.value);
            if (text.trim()) router.push(searchHref(text, event.target.value));
          }}
        >
          <option value={ALL}>All priorities</option>
          <option value="P1">P1</option>
          <option value="P2">P2</option>
          <option value="P3">P3</option>
          <option value="P4">P4</option>
        </select>
      </div>
      <div className="c1 tb-clear">
        <button
          type="button"
          className="btn"
          onClick={() => {
            setText("");
            setChosen(ALL);
            router.push("/");
          }}
        >
          Clear
        </button>
      </div>
      <p id="q-hint" className="hint c3 tb-hint">
        Type a ticket ID, such as T00727, or describe the problem in plain words. Priority applies to the search.
      </p>
    </form>
  );
}
