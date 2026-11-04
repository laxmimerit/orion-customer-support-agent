// Display helpers. A missing value reads "Not recorded", never 0 or an empty cell (M07).

export const NOT_RECORDED = "Not recorded";

export function orNotRecorded(value: string | number | null | undefined) {
  return value === null || value === undefined || value === "" ? NOT_RECORDED : String(value);
}

// "in progress" -> "In progress". The API stores statuses in lower case.
export function sentenceCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

// "api" or "API" -> "API", "web" -> "Web".
export function channelLabel(channel: string | null) {
  if (!channel) return NOT_RECORDED;
  return channel.toLowerCase() === "api" ? "API" : sentenceCase(channel.toLowerCase());
}

// Moves the decimal point in the number's own digits, so no multiplication adds float error.
function shifted(value: number, places: number) {
  const [digits, exponent = "0"] = String(value).split("e");
  return Number(`${digits}e${Number(exponent) + places}`);
}

// Rounds half up on the decimal value: 17.65 -> 17.7, where toFixed gives 17.6 from the binary float.
export function rounded(value: number, places = 1) {
  return shifted(Math.round(shifted(value, places)), -places);
}

// A share as a percentage, rounded by the same rule: 0.285 -> 29, where 0.285 * 100 falls just short of 28.5.
export function asPercent(share: number, places = 0) {
  return rounded(shifted(share, 2), places);
}

// 7.96 -> "7h 58m", 3 -> "3h", 0.5 -> "30m". Hours from the API are exact decimal strings with four places.
// Six places keep every real value and drop the float error of the * 60, so 1.025 is 61.5 minutes and rounds up.
export function duration(hours: string | number) {
  const minutes = Math.round(rounded(Math.abs(Number(hours)) * 60, 6));
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

// 16.2 -> "16.2h"; the hours figure the reports show.
export function hoursShort(value: string | number, places = 1) {
  return `${rounded(Number(value), places).toFixed(places)}h`;
}

// 2451, 4000 -> "61%". Null when there is nothing to divide by, so no 0% is invented.
export function percent(part: number, whole: number) {
  return whole > 0 ? `${asPercent(part / whole)}%` : null;
}

export function plural(count: number, one: string, many = `${one}s`) {
  return `${count} ${count === 1 ? one : many}`;
}

// ["a", "b", "c"] -> "a, b and c".
export function listOf(words: string[]) {
  return words.length < 2 ? words.join("") : `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}`;
}

// ["subject", "plan_id"] -> "Same subject and plan". The names are the API's matched_on fields.
export function matchedPhrase(fields: string[]) {
  return `Same ${listOf(fields.map((field) => (field === "plan_id" ? "plan" : field)))}`;
}

// "Fern Platform 086" -> "F".
export function initial(name: string | null) {
  return (name?.trim().charAt(0) || "?").toUpperCase();
}

// A ticket with no status is still active, as the API counts it.
export function isResolved(status: string | null) {
  return status?.toLowerCase() === "resolved";
}

// "99.0000" -> 9900. Money stays in whole cents so sums pick up no float error. Null if it is not a number.
export function toCents(amount: string | null) {
  const match = amount?.trim().match(/^(-?)(\d+)(?:\.(\d+))?$/);
  if (!match) return null;
  const digits = (match[3] ?? "").padEnd(3, "0");
  const cents = Number(match[2]) * 100 + Number(digits.slice(0, 2)) + (digits[2] >= "5" ? 1 : 0);
  return match[1] ? -cents : cents;
}

// 475200 -> "4752.00 USD".
export function centsToMoney(cents: number) {
  const whole = Math.abs(cents);
  return `${cents < 0 ? "-" : ""}${Math.floor(whole / 100)}.${String(whole % 100).padStart(2, "0")} USD`;
}

// "99.0000" -> "99.00 USD".
export function money(amount: string | null) {
  const cents = toCents(amount);
  return cents === null ? NOT_RECORDED : centsToMoney(cents);
}

// Splits stored text on its blank lines. Empty or missing text gives no paragraphs.
export function paragraphs(text: string | null) {
  return (text ?? "").split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean);
}
