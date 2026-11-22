# Real-estate agent

Covers: a person or agency that sells or lets homes and other property on behalf of owners: listings, valuations, enquiries and viewings. Includes a one-person agent, an independent agency, an office of a franchise network, and letting and property-management agents.
Does not cover: a developer marketing one new building (use `landing-page.md`); short holiday stays (use `hotel-guesthouse.md`); mortgage brokers and property portals that list many agents' stock.
Written 2026-11-22. References checked 2026-11-22. Template: [README.md](README.md).

## 1. Objects

An agent sells **trust on behalf of someone else**. The agent does not own what is listed: the seller or landlord does. So every listing must be true today, every price must say what kind of price it is, and the agent's own licence and complaints route matter as much as the photos. Two audiences use the same site: people looking for a home, and owners deciding whether to give the agent their home to sell or let.

### Agency

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Riverside Homes" |
| Sale, rent or both | required | |
| Areas covered | required | named towns, districts or postcodes |
| Phone | required | |
| Office address, or "no public office" | required | |
| Opening hours, per day of the week | required if there is an office | Mon-Fri 09:00-18:00, Sat 10:00-16:00, closed Sun |
| Licence or registration number | required where the law requires it | an Israeli broker licence number; a US state licence number |
| Redress scheme or complaints body | required where the law requires it | in the UK, membership of an approved redress scheme |
| Client money protection | required for letting agents where the law requires it | |
| Fees | required where the law requires them shown | letting fees for landlords |
| Email | optional | |
| Year founded, short story | optional | |
| Social account | optional | |

### Office (only when there is more than one)

Same fields as address, phone, hours and areas, repeated per office. Reference 4 is a network of over a hundred independently owned offices; each listing belongs to one office.

### Agent (team member)

| Field | Required | Example |
|---|---|---|
| Display name | required | as the agent wants it public |
| Role | optional | sales, lettings, valuer, property manager |
| Direct phone or email | optional | |
| Photo | optional | only with consent |
| Personal licence number | required where the law requires it per agent | |
| Areas or listings | optional | |

### Listing (a property)

| Field | Required | Example |
|---|---|---|
| Sale or rent | required | |
| Status | required | see the status list below |
| Price | required, or an explicit "price on application" | 750,000; 2,000 |
| Price qualifier | required | asking price, guide price, offers over, fixed price, price on application |
| Rent period | required for rentals | per month, per week |
| Location as shown publicly | required | street and district, or district only; the exact address only if the owner agreed |
| Location for the map | optional | an approximate point unless the owner agreed to an exact one |
| Property type | required | flat, house, land, office |
| Bedrooms | required for homes | the counting convention of the country (see rule 9) |
| Bathrooms | optional | |
| Size | optional; with units | 57 square metres; 608 sq ft |
| Photos | required, at least one | of this property |
| Floor plan | optional | marked as approximate |
| Description | required | in the agent's words, based on facts from the owner |
| Key features | optional | outdoor space, parking, lift, floor, safe room |
| Tenure or ownership type | required where the market uses it | freehold, leasehold, share of freehold (UK) |
| Energy rating | required where the law requires it | an EPC rating (UK, EU) |
| Running costs | required where the law or market expects them | service charge, municipal tax band, HOA fee |
| Available from (rentals) | required for rentals | a date or "now" |
| Furnished (rentals) | optional | |
| Deposit (rentals) | optional; required where the law requires it shown | |
| Responsible agent or office | required | |
| Reference number | required (system) | |
| Date listed | required (system) | |
| Video or 3D tour | optional | |

