# Craftsman and renovation

Covers: tradespeople and firms who do work in or on a client's home or building, and are paid per job after a quote: carpenters and joiners, kitchen makers and fitters, builders, extension and loft firms, design-build remodelers, plumbers, electricians, painters, tilers, roofers and handymen. From a one-person business with a van to a firm with design studios.
Does not cover: architects and interior designers presenting their work (use `portfolio.md`); selling furniture or materials from a range (use `catalogue-collection.md`); car repair (use `garage.md`); cleaning services (no phase-1 file).
Written 2026-11-22. References checked 2026-11-22. Template: [README.md](README.md).

## 1. Objects

A craftsman sells **a job that does not exist yet**. The visitor cannot see the product before buying, so the domain runs on proof and on a sequence: enquiry, visit, quote, work, handover. Everything on the site either proves skill (past projects) or moves the visitor one step along that sequence.

### Business

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Harbour Joinery" |
| Trade or trades | required | joinery and fitted furniture; kitchens; extensions; plumbing |
| Jobs done, and jobs not done | required | "alcove units, wardrobes, kitchens; no structural work" |
| Area covered | required | named towns or districts, or a radius from a named place |
| Phone | required | a number that is answered, or says when it is answered |
| When enquiries are answered | required | "Mon-Fri 07:30-18:00, Sat 09:00-14:00" |
| How to start | required | call, message, form, book a visit or consultation |
| Is the first visit free | required | free design visit; paid feasibility study |
| Workshop, showroom or studio address | optional | only if the customer wants it public; a home address is never published by default |
| Email | optional | |
| Registrations and licences | required when the trade or country requires them | a gas-safety registration number; a contractor licence number |
| Insurance | optional; only as stated | "public liability cover of a stated amount" |
| Guarantee | optional; only as stated | "two years on workmanship" |
| Memberships of trade bodies | optional; only real ones | |
| Year started, short story | optional | |
| Social account | optional | |

### Service (type of job)

| Field | Required | Example |
|---|---|---|
| Name | required | "Fitted wardrobes", "Side return extension", "Boiler replacement" |
| Short description | required | what it involves, in one or two sentences |
| Typical price | optional, see rule 5 | "most kitchens between X and Y" |
| Typical duration | optional | "3-6 weeks in the workshop, 1-2 weeks on site" |
| Needs a site visit before any price | optional | most jobs |
| Needs permits or notices | optional | planning permission, building control, party-wall notice |
| Currently offered | required, default yes | |

### Project (finished work)

| Field | Required | Example |
|---|---|---|
| Title | required | named by street or district, never by full address |
| Type of job | required | links to a service |
| Area | required | district or town only |
| Photos | required | the business's own photos of this job |
| Before photos | optional | same angle as the after photo |
| Short story | optional | what the client needed and what was done |
| Size, duration | optional | "added 28 square metres" |
| Client's consent to publish | required | stored, not shown |
| Client quote | optional | only real, with consent |

### Enquiry (a lead)

| Field | Required | Example |
|---|---|---|
| Name | required | |
| Phone or email | required | |
| Area or postcode | required | to know at once whether the job is in range |
| Type of job | required | from the service list, plus "other" |
| Description | optional | |
| Photos or a sketch | optional | reference 1 says a photo, dimensions or a sketch are often enough for an initial estimate |
| When the work is wanted | optional | |
| Budget band | optional | some businesses ask; many do not |
| How they heard of us | optional | reference 7 asks this with a long list |
| Status | required (system) | new, contacted, visit booked, quoted, won, lost, out of area |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Visit or consultation | date, time, in person or video, length, free or paid, address of the job | Reference 5 lets the visitor pick a day for a 30-minute call |
| Quote | items, prices, tax, what is excluded, how long it is valid, payment stages, start date | App only. A quote is a promise; an estimate is not (see section 6) |
| Job | quote, start date, stages, status, photos, payments | App only. Reference 7 has a "Make a Payment" link for clients |
| Process step | order, name, one line | Most references show the process as 3 to 7 steps |
| Review | text, first name or "homeowner", area, date, source | Only real reviews |
| Accreditation | name of body, registration number, expiry | Shown only if real and current |
| Area | name of town or district, or postcode prefix | Each can have its own page; reference 2 lists dozens |
| FAQ | question, answer | Reference 2 answers price, duration, area, reuse of existing units and guarantee |
| Finance offer | provider, terms link | Regulated; see Legal |
| Open house or showroom visit | date, place | Reference 5 runs tours of finished projects |

