# Event

Covers: a gathering that happens on a known date at a known place (or online): a conference, festival, concert, workshop day, meetup, gala, fair. One-off or repeated each year (editions).
Does not cover: a wedding (use `wedding.md`); a regular community programme with members (use `community.md`); a fundraising gala as part of a charity's site (use `nonprofit.md`, with this file for the gala page); guided tours (use `tour-guide.md`).
Written 2026-11-22. References checked 2026-11-22 (the brief named 2026-11-21; the fetches ran on 2026-11-22). Template: [README.md](README.md).

## 1. Objects

An event sells **a place in a room on a date that will not come again**. Before the date, everything is a promise (who will speak, what it costs, where to go); on the date, the site becomes a tool people read on a phone at the door; after the date, it becomes an archive and a reason to come next time. The same objects change meaning across those three phases.

### Event (the series or the brand)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Harbour Design Day" |
| What it is | required | one sentence: "a one-day conference for product designers" |
| Who it is for | required | "designers and front-end developers"; "families"; "18+" |
| Organiser (legal name) | required | the person or company responsible |
| Contact email | required | |
| Phone | optional | many events have none; an email must then be answered |
| Social accounts | optional | |
| Code of conduct | optional, strongly advised for gatherings of strangers | |
| Past editions | optional | archive with talks, photos |

### Edition (one occurrence)

| Field | Required | Example |
|---|---|---|
| Event | required | |
| Start date and time | required | 3 June 2027, doors 08:30 |
| End date and time | required | 4 June 2027, 18:00 |
| Time zone | required | Europe/Amsterdam |
| Format | required | in person, online, both |
| Venue | required for in person | name and address |
| Status | required | announced, tickets on sale, sold out, postponed, cancelled, happened |
| Capacity | optional, required for ticket sales | 400 |
| Edition number | optional | "our 13th edition" |

### Venue

| Field | Required | Example |
|---|---|---|
| Name | required | |
| Address | required | street, city, country, map link |
| How to get there | optional, strongly advised | public transport, parking, nearest station |
| Accessibility | optional, strongly advised | step-free entrance, hearing loop, quiet room, accessible toilets; "not step-free" is a valid answer |
| Rooms or stages | optional | "Main stage", "Room B" |
| Nearby accommodation | optional | |

### Session (schedule item)

| Field | Required | Example |
|---|---|---|
| Title | required | |
| Start and end time | required once the schedule is published | 10:00-10:40 |
| Room or stage | optional, required when more than one | |
| Type | optional | talk, workshop, keynote, panel, set, break |
| Speakers or performers | optional | linked |
| Short description | optional | |
| Needs separate ticket | optional | workshops often do |
| Recording available after | optional | |

### Speaker or performer

| Field | Required | Example |
|---|---|---|
| Display name | required | as the person wants it shown |
| Role or affiliation | optional | |
| Photo | optional, only with the person's consent | |
| Short bio | optional, provided or approved by the person | |
| Confirmed | required | only confirmed people are shown |

### Ticket type

| Field | Required | Example |
|---|---|---|
| Name | required | early bird, regular, student, workshop, day pass, full pass |
| Price | required | 299 |
| Currency | required | EUR |
| Taxes and fees included or added | required | "includes VAT; booking fee 2.50 added" |
| What it gives access to | required | "both conference days, not workshops" |
| Sale period | optional | until 31 March |
| Quantity available | optional | 100 |
| Who may buy it | optional | "students with a valid card" |
| Transferable, refundable | required when sold | "name change allowed until 7 days before; no refunds" |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Order | buyer, tickets, attendee names if required, payment status, ticket codes | Only when the product sells tickets |
| Attendee | name, email, ticket type, check-in status, dietary or access needs | Only what the event needs |
| Sponsor or partner | name, logo, level, link | Shown only with the sponsor's agreement |
| FAQ | question, answer | Practical answers: age, bags, food, refunds, recording |
| News or announcement | title, date, text | Lineup announcements, changes |
| Waitlist entry | email, ticket type, date | For sold-out editions |
| Call for speakers | deadline, topics, how to apply | Optional |
| Volunteer or scholarship | how to apply | Optional; seen in one reference |