Status list: coming soon, available, under offer, sold subject to contract, sold, let agreed, let, withdrawn. A market may use its own words (see section 6).

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Enquiry about a listing | listing (required), name, phone or email, message, buyer's or renter's situation | Goes to the listing's agent or office |
| Viewing request | listing, preferred times, contact | A request until the agent confirms |
| Valuation request | owner's name, contact, property address, sale or let, timing | The main business source for an agent; every reference except 6 offers one |
| Applicant (registered buyer or renter) | contact, search criteria, alerts consent | App only; references 3 and 4 offer accounts |
| Saved search and alert | criteria, frequency | App only |
| Sold or let archive | listings with final status | Proof of track record; reference 6 shows sold prices, one as "price upon request" |
| Area guide | place, text, photos, linked listings | References 3 and 5 |
| Review | text, first name or initials, office, date, source | Only real reviews |
| Document | brochure, floor plan, energy certificate | Per listing |
| Calculator | stamp duty, borrowing, rental yield | Reference 3 and 4 offer these; they are tools, not facts about a property |

## 2. Rules

1. Every listing has exactly one status from the declared list, and it is true today.
2. A listing that is sold, let or withdrawn is never shown as available. It either moves to an archive with its final status, or is removed with a redirect.
3. Every price carries its qualifier and currency. A rent carries its period. "Price on application" is allowed; a blank or zero price is not.
4. A price shown on the agency's site matches the price the agency publishes elsewhere for the same listing. A change is made in one place and flows everywhere.
5. The public location of a listing is chosen by the owner. The default is street or district level; the exact address and an exact map pin need the owner's agreement.
6. Photos are of the listed property and current. A virtually staged or edited photo is labelled as such.
7. Photos do not show the occupants, children, family photos, documents, or anything that identifies the people who live there.
8. A floor plan is labelled as approximate and not to scale unless it was professionally measured and the agent says so.
9. Bedroom and room counts follow one stated convention per country (for example, Israel commonly counts the living room as a room). The convention is stated where it could mislead.
10. Size carries its unit and, where the market distinguishes them, whether it is internal or gross area.
11. Information the law requires in an advert (energy rating, tenure, running costs, licence number) is shown on every listing where it applies. See Legal.
12. Listing descriptions do not use words that exclude people by family status, religion, origin, disability or other protected grounds ("no children", "ideal for a Christian family"). This is unlawful in many jurisdictions.
13. A review is real and carries its source. A review that names staff or reviewers is shown only as the source published it, with consent. No rating is shown without a count and a source.
14. Statistics about the agency ("most sales in the area", "96% of asking price") appear only when the customer states them with their source and period.
15. Every enquiry carries the listing's reference, and reaches the listing's agent or office.
16. A viewing request is shown as a request until the agent confirms it.
17. A listing's address leads somewhere after removal: to the archive page or to the search with a short "no longer available" note.
18. The main actions (search, enquire, request a valuation) are reachable from every page on a phone. The phone number is a tappable link.
19. Data that comes from a shared listing service (an MLS in the US) carries the attribution the service requires. Reference 5 shows such a notice.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Agency name | "What is your agency called?" | Without a name people cannot find you or recommend you. |
| 2 | Sale, rent or both | "Do you sell, let, or both? Do you also manage rented homes?" | Buyers, renters and owners each look for a different door. |
| 3 | Areas | "Which towns or neighbourhoods do you cover?" | People search by place. An owner wants an agent who knows their street. |
| 4 | Phone and office | "What number should people call, and is there an office people can visit? When is it open?" | Without it people cannot ask, and arrive at a closed door. |
| 5 | Licence or registration | "What is your licence or registration number, and are you a member of a complaints scheme?" | In many countries the law requires it, and careful people check before they trust. |
| 6 | Where the listings live today | "Where do you keep your listings now: a property system, the portals, a spreadsheet, nowhere yet?" | The site must show the same homes and prices as everywhere else. Two lists drift apart and one becomes wrong. |
| 7 | The listings themselves | "Send me the homes you have now: for each, the price, where it is, rooms, size and photos." | Without real listings there is nothing to look at. Inventing a home is never allowed. |
| 8 | How status stays true | "Who will mark a home as under offer, sold or let, and how quickly?" | A home shown as available after it is sold wastes people's evenings and makes them distrust every other listing. |
| 9 | Address privacy | "Do your sellers agree to the exact address being shown, or only the street or area?" | A seller may not want strangers at the door before a viewing. |
| 10 | Valuations | "Do you offer owners a valuation? Free? How do they ask for one?" | This is how owners become clients. If it is missing, the site serves only buyers. |
| 11 | Where enquiries go | "Where should each enquiry go: to you, to the agent on the listing, to an office?" | An enquiry that reaches nobody is a buyer who calls another agent. |
| 12 | Who is the business legally | "What is the registered name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only in some cases:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 13 | Fees (letting agents, and where the law requires fees shown) | "What do you charge landlords, and is anything charged to tenants?" | In some places fees must be shown, and some tenant fees are banned. |
| 14 | Team (if agents are shown) | "Who should appear on the site, with which phone, and have they agreed to their photo?" | People like to know who they will meet. Only with each person's consent. |
| 15 | Required listing information | "In your country, what must every advert show: energy rating, tenure, running costs, a licence number?" | Missing it can be a legal problem and leaves buyers asking the same questions. |
| 16 | Viewing rules | "Can people request a viewing online? Who confirms it?" | A viewing that nobody confirms is a stranger on a doorstep. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about a property.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Listing card fields | photo, price with qualifier, location as shown, bedrooms, bathrooms, size, status label | The set seen across references 1, 5 and 6 | Shown as "fields on each card - change them" |
| Order of listings | newest first | Common and neutral | Setting, labelled "default order" |
| Search filters | sale or rent, area, price range, bedrooms, property type | Seen in references 3 and 4 | Editable list |
| Public location | street and district, no exact pin | Protects the seller until they agree otherwise | Labelled "default: street level" |
| Status labels | the list in section 1, in the country's usual words | Domain vocabulary, not a fact | Editable list |
| Price qualifier when none given | none: the listing is held back until the customer chooses | A qualifier changes what the price means; it is never assumed | Listed for the customer as "price type missing" |
| Floor plan note | "Approximate, not to scale, for guidance only" | Says less, not more | Marked "draft wording" |
| Sold or let archive | on, showing final status; prices shown only if the customer agrees | Proof of track record, as in reference 6 | Setting |
| Valuation form fields | name, contact, property address, sale or let, timing | The minimum to call back | Shown before publishing |
| Units | square metres, or square feet in the US and as the UK market uses | Follows the country | Shown, changeable |
| Currency | the customer's country | Follows the area | Shown next to every price |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Empty search message | "No homes match - try fewer filters or a nearby area" | Honest | Shown, changeable |
| Legal page structure | headings only: who we are, licence and complaints body, what we collect, why, how long, your rights, contact | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing area guide is better than an empty one | Listed as "not shown yet: team, area guides, reviews" |

