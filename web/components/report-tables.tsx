"use client";

import { createContext, useContext, useMemo, useState } from "react";

import { TableIcon } from "@/components/icons";

const Tables = createContext<{ show: boolean; toggle: () => void }>({ show: false, toggle: () => {} });

// Holds the "Show tables" choice so the button in the heading can reveal tables further down the page.
export function TablesProvider({ children }: { children: React.ReactNode }) {
  const [show, setShow] = useState(false);
  const value = useMemo(() => ({ show, toggle: () => setShow((current) => !current) }), [show]);
  return <Tables.Provider value={value}>{children}</Tables.Provider>;
}

export function TablesToggle() {
  const { show, toggle } = useContext(Tables);
  return (
    <button type="button" className="rp-toggle" aria-pressed={show} onClick={toggle}>
      <TableIcon />
      {show ? "Hide tables" : "Show tables"}
    </button>
  );
}

export function WhenTables({ children }: { children: React.ReactNode }) {
  return useContext(Tables).show ? children : null;
}
