import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { LEGAL, LEGAL_DOCS, REGIONS, SUBPROCESSORS, loadRegion, regionById, saveRegion, type RegionId } from '../../lib/legal'
import { SectionHead } from './sections'
import { usePageMeta } from '../../lib/seo'

type Section = { id: string; heading: string; body: ReactNode }

const Contact = () => <Link to={LEGAL.contactPath}>contact form</Link>


function LegalDoc({ title, summary, sections, children }: { title: string; summary: string; sections: Section[]; children?: ReactNode }) {
  usePageMeta(title, summary)
  return (
    <section className="section legal">
      <SectionHead eyebrow="Legal" title={title} />
      <p className="muted small legal-meta">
        Effective {LEGAL.effectiveDate} · Version {LEGAL.version} · <Link to="/legal">All legal documents</Link>
      </p>
      <div className="legal-layout">
        <nav className="legal-toc" aria-label="On this page">
          <div className="legal-toc-title">On this page</div>
          {sections.map((s, i) => (
            <a key={s.id} href={`#${s.id}`}>
              {i + 1}. {s.heading}
            </a>
          ))}
        </nav>
        <div className="prose legal-body">
          <p className="legal-summary">{summary}</p>
          {children}
          {sections.map((s, i) => (
            <section key={s.id} id={s.id} className="legal-section">
              <h2>
                {i + 1}. {s.heading}
              </h2>
              {s.body}
            </section>
          ))}
        </div>
      </div>
    </section>
  )
}

function useRegion(): [RegionId, (id: RegionId) => void] {
  const [region, setRegion] = useState<RegionId>(() => loadRegion())
  return [
    region,
    (id) => {
      setRegion(id)
      saveRegion(id)
    },
  ]
}

function RegionPicker({ value, onChange }: { value: RegionId; onChange: (id: RegionId) => void }) {
  return (
    <div className="legal-region">
      <label htmlFor="legal-region">Showing rights for</label>
      <select id="legal-region" value={value} onChange={(e) => onChange(e.target.value as RegionId)}>
        {REGIONS.map((r) => (
          <option key={r.id} value={r.id}>
            {r.label}
          </option>
        ))}
      </select>
      <span className="muted small">Picked from your browser’s time zone and language. Change it if it’s wrong.</span>
    </div>
  )
}

const ul = (items: ReactNode[]) => (
  <ul>
    {items.map((x, i) => (
      <li key={i}>{x}</li>
    ))}
  </ul>
)

// ---- Hub -------------------------------------------------------------------

