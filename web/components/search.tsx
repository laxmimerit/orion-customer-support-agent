"use client";

import { useEffect, useRef } from "react";

import { SearchIcon } from "@/components/icons";

// The top bar's search box. `value` and `onChange` make it filter as you type.
// `action` and `param` make Enter open that page with the words as a query (`/?q=...`), so it also
// works on pages with nothing of their own to filter. Pressing "/" focuses it when `shortcut` is set.
export function SearchField({ label, placeholder, value, onChange, action, param = "q", shortcut = false, onSubmit }: {
  label: string;
  placeholder: string;
  value?: string;
  onChange?: (value: string) => void;
  action?: string;
  param?: string;
  shortcut?: boolean;
  onSubmit?: (value: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!shortcut) return;
    function focusOnSlash(event: KeyboardEvent) {
      const target = event.target as Element | null;
      const typing = target?.closest?.("input, textarea, select, [contenteditable]");
      if (event.key === "/" && !typing && !event.metaKey && !event.ctrlKey && !event.altKey) {
        event.preventDefault();
        input.current?.focus();
      }
    }
    document.addEventListener("keydown", focusOnSlash);
    return () => document.removeEventListener("keydown", focusOnSlash);
  }, [shortcut]);

  return (
    <form
      className="search"
      role="search"
      action={action}
      method="get"
      onSubmit={onSubmit ? (event) => { event.preventDefault(); onSubmit(input.current?.value ?? ""); } : undefined}
    >
      <SearchIcon />
      <label className="visually-hidden" htmlFor="desk-search">{label}</label>
      <input
        ref={input}
        id="desk-search"
        type="search"
        name={action ? param : undefined}
        placeholder={placeholder}
        value={value}
        onChange={onChange ? (event) => onChange(event.target.value) : undefined}
        autoComplete="off"
      />
      {shortcut && <kbd>/</kbd>}
    </form>
  );
}
