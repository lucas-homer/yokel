# Fresh civic-tech product ideas: deliberation, consensus, and action quality

Lens: products that convert raw public concern into trusted, non-duplicative, official-record input — not generic discussion rooms.

## 1. RecordReady Triage Desk

**One-line product:** A clerk-facing intake layer that converts messy resident emails, voicemails, form submissions, and petition links into source-linked, deduplicated public-record packets tied to the correct agenda item or docket.

### Target user
City/county clerks, planning-board staff, and agency public-comment coordinators who must process public input before a hearing, board vote, or comment close.

### Painful trigger / deadline
The 72 hours before a council, planning commission, school-board, or state-agency meeting when staff receive hundreds of duplicative emails, screenshots, and late attachments, then must decide what belongs in the official packet and what is spam, off-topic, or procedurally invalid.

### Data / protocols / repos to build on
- **Legistar OData API** for agenda items, bills, committees, actions, sponsors, attachments, and meeting dates.
- **OCD Event / Organization concepts** from Open Civic Data for canonical meeting/item IDs.
- **City Scrapers patterns** for non-Legistar agendas and vanished/cancelled meeting handling.
- **MAPLE-style event feed + archive** for receipts, follow-up, and public browsing.
- **Decidim-style verification tiers** conceptually: unverified input, verified resident, verified affected party.
- Email ingestion via IMAP/Gmail/Graph API; webform exports via CSV; optional SMS/voicemail transcription.

### Action loop
1. Staff connect an agenda source and an intake mailbox/form.
2. Product routes each incoming concern to the likely agenda item or flags “no official target found.”
3. It clusters duplicates, extracts claims, attachments, location references, and requested actions.
4. Residents receive a receipt: “your comment is attached to item 24-031, hearing June 17.”
5. Staff publish an official-record packet with provenance, duplicate counts, and representative distinct comments.
6. After the vote/action, residents receive the outcome and whether their issue was acknowledged, amended, continued, or not addressed.

### Why this does not duplicate existing tools
PublicInput/Granicus/EngagementHQ collect comments inside government-run project silos. MAPLE helps residents submit testimony for one legislature. This product starts from the government’s messy inbound reality and creates a trustworthy record-quality packet across agenda systems, especially where people already emailed or organized elsewhere.

### MVP
One Legistar city, one department or board, one shared intake mailbox, agenda-item matching, duplicate clustering, staff review queue, exportable PDF/CSV packet, and receipt emails. No resident social network, no citywide portal, no automated legal determination.

### Funding path
B2G subscription for clerks/agencies; pilot through municipal innovation funds or a civic-tech foundation; later sell as an add-on to agenda-management consultants and small jurisdictions not served well by Granicus engagement suites.

### Fatal risk
Government staff may not trust automated classification enough to let it touch the official record. If review time does not drop materially without increasing legal risk, it becomes another inbox rather than infrastructure.

---

## 2. Consensus Comment Composer

**One-line product:** A Pol.is-style consensus engine that turns a campaign’s raw opinions into a small number of distinct, evidence-backed official comments instead of thousands of discountable form letters.

### Target user
Civic nonprofits, neighborhood coalitions, professional associations, and issue campaigns preparing comments on a live federal/state docket or local hearing item.

### Painful trigger / deadline
A comment window closes in 10–21 days. The organizer has a petition list, meeting notes, and angry supporters, but agencies discount identical form letters and officials need substantive claims, data, alternatives, and affected-party examples.

### Data / protocols / repos to build on
- **Regulations.gov v4 API**, **Federal Register API**, and **Mirrulations S3 / mirrulations-search** for docket documents, deadlines, and historical comments.
- **Legistar OData** for local agenda items when the official target is a hearing/vote.
- **Pol.is consensus pattern**: cluster opinion, surface statements supported across factions.
- **MAPLE archive/notification pattern** for comment history and follow-up.
- Similarity detection over prior submitted comments to prevent template spam.

### Action loop
1. Organizer imports a docket/agenda link and supporter list.
2. Participants answer short prompts about lived impact, costs, alternatives, and factual corrections.
3. The product clusters participants into viewpoints and identifies consensus statements with broad support.
4. It generates 3–7 distinct comment packets: consensus core, minority concerns, technical appendix, and affected-party stories.
5. Each signer attests to facts they personally endorse; the system files or provides exact filing instructions and captures receipts.
6. Final rule/vote tracking maps agency responses back to the claims raised.

### Why this does not duplicate existing tools
Pol.is surfaces consensus but does not package official comments or track dockets. Resistbot/5 Calls optimize contact volume. Regulations.gov hosts raw submissions. This product optimizes action quality: fewer, more substantive, provenance-backed comments with visible consensus strength.

### MVP
Federal Regulations.gov dockets only; organizer creates one campaign; participants complete a 7-question evidence interview; output is a human-reviewed comment packet and CSV of attested claims. Manual filing support before server-side submission.

