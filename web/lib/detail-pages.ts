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

// A queue page number from the address. Anything that isn't a whole number from 1 up means the first page.
export function queuePage(value: string | string[] | undefined) {
  const requested = typeof value === "string" && value ? Number(value) : 1;
  return Number.isInteger(requested) && requested >= 1 ? Math.min(requested, 100_000) : 1;
}

export function queueHref(page: number) {
  return page === 1 ? "/" : `/?page=${page}`;
}

// The ticket carries the queue page it was opened from, so Back to queue can return there.
export function ticketHref(ticketId: string, page: number) {
  const href = `/tickets/${encodeURIComponent(ticketId)}`;
  return page === 1 ? href : `${href}?queue=${page}`;
}