## 2. Rules

1. Every edition has a start, an end and a time zone. Dates are shown with the weekday and the year.
2. An in-person edition has a venue with a full address. "Venue to be announced" is allowed, and is shown as exactly that.
3. A speaker or performer is shown only when confirmed. "More to be announced" is honest; an unconfirmed name is not.
4. A ticket price is shown with its currency and with whether taxes and fees are included. Mandatory fees are part of the price shown first, or shown next to it before the visitor chooses (see Legal).
5. A ticket says what it gives access to. A workshop that needs a separate ticket is marked as such in the schedule.
6. Tickets cannot be sold beyond capacity. Remaining tickets are computed from paid orders, not typed by hand.
7. "Sold out" is shown when no tickets remain, and the buy button is replaced by a waitlist or a clear "sold out".
8. A countdown or "price rises soon" claim must be true: the date it counts to is the real end of that price.
9. Refund and transfer terms are shown before payment, not only in the confirmation.
10. If an edition is postponed or cancelled, the status changes on every page that shows the date, ticket holders are told, and what happens to their money is stated.
11. Schedule times are in the event's local time zone. Online events also show times in at least one other named zone or let the visitor convert.
12. After the end date, the site no longer offers tickets for that edition. It either points to the next edition or says the event has happened.
13. Photos of attendees are published only under a stated photography policy, and people can ask to be removed. Children need a parent's consent.
14. Age limits, if any, are stated before purchase.
15. Accessibility information about the venue is published, or the site says "ask us about access" with a contact. It never says "fully accessible" unless the customer stated it.
16. A sponsor logo appears only for a real, current sponsor.
17. A quote from a past attendee or speaker is shown only if real and attributed.
18. The main action (tickets, register) is reachable from every page without scrolling back up on a phone, until the edition is sold out or over.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the event called?" | People share a name. |
| 2 | What and for whom | "In one sentence: what happens there, and who should come?" | A visitor decides in seconds whether it is for them. |
| 3 | When | "Which date or dates, from what time to what time?" | Without a date nobody can come. |
| 4 | Where | "Where is it: venue name and full address, or online?" | Without a place nobody can arrive. |
| 5 | How to attend | "How do people get in: buy a ticket, register for free, or just show up?" | The whole page leads to this action. |
| 6 | Price, or free | "What does it cost? Are taxes and fees included? Are there different ticket types?" | Price decides whether people come; hidden fees make them angry. |
| 7 | Organiser | "Who is organising it, legally, and which email answers questions?" | People need someone responsible, and legal pages must name them. |
| 8 | Programme status | "Who is confirmed to speak or perform so far? If no one yet, should we say 'to be announced'?" | Naming someone who is not coming is a broken promise. |

Needed only when the product sells tickets or takes registrations:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 9 | Capacity | "How many people can attend in total, and per ticket type?" | Without it you sell more seats than the room holds. |
| 10 | Refunds and transfers | "Can people get money back or give their ticket to someone else? Until when?" | Must be shown before payment. |
| 11 | What you need from attendees | "What do you need to know about each attendee: only name and email, or also diet, access needs, company?" | Asking for more than needed is a privacy risk; asking for less leaves you without lunch numbers. |
| 12 | Where orders go | "Where should each order or registration reach you?" | An order nobody sees is a person with a ticket the door does not know about. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the event.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Main action label | "Get tickets" (paid) or "Register" (free) | Follows from fact 5 | Labelled "default" |
| Unconfirmed programme | "Programme to be announced" | Honest; seen in one reference ("far from complete yet") | Shown to the customer as "no speakers listed" |
| Schedule display | by day, then by time, then by room | Standard structure | "Suggested layout" |
| Time format | the format of the event's country | Follows from the place | Changeable |
| Second time zone for online events | none until the customer names the audience | A wrong second zone is worse than none | Asked |
| FAQ headings | getting there, access, food, tickets and refunds, photography, code of conduct | Structure only; answers are facts | Each answer left empty until given; empty items hidden |
| Code of conduct | structure of headings only | Content is the organiser's commitment | "Draft - the organiser must write and enforce it" |
| After-event state | "This event has happened" with a link to the next edition or to the newsletter | Prevents selling dead tickets (rule 12) | Automatic on the end date, shown to the customer at setup |
| Waitlist when sold out | on, collecting email only | Least data, honest | Setting, labelled "default" |
| Legal page structure | headings only | Structure is general | "Draft - not legal advice" |
| Empty optional sections | hidden | An empty speaker grid looks like a cancelled event | Listed as "not shown yet" |