### Funding path
Per-campaign fee for nonprofits/associations; foundation grants for public-interest dockets; bundled module inside vertical products like ScopeWatch or Watershed Watch.

### Fatal risk
The tool could be perceived as AI-laundered astroturf. It must prove participants genuinely endorsed distinct claims and that generated text is grounded, not mass paraphrase.

---

## 3. Affected-Party Verifier

**One-line product:** A lightweight verification and standing layer that lets official bodies distinguish “directly affected resident/business/parcel” input from generic mass comments without excluding unverified speakers.

### Target user
Planning departments, zoning boards, environmental-review teams, neighborhood legal clinics, and resident organizers in processes where proximity, tenancy, business location, or district residency matters.

### Painful trigger / deadline
A variance, rezoning, permit appeal, or environmental review has a statutory notice radius and a hearing date. Officials receive broad opposition/support but cannot easily tell who is actually within the affected area, who is a renter, who owns nearby property, or who is simply part of a wider campaign.

### Data / protocols / repos to build on
- Parcel and address data from **ArcGIS**, **Socrata**, county open-data portals, or assessor exports where available.
- Planning-board agendas from **Legistar** or **City Scrapers-style spiders**.
- **MapIt-style geocoding / jurisdiction matching** for districts and boundaries.
- **Decidim verification-tier design**: scoped permissions without making all participation binding.
- Optional USPS address validation and privacy-preserving address hashing.

### Action loop
1. Organizer or agency creates a case boundary: parcel, notice radius, district, watershed, or custom polygon.
2. Participant verifies relationship: resident, renter, owner, nearby business, worker, parent, visitor, or general public.
3. Product collects comments with verification metadata separated from public text.
4. The official packet reports counts and distinct arguments by affected status, not just raw volume.
5. After hearing/vote, participants get an outcome receipt and any changed conditions.

### Why this does not duplicate existing tools
coUrbanize/PublicInput host project comments but do not provide a neutral, reusable affected-status layer for official packets. Decidim has verification concepts but assumes a government platform and resident census. This is a narrow trust primitive for land-use and local administrative records.

### MVP
One city, one process type: zoning variances within a notice radius. Verify address to radius membership, allow renter self-attestation, produce a staff-reviewed packet with public comments and private verification audit trail.

### Funding path
Paid by planning/legal-aid pilots, city innovation budgets, or foundations focused on fair housing and procedural justice; later API/add-on pricing for civic participation vendors.

### Fatal risk
Verification can become exclusionary or privacy-invasive. If renters, undocumented residents, unhoused people, or non-address stakeholders cannot participate safely, the product will damage legitimacy rather than improve it.

---

## 4. Concern Router for Newsrooms and Hotlines

**One-line product:** A routing tool for local newsrooms, 311-style civic hotlines, libraries, and community groups that maps a raw concern — “they’re closing our clinic,” “my block is being rezoned,” “new EPA rule hurts us” — to the correct live official process and comment path.

### Target user
Local reporters, public-library civic navigators, community foundation help desks, neighborhood associations, and issue-tip inbox managers who hear concerns before residents know the procedural target.

### Painful trigger / deadline
A story, rumor, viral post, or community meeting surfaces public concern, but the relevant action window may close before anyone identifies whether the correct venue is a docket, council item, zoning board, school-board vote, state bill hearing, or agency rulemaking.

### Data / protocols / repos to build on
- **DocketClock-style deadline index** from Regulations.gov, Federal Register, and Mirrulations.
- **Open States v3 API** for state bills, hearings, sponsors, committees, and “who represents me.”
- **Legistar OData** for local agendas and legislative files.
- **City Scrapers** for non-Legistar meetings.
- **RuleBox pattern** for cheap classification rules generated from examples.
- **WriteToThem / MapIt pattern** for jurisdiction and official routing.

### Action loop
1. Navigator enters a plain-language concern, location, and any known organization/person/place.
2. Product searches live official processes and returns likely targets with confidence, deadlines, and “why this matches.”
3. It produces a short public explainer: what is still actionable, who can comment, what evidence matters, and exact filing/hearing steps.
4. Residents are routed into a quality-controlled comment flow or to the correct official contact.
5. Navigator tracks whether the concern produced official-record input and publishes a follow-up note when the process changes.

### Why this does not duplicate existing tools
Search portals require docket/bill knowledge; action tools assume the target is Congress; newsroom tip systems do not connect tips to official deadlines. This product is the missing router between ambient public concern and the procedural venue where input counts.

### MVP
One metro area plus federal dockets; intake form for librarians/newsroom staff; search across Federal Register/Regulations.gov, Open States for the state, and one Legistar city/county; confidence-scored matches; no public self-serve app until navigator workflows are validated.

### Funding path
Local-newsroom grants, library/community-foundation pilots, civic information philanthropy, then SaaS for newsrooms, advocacy coalitions, and public-interest legal organizations.

### Fatal risk
Routing errors are costly: sending people to the wrong venue or overstating an action window burns scarce civic trust. The product needs conservative confidence thresholds and a “no reliable official path found” answer.
