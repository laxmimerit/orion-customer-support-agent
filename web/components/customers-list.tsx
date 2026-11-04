"use client";

import Link from "next/link";
import { useState } from "react";

import { PageHead, TopBar } from "@/components/desk";
import { SearchField } from "@/components/search";
import type { CustomerListItem } from "@/lib/api";
import { initial, NOT_RECORDED, orNotRecorded, plural } from "@/lib/format";

const PAGE_SIZE = 20;
// The API returns customers in this order.
const SORT_LABEL = "Company name · A–Z";

const planOf = (customer: CustomerListItem) => customer.plan ?? NOT_RECORDED;
const regionOf = (customer: CustomerListItem) => customer.region ?? NOT_RECORDED;

// "Not recorded" -> "is-not-recorded". Known plans have a colour in customers.css.
const toneClass = (label: string) => `is-${label.toLowerCase().replace(/\W+/g, "-")}`;

type Count = { label: string; count: number };

function countBy(items: CustomerListItem[], pick: (customer: CustomerListItem) => string): Count[] {
  const counts = new Map<string, number>();
  for (const item of items) counts.set(pick(item), (counts.get(pick(item)) ?? 0) + 1);
  return [...counts].map(([label, count]) => ({ label, count }));
}

export function CustomersList({ total, items, description }: {
  total: number; items: CustomerListItem[]; description: string;
}) {
  const [query, setQuery] = useState("");
  const [plan, setPlan] = useState<string | null>(null);
  const [region, setRegion] = useState<string | null>(null);
  const [shown, setShown] = useState(PAGE_SIZE);

  // Plans run from most customers to fewest, regions A to Z. Both stay put while filtering.
  const plans = countBy(items, planOf).sort((a, b) => b.count - a.count);
  const regions = countBy(items, regionOf).sort((a, b) => a.label.localeCompare(b.label, "en"));

  const words = query.trim().toLowerCase();
  const filtered = items.filter((customer) =>
    (plan === null || planOf(customer) === plan) &&
    (region === null || regionOf(customer) === region) &&
    (!words || [customer.company, customer.customer_id, customer.industry]
      .some((value) => value?.toLowerCase().includes(words))));
  const rows = filtered.slice(0, shown);
  const left = filtered.length - rows.length;

  function search(value: string) {
    setQuery(value);
    setShown(PAGE_SIZE);
  }
  function pickPlan(value: string | null) {
    setPlan(value);
    setShown(PAGE_SIZE);
  }
  function pickRegion(value: string | null) {
    setRegion(value);
    setShown(PAGE_SIZE);
  }
  function clearFilters() {
    setQuery("");
    setPlan(null);
    setRegion(null);
    setShown(PAGE_SIZE);
  }

  return (
    <>
      <TopBar>
        {/* onSubmit stops Enter from reloading the page and losing the filters. */}
        <SearchField label="Search customers" placeholder="Search company, customer ID or industry"
          value={query} onChange={search} onSubmit={search} />
      </TopBar>
      <main className="page clist-page">
        <PageHead title="Customers" description={description} />
        <Summary total={total} items={items} plans={plans} regions={regions} />

        <section className="card clist-card" aria-label="Customer list">
          <div className="clist-filters">
            <FilterChips label="Plan" allLabel="All plans" options={plans} value={plan} onPick={pickPlan} />
            <span className="clist-divider" aria-hidden="true" />
            <FilterChips label="Region" allLabel="All regions" options={regions} value={region} onPick={pickRegion} />
            <span className="clist-caption" aria-live="polite">
              {rows.length} of {filtered.length} · {SORT_LABEL}
            </span>
          </div>

          {rows.length > 0 ? (
            <ul className="clist-rows">
              {rows.map((customer) => <CustomerRow key={customer.customer_id} customer={customer} />)}
            </ul>
          ) : items.length > 0 ? (
            <div className="empty">
              <p className="empty-title">No customers match</p>
              <button type="button" className="button" onClick={clearFilters}>Clear filters</button>
            </div>
          ) : (
            <div className="empty"><p className="empty-title">No customers recorded</p></div>
          )}

          {left > 0 && (
            <div className="clist-more">
              <button type="button" className="button" onClick={() => setShown(shown + PAGE_SIZE)}>
                Show {Math.min(PAGE_SIZE, left)} more
              </button>
            </div>
          )}
        </section>
      </main>
    </>
  );
}