Never a default, whatever the customer left out: dates, times, venue, address, prices, fees, capacity, speakers, performers, sponsors, attendee numbers ("1,000+ attendees"), past-edition statistics, press quotes, refund terms, age limits, accessibility claims, "sold out", "selling fast".

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Wrong date or year | Books travel for the wrong day | Anger, refund demands | Rule 1; customer confirms the date read back with weekday |
| Time zone missing on an online event | Joins an hour late | Misses the talk | Rule 11 |
| Unconfirmed speaker shown | Buys a ticket to see someone who is not there | Refunds, reputation | Rule 3 |
| Fees appear only at checkout | Price jumps at the last step | Abandoned orders; legal risk | Rule 4 |
| Oversold | More people than seats at the door | Turned-away ticket holders | Rule 6 enforced when the order is saved |
| Order saved, organiser not told, ticket code not valid at the door | Stopped at the door with a ticket | The worst case in this domain | Mandatory fact 12; check-in reads the same order store |
| Postponement not shown everywhere | Arrives on the old date | Wasted trip | Rule 10; one date field used everywhere |
| Tickets still on sale after the event | Buys a ticket to the past | Refund, looks abandoned | Rule 12 |
| Schedule changed, old version cached or printed | Goes to the wrong room | Missed session | "Schedule last updated" time on the schedule |
| Venue access not stated | Wheelchair user meets stairs | Exclusion, complaint | Rule 15 |
| Countdown that resets | Notices the "last chance" never ends | Distrust; misleading-pricing risk | Rule 8 |
| Photos published of someone who opted out | Sees their own face | Complaint; privacy problem | Rule 13 |
| No phone or answered email on the day | Cannot ask where the entrance is | Late, frustrated | Day-of contact in the confirmation |
| Sponsor logo of a past sponsor | Sponsor complains | Lost relationship | Rule 16; sponsors per edition |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with event professionals in either language. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Event | the gathering | אירוע | فعالية / حدث |
| Conference | talks for professionals | כנס | مؤتمر |
| Festival | many performances, often several days | פסטיבל | مهرجان |
| Workshop | hands-on session | סדנה | ورشة عمل |
| Meetup | small informal gathering | מפגש / מיטאפ | لقاء |
| Edition | one year's occurrence | מהדורה (not verified as common usage for events) | دورة (not verified) |
| Venue | the place | מקום האירוע / אולם | مكان الفعالية |
| Lineup | who performs or speaks | ליין-אפ / מרצים | قائمة المشاركين (not verified) |
| Speaker | person giving a talk | מרצה / דובר | متحدث |
| Keynote | the main talk | הרצאה מרכזית / הרצאת מליאה | الكلمة الرئيسية (not verified) |
| Schedule, programme, agenda | what happens when | לוח זמנים / תוכנית | جدول الأعمال / البرنامج |
| Ticket | right to enter | כרטיס | تذكرة |
| Early bird | cheaper ticket for early buyers | כרטיס מוקדם / ארלי בירד | not verified |
| Badge, pass | entry pass, often for conferences | תג / כרטיס כניסה | بطاقة دخول (not verified) |
| Sold out | no tickets left | אזל / סולד אאוט | نفدت التذاكر |
| Waitlist | list for freed tickets | רשימת המתנה | قائمة الانتظار |
| Registration | signing up (often free) | הרשמה | تسجيل |
| Check-in | entry at the door | צ'ק-אין / כניסה | تسجيل الحضور (not verified) |
| Code of conduct | behaviour rules | קוד התנהגות | مدونة السلوك (not verified) |
| Sponsor | company paying for visibility | נותן חסות | راعٍ |
| Call for speakers, call for papers | invitation to submit talks | קול קורא להרצאות (not verified) | not verified |