## 2. Rules

1. The area covered is stated as named places or a radius from a named place. "Nationwide" only if true.
2. An enquiry asks for the area or postcode, and an enquiry from outside the area is answered honestly, not left unanswered.
3. Every project belongs to one service type.
4. A project names its area at district or town level. A client's full address, house number or anything that identifies the house (a visible street number, a car plate) never appears.
5. A price is optional, but its absence is explicit: "price after a visit" or "free quote", never a blank. A price range shown on the site is the customer's own range, stated by the customer, with what it includes and excludes.
6. A "quote" and an "estimate" are different words. The site uses the one the customer actually gives. If the customer promises a fixed quote, the site may say so; otherwise it says estimate.
7. "Free" (visit, quote, consultation) appears only if it is free. A paid first step says its price or says that it is paid.
8. Registrations, licences, insurance amounts, guarantees and memberships appear only as the customer stated them. A logo of a trade body appears only if the customer is a current member.
9. Work that a country restricts to registered people (gas work, some electrical work, structural work) is offered only when the customer confirms the registration.
10. Photos are of the customer's own work. Stock photos, manufacturer brochure photos and other firms' photos are never presented as the customer's work.
11. Photos of a client's home are published only with that client's consent, and people in them only with their own consent.
12. Before and after photos come from the same job.
13. A review is real and carries its source. No star rating without a count and a source.
14. Any deposit, stage payment or cancellation term is shown before the client commits.
15. Response time ("we reply within a day") appears only if the customer promises it.
16. Durations are ranges, not exact dates, unless the customer gives a date.
17. The main action (call, message, book a visit) is reachable from every page without scrolling back to the top on a phone. The phone number is a tappable link.
18. An emergency or 24-hour claim appears only if the customer really answers at night, with the number that does.
19. A finance offer appears only if the customer is allowed to offer it (see Legal).

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Business name | "What is your business called?" | Without a name nobody can recommend you. |
| 2 | Trade and jobs | "What jobs do you do, and which jobs do you turn down?" | A visitor decides in seconds whether you do their job. Saying what you do not do saves you wasted calls. |
| 3 | Area | "Which towns or areas do you work in?" | Without it you get calls from too far away, and nearby people are not sure you come to them. |
| 4 | Phone | "What number should people call or message?" | Most people in this domain still call first. |
| 5 | When you answer | "On which days and hours do you answer the phone or messages?" | Someone who calls at 21:00 and hears nothing thinks you have closed. |
| 6 | First step | "How does a job start with you: a call, a visit to the house, a video call? Is the first visit free?" | The whole site leads to this step. If "free" is wrong, the first meeting starts with a broken promise. |
| 7 | Photos of your own work | "Send me photos of jobs you have finished, and tell me you have the clients' permission." | Your work is the proof. Without it the site asks people to trust a stranger. |
| 8 | Prices, or the decision not to show them | "Do you want a price range shown? If yes, what range, and what does it include?" | Price is the first fear. Hiding it is allowed; inventing it is not. |
| 9 | Registrations and licences | "Does your trade need a registration or licence where you work? What is the number?" | For some work the law requires it, and clients check. |
| 10 | Where enquiries go | "Where should I send each new enquiry: which phone or email?" | An enquiry nobody sees is a client who hires someone else. |
| 11 | Who is the business legally | "What is the registered name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only in some cases:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 12 | Guarantee | "Do you give a guarantee on your work? For how long, and what does it cover?" | Only a real guarantee may be shown; clients will hold you to it. |
| 13 | Insurance | "Do you want your insurance shown? What cover exactly?" | Only what the policy says. |
| 14 | Payment terms (when the product shows or takes payments) | "Do you take a deposit? In what stages do clients pay?" | The client must know before agreeing. |
| 15 | Visit booking (when visits are booked online) | "On which days and times can you do visits or calls?" | Without it a client books a time you cannot come. |
| 16 | Workshop or showroom address | "Is there a workshop or showroom people may visit? Should its address be public?" | Many tradespeople work from home and do not want that address public. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Process steps | enquiry - visit and measure - drawing and quote - work - handover | The common shape in references 1, 2, 3 and 7; the customer edits the words | Labelled "suggested steps - make them yours" |
| Missing price | "Price after a visit" | Says openly there is no number | Listed for the customer as "no price given" |
| Main action | "Call", using the phone number; "Book a visit" only if the customer has times | Works with zero setup | Labelled "default: phone" |
| Enquiry form fields | name, phone or email, area, job type, description, optional photos | The minimum to decide whether to call back | Shown before publishing |
| Project card fields | photo, job type, area (district) | Seen in references 1, 5 and 7 | Shown, changeable |
| Project title | the district and job type | Protects the client's address | Customer confirms each title |
| FAQ questions | price, duration, area, guarantee, mess and access, permits | Common visitor questions; reference 2 answers most of these | Questions are defaults; every answer is the customer's, and unanswered questions are hidden |
| Area display | the list of places as the customer said them | | Shown |
| Page order | Skeleton A below; Skeleton B for firms with a design team | Extracted from the references | Named as the default skeleton |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Currency | the customer's country | Follows the area | Shown next to every price |
| Legal page structure | headings only: who we are, what we collect, why, how long, your rights, photos of clients' homes, contact | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing gallery is better than an empty one | Listed as "not shown yet: projects, reviews, FAQ" |

