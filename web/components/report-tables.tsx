"use client";

import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

import { TableIcon } from "@/components/icons";

const Tables = createContext<{ show: boolean; toggle: () => void }>({ show: false, toggle: () => {} });

// Holds the "Show tables" choice so the button in the heading can reveal tables further down the page.
export function TablesProvider({ children }: { children: React.ReactNode }) {
  const [show, setShow] = useState(false);
  const value = useMemo(() => ({ show, toggle: () => setShow((current) => !current) }), [show]);
  return <Tables.Provider value={value}>{children}</Tables.Provider>;
}

// The label alone carries the state, so a screen reader never hears "Hide tables, pressed". The tables open
// far below the button, so a status line says where; it stays empty until the first press.
export function TablesToggle({ shownNotice }: { shownNotice: string }) {
  const { show, toggle } = useContext(Tables);
  const [notice, setNotice] = useState("");
  const press = () => {
    setNotice(show ? "Tables hidden." : shownNotice);
    toggle();
  };
  return (
    <>
      <button type="button" className={`rp-toggle${show ? " is-on" : ""}`} onClick={press}>
        <TableIcon />
        {show ? "Hide tables" : "Show tables"}
      </button>
      <span className="visually-hidden" role="status">{notice}</span>
    </>
  );
}

export function WhenTables({ children }: { children: React.ReactNode }) {
  return useContext(Tables).show ? children : null;
}

// A box that scrolls sideways on narrow screens. Only while it really overflows is it a named stop on the
// Tab order, so keyboard users can scroll it with the arrow keys. A pixel of overflow is rounding, not
// scrolling, and a box that holds focus keeps its stop so a resize does not throw the focus away.
export function ScrollBox({ className, label, children }: {
  className: string; label: string; children: React.ReactNode;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [scrolls, setScrolls] = useState(false);
  useEffect(() => {
    const node = box.current;
    if (!node) return;
    const observer = new ResizeObserver(() => {
      setScrolls(node.scrollWidth > node.clientWidth + 1 || document.activeElement === node);
    });
    observer.observe(node);
    if (node.firstElementChild) observer.observe(node.firstElementChild);
    return () => observer.disconnect();
  }, []);
  const stop = scrolls ? { tabIndex: 0, role: "region", "aria-label": label } : undefined;
  return <div ref={box} className={className} {...stop}>{children}</div>;
}