Notes on language:

- Conferences say "badge" or "pass"; concerts and festivals say "ticket" or "wristband". Use the customer's word.
- "Convince your boss" is a recognisable section in professional conferences (seen in two references): a document an employee shows to get the ticket paid. Offer it only for professional events.
- Words to avoid unless the customer can back them: "world's best", "largest", "unmissable", "selling fast", "limited tickets", "1,000+ attendees".

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file.

### Applies almost everywhere

- **Privacy notice** for registrations and ticket orders. Attendee lists shared with sponsors need a clear basis and, in many places, consent.
- **Health data**: dietary and access needs may count as health data. Collect only if the event uses it.
- **Photography and recording**: a stated policy, a way to opt out, and care with children.
- **Terms of sale**: refunds, transfers, postponement and cancellation, age limits, entry conditions.
- **Code of conduct**: not a legal requirement in most places as far as the author knows; a safety and trust practice. Not verified.
- **Venue safety and capacity**: set by the venue and local authorities, not by the website. The site must not promise capacity the venue does not have.

### Israel

- Public events may need a business licence or police approval depending on size and type. Not verified.
- Website accessibility: an accessibility statement is required for businesses serving the public under the Equal Rights for Persons with Disabilities Law regulations, with exemptions by size. Thresholds: not verified. Accessibility of the event venue itself is also regulated. Not verified.
- Consumer prices displayed must include VAT. Whether added booking fees are allowed and how they must be shown: not verified.
- Cancellation of tickets bought at a distance: the Consumer Protection Law has rules, with exceptions for leisure services on a set date believed to exist. Not verified.

### European Union and United Kingdom

- GDPR (EU) and UK GDPR apply to registration and ticket data; non-essential cookies need consent.
- The Consumer Rights Directive is believed to exclude leisure services on a specific date from the 14-day withdrawal right. Believed; not verified against the text for this file.
- UK: the Digital Markets, Competition and Consumers Act 2024 is believed to ban "drip pricing" (mandatory fees revealed late) from 2025. Not verified.
- EU: price indication rules require the total price including taxes. How booking fees must be shown: not verified.
- Ticket resale rules (caps, disclosure) exist in several countries. Not verified per country.
- European Accessibility Act: whether ticket sales by a small organiser are in scope: not verified.

### United States

- The FTC rule on unfair or deceptive fees is believed to require all-in pricing for live-event tickets from 2025. Not verified.
- State ticketing laws differ (refunds, resale, fee disclosure). Not verified.
- ADA applies to venues; courts have applied it to websites in many cases. Not verified.

### What the product does with this

- The product generates the **structure** of privacy, terms, photography and code-of-conduct pages, marked as drafts.
- The product never states that the event or site "complies with" a named law, and never writes an accessibility claim about the venue.
- The product asks in which country the event takes place before generating any legal page.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, about, programme or lineup, schedule, venue and travel, accessibility, FAQ, code of conduct, sponsors, past editions, contact, legal pages. With a link to an external ticket shop or "free entry, no registration", this is a complete product. One reference publishes its event almost entirely as a short page with dates, venue, format and two links (accessibility statement, code of conduct).

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Lineup | "Programme to be announced" | broken photo hidden | Never placeholder faces |
| Schedule | "Schedule coming soon - doors open at [time]" | | Shows "last updated" |
| Sponsors | section hidden | | |
| Past editions | section hidden for a first edition | | |
| Venue map | address text always shown | text and link remain if the map fails | |
| Countdown | hidden if no real deadline | | Rule 8 |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Free registration | stores name, email, needs; capacity | "Registration opens on [date]" or "Registration is full - join the waitlist" | button shows "registering" and cannot be pressed twice | "Not registered - please try again or email us" | confirmation with date, time, place, add-to-calendar | visitor: own registration; organiser: list |
| Ticket sale | ticket types, capacity, orders, payment | sold out: waitlist | "checking availability" | "That ticket type just sold out - here are the others" | paid only after the payment provider confirms; ticket with code sent | buyer: own order; organiser: all orders |
| Waitlist | email, ticket type | | | | "You are on the list - we will email you if a place opens" | organiser only |
| Check-in at the door | order store, ticket codes | "No attendee with this code" | | offline at the venue: must still work or have a printed fallback | marks checked-in with time | door staff, behind a login |
| Schedule editing | sessions, rooms, speakers | | | failed save keeps what was typed | live on save; "last updated" set | organiser only |
| Attendee messages | list of ticket holders, sending channel | | | failed sends listed | | organiser only; attendees can unsubscribe from non-essential messages |
| Personal agenda | attendee picks sessions | "No sessions picked yet" | | | saved per device or per account | the attendee only |