Never a default, whatever the customer left out: area, prices, durations, "free" anything, guarantee, insurance, registrations, trade-body logos, years in business, number of projects, review scores, response times, "24-hour", "fully insured", "certified", "eco-friendly", "family business", or any other claim.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Enquiry form sends to nobody | Waits for a call that never comes | Silent loss; the worst case in this domain | Mandatory fact 10; test the form at publish and on a schedule |
| Area unclear | Enquires from far away, or does not enquire from next door | Wasted calls, lost local work | Rule 1; area asked first on the form (rule 2) |
| Phone not answered and no hours shown | Thinks the business is closed | A lost job | Mandatory fact 5; hours next to the number |
| "Free quote" turns out to be paid | Feels misled at the first meeting | Distrust from the start | Rule 7 |
| Price range on the site is years old | Expects a price the business no longer charges | An awkward first visit | Date on the range; yearly prompt |
| Client's house identifiable in a photo | A neighbour recognises the house; the client is upset | A complaint; a privacy problem | Rules 4 and 11 |
| Accreditation logo for a lapsed membership | (A careful visitor checks the register and finds nothing) | Distrust; possibly a legal problem | Rule 8; expiry date on each accreditation |
| Stock photos as the business's work | The finished job looks nothing like the pictures | A dispute; distrust | Rule 10 |
| Only big expensive projects shown | A visitor with a small job thinks it is too small to ask | Lost small jobs | Show the range of jobs; say "no job too small" only if true |
| Job type not listed | A visitor with that job leaves | A lost job | Mandatory fact 2; "other" on the form |
| Gallery of large photos not resized | Pages crawl on a phone at the client's door | Leaves | Resize on upload |
| Booking a visit at a time the business cannot do | Waits at home for nobody | An angry first contact | Mandatory fact 15; "requested" until confirmed |
| Emergency claim with nobody answering | A leak at night and no answer | Danger and fury | Rule 18 |
| Builder-tool placeholder text left on the page | Sees a technical message instead of a signup box | Looks unfinished | Check every published page for unfilled fields (one rejected reference in section 9 shows this) |
| Reviews all old | Wonders whether the business still exists | Doubt | Show dates; prompt for new reviews |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working tradesperson in either language. Regional Arabic usage varies. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Contractor, builder | runs building work | קבלן | مقاول |
| Renovation (UK), remodel (US) | changing an existing home | שיפוץ | ترميم / تجديد |
| Carpenter | works wood on site | נגר | نجّار |
| Joiner, joinery | makes wooden parts in a workshop | נגר / נגרות | نجارة |
| Cabinet maker | makes cupboards and furniture | נגר רהיטים (not verified) | not verified |
| Fitted furniture | built into the room | רהיטים בהתאמה / נגרות בהתאמה אישית (not verified) | not verified |
| Kitchen fitter | installs kitchens | מתקין מטבחים | not verified |
| Plumber | water and drains | אינסטלטור | سبّاك |
| Electrician | wiring | חשמלאי | كهربائي |
| Painter and decorator | paints, wallpapers | צבעי | دهّان |
| Tiler | lays tiles | רצף | بلّيط (Levantine; not verified) |
| Handyman | small mixed jobs | הנדימן / איש תחזוקה (not verified) | not verified |
| Quote | a fixed price for defined work | הצעת מחיר | عرض سعر |
| Estimate | an approximate price | הערכת מחיר / אומדן (not verified) | تقدير (not verified) |
| Site visit, survey | going to see and measure | ביקור באתר / מדידה (not verified) | زيارة موقع (not verified) |
| Scope of work | what is and is not included | היקף העבודה / כתב כמויות (for a bill of quantities) | نطاق العمل (not verified) |
| Day rate | price per working day | מחיר ליום עבודה | أجرة يومية |
| Materials and labour | parts and work | חומרים ועבודה | مواد وأجرة |
| Deposit | paid before starting | מקדמה | عربون / دفعة مقدمة |
| Stage payment | paid as the work progresses | תשלום לפי שלבים | دفعات حسب المراحل (not verified) |
| Variation (UK), change order (US) | a change to the agreed work | תוספת / שינוי (not verified as trade term) | not verified |
| Snagging, punch list | small faults fixed at the end | רשימת ליקויים (not verified) | not verified |
| Handover, completion | the job is finished and handed back | מסירה | تسليم |
| Extension, addition | new built space | תוספת בנייה | توسعة / إضافة بناء (not verified) |
| Loft conversion | turning an attic into rooms | הסבת עליית גג (not verified) | not verified |
| Planning permission (UK), building permit (US) | permission to build | היתר בנייה | رخصة بناء |
| Building regulations, building control (UK) | the technical rules and their inspection | תקנות התכנון והבנייה (not verified as equivalent) | not verified |
| Party wall (UK) | a wall shared with a neighbour | קיר משותף | جدار مشترك |
| Design-build | one firm designs and builds | תכנון וביצוע | تصميم وتنفيذ |
| Subcontractor | a firm hired by the main contractor | קבלן משנה | مقاول من الباطن / مقاول فرعي |
| Public liability insurance | covers damage to others | ביטוח צד שלישי / ביטוח צד ג' | تأمين ضد الغير (not verified) |
| Guarantee, warranty | promise to fix faults | אחריות | ضمان |
| Lead time | time before work can start | זמן המתנה / זמן אספקה | not verified |
| First fix, second fix (UK) | work before and after plastering | not verified | not verified |

