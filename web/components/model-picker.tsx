import { type AllowedModel, modelOption } from "@/lib/models";

// The list comes from the API, which refuses anything else. A line that has not been run shows, and can't be chosen.
export function ModelPicker({ id, models, value, onChange, disabled }: {
  id: string;
  models: AllowedModel[];
  value: string | null;
  onChange: (model: string) => void;
  disabled: boolean;
}) {
  if (models.length === 0) return null;
  const paid = models.find((model) => model.id === value)?.paid === true;
  return (
    <div className="ask-model">
      <label htmlFor={id}>Model</label>
      <select id={id} value={value ?? ""} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
        {models.map((model) => <option key={model.id} value={model.id} disabled={!model.run}>{modelOption(model)}</option>)}
      </select>
      {paid && <p className="ask-hint">Paid: each use spends OpenRouter credit. The desk only uses a paid model when you pick one here.</p>}
    </div>
  );
}
