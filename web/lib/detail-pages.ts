const LOADING_LABELS = new Map([
  ["tickets", "Loading the case"],
  ["customers", "Loading customer"],
  ["knowledge", "Loading the article"],
]);

// What a screen reader hears while a ticket, customer or article opens. Null for any other address.
export function detailLoadingLabel(pathname: string) {
  const [, section, id, ...rest] = pathname.split("/");
  if (!section || !id || rest.length > 0) return null;
  return LOADING_LABELS.get(section) ?? null;
}

// True when `to` is the list that the detail page `from` belongs to. Tickets are listed on the queue, at "/".
export function isBackToList(from: string, to: string) {
  if (!detailLoadingLabel(from)) return false;
  const section = from.split("/")[1];
  return to === (section === "tickets" ? "/" : `/${section}`);
}