Notes on language:

- UK and US English differ: renovation/remodel, extension/addition, planning permission/permit, snagging/punch list, variation/change order. Pick one by the customer's country.
- Visitors say "how much" and "how long". The trade says "scope", "spec" and "programme". Write for the visitor.
- Words to avoid unless the customer said them and can back them: "best", "cheapest", "fully insured", "certified", "approved", "guaranteed", "24/7", "no hidden costs", "eco", "award-winning".

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the customer's country before it is relied on.

### Applies almost everywhere

- **Privacy notice.** Needed as soon as the site collects a name, phone, address of the job or photos of a home.
- **Photos of clients' homes** are the client's private space. Consent before publishing; no identifying details.
- **Contracts made in the client's home** often carry special cancellation rights and information duties, different from a contract signed in a shop. Not verified per country.
- **Claims about registration, insurance and guarantees** are part of the offer. A false claim is treated as misleading advertising in most jurisdictions.
- **Reviews** must be real. Fake reviews are banned outright in some places (see United Kingdom).
- **Marketing messages** generally need prior agreement.

### Israel

- Accessibility: businesses serving the public are required to make their websites accessible and publish an accessibility statement, under the Equal Rights for Persons with Disabilities Law and its service-accessibility regulations, with Israeli Standard 5568 as the technical reference. Thresholds: not verified.
- Contractor registration: building work above a value threshold must be done by a contractor registered under the Registration of Contractors for Engineering Construction Works Law. The threshold and what the site must show: not verified.
- Electricians are licensed under the Electricity Law. Whether a licence number must appear in advertising: not verified.
- Privacy: the Protection of Privacy Law applies; Amendment 13 came into force in August 2025. Not verified for a small trade business.
- Cancellation: the Consumer Protection Law gives cancellation rights for transactions made at the consumer's home (door-to-door) and at a distance. How this applies to renovation work: not verified.
- Prices shown to consumers must include VAT: believed true; not verified for price ranges.

