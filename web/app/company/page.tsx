import type { Metadata } from "next";

import { ApiProblemPanel, PageHead, TicketSearchBar } from "@/components/desk";
import { type CompanySection, type StaffRequest, companyHandbook } from "@/lib/api";
import { NOT_RECORDED, initial, paragraphs } from "@/lib/format";
import "./company.css";

export const metadata: Metadata = { title: "Company handbook" };

const TITLE = "Company handbook";
const DESCRIPTION = "Operating context, support policies and current improvement requests.";

function Body({ text, className }: { text: string | null; className: string }) {
  const parts = paragraphs(text);
  return (
    <div className={className}>
      {parts.length > 0 ? parts.map((part, index) => <p key={index}>{part}</p>) : <p>{NOT_RECORDED}</p>}
    </div>
  );
}

function Section({ section, anchor }: { section: CompanySection; anchor: string }) {
  return (
    <section id={anchor} className="company-section" aria-labelledby={`${anchor}-heading`}>
      <h2 id={`${anchor}-heading`} className="company-heading">{section.title ?? NOT_RECORDED}</h2>
      <div className="company-byline">
        <span className="company-avatar" aria-hidden="true">{initial(section.owner)}</span>
        <span>
          <strong>{section.owner ?? NOT_RECORDED}</strong>
          {section.team && ` · ${section.team}`}
        </span>
      </div>
      <Body text={section.body} className="company-body" />
    </section>
  );
}

function Request({ request }: { request: StaffRequest }) {
  return (
    <div className="card company-request">
      <span className="pill company-request-id">{request.request_id}</span>
      <h3>{request.title ?? NOT_RECORDED}</h3>
      <Body text={request.body} className="company-request-body" />
      <div className="company-byline company-request-by">
        <span className="company-avatar" aria-hidden="true">{initial(request.requested_by)}</span>
        <span>Requested by <strong>{request.requested_by ?? NOT_RECORDED}</strong></span>
      </div>
    </div>
  );
}

export default async function CompanyPage() {
  const result = await companyHandbook();

  if (!result.ok) {
    return (
      <>
        <TicketSearchBar />
        <main className="page company-page">
          <PageHead title={TITLE} description={DESCRIPTION} />
          <ApiProblemPanel problem={result.problem} />
        </main>
      </>
    );
  }

  const { sections, staff_requests: requests } = result.data;
  const anchorOf = (index: number) => `section-${index + 1}`;

  return (
    <>
      <TicketSearchBar />
      <main className="page company-page">
        <PageHead title={TITLE} description={DESCRIPTION} />
        <div className="company-layout">
          <nav className="company-toc" aria-label="On this page">
            <span className="company-toc-label">On this page</span>
            {sections.map((section, index) => (
              <a key={section.document_id} href={`#${anchorOf(index)}`}>{section.title ?? NOT_RECORDED}</a>
            ))}
            <a className="company-toc-requests" href="#requests">Staff requests · {requests.length}</a>
          </nav>

          <div className="company-main">
            {sections.length === 0 ? (
              <div className="card empty"><p className="empty-title">No handbook sections recorded</p></div>
            ) : (
              <article className="card company-sections">
                {sections.map((section, index) => (
                  <Section key={section.document_id} section={section} anchor={anchorOf(index)} />
                ))}
              </article>
            )}

            <section id="requests" className="company-requests" aria-labelledby="requests-heading">
              <div>
                <h2 id="requests-heading" className="company-heading">Staff requests</h2>
                <p className="company-requests-desc">Current improvement requests from the team.</p>
              </div>
              {requests.length === 0 ? (
                <div className="card empty"><p className="empty-title">No staff requests recorded</p></div>
              ) : (
                <div className="company-request-grid">
                  {requests.map((request) => <Request key={request.request_id} request={request} />)}
                </div>
              )}
            </section>
          </div>
        </div>
      </main>
    </>
  );
}