### Needs accounts

- The organiser always, as soon as anything is stored.
- Door staff for check-in.
- Attendees do not need an account to buy or register; the ticket link is enough. An account is justified only for a personal agenda across devices or multi-event passes (one reference has login, cart and purchase history).

### Needs payments

- Ticket sales, add-ons (workshops), merchandise.
- Each brings refunds, partial refunds for postponements, receipts with tax, failed payments, and chargebacks.
- Default: no payments in the product. Free registration, or a link to the organiser's existing ticket shop, until the customer states capacity and refund terms (facts 9 and 10).

### Using an existing ticket shop

Many events sell through an external ticketing system (reference 6 links "tickets" to a separate shop domain; reference 4 to a cart on its own subdomain). Then the product is a content site whose action is that link. The failure mode is the link pointing at a closed or past sale.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality and the image-to-text ratio are **not** observed, and every ratio is an estimate from counts in the extracted text. Image counts include logos and icons. Some extractions return only part of a page.

**Curation.** Chosen by the author from known design, technology and arts events in Europe and the US, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner. All are in English, in Latin script.

**Limit.** All six are professional conferences or large festivals. No small local event (a market, a gig in a bar, a one-evening meetup) was verified. The skeletons are a ceiling for structure.

Verified: 6.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://smashingconf.com/freiburg-2027 | 2026-11-22 | One edition page of a recurring front-end conference. Content: edition number and audience - a short list: dates, venue name and city, "in-person + online", 2 days, 10 speakers plus 6 workshops, a "safe, inclusive" statement, social programme - "convince your boss" PDF and letter - links to an accessibility statement and a code of conduct. The site footer (fetched via the home page) lists code of conduct, contact, accessibility statement, scholarship and volunteering, about, terms. Extraction: 18 images, under 1,000 characters for the edition text. |
| 2 | https://cssday.nl | 2026-11-22 | Single annual conference. Order: one paragraph saying what it is and for whom - dates and edition number - a ticket note - newsletter for early-bird tickets - the previous edition's archive (videos, photos) - "our 2027 line-up" stated openly as far from complete. Shows an honest pre-announcement state. Extraction: 14 images, under 1,000 characters. |
| 3 | https://beyondtellerrand.com | 2026-11-22 | Conference series in several cities. Order: next edition (date, city, "buy tickets") at the very top - headline - one paragraph - a past attendee's quote with name - upcoming events, each with date, city, "buy tickets", "view event" - past speakers with portraits - themes - photos from past events - talks archive - newsletter - partners with logos. Extraction: 24 images; character count not measured. |
| 4 | https://www.sxsw.com | 2026-11-22 | Large multi-strand festival and conference. Order: dates and city repeated in a top bar - "badges on sale" with a countdown to a price increase - schedule, login, cart - history photos with years - four strands (innovation, film and TV, music, comedy) each with "dive in" and "buy badge" - tracks - numbers - "convince your boss" - badge tiers with price and a list of what each includes - past partners - news. Extraction: 17 images; character count not measured. |
| 5 | https://websummit.com | 2026-11-22 | Large technology conference. Order: offer link - past speakers with roles - logo walls by group (companies, startups, media, investors), each with a call to action (exhibit, apply for media accreditation) - dates and city with "secure tickets" - attendee quotes with names and roles - press quotes with the publication - newsletter. Logo-heavy. Extraction: about 85 images; character count not measured. |
| 6 | https://www.offf.barcelona | 2026-11-22 | Design festival. Navigation: get tickets, lineup, about, contact, press room, sponsors, schedule, masterclasses, workshops, keynotes. Order: venue and dates - numbered lineup with country per artist - "all artists" - about in two sentences - programme types - other cities with their dates or "to be announced" - news - sponsors, partners and media partners by group. Extraction: 1 image returned (site-builder page); character count not measured. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.lollapalooza.com | 2026-11-22 | Loads, but between editions the home page is a merchandise drop and a newsletter prompt; no event structure to extract. |
| https://www.glastonburyfestivals.co.uk | 2026-11-22 | Loads, but the extracted home page is a news list and settings. Worth noting for later: it offers colour modes (greyscale, high contrast) and British Sign Language video versions of sections. |
| https://www.kikk.be | 2026-11-22 | Did not load (fetch failed). Replaced. |
| https://www.primaverasound.com | 2026-11-22 | Did not load (fetch failed). Replaced. |

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the single event (one edition)