### European Union and United Kingdom

- GDPR (EU) and UK GDPR apply to enquiry data and job photos. Non-essential cookies need consent (one reference, 5, shows an accept-or-reject cookie notice, observed 2026-11-22).
- UK: the Consumer Contracts Regulations 2013 give a 14-day cancellation period for contracts made away from business premises (for example in the client's home), with written information duties; work started inside the period at the client's request may still be charged proportionally. Believed true; not verified.
- UK: gas work must be done by a business on the Gas Safe Register. Believed true; not verified for what the site must show.
- UK: building regulations apply to many renovation jobs; some electrical work in homes must be notified (Part P in England). Not verified.
- UK: the Party Wall etc. Act 1996 requires notices to neighbours for some work on shared walls. Reference 5 lists party-wall surveying as a service. Details not verified.
- UK: the Digital Markets, Competition and Consumers Act 2024 bans fake reviews and concealed incentivised reviews, from April 2025. Not verified.
- UK: offering finance as a credit broker needs Financial Conduct Authority authorisation. Reference 2 links to finance. Not verified.
- EU: rules on off-premises contracts follow the Consumer Rights Directive (14 days). Not verified per member state.

### United States

- Contractor licensing is by state, and sometimes by city. Some states require the licence number in all advertising, including websites (California is commonly cited). Not verified per state.
- Some states require home-improvement contractor registration and specific contract terms. Not verified.
- Work that disturbs paint in homes built before 1978 requires lead-safe certification under the EPA Renovation, Repair and Painting rule. Believed true; not verified for website duties.
- The FTC's cooling-off rule gives three days to cancel some sales made at the buyer's home. How it applies to renovation contracts: not verified.
- The Americans with Disabilities Act is applied by courts to business websites in many cases. Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page, a terms page and an accessibility statement. It marks each as a draft that needs review.
- The product never states that the site or the business "complies with" a named law, and never adds a registration or licence badge on its own.
- The product asks which country, and which trade, before generating any legal page, and asks for the registration number when the trade needs one.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, services, projects, about, how we work, areas covered, FAQ, contact, legal pages. These work with a phone link as the only action. This is a complete and honest product for a tradesperson who takes work by phone and word of mouth.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Projects | section hidden; never filled with stock photos | broken image hidden | Each project shows its area and job type |
| Price range | "Price after a visit", never an empty field | n/a | Shows the date it was last updated |
| Reviews | section hidden | | Never filled with placeholders |
| FAQ | unanswered questions hidden | | |
| Areas | cannot be empty (mandatory fact) | | |
| Hours | cannot be empty (mandatory fact 5) | | "Answering now / back at 07:30" needs the time zone |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Enquiry form | stores the enquiry and photos; alerts the business | n/a | upload progress per photo; button shows "sending" and cannot be pressed twice | "Not sent - please call", with the number; typed text kept | visitor sees "received" and when to expect a call back | visitor writes; only the business reads |
| Out-of-area check | the area list | | | | out-of-area visitor is told plainly, and may still leave details if the business wants | |
| Visit or consultation booking | available slots, length, in person or video | "No free times this week - call us or see next week" (reference 5 links a full calendar) | placeholder slots, never an empty calendar that looks fully booked | "Could not load times - call us" | status "requested" until the business confirms, unless the business chose instant booking | visitor sees only their own booking |
| Leads inbox | enquiries with status | "No new enquiries" | | never show a stale list without saying so | status changes saved at once, with who changed them | owner and named staff, behind a login |
| Quote viewer | a quote document per client | | | link expired: show the phone | client can accept; acceptance recorded with date and time | only the client with the link, and the business |
| Client project page | job stages, photos, documents, payments | "Nothing to show yet - work starts on [date]" | | | | only that client and the business |
| Owner edits projects and content | an edit screen with photo upload | | upload progress | a failed save says so and keeps what was typed | visible on the public site right after saving | owner only |
| Reviews request | a sending channel and the client's consent | | | a failed send is shown to the owner | | sent only after a finished job |

### Needs accounts

- The owner always needs one, as soon as anything is editable or any enquiry is stored.
- Staff need them only if several people handle enquiries or jobs.
- Clients should not need an account to enquire or book a visit. A client link (no password) is enough for viewing a quote or a project page.

### Needs payments

- Deposits, stage payments, paying an invoice online (reference 7 shows "Make a Payment"), a paid first consultation (reference 6 describes a paid first step with a satisfaction guarantee).
- Each brings refunds, receipts, failed-payment states, and the cancellation law for contracts made at home.
- Default: no payments. Added only when the customer asks and has stated the terms (mandatory fact 14).

### Using an existing system

Firms with a design team often already use project-management or quoting software, and some link to an external calendar for consultations. In that case the product is a content site whose actions are those links. Ask before building a second leads inbox. The failure mode is the link breaking silently (see section 5).

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos, icons and badges. Character counts are approximate, after removing link targets. Only home pages were fetched.

**Curation.** Three small UK workshops (references 1 to 3) were found through a web search for independent joiners and then read in full; the four larger firms were chosen by the author as known renovation and kitchen businesses with their own sites. Every one was kept only if the page loaded and read as the business's own site. No awwwards.com category was consulted; none is claimed as an award winner. All seven are in English, in Latin script.

**Limit.** All seven are in the UK or the US, and all are in the wood, kitchen and building trades. No plumber, electrician, painter, roofer or handyman site was verified. Four are large design-build or kitchen firms that are well above the typical customer. The skeletons cover the joinery and building end of the domain best.

Verified: 7.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.mcmulleninteriors.co.uk | 2026-11-22 | Small family carpentry and joinery business, East London. Phone and email at the very top, "for a quote". Order: a photo strip - headline naming the trade and the area - two paragraphs (small local business, decades of experience, own workshop) - five service cards - one section per core service (alcove units, wardrobes, TV units, shelving), each with two short points and a link to a finished job named by district - materials - "What to expect" in three steps (advice and quotation, where an initial estimate can come from dimensions, a photo or a sketch; design and construction in the workshop; finishing and install) - gallery links - contact - testimonials heading. No prices. Extraction: 26 images, about 7,000 characters. |
| 2 | https://www.ollieshandmadekitchen.co.uk | 2026-11-22 | One-person kitchen maker, West Sussex and London. Header: two phone numbers, email, area line, "Finance available", "Free design visit". Order: photo strip - headline - four proof points (hand made, a two-year guarantee with a stated insurance amount, materials, painted on site) - the maker's story in the first person plural - materials - joints - six kitchen styles - five photos of recent work - process: four of seven steps (first visit, measure, drawing and itemised fixed quote, choosing details) - four testimonials, three attributed only as "Homeowner" with a town or postcode district - areas served - FAQ that states a typical price range for complete kitchens, workshop and site durations, areas, reusing existing units, and the guarantee - free design visit call to action - footer with hours (Mon-Fri, Sat) and a long list of towns, many with their own page. Extraction: 22 images, about 11,000 characters. |
| 3 | https://www.benjworkshop.com | 2026-11-22 | Joinery company with a workshop in East London, working for architects, designers, contractors and private clients. Order: one paragraph saying who they serve - six kinds of work (kitchens, wardrobes, bathrooms, offices, internal doors, storage) - "Very happy clients" paragraph - three testimonials attributed to named firms - "How we work" in five steps (brief; a detailed quote that stays fixed unless the brief changes; a drawing pack and a laser survey; making in the workshop; delivery and install to the agreed schedule). Extraction: 14 images, about 3,600 characters. |
| 4 | https://www.plainenglishdesign.co.uk | 2026-11-22 | English kitchen and cabinetry maker with showrooms in three cities. Header: "View Brochure", "Make an Enquiry". Order: founding line - city names - a row of eleven room types (kitchens, pantries, mudrooms ... home offices) - six image tiles, each a heading and one sentence (kitchens, how we work, other rooms, two showrooms, colour collections) - enquiry form with a required-field marker. Image-led, very little text. Extraction: 47 images, about 1,900 characters. |
| 5 | https://www.buildteam.com | 2026-11-22 | London house-extension firm. Header: phone, "Book Free Consultation", "Instant Quote". Order: headline with start year, a project count and a review score with its source - "What do you want to build?" with eight job types - book a free 30-minute consultation by picking a day (about the house, the budget and what the council is likely to allow), with a link to the full calendar - one client quote - "Featured in" - case studies with downloadable files - a credentials block from a home-design platform - six client quotes - "Find a finished project like yours": cards named by street and job type - open houses (walk round a finished extension in person) - 3D tours - newsletter - cookie notice with accept or reject. Extraction: 33 images, about 3,700 characters. |
| 6 | https://www.casedesign.com | 2026-11-22 | Design-build remodeler, Washington DC region. Order: headline - years in business and region - one testimonial with a first name and initial - a named paid first step described with a satisfaction guarantee - four neighbourhood design studios - "Our Work" by six project types - articles including remodelling costs and financing - "Schedule a conversation". Extraction: 28 images, about 1,700 characters. |
| 7 | https://www.normandyremodeling.com | 2026-11-22 | Design-build remodeler, Chicago area. Navigation includes "Make a Payment" for existing clients. Order: appointment request with the phone number and a form (project type; "how did you hear about us" with about seventeen options) - headline with start year - the process in one paragraph (designer, product selections, blueprints, permits, a site superintendent, final inspection) - seminars before starting - two design studios - meet the designers - neighbours' testimonials - projects near you - newsletter - footer with two studio addresses and phones. Extraction: 9 images, about 3,300 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.bowa.com | 2026-11-22 | Loads and is the firm's own site. The extraction was mostly a repeated slide headline and project-type labels (about 1,500 characters); its structure adds nothing beyond references 6 and 7. |
| https://www.sebastiancox.co.uk | 2026-11-22 | Loads, but the extraction contains leftover site-builder text telling the site editor that the newsletter form needs a storage option, and the business sells furniture, closer to `catalogue-collection.md`. |

Tried and did not load: none. Every candidate fetched loaded.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the local tradesperson (call-first)

For a one-person business or a small workshop that gets work by phone and visits. Default for this domain.
From references 1, 2 and 3; the contact strip from 1 and 2, the per-service sections with district-named jobs from 1, the steps from 1 and 3, the FAQ and area list from 2.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Contact strip and header | phone (tappable), area in a few words, the first step ("free visit" only if free) | the phone is the most prominent element after the name | yes |
| 1 | Opening | one sentence: the trade, the kind of jobs, the area; the main action | one heading, one line, one action; a photo of real work if there is one | yes |
| 2 | Jobs we do | each job type: name, one or two sentences, a link to a finished example | card or short section per job type | yes |
| 3 | Finished work | photos of real jobs, each named by district and job type | images first, short captions | optional, hidden when empty |
| 4 | How it works | three to five steps from first call to handover, in the customer's words | numbered, one line each | yes |
| 5 | Why trust us | guarantee, insurance, registration number, years - only stated facts | short list | optional, hidden when empty |
| 6 | What clients say | real reviews with area and source | at most three | optional, hidden when empty |
| 7 | Questions | price range or "price after a visit", duration, area, guarantee | short answers | optional; unanswered questions hidden |
| 8 | Where we work | the area as named places | list | yes |
| 9 | Final action | the main action again, with hours | one line, one button | yes |
| 10 | Footer | name, phone, hours, area; registration where required; privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1 to 3 returned 14 to 26 images against about 3,600 to 11,000 characters). Text-led with a photo per section: roughly one real photograph for every two text blocks. The visitor reads to decide trust and checks the photos for proof. Not confirmed in a rendered view.