Never a default, whatever the customer left out: a listing, a price, a price qualifier, a status, an address, a size, a room count, an energy rating, tenure, running costs, a licence number, fees, sold prices, statistics about the agency, reviews, awards, or claims such as "best agent in the area".

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Sold or let home still shown as available | Enquires, is told it went weeks ago | Distrust of every listing; a wasted viewing | Rules 1 and 2; mandatory fact 8 |
| Site and portals show different prices | Sees two prices for one home | Distrust; an argument at the offer | Rule 4; one source of truth (mandatory fact 6) |
| Feed from the property system stops silently | The site freezes at last month's stock | Silent loss for weeks | Show "listings updated [time]"; alert the customer when an import fails or returns zero |
| Rent shown without period | Reads a weekly rent as monthly, or the reverse | A wasted viewing; anger | Rule 3 |
| Price shown without qualifier | Takes a guide price as fixed | A failed negotiation | Rule 3; default holds the listing back |
| Exact address published against the seller's wish | Strangers knock on the seller's door | A complaint; a lost client | Rule 5; mandatory fact 9 |
| Occupants or family photos in listing pictures | Sees a stranger's children | A privacy complaint | Rule 7 |
| Floor plan or size read as exact | Furniture does not fit; a buyer feels misled | A dispute | Rules 8 and 10 |
| Search returns nothing and shows an empty page | Thinks the agency has no homes | Leaves | Empty-search message with suggestions |
| Enquiry goes to an agent who left | No reply | A lost buyer | Rule 15; enquiries go to an office address, not only to a person |
| Valuation request never followed up | Owner waits, then calls a competitor | The most expensive loss in this domain | Mandatory fact 10; alert and status on each request |
| Removed listing's link breaks | A shared link leads to an error page | Looks careless | Rule 17 |
| Required advert information missing | (A careful buyer asks; a regulator may notice) | A legal problem in some countries | Rule 11; mandatory fact 15 |
| Discriminatory wording in a description | Some visitors read that they are not welcome | Unlawful in many places; reputational damage | Rule 12; check descriptions before publishing |
| Map pin in the wrong place | Goes to the wrong street | A missed viewing | Customer confirms each pin; approximate by default |
| Template placeholders left on the page | Sees code-like words instead of content | Looks broken | Check every published page for unfilled fields; one rejected reference (section 9) showed this |
| Photos not resized | Listing pages crawl on a phone | Leaves before the second photo | Resize on upload |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working agent in either language. Regional Arabic usage varies. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Real-estate agent (UK estate agent; US broker, agent) | acts for the owner | מתווך / מתווכת נדל"ן | وسيط عقاري / سمسار |
| Brokerage, agency | the business | משרד תיווך | مكتب وساطة عقارية (not verified) |
| Property | what is sold or let | נכס | عقار |
| Listing | a property on the market | נכס למכירה / להשכרה; "מודעה" for an advert | إعلان عقاري (not verified) |
| Seller, vendor | owner selling | מוכר | بائع |
| Landlord | owner letting | משכיר | مؤجّر |
| Buyer | | קונה | مشترٍ |
| Tenant, renter | | שוכר | مستأجر |
| Valuation, market appraisal | the agent's view of the price | הערכת מחיר / הערכת שווי (a licensed appraiser is שמאי, a different job) | تقييم (not verified) |
| Asking price | the price the seller asks | מחיר מבוקש | السعر المطلوب (not verified) |
| Guide price, offers over | an indication, not fixed | not verified | not verified |
| Price on application (POA) | no public price | מחיר לפי פנייה (not verified) | السعر عند الطلب (not verified) |
| Under offer | an offer accepted, not yet final | בתהליך / יש הצעה (not verified as standard) | not verified |
| Sold subject to contract (STC, UK) | agreed, contracts not exchanged | not verified | not verified |
| Exchange, completion (UK); closing (US) | the legal steps of the sale | חתימת חוזה / מסירה (not verified as equivalents) | not verified |
| Let agreed | a tenant found, not yet moved in | not verified | not verified |
| Viewing (UK), showing (US) | visiting the property | ביקור בנכס / סיור בנכס (not verified) | معاينة (not verified) |
| Open house | public viewing at set times | בית פתוח | not verified |
| Sole agency, exclusive | only this agent may sell | בלעדיות | حصرية (not verified) |
| Commission, agent's fee | the agent's payment | דמי תיווך | عمولة |
| Brokerage agreement | signed order for the agent's services | הזמנת שירותי תיווך | عقد وساطة (not verified) |
| Freehold, leasehold, share of freehold (UK) | forms of ownership | not verified as equivalents | not verified |
| Land registry extract | official ownership record | נסח טאבו | not verified |
| Service charge (UK), HOA fee (US) | shared building costs | ועד בית (not verified as equivalent) | not verified |
| Municipal property tax | local tax on the home | ארנונה | ضريبة الأملاك / الأرنونا (not verified) |
| Energy performance certificate (EPC) | energy rating | not verified | not verified |
| Floor plan | drawing of the rooms | תוכנית דירה / שרטוט | مخطط الشقة (not verified) |
| Square metres | size | מ"ר | متر مربع |
| Rooms, bedrooms | counting differs by country | חדרים (living room counted) | غرف |
| Safe room | reinforced room (Israel) | ממ"ד | غرفة محصّنة (not verified) |
| Lift, parking, balcony, floor | key features | מעלית, חניה, מרפסת, קומה | مصعد، موقف سيارات، شرفة، طابق |
| Multiple listing service (MLS, US) | shared listings database | not verified | not verified |
| Realtor | a trademark in the US for members of one association | not used | not used |

