// Display helpers. A missing value reads "Not recorded", never 0 or an empty cell (M07).

export const NOT_RECORDED = "Not recorded";

export function orNotRecorded(value: string | number | null | undefined) {
  return value === null || value === undefined || value === "" ? NOT_RECORDED : String(value);
}

// "in progress" -> "In progress". The API stores statuses in lower case.
export function sentenceCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

// "7.9600" -> "7.96", "24.0000" -> "24". The decimal string is trimmed, never rounded.
export function trimDecimal(value: string) {
  return value.includes(".") ? value.replace(/0+$/, "").replace(/\.$/, "") : value;
}

// "7.9600" -> "7.96 h".
export function hours(value: string) {
  return `${trimDecimal(value)} h`;
}
