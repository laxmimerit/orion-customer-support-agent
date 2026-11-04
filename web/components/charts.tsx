// Report charts (notes/design-brief.md, Chart rules). Every value is printed beside its bar,
// so the bars are decorative and carry no hover, controls or rounded ends.
import { NOT_RECORDED } from "@/lib/format";

export const SERIES = {
  resolved: "var(--series-resolved)",
  unresolved: "var(--series-unresolved)",
  met: "var(--series-resolved)",
  single: "var(--series-unresolved)",
  missed: "var(--series-missed)",
  none: "var(--series-none)",
};

type Series = { name: string; color: string };

export type Bar = {
  label?: React.ReactNode;
  segments: { value: number; color: string }[];
  text: React.ReactNode;
};

export type Pair = {
  label: React.ReactNode;
  items: { value: string | null; color: string; text: string }[];
};

function percent(value: number, scale: number) {
  return `${scale > 0 ? (value / scale) * 100 : 0}%`;
}

function barTotal(bar: Bar) {
  return bar.segments.reduce((sum, segment) => sum + segment.value, 0);
}

// The longest bar in a set. Every axis starts at zero, so this alone sets the scale.
export function largest(bars: Bar[]) {
  return Math.max(0, ...bars.map(barTotal));
}

// "3.61 from 213 tickets, 107 not recorded". A value the API did not return is never a number.
export function averageText(value: string | null, unit: string, counted: number, missing: number) {
  return value === null ? NOT_RECORDED : `${value}${unit} from ${counted} tickets, ${missing} not recorded`;
}

export function averageBar(label: React.ReactNode, value: string | null, unit: string, counted: number, missing: number): Bar {
  return {
    label,
    segments: value === null ? [] : [{ value: Number(value), color: SERIES.single }],
    text: averageText(value, unit, counted, missing),
  };
}

export function Legend({ items, style }: { items: Series[]; style?: React.CSSProperties }) {
  return (
    <div className="legend" style={style}>
      {items.map((item) => (
        <span key={item.name}><i style={{ background: item.color }} />{item.name}</span>
      ))}
    </div>
  );
}

export function Chart({ title, note, legend, className = "", style, children }: {
  title: string; note: string; legend?: Series[]; className?: string; style?: React.CSSProperties; children: React.ReactNode;
}) {
  return (
    <div className={`chart ${className}`} style={style}>
      <h3>{title}</h3>
      <p className="cap">{note}</p>
      {legend && <Legend items={legend} />}
      {children}
    </div>
  );
}

// Rows stay in the order given. Pass `scale` when two charts share one.
export function Bars({ bars, scale = largest(bars) }: { bars: Bar[]; scale?: number }) {
  return (
    <div className="bars">
      {bars.map((bar, index) => (
        <div key={index}>
          {bar.label !== undefined && <div className="bl">{bar.label}</div>}
          <div className="track" aria-hidden="true">
            <div className="stackbar" style={{ width: percent(barTotal(bar), scale) }}>
              {bar.segments.filter((segment) => segment.value > 0).map((segment) => (
                <span key={segment.color} className="seg" style={{ flex: segment.value, background: segment.color }} />
              ))}
            </div>
          </div>
          <div className="bv">{bar.text}</div>
        </div>
      ))}
    </div>
  );
}

// Two bars per row on one shared scale. A value the API did not return draws no bar.
export function PairedBars({ pairs }: { pairs: Pair[] }) {
  const scale = Math.max(0, ...pairs.flatMap((pair) => pair.items.map((item) => Number(item.value))));
  return (
    <div className="bars">
      {pairs.map((pair, index) => (
        <div key={index} className="pair">
          <div className="bl" style={{ margin: 0 }}>{pair.label}</div>
          {pair.items.map((item) => (
            <div key={item.color}>
              <div className="track" style={{ height: 8 }} aria-hidden="true">
                <div className="stackbar">
                  {item.value !== null && (
                    <span className="seg" style={{ flex: "none", width: percent(Number(item.value), scale), background: item.color }} />
                  )}
                </div>
              </div>
              <div className="bv">{item.text}</div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