Notes on language:

- UK and US English differ widely: estate agent/broker, flat/apartment, viewing/showing, completion/closing, let/rent. Pick one by the customer's country.
- "Realtor" is a registered trademark in the US. Do not use it unless the customer is a member and says so.
- Words to avoid unless the customer said them and can back them: "best", "number one", "guaranteed sale", "investment opportunity", "will not last", "bargain", "luxury", "exclusive" (unless it means sole agency), and any word about who the home suits by family, religion or origin.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the customer's country before it is relied on.

### Applies almost everywhere

- **Agents are licensed or registered** in many countries, and adverts must often show it. Not verified per country.
- **Adverts must not mislead.** Price, size, condition, ownership type and running costs are treated as part of the offer.
- **Fair housing and non-discrimination.** Descriptions and selection of buyers or tenants may not exclude protected groups. Not verified per country.
- **Privacy notice.** Needed for enquiries, viewings, valuations and applicant accounts. Seller and tenant data (names, phone numbers, whether a home is empty) is especially sensitive.
- **Anti-money-laundering** duties apply to agents in many countries (identity checks on buyers and sellers). Reference 3 links to "AML documents". Not verified per country.
- **Reviews** must be real.
- **Marketing messages** (alerts, newsletters) need prior agreement.

### Israel