### Skeleton B: the design-and-build firm (consultation-first)

For a firm with designers, a showroom or studios, selling larger projects through a first consultation.
From references 4 to 7; the job-type chooser and day picker from 5, the paid or free first step from 6, the process paragraph and payment link from 7, the room list and enquiry form from 4.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | phone; "book a consultation"; a link for existing clients (pay, project page) if the firm has one | consultation is the main action | yes |
| 1 | Opening | headline; years, region, and a review score with source - only stated facts | heading, one line, one action | yes |
| 2 | What do you want to do? | project types as tiles (kitchen, extension, bathroom, whole house) | tile per type, each leading to its page | yes |
| 3 | First step | what the consultation is, how long, free or paid, what you get; book by choosing a day | short text and a day picker or the phone | yes |
| 4 | Projects like yours | finished projects by type and area, with photos | image-led cards | yes |
| 5 | Process | the stages from design to final inspection, who does what | numbered steps or one paragraph | yes |
| 6 | Proof | reviews with source; press; credentials | one strong item first | optional |
| 7 | Studios or showroom | addresses, hours, visit by appointment | complete without a map | optional |
| 8 | Learn before you start | articles on costs and permits; seminars or open houses | links | optional |
| 9 | Footer | addresses, phones, licence or registration, privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**. Image-led: references 4 and 5 returned 47 and 33 images against about 1,900 and 3,700 characters. Photos of finished rooms carry the page; text names the project type and the next step. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working tradesperson. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source. This includes the Israeli contractor-registration threshold, the UK 14-day off-premises rule, Gas Safe, Part P, the Party Wall Act, the 2024 fake-reviews ban, US licence-number advertising rules, the EPA lead rule and the FTC cooling-off rule.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. No plumber, electrician, painter, roofer, tiler or handyman reference was verified. All references are in the UK or the US.
6. Sub-pages (service pages, project pages, booking calendars, quote and payment links) were not fetched. Whether the "Make a Payment" and calendar links lead to the firm's own system or to a third party was not followed.
7. The claim that many firms already use project-management or quoting software is the author's belief, not observed.
8. References were checked on 2026-11-22, one day after the date given in the brief (2026-11-21), because that is when they were loaded.
9. Price ranges, guarantee terms, insurance amounts, review scores and project counts mentioned in the reference notes are what the pages stated on the day; they were not checked against any other source.
10. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