export function LegalHubPage() {
  usePageMeta('Legal', 'ARC legal and trust documents: terms, privacy, DPA, AI use, acceptable use, cookies and sub-processors.')
  return (
    <section className="section">
      <SectionHead
        eyebrow="Legal"
        title="Legal and trust documents."
        lede="Plain-language policies for everyone who uses ARC. Where the law differs by country, the Privacy Policy and Terms show the rules for your region."
      />
      <div className="cap-grid">
        {LEGAL_DOCS.map((d) => (
          <Link key={d.to} to={d.to} className="cap" style={{ color: 'inherit', textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>{d.title}</h3>
            <p>{d.blurb}</p>
          </Link>
        ))}
        <Link to="/security" className="cap" style={{ color: 'inherit', textDecoration: 'none' }}>
          <h3 style={{ marginTop: 0 }}>Security</h3>
          <p>The controls that protect your workspace today, and how to report a vulnerability.</p>
        </Link>
      </div>
      <p className="muted small" style={{ marginTop: 20 }}>
        Questions about any of these documents? Use the <Contact /> and choose the “Security” or “Other” topic.
      </p>
    </section>
  )
}

// ---- Terms -----------------------------------------------------------------

export function TermsPage() {
  const [regionId, setRegionId] = useRegion()
  const region = regionById(regionId)
  const sections: Section[] = [
    {
      id: 'agreement',
      heading: 'The agreement',
      body: (
        <>
          <p>
            These Terms of Service (“Terms”) are an agreement between you and {LEGAL.company} (“ARC”, “we”, “us”) for
            your use of the ARC website, web application, API and related services (the “Service”). If you use the
            Service for an organisation, you accept these Terms on its behalf and confirm you have authority to do so;
            “you” then means that organisation.
          </p>
          <p>
            The legal entity that provides the Service to you is the one named on your order form or invoice. These
            Terms incorporate our <Link to="/privacy">Privacy Policy</Link>, <Link to="/acceptable-use">Acceptable Use Policy</Link>,{' '}
            <Link to="/ai-policy">AI Use Policy</Link> and <Link to="/refunds">Refunds and Cancellation</Link> policy, and, where you need one,
            our <Link to="/dpa">Data Processing Agreement</Link>.
          </p>
        </>
      ),
    },
    {
      id: 'accounts',
      heading: 'Eligibility and accounts',
      body: ul([
        'You must be at least 18 and able to form a binding contract. The Service is designed for businesses and professionals.',
        'Give accurate account details and keep them up to date.',
        'Keep your password secure. You are responsible for activity under your account and for the people you invite to your workspace and the roles you give them.',
        'Tell us promptly through the contact form if you believe your account has been compromised.',
      ]),
    },
    {
      id: 'service',
      heading: 'What the Service does',
      body: (
        <>
          <p>
            ARC coordinates specialist AI agents that research, plan and draft marketing work for your review. Work moves
            through an approval system: an approval is tied to an exact version of a deliverable, and any change creates a
            new version that needs a new approval.
          </p>
          <p>
            <strong>ARC never publishes, sends, posts or spends on your behalf without an explicit approval from an
            authorised member of your workspace.</strong> Where you connect an outside service (for example Zapier or Make
            through a webhook), ARC sends only content that has been approved, and only to the destinations you
            configured. You are responsible for what you approve and publish.
          </p>
          <p>
            Features marked “planned”, “beta” or “not connected” may change or be withdrawn and are provided without any
            commitment that they will become generally available.
          </p>
        </>
      ),
    },
    {
      id: 'content',
      heading: 'Your content and data',
      body: (
        <>
          <p>
            “Your Content” means everything you or your team put into the Service (business profile, briefs, knowledge,
            files) and everything the agents produce for you (“Output”). As between you and us, <strong>you own Your
            Content, including Output</strong>.
          </p>
          <p>
            You give us a limited licence to host, copy, process and transmit Your Content only as needed to provide,
            secure and support the Service, including sending it to the AI providers listed on our{' '}
            <Link to="/subprocessors">sub-processor page</Link>. <strong>We do not use Your Content to train AI
            models</strong>, and we do not sell it.
          </p>
          <p>
            You confirm you have the rights to the material you upload and that using it with the Service will not
            infringe anyone else’s rights or break the law.
          </p>
        </>
      ),
    },
    {
      id: 'ai-output',
      heading: 'AI output',
      body: ul([
        'Output is generated by AI and can be inaccurate, incomplete, out of date, or similar to content produced for others. Review it before you use it.',
        'Output is not legal, financial, medical or other professional advice.',
        'You are responsible for making sure the content you publish complies with advertising, consumer protection and privacy law, with platform policies, and with any disclosure rules for AI-generated content that apply to you.',
        'Outcomes depend on your business, data, channels and budget. We do not promise any particular result.',
      ]),
    },
    {
      id: 'use',
      heading: 'Acceptable use',
      body: (
        <p>
          You must follow our <Link to="/acceptable-use">Acceptable Use Policy</Link>. We may remove content or suspend
          access that breaks it, and will tell you why unless the law or a security concern prevents it.
        </p>
      ),
    },
    {
      id: 'third-party',
      heading: 'Third-party services',
      body: (
        <p>
          The Service can work with services we do not control, such as automation tools, social networks, ad platforms
          and analytics. Your use of them is governed by their own terms. We are not responsible for them, for changes
          to their APIs, or for their decisions about your content or accounts. Names of third parties describe
          compatibility, not a partnership or endorsement.
        </p>
      ),
    },
    {
      id: 'billing',
      heading: 'Plans, trials and billing',
      body: ul([
        'Paid plans are billed in advance for each billing period (monthly, or yearly where offered) and renew automatically until cancelled.',
        'Prices are shown before you buy and exclude taxes unless stated. You are responsible for applicable taxes.',
        `We will give at least ${LEGAL.noticeDays} days’ notice of a price increase, which applies from your next billing period. You can cancel before it takes effect.`,
        'If a trial is offered, it ends on the date shown in your workspace. You will not be charged unless you choose a paid plan.',
        'Plan limits (for example runs, seats and AI budget) are enforced by the Service and shown on your Usage page.',
        'If a payment fails we may retry it, move you to a lower plan or suspend paid features until it is resolved.',
        <>Refunds are covered in our <Link to="/refunds">Refunds and Cancellation</Link> policy.</>,
      ]),
    },
    {
      id: 'termination',
      heading: 'Cancellation, suspension and termination',
      body: (
        <>
          <p>
            You can cancel at any time from your workspace’s Billing page. Cancellation takes effect at the end of the
            current billing period, and you keep access until then.
          </p>
          <p>
            We may suspend or end your access if you materially breach these Terms, fail to pay, create a security or
            legal risk, or if we are required to by law. Where reasonable we will warn you first and give you a chance to
            fix the problem.
          </p>
          <p>
            Workspace owners can export all workspace data at any time and can schedule deletion. Deleted workspaces are
            permanently purged after a {LEGAL.deletionGraceDays}-day grace period, except where we must keep records
            by law.
          </p>
        </>
      ),
    },
    {
      id: 'confidentiality',
      heading: 'Confidentiality and security',
      body: (
        <p>
          We treat Your Content as confidential and protect it with the measures described on our{' '}
          <Link to="/security">Security page</Link> and in our <Link to="/dpa">DPA</Link>. We will notify affected customers
          without undue delay if we become aware of a security breach affecting their data.
        </p>
      ),
    },
    {
      id: 'ip',
      heading: 'Our intellectual property',
      body: (
        <p>
          The Service, including its software, agent designs, interface and documentation, belongs to us and our
          licensors. We give you a non-exclusive, non-transferable right to use it during your subscription under these
          Terms. If you send us feedback, we may use it without obligation to you.
        </p>
      ),
    },
    {
      id: 'warranties',
      heading: 'Warranties and disclaimers',
      body: (
        <p>
          We will provide the Service with reasonable skill and care. Apart from that, and to the extent the law allows,
          the Service is provided “as is” and “as available”, and we disclaim implied warranties such as merchantability,
          fitness for a particular purpose and non-infringement. We do not guarantee that the Service will be
          uninterrupted or error-free.
        </p>
      ),
    },
    {
      id: 'liability',
      heading: 'Limitation of liability',
      body: (
        <>
          <p>
            To the extent the law allows: (a) neither party is liable for indirect, incidental, special or consequential
            loss, or for lost profits, revenue, goodwill or data; and (b) each party’s total liability arising out of these
            Terms in any 12-month period is limited to the fees you paid for the Service in that period.
          </p>
          <p>
            Nothing in these Terms limits liability for death or personal injury caused by negligence, for fraud, or for
            anything else that cannot be limited by law.
          </p>
        </>
      ),
    },
    {
      id: 'indemnity',
      heading: 'Indemnity (business customers)',
      body: (
        <p>
          If you use the Service for business, you will defend and compensate us against third-party claims arising from
          content you publish, your breach of the Acceptable Use Policy, or your violation of law.
        </p>
      ),
    },
    {
      id: 'changes',
      heading: 'Changes to these Terms',
      body: (
        <p>
          We may update these Terms. For material changes we will give at least {LEGAL.noticeDays} days’ notice in the
          app or by email before they apply. If you do not agree, you can cancel before the change takes effect. The
          version you accepted is recorded with your account.
        </p>
      ),
    },
    {
      id: 'law',
      heading: 'Governing law and disputes',
      body: (
        <>
          <p>
            Please contact us first so we can try to resolve any dispute informally; we will respond within 30 days.
            If it is not resolved, these Terms are governed by the laws of the country in which the ARC entity named on
            your order form or invoice is established, and disputes go to its courts.
          </p>
          <p>
            <strong>This never takes away protections that the law of your own country gives you and that cannot be
            waived by contract.</strong> The rules for your region are below.
          </p>
          <RegionPicker value={regionId} onChange={setRegionId} />
          <div className="legal-region-card">
            <h3>{region.label}</h3>
            <p>{region.consumer}</p>
          </div>
        </>
      ),
    },
    {
      id: 'general',
      heading: 'General',
      body: ul([
        'Neither party is responsible for delays caused by events beyond its reasonable control.',
        'You may not transfer these Terms without our consent. We may transfer them as part of a merger, acquisition or sale of assets, with notice to you.',
        'If part of these Terms is unenforceable, the rest still applies. Not enforcing a right is not a waiver of it.',
        'These Terms, with the policies they incorporate and any signed order form, are the whole agreement between us about the Service. A signed order form wins if it conflicts with these Terms.',
      ]),
    },
    {
      id: 'contact',
      heading: 'Contact',
      body: (
        <p>
          Questions about these Terms? Use the <Contact />.
        </p>
      ),
    },
  ]
  return (
    <LegalDoc
      title="Terms of Service"
      summary="In short: you own your content and everything the agents produce for you. We never train AI on it. Nothing leaves ARC without your team’s approval. You can cancel any time and export your data. Local consumer protections always apply."
      sections={sections}
    />
  )
}

// ---- Privacy ---------------------------------------------------------------

export function PrivacyPage() {
  const [regionId, setRegionId] = useRegion()
  const region = regionById(regionId)
  const sections: Section[] = [
    {
      id: 'who',
      heading: 'Who we are and our role',
      body: (
        <>
          <p>
            This policy explains how {LEGAL.company} (“ARC”, “we”) handles personal data when you visit our website or
            use the ARC Service.
          </p>
          {ul([
            <><strong>Controller:</strong> we decide how account, billing, website and support data is used.</>,
            <><strong>Processor:</strong> for the content your organisation puts into its workspace (business profile, briefs, knowledge, files and agent output), we act on your organisation’s instructions under our <Link to="/dpa">DPA</Link>. Your organisation is the controller of that data.</>,
          ])}
        </>
      ),
    },
    {
      id: 'collect',
      heading: 'What we collect',
      body: ul([
        <><strong>Account data:</strong> name, email address, password (stored only as a secure hash), role and workspace memberships, and the version of these terms you accepted.</>,
        <><strong>Workspace content:</strong> what you and your team enter or upload, and the drafts, plans and reports the agents produce.</>,
        <><strong>Operational records:</strong> tasks, approvals, audit events, usage and cost records, so the Service can run and you can see who did what.</>,
        <><strong>Technical data:</strong> IP address, browser type and request logs, used for security, rate limiting and troubleshooting.</>,
        <><strong>Billing data:</strong> plan, invoices and billing contact. Card details are collected and held by our payment provider, never by ARC.</>,
        <><strong>Messages:</strong> what you send through the contact form or support.</>,
      ]),
    },
    {
      id: 'use',
      heading: 'How we use it',
      body: ul([
        'To provide the Service: run your workspace and agents, enforce approvals and plan limits, and keep records you can export.',
        'To secure it: authentication, rate limiting, fraud and abuse prevention, and investigating incidents.',
        'To communicate: service messages, security notices, invitations and replies to your questions.',
        'To bill you, where you are on a paid plan.',
        'To improve the Service using aggregated, non-identifying usage information.',
        'To meet legal obligations.',
      ]),
    },
    {
      id: 'ai',
      heading: 'AI processing',
      body: (
        <>
          <p>
            When an agent runs, the relevant parts of your workspace content (for example the campaign brief, business
            profile and approved knowledge) are sent to an AI model provider listed on our{' '}
            <Link to="/subprocessors">sub-processor page</Link> to generate the draft.
          </p>
          <p>
            <strong>We do not use your content to train AI models.</strong> We use AI providers under API terms that,
            according to their published policies, do not permit them to train their models on the data we send. See our{' '}
            <Link to="/ai-policy">AI Use Policy</Link> for details.
          </p>
        </>
      ),
    },
    {
      id: 'sharing',
      heading: 'Who we share it with',
      body: ul([
        <>Service providers that host and run ARC, listed with their purpose and location on our <Link to="/subprocessors">sub-processor page</Link>. They may only use the data to provide their service to us.</>,
        'Outside services you connect yourself (for example a Zapier or Make webhook), only for content you approve to send there.',
        'Authorities, when the law requires it. We push back on requests that are overly broad.',
        'A buyer or successor, if ARC is involved in a merger or acquisition, under the same protections.',
        <><strong>We do not sell personal data</strong> and do not share it for cross-context behavioural advertising.</>,
      ]),
    },
    {
      id: 'transfers',
      heading: 'International transfers',
      body: (
        <p>
          ARC’s providers process data mainly in the United States. {region.transfers}
        </p>
      ),
    },
    {
      id: 'retention',
      heading: 'How long we keep it',
      body: ul([
        'Account and workspace data: for as long as your account or workspace is active.',
        `Deleted workspaces: permanently purged after a ${LEGAL.deletionGraceDays}-day grace period, so an accidental deletion can be undone.`,
        'Audit records: kept with the workspace so you have a complete history, and removed with it.',
        'Billing records: kept for as long as tax and accounting law requires.',
        'Security logs: kept for a limited period, then deleted.',
      ]),
    },
    {
      id: 'security',
      heading: 'Security',
      body: (
        <p>
          Data is encrypted in transit, workspaces are isolated on the server, access follows least privilege, and every
          consequential action is recorded. Read more on our <Link to="/security">Security page</Link>.
        </p>
      ),
    },
    {
      id: 'rights',
      heading: 'Your rights',
      body: (
        <>
          <p>
            Wherever you are, you can ask us to access, correct, delete or export your personal data, and opt out of
            marketing emails. Workspace admins can export and delete workspace data directly in the app. For anything
            else, use the <Contact />. We reply within 30 days, or sooner if your local law requires, and may need to
            verify your identity first. If your data sits in another organisation’s workspace, we will pass your request
            to them, as they control it.
          </p>
          <RegionPicker value={regionId} onChange={setRegionId} />
          <div className="legal-region-card">
            <h3>{region.label}</h3>
            <p>
              We process your data in line with {region.law}. You have the right to:
            </p>
            {ul(region.rights)}
            <p>{region.complaint}</p>
            {region.id === 'eu' || region.id === 'uk' ? (
              <p className="small">
                Legal bases we rely on: performance of our contract with you (to provide the Service), legitimate
                interests (security, preventing abuse and improving the Service), consent (where we ask for it) and
                legal obligation.
              </p>
            ) : null}
          </div>
        </>
      ),
    },
    {
      id: 'children',
      heading: 'Children',
      body: <p>ARC is a business service and is not directed at children. We do not knowingly collect data from anyone under 16.</p>,
    },
    {
      id: 'cookies',
      heading: 'Cookies',
      body: (
        <p>
          We use one strictly necessary cookie to keep you signed in and protect forms. We do not use advertising or
          analytics cookies. See our <Link to="/cookies">Cookie Policy</Link>.
        </p>
      ),
    },
    {
      id: 'changes',
      heading: 'Changes to this policy',
      body: (
        <p>
          We will post any update here with a new effective date, and tell you in the app or by email before a material
          change takes effect.
        </p>
      ),
    },
    {
      id: 'contact',
      heading: 'Contact',
      body: (
        <p>
          For privacy questions or requests, use the <Contact /> and choose the topic “Security”.
        </p>
      ),
    },
  ]
  return (
    <LegalDoc
      title="Privacy Policy"
      summary="In short: we collect what we need to run your workspace, never sell it, never use it to train AI, and you can export or delete it at any time. Your local privacy rights are shown below."
      sections={sections}
    />
  )
}

// ---- Cookies ---------------------------------------------------------------

export function CookiesPage() {
  const sections: Section[] = [
    {
      id: 'cookies',
      heading: 'Cookies we use',
      body: (
        <div className="table-wrap">
          <table className="responsive">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Purpose</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td data-label="Name">
                  <code>session</code>
                </td>
                <td data-label="Type">Strictly necessary</td>
                <td data-label="Purpose">Keeps you signed in and holds the security token that protects forms against cross-site request forgery.</td>
                <td data-label="Duration">Until you sign out or close the browser</td>
              </tr>
            </tbody>
          </table>
        </div>
      ),
    },
    {
      id: 'storage',
      heading: 'Preferences stored in your browser',
      body: ul([
        <><code>activeOrganizationId</code> — remembers which workspace you last opened.</>,
        <><code>arc-legal-region</code> — remembers the region you chose on our legal pages.</>,
        'These stay on your device, are never sent to advertisers, and you can clear them in your browser settings at any time.',
      ]),
    },
    {
      id: 'none',
      heading: 'What we don’t use',
      body: (
        <p>
          ARC does not use advertising, tracking, social media or analytics cookies, so there is nothing to opt into or
          out of. If we ever add optional cookies, we will ask for your consent first where the law requires it, and
          update this page.
        </p>
      ),
    },
    {
      id: 'control',
      heading: 'Your choices',
      body: (
        <p>
          You can block or delete cookies in your browser settings. If you block the <code>session</code> cookie you
          won’t be able to sign in, because it is needed for the Service to work.
        </p>
      ),
    },
  ]
  return <LegalDoc title="Cookie Policy" summary="ARC uses a single strictly necessary cookie. No advertising, analytics or tracking cookies." sections={sections} />
}

// ---- Sub-processors --------------------------------------------------------

export function SubprocessorsPage() {
  const sections: Section[] = [
    {
      id: 'list',
      heading: 'Current sub-processors',
      body: (
        <>
          <div className="table-wrap">
            <table className="responsive">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Purpose</th>
                  <th>Data</th>
                  <th>Location</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {SUBPROCESSORS.map((s) => (
                  <tr key={s.name}>
                    <td data-label="Provider">
                      <a href={s.link} target="_blank" rel="noreferrer">
                        {s.name}
                      </a>
                    </td>
                    <td data-label="Purpose">{s.purpose}</td>
                    <td data-label="Data">{s.data}</td>
                    <td data-label="Location">{s.location}</td>
                    <td data-label="Status">
                      <span className={`int-status ${s.status === 'active' ? 'available_tested' : 'planned'}`}>
                        {s.status === 'active' ? 'In use' : 'When enabled'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small">
            “When enabled” providers only receive data once that feature is switched on for the Service. Outside services
            you connect yourself (for example Zapier or Make) are your own choice and are not our sub-processors.
          </p>
        </>
      ),
    },
    {
      id: 'changes',
      heading: 'Changes',
      body: (
        <p>
          We will update this page at least {LEGAL.noticeDays} days before a new sub-processor starts processing customer
          data. Customers with a DPA can object to a new sub-processor on reasonable data protection grounds during that
          period.
        </p>
      ),
    },
  ]
  return (
    <LegalDoc
      title="Sub-processors"
      summary="These are the companies that process data for ARC, what they do, and where. Each is bound by contract to protect it."
      sections={sections}
    />
  )
}

// ---- DPA -------------------------------------------------------------------

export function DpaPage() {
  const sections: Section[] = [
    {
      id: 'scope',
      heading: 'Scope and roles',
      body: (
        <p>
          This Data Processing Agreement (“DPA”) forms part of the <Link to="/terms">Terms</Link> between ARC and the
          customer whenever ARC processes personal data contained in the customer’s workspace (“Customer Personal
          Data”). The customer is the controller; ARC is the processor. Where the customer is itself a processor, ARC is
          its sub-processor.
        </p>
      ),
    },
    {
      id: 'details',
      heading: 'Details of processing',
      body: ul([
        <><strong>Subject matter and purpose:</strong> providing the Service — running AI agents that research, plan and draft marketing work, managing approvals and exports.</>,
        <><strong>Duration:</strong> the term of the subscription, plus the deletion grace period.</>,
        <><strong>Data subjects:</strong> the customer’s users, and people mentioned in content the customer uploads (for example customers, prospects or contacts).</>,
        <><strong>Categories of data:</strong> names, contact details, business information and any personal data the customer chooses to include. The customer should not upload special-category, health, payment card or children’s data.</>,
      ]),
    },
    {
      id: 'obligations',
      heading: 'ARC’s obligations',
      body: ul([
        'Process Customer Personal Data only on the customer’s documented instructions, including these Terms and the customer’s use of the Service.',
        'Make sure everyone who can access the data is bound by confidentiality.',
        'Apply the technical and organisational measures described below.',
        'Help the customer respond to data subject requests, mainly through in-app export and deletion.',
        'Help the customer with security, breach notification and data protection impact assessments, taking into account the information available to ARC.',
        'Not use Customer Personal Data to train AI models, and not sell it.',
      ]),
    },
    {
      id: 'subprocessors',
      heading: 'Sub-processors',
      body: (
        <p>
          The customer authorises the sub-processors on our <Link to="/subprocessors">sub-processor page</Link>. ARC
          imposes data protection terms on each that are no less protective than this DPA, remains responsible for them,
          and gives {LEGAL.noticeDays} days’ notice of new ones. The customer may object on reasonable grounds; if we
          cannot address the objection, the customer may terminate the affected service and receive a refund of prepaid
          fees for the remaining period.
        </p>
      ),
    },
    {
      id: 'security',
      heading: 'Security measures',
      body: ul([
        'Encryption of data in transit (TLS) and encryption at rest provided by our database and storage providers.',
        'Server-side tenant isolation on every request, tested for every workspace-scoped endpoint.',
        'Role-based access with least privilege; only approvers can approve, only owners manage billing and deletion.',
        'Hashed passwords, rate-limited authentication, HttpOnly session cookies and CSRF protection; password reset revokes other sessions.',
        'Agents can only produce schema-validated drafts — no code execution, database access or arbitrary web requests.',
        'Approvals bound to an exact version and payload hash, re-checked immediately before any export or outbound action.',
        'Append-only audit log of consequential actions; signed webhooks with replay protection.',
        'Provider keys and secrets kept on the server only.',
      ]),
    },
    {
      id: 'breach',
      heading: 'Personal data breaches',
      body: (
        <p>
          ARC will notify the customer without undue delay after becoming aware of a personal data breach affecting
          Customer Personal Data, with the information the customer reasonably needs to meet its own obligations, and
          will take reasonable steps to contain it.
        </p>
      ),
    },
    {
      id: 'transfers',
      heading: 'International transfers',
      body: (
        <p>
          Customer Personal Data is processed mainly in the United States. Where the law of the customer’s country
          requires a transfer mechanism, the parties agree that the applicable one applies — for example the EU Standard
          Contractual Clauses (module two or three), the UK Addendum or IDTA, or the Swiss amendments — and that it is
          incorporated by reference.
        </p>
      ),
    },
    {
      id: 'deletion',
      heading: 'Return and deletion',
      body: (
        <p>
          The customer can export all workspace data at any time. When a workspace is deleted, ARC purges Customer
          Personal Data after the {LEGAL.deletionGraceDays}-day grace period, unless the law requires it to be kept.
        </p>
      ),
    },
    {
      id: 'audits',
      heading: 'Information and audits',
      body: (
        <p>
          ARC will make available the information reasonably necessary to demonstrate compliance with this DPA, including
          answers to security questionnaires. Where the law requires, ARC will allow audits by the customer or an
          independent auditor, with reasonable notice, no more than once a year, and subject to confidentiality.
        </p>
      ),
    },
    {
      id: 'sign',
      heading: 'Signed copies',
      body: (
        <p>
          This DPA applies automatically. If your organisation needs a countersigned copy, use the <Contact /> with the
          topic “Security”.
        </p>
      ),
    },
  ]
  return (
    <LegalDoc
      title="Data Processing Agreement"
      summary="For customers who put personal data into ARC: we process it only on your instructions, protect it, never train AI on it, and delete it when you ask."
      sections={sections}
    />
  )
}

// ---- Acceptable use --------------------------------------------------------

export function AcceptableUsePage() {
  const sections: Section[] = [
    {
      id: 'content',
      heading: 'Content you must not create or publish with ARC',
      body: ul([
        'Anything illegal, or that promotes illegal activity.',
        'False, misleading or deceptive advertising, including fake reviews, testimonials or endorsements, and undisclosed paid promotion.',
        'Content that impersonates a person or organisation, or implies an endorsement that does not exist.',
        'Hate speech, harassment, threats, or content that discriminates unlawfully — including discriminatory targeting of housing, employment or credit ads.',
        'Sexual content involving minors, or any content that exploits children.',
        'Misleading health, financial or legal claims, and political or election content designed to deceive voters.',
        'Content that infringes copyright, trademarks or other intellectual property.',
      ]),
    },
    {
      id: 'conduct',
      heading: 'Conduct',
      body: ul([
        'Sending spam or messages to people who have not agreed to receive them, or breaking anti-spam laws.',
        'Uploading personal data you have no right to use, or special-category, health or payment card data.',
        'Trying to get around approvals, plan limits, rate limits, the kill switch or other safeguards.',
        'Trying to make the agents ignore their instructions or reveal other customers’ data (prompt injection).',
        'Probing, scanning or testing the Service’s security without our written permission, or uploading malware.',
        'Reselling or giving access to the Service outside your organisation without an agreement with us.',
        'Using the Service to build a competing product, or scraping it.',
      ]),
    },
    {
      id: 'platforms',
      heading: 'Platform rules',
      body: (
        <p>
          When you publish to social networks, ad platforms, email tools or websites, you must also follow their policies,
          including any rules for labelling AI-generated content.
        </p>
      ),
    },
    {
      id: 'enforcement',
      heading: 'What happens if this policy is broken',
      body: (
        <p>
          We may remove content, pause agents, or suspend or close an account, depending on how serious the issue is.
          Where we can, we will tell you and give you a chance to fix it. To report abuse, use the <Contact />.
        </p>
      ),
    },
  ]
  return <LegalDoc title="Acceptable Use Policy" summary="Use ARC to market your business honestly and lawfully. These are the things it must never be used for." sections={sections} />
}

// ---- AI policy -------------------------------------------------------------

export function AiPolicyPage() {
  const sections: Section[] = [
    {
      id: 'how',
      heading: 'How ARC uses AI',
      body: (
        <p>
          ARC runs twelve specialist agents — from the CMO to the Record Keeper — that each produce one kind of
          structured draft: a strategy, research notes, a plan, a content pack and so on. Every draft is checked against a
          schema and code-level quality checks before it is saved. Agents work in a fixed order and only see the outputs
          they depend on.
        </p>
      ),
    },
    {
      id: 'human',
      heading: 'People stay in control',
      body: ul([
        'Anything that leaves your workspace needs an explicit approval from an authorised person.',
        'An approval applies to one exact version. Any edit creates a new version and needs a new approval.',
        'Agents cannot change ad spend, make payments, sign contracts or reply publicly on sensitive issues — these are locked platform rules.',
        'Owners and admins can pause every agent or engage a kill switch at any time.',
      ]),
    },
    {
      id: 'limits',
      heading: 'What agents can never do',
      body: (
        <p>
          Agents have no tools beyond writing structured drafts. They cannot run code, query databases, browse the web,
          read other workspaces, or send messages. Your business profile and knowledge are passed to them as untrusted
          data, never as instructions.
        </p>
      ),
    },
    {
      id: 'training',
      heading: 'Your data and model training',
      body: (
        <p>
          <strong>ARC does not use your content to train AI models.</strong> We send only what an agent needs for its
          task to the model provider listed on our <Link to="/subprocessors">sub-processor page</Link>, under API terms
          that, according to the providers’ published policies, do not allow them to train on that data.
        </p>
      ),
    },
    {
      id: 'accuracy',
      heading: 'Accuracy and transparency',
      body: ul([
        'AI drafts can be wrong. ARC labels estimates, marks integrations that are not connected, and never invents performance numbers.',
        'Review every draft before approving it. You are responsible for what you publish.',
        'Where a platform or law requires AI-generated content to be disclosed, you are responsible for adding that disclosure.',
      ]),
    },
    {
      id: 'questions',
      heading: 'Questions',
      body: (
        <p>
          To ask about how ARC uses AI, use the <Contact />.
        </p>
      ),
    },
  ]
  return (
    <LegalDoc
      title="AI Use Policy"
      summary="AI drafts the work; people approve it. Agents have no tools beyond writing drafts, and your data is never used to train models."
      sections={sections}
    />
  )
}

// ---- Refunds ---------------------------------------------------------------

export function RefundsPage() {
  const sections: Section[] = [
    {
      id: 'trial',
      heading: 'Free trial',
      body: <p>If your workspace includes a free trial, you are not charged during it, and nothing is charged unless you choose a paid plan.</p>,
    },
    {
      id: 'cancel',
      heading: 'Cancelling',
      body: (
        <p>
          You can cancel at any time from your workspace’s Billing page. Your plan stays active until the end of the
          period you have paid for, and is not renewed after that. You can export your data before and after cancelling,
          until the workspace is deleted.
        </p>
      ),
    },
    {
      id: 'pause',
      heading: 'Pausing',
      body: (
        <p>
          If you need a break, you can pause automation in your workspace at any time; nothing runs while it is paused.
          Pausing your subscription itself, where offered, is shown on the Billing page.
        </p>
      ),
    },
    {
      id: 'refunds',
      heading: 'Refunds',
      body: ul([
        'Subscription fees are not refunded for partially used periods, except as described here or where the law requires.',
        'If you were charged in error — for example twice, or after you cancelled — we will refund the charge in full.',
        'If the Service was unavailable for a significant part of a billing period because of a problem on our side, contact us and we will credit or refund that period fairly.',
        'If you object to a new sub-processor under our DPA and we cannot resolve it, we refund prepaid fees for the remaining period.',
        'Statutory rights in your country, including any cooling-off period that applies to consumers, are not affected.',
      ]),
    },
    {
      id: 'how',
      heading: 'How to ask for a refund',
      body: (
        <p>
          Use the <Contact /> with the topic “Support”, including your workspace name and the charge date. We reply within
          5 business days. Approved refunds go back to the original payment method.
        </p>
      ),
    },
  ]
  return (
    <LegalDoc title="Refunds and Cancellation" summary="Cancel any time, keep access until the end of the period you paid for, and get a full refund for any charge made in error." sections={sections} />
  )
}