- Real Estate Agents Law, 1996: a broker must hold a licence; commission depends on a written, signed order for brokerage services containing required details; exclusivity has its own rules. Whether the licence number must appear in every advert: not verified.
- Accessibility: businesses serving the public are required to make their websites accessible and publish an accessibility statement, under the Equal Rights for Persons with Disabilities Law and its service-accessibility regulations, with Israeli Standard 5568 as the technical reference. Thresholds: not verified.
- Privacy: the Protection of Privacy Law applies; Amendment 13 came into force in August 2025. Not verified for a small agency.
- Consumer Protection Law: misleading advertising is prohibited. How it applies to room counts and sizes in listings: not verified.
- Marketing messages: section 30A of the Communications Law requires prior consent. Details: not verified.

### European Union and United Kingdom

- GDPR (EU) and UK GDPR apply. Non-essential cookies need consent (one rejected reference, 2026-11-22, shows a cookie notice with three choices).
- UK: estate and letting agents must belong to a government-approved redress scheme. Reference 1 and its sister site (rejected in section 9) include an ombudsman image, seen as a file name only. Believed true; not verified.
- UK: letting agents must belong to a client money protection scheme and display their fees, and most fees charged to tenants in England are banned under the Tenant Fees Act 2019. Not verified.
- UK: material information (price, tenure, council tax band, and more) is expected in every listing under National Trading Standards guidance applying consumer protection law. Not verified in detail.
- UK: an energy performance certificate is required when a home is marketed for sale or rent. Believed true; not verified.
- UK: the Renters' Rights Act changes tenancy rules; references 3 and 4 both lead with explainers on it (observed 2026-11-22). What it requires on an agent's website: not verified.
- EU: energy-certificate display in property adverts is required under EU energy-performance rules as applied by each member state. Not verified per state.
- Accessibility: the European Accessibility Act applies from June 2025 to certain consumer services with a microenterprise exemption. Whether an agency site is in scope: not verified.

### United States

