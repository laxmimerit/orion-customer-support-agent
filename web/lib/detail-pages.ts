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
