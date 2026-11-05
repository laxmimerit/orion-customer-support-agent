// The allow-list as the desk reads it. Used in the browser, so it holds nothing from the server.

// One line of the list. `id` is all a request sends: the API decides which model that means. `mail` is true where Ask has the mail tools.
export type AllowedModel = { id: string; label: string; provider: string; model: string; paid: boolean; run: boolean; mail: boolean };

// The longest `model` the API takes (on /api/tickets/{ticket_id}/ask and /triage).
export const MODEL_ID_LIMIT = 64;

// The API lists the default first, so the first line it will call is what the desk starts on.
export function firstRunnable(models: AllowedModel[]) {
  return models.find((model) => model.run)?.id ?? null;
}

export function modelOption(model: AllowedModel) {
  const name = `${model.label} · ${model.provider}`;
  if (!model.run) return `${name} · Not run`;
  return `${name} · ${model.paid ? "Paid" : "Free"}`;
}

export function modelLabel(models: AllowedModel[], id: string | null) {
  return models.find((model) => model.id === id)?.label ?? null;
}

export function modelHasMail(models: AllowedModel[], id: string | null) {
  return models.find((model) => model.id === id)?.mail === true;
}