- Brokers and agents are licensed by each state; advertising rules (brokerage name shown, licence numbers) differ by state. Not verified per state.
- The Fair Housing Act prohibits discriminatory advertising of housing; many sites show an equal-housing-opportunity notice. Not verified for website duties.
- Listing data from an MLS is shown under the MLS's display rules, with required attribution. Reference 5 shows such an attribution notice at the foot of the page.
- "Realtor" is a trademark of the National Association of Realtors.
- The Americans with Disabilities Act is applied by courts to business websites in many cases. Not verified.
- State privacy laws apply above thresholds. Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page, a terms page, a fees page and an accessibility statement. It marks each as a draft that needs review.
- The product never states that the site "complies with" a named law and never adds a licence, redress or equal-housing badge on its own.
- The product asks which country before generating any legal page or listing template, and asks which advert information that country requires (mandatory fact 15).

## 8. Site vs app

### Content pages (no data, no accounts)

Home, about, selling with us, letting with us, property management, areas, team, fees, contact, legal pages. A one-person agent with a handful of listings that change monthly can run as a content site with each listing as a page and a phone link. It is honest only if the customer will update status the same day (mandatory fact 8).

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Listing page | cannot be empty: no listing, no page | missing photo shows "photos coming soon" | Status always visible |
| Team | section hidden | | Only consented photos |
| Area guides | hidden | | |
| Reviews | hidden | | Never filled with placeholders |
| Fees | cannot be empty where the law requires it | | |
| Hours | cannot be empty if there is an office | | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Listing search with filters | listings, statuses, areas | "No homes match - try fewer filters or a nearby area"; never an empty page | card placeholders, never an empty grid that looks like "no homes" | "Could not load homes - call us", with the number | n/a | everyone reads; only staff change |
| Map view | approximate points (rule 5) | "No homes in this area - zoom out" | | if the map fails, the list remains | n/a | everyone reads |
| Listing page | one listing with photos, plan, documents | n/a | text first, photos progressively | removed listing: "No longer available" with similar homes (rule 17) | n/a | everyone reads |
| Enquiry and viewing request | stores with the listing reference; alerts the agent or office | n/a | button shows "sending" and cannot be pressed twice | "Not sent - please call", with the number | visitor sees "received", and that a viewing is not confirmed until the agent replies | visitor writes; the listing's agent and the office read |
| Valuation request | stores the request; alerts the office | n/a | as above | as above | "received - we will call you within [customer's promise]" only if the customer promises a time | office staff only |
| Listings import (feed) | a connection to the property system or a file | "No listings imported yet" | import progress | failed or zero-result import alerts the customer and keeps the last good list, marked with its time | each import logged with counts added, changed, removed | owner only |
| Staff listing editor | listings, photos, statuses | "No listings yet - add the first" | upload progress | failed save keeps what was typed | status change is one action and shows on the site at once | staff behind a login; each office edits its own |
| Applicant account and saved searches | accounts, criteria, consent | "No saved searches yet" | | | alerts sent only with consent; one-click unsubscribe | visitor only |
| Owner, landlord and tenant portal | documents, offers, rent notices | "Nothing yet" | | | actions recorded with date and time | each party sees only their own property (reference 3 describes signing documents and sending or accepting offers in its account) |

### Needs accounts

- Staff always need them as soon as listings are stored or edited. A network of offices needs per-office permissions.
- Visitors do not need an account to search, enquire, book a viewing or ask for a valuation. Accounts are justified for saved searches and alerts, and for owners and tenants following their own transaction.

### Needs payments

- Holding deposits, rent collection, application fees where lawful, property-management charges.
- Each brings client-money rules, refunds and receipts, and in some countries specific bans (see Legal).
- Default: no payments. Payments are a separate product decision, never added by default.

### Using an existing property system

Most agents already keep listings in a property-management or CRM system that also feeds the portals. In that case the product should read listings from that system, not ask the agent to type them twice. Ask first (mandatory fact 6). The failure mode is the feed stopping silently (see section 5).

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos and icons. Character counts are approximate, after removing link targets. Only home pages were fetched; no listing page, search result or valuation form was opened.

**Curation.** Chosen by the author from UK and US agencies with their own sites: two design-led or prime UK agencies, two large UK agencies, a US national brokerage and a Los Angeles brokerage. Kept only if the page loaded and read as the agency's own. No awwwards.com category was consulted; none is claimed as an award winner. All six are in English, in Latin script. Reviews on reference 4 name private reviewers and staff; those names are not repeated here.