function Summary({ total, items, plans, regions }: {
  total: number; items: CustomerListItem[]; plans: Count[]; regions: Count[];
}) {
  const seats = items.reduce((sum, customer) => sum + (customer.seats ?? 0), 0);
  const active = items.reduce((sum, customer) => sum + customer.active_cases, 0);
  const allCases = items.reduce((sum, customer) => sum + customer.all_cases, 0);
  const withActive = items.filter((customer) => customer.active_cases > 0).length;
  const largestRegion = Math.max(1, ...regions.map((region) => region.count));

  return (
    <section className="clist-summary" aria-label="Customer summary">
      <div className="clist-cell">
        <span className="clist-cell-label">Customers</span>
        <span className="clist-figure">{total}</span>
        <span className="clist-note">{plural(seats, "seat")} in all</span>
      </div>
      <div className="clist-cell is-chart">
        <span className="clist-cell-label">By plan</span>
        <div className="clist-planbar" role="img"
          aria-label={plans.map((plan) => `${plan.label} ${plan.count}`).join(", ")}>
          {plans.map((plan) => (
            <span key={plan.label} className={`clist-mark ${toneClass(plan.label)}`} style={{ flexGrow: plan.count }} />
          ))}
        </div>
        <ul className="clist-legend">
          {plans.map((plan) => (
            <li key={plan.label}>
              <span className={`clist-mark ${toneClass(plan.label)}`} aria-hidden="true" />
              {plan.label} <strong>{plan.count}</strong>
            </li>
          ))}
        </ul>
      </div>
      <div className="clist-cell">
        <span className="clist-cell-label">By region</span>
        <ul className="clist-regions">
          {regions.map((region) => (
            <li key={region.label} className="clist-region">
              <span className="clist-region-name">{region.label}</span>
              <span className="bar-track" aria-hidden="true">
                <span className="bar-fill" style={{ width: `${(region.count / largestRegion) * 100}%` }} />
              </span>
              <strong>{region.count}</strong>
            </li>
          ))}
        </ul>
      </div>
      <div className="clist-cell">
        <span className="clist-cell-label">Active cases</span>
        <span className="clist-figure">{active}</span>
        <span className="clist-note">across {plural(withActive, "customer")} · {plural(allCases, "case")} in all</span>
      </div>
    </section>
  );
}

function FilterChips({ label, allLabel, options, value, onPick }: {
  label: string; allLabel: string; options: Count[]; value: string | null; onPick: (value: string | null) => void;
}) {
  return (
    <div className="chips" role="group" aria-label={label}>
      <button type="button" className="chip" aria-pressed={value === null} onClick={() => onPick(null)}>{allLabel}</button>
      {options.map((option) => (
        <button key={option.label} type="button" className="chip" aria-pressed={value === option.label}
          onClick={() => onPick(option.label)}>
          {option.label}
        </button>
      ))}
    </div>
  );
}

function CustomerRow({ customer }: { customer: CustomerListItem }) {
  const { customer_id: id, company, seats, active_cases: active, all_cases: all } = customer;
  const plan = planOf(customer);
  return (
    <li className="row clist-row">
      <span className="clist-avatar" aria-hidden="true">{initial(company ?? id)}</span>
      <span className="row-text">
        <Link className="row-title clist-link" href={`/customers/${encodeURIComponent(id)}`}>{company ?? id}</Link>
        <span className="row-sub">{id} · {orNotRecorded(customer.industry)}</span>
      </span>
      <span className="clist-meta">
        <span className={`pill clist-plan ${toneClass(plan)}`}>{plan}</span>
        <span className="clist-meta-text clist-seats">
          {seats === null ? NOT_RECORDED : <><strong>{seats}</strong> {seats === 1 ? "seat" : "seats"}</>}
        </span>
        <span className="clist-meta-text clist-region-text">{regionOf(customer)}</span>
        <span className={`pill clist-active ${active > 0 ? "tone-pending" : "tone-resolved"}`}>{active} active</span>
        <span className="clist-meta-text clist-cases">{plural(all, "case")}</span>
      </span>
    </li>
  );
}