For one event on one date, or a small annual event. Default for this domain.
From references 1, 2 and 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; date and city; one action (tickets / register) that stays reachable on a phone | date and action are the most prominent after the name | yes |
| 1 | Opening | one sentence: what it is and for whom; date with weekday; place; format | one heading, one line, one action | yes |
| 2 | Key facts | short list: dates, venue, format, number of days or sessions, price from | list, plain words | yes |
| 3 | Programme | confirmed speakers or performers, or "to be announced" | grid or list; never placeholders | yes (may say "to be announced") |
| 4 | Schedule | by day, time, room | table | optional until published |
| 5 | Tickets | each type: price, what it includes, fees, refund terms | one row or card per type | yes if paid |
| 6 | Venue and travel | address, map link, transport, accessibility | must be complete without the map | yes for in person |
| 7 | FAQ | practical answers | short | optional |
| 8 | Past editions | photos, talks, a real quote | | optional, hidden for a first edition |
| 9 | Code of conduct and accessibility | links or short text | | strongly advised |
| 10 | Newsletter | email for next announcements | | optional |
| 11 | Footer | organiser, contact, privacy, terms, accessibility statement, sponsors | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1 and 2 returned 14 to 18 images against under 1,000 characters of edition text; reference 3 returned 24 images against a long text page). Speaker portraits and past-edition photos carry most images; the facts are text. Not confirmed in a rendered view.

### Skeleton B: the large event (many strands, many ticket types)

For a festival or conference with several stages, strands, ticket tiers or cities.
From references 4, 5 and 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Top bar | dates, city, ticket action, login and cart if accounts exist | always visible | yes |
| 1 | Opening | identity line; dates; main action | | yes |
| 2 | Strands or programme types | one block per strand with its own entry link and ticket link | equal blocks | yes |
| 3 | Lineup highlights | names with role or country, link to all | | yes when confirmed |
| 4 | Ticket tiers | price, what is included, sale deadline (real) | side by side | yes |
| 5 | Who comes | real numbers with source, attendee and company groups | | optional |
| 6 | Proof | attributed quotes, press with publication named | | optional |
| 7 | Other editions or cities | each with dates or "to be announced" | | optional |
| 8 | Partners | grouped by level, current edition only | | optional |
| 9 | News | dated | | optional |
| 10 | Footer | organiser, contact, legal pages | | yes |

Image-to-text ratio: **estimate**. Image-heavy: reference 5 returned about 85 images, mostly logos and portraits. Not confirmed in a rendered view.

Risk seen in reference 4: a countdown to a price change is persuasive and must be true (rule 8). In reference 5 the logo walls come before the dates; for a small event the date must come first.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6.
2. Every legal statement in section 7, especially fee-display rules (UK, EU, US), event licensing in Israel, and withdrawal-right exceptions.
3. Image-to-text ratios and visual quality of all references: text extraction only.
4. No awwwards.com category was consulted.
5. No small local event was verified.
6. Ticket sub-pages, schedules and checkout flows of the references were not fetched; observations are of home or edition pages only.
7. That many events use an external ticket shop is inferred from one reference's link and general knowledge; the link targets were not followed. Character counts for references 3 to 6 were not measured.
8. That a code of conduct is not a legal requirement is the author's belief.
9. No references in Hebrew, Arabic or any non-Latin script.