**Limit.** All six are large or upmarket agencies in the UK and the US. No one-person agent, no small independent agency and no letting-only agent was verified. Three home pages returned little text (1, 2 and 6), so their structure is partly inferred from the order of the few lines returned.

Verified: 6.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.themodernhouse.com | 2026-11-22 | UK agency for design-led homes. Listing cards, each: the house or street name, a price, the town or postcode district, and either the ownership type (freehold, share of freehold) or a status ("New", "Sold"); one card shows no price. Press quotes are placed between the listing cards. "How much is my home worth?" with "Get a free market appraisal". "About us". An ombudsman image appears among the page's images (file name only). Extraction: 18 images, about 1,100 characters. |
| 2 | https://www.knightfrank.co.uk | 2026-11-22 | Large UK agency. Order: "Find your next property" - an offer to estimate a property's value - "Over 150 services" - "Dream properties": homes from city flats to country houses, farms and homes abroad - "We're here for you" (buy, sell, rent, invest) - one testimonial - "The Knight Frank difference". Image file names suggest a carousel of property categories. Extraction: 24 images, about 800 characters. |
| 3 | https://www.foxtons.co.uk | 2026-11-22 | London agency. Navigation by audience (buy, rent, landlords, sell) with tools and duties named: valuation, stamp duty calculator, borrowing calculator, rental yield calculator, property-fraud protection, Right to Rent, fees and terms, legal requirements, EPCs, AML documents, Renters' Rights Act, complaints. Home: headline - search by map, travel time, school, station or near me - four audience blocks, each with a stated statistic - valuation booking - account features (review and sign documents, send or accept offers, rental notifications) - Renters' Rights Act explainer - blog, local life, interiors - nearest office - opening hours per day in two columns. Extraction: 6 images, about 7,000 characters, mostly navigation. |
| 4 | https://www.winkworth.co.uk | 2026-11-22 | UK agency network of over a hundred independently owned offices. Order: audience menus (buy, sell, rent, let) with guides and calculators - headline - search filter (price range, bedrooms, property type, search radius) - three numbers with a data-source footnote - an account to save properties and track updates - four audience tiles - a long run of dated reviews, each with the office town, staff first names and the reviewer's name - find your local office. Extraction: 38 images, about 18,000 characters. |
| 5 | https://www.compass.com | 2026-11-22 | US national brokerage. Order: hero promoting listings shown before other sites - three listing cards: price, bedrooms, bathrooms, square feet (one shows "Unavailable"), street address with unit and neighbourhood, and a listing-service compliance logo - a mortgage pre-approval partner link - a seller programme paying for home improvements, with a footnote that fees or interest may apply depending on the state - neighbourhood guides by region - popular cities - markets by state - a listing-service data attribution and disclaimer at the foot. Extraction: 20 images, about 5,000 characters. |
| 6 | https://www.hiltonhyland.com | 2026-11-22 | Los Angeles luxury brokerage. Order: positioning headline - story with founding year - featured listings, each "street, city", price, and "bedrooms, bathrooms, square feet or acres" - "Showcase sold properties" shown as prices only, one as "price upon request" - social feed with listing captions - "View properties". Extraction: 5 images, about 3,500 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.inigo.com | 2026-11-22 | Loads; sister agency of reference 1. Text returned was a cookie notice with three choices, one listing line and a positioning sentence (about 400 characters). Too thin; would duplicate reference 1. |
| https://www.aucoot.com | 2026-11-22 | Loads; text returned was one listing line (about 50 characters). Too thin. |
| https://www.theagencyre.com | 2026-11-22 | Loads and is the brokerage's own site, but the extraction contains unrendered template placeholders (for example a field name in double curly braces in the new-developments block, and a heading key instead of a heading). Not a quality reference; used only as evidence for the placeholder failure mode. |
| https://www.elliman.com | 2026-11-22 | Loads; text returned was a heading and two links (about 120 characters). Too thin. |

Tried and did not load (not counted): chestertons.co.uk.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the local agency (search and valuation)

For an agency serving one area with a stock of listings that changes weekly. Default for this domain.
From references 2, 3 and 4; the audience split from 3 and 4, the search filters from 4, the valuation block from 1, 2 and 3, the office hours table from 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; buy, rent, sell, let (only those offered); phone; "free valuation" if offered | search and valuation are the two main actions | yes |
| 1 | Opening | one sentence: what the agency does and where; a search with sale or rent, area, price, bedrooms | search is the largest control | yes |
| 2 | Latest homes | listing cards: photo, price with qualifier, location as shown, rooms, size, status label | identical card layout | yes |
| 3 | For owners | what selling or letting with the agency involves; the valuation request | short text and one action | yes if valuations are offered |
| 4 | Why us | only stated facts: years, offices, sold track record with source | short list | optional, hidden when empty |
| 5 | What clients say | real reviews with source, date and office | at most three | optional, hidden when empty |
| 6 | Area knowledge | guides to the areas covered | links | optional |
| 7 | Find us | office address, phone, hours per day with closed days named; repeated per office | complete without a map | yes |
| 8 | Footer | name; licence or registration number; complaints body; fees page; privacy, terms, accessibility statement; listing-data attribution if required | small but complete | yes |

Listing page (domain knowledge; no reference listing page was fetched): photos - price with qualifier and status - location as shown - key facts (rooms, size, type, ownership, running costs, energy rating) - description - floor plan marked approximate - map at the agreed precision - enquire and request a viewing - the responsible agent or office.

Image-to-text ratio: **estimate**, from extraction counts only (references 3 and 4 returned 6 and 38 images against about 7,000 and 18,000 characters, most of it navigation and reviews). On the home page, text and controls lead; photographs live in the listing cards. Not confirmed in a rendered view.

### Skeleton B: the curated or prime agency (listings as the page)

For an agency with fewer, distinctive homes, where each listing is a showpiece and the brand is the selection.
From references 1, 5 and 6; listings between press quotes from 1, the fact line on each card from 5 and 6, the sold showcase from 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; homes; sell with us; contact | minimal | yes |
| 1 | Opening | one featured home: large photo, name, price, place | the photo carries the page | yes |
| 2 | Homes | a grid of listing cards: photo, name or street, price, place, ownership type or status | large images, few words per card | yes |
| 3 | Proof between listings | press quotes with the publication named, or one testimonial | one quote at a time | optional |
| 4 | For owners | "what is my home worth?" and the appraisal request | one heading, one action | yes if valuations are offered |
| 5 | Sold | recent sales as photos with final status; prices only with the customer's agreement | quieter than live listings | optional |
| 6 | About | who chooses the homes and why | one short block | optional |
| 7 | Footer | as Skeleton A | | yes |

Image-to-text ratio: **estimate**. Image-led: reference 1 returned 18 images against about 1,100 characters; reference 6 returned few images in the extraction but its text is mostly one line of facts per listing. Roughly one large photograph per listing with one line of facts under it. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working agent. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source. This includes the Israeli Real Estate Agents Law details, UK redress and client money schemes, the Tenant Fees Act, material-information guidance, EPC duties, the Renters' Rights Act, US licence and fair-housing advertising rules, and MLS display rules.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view. Three references returned very little text.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. Only 6 references, all large or upmarket agencies in the UK and US. No one-person agent, small independent or letting-only agent.
6. No listing page, search result, map, valuation form or account area of any reference was fetched. The listing-page order in section 10 is domain knowledge.
7. The ombudsman membership of reference 1 is inferred from an image file name, not from visible text.
8. The claim that most agents keep listings in a property system that feeds the portals is the author's belief, not observed.
9. References were checked on 2026-11-22, one day after the date given in the brief (2026-11-21), because that is when they were loaded.
10. Prices, statistics and review counts mentioned in the reference notes are what the pages stated on the day.
11. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
