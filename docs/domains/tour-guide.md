# Tour guide

Covers: a person or small company that leads people on foot, by bike, boat or vehicle through a place and explains it: city walks, food tours, museum tours, day trips, private guiding.
Does not cover: multi-day packages that include accommodation and transport as the main product (closer to a travel agency; no domain file yet); a hotel that also runs tours (use `hotel-guesthouse.md`); a one-off festival or conference (use `event.md`).
Written 2026-11-22. References checked 2026-11-22 (the brief named 2026-11-21; the fetches ran on 2026-11-22). Template: [README.md](README.md).

## 1. Objects

A tour sells **a seat in a group that leaves from one spot at one time**. If the visitor is not at the meeting point when the group leaves, the seat is lost; if the guide is not there, the whole group is lost. Everything follows from that: a tour has a meeting point, a start time, a length and a group size, and a departure is one tour on one date.

### Guide or company (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Old Town Walks" |
| Where the tours happen | required | city or region, for example "Lisbon and day trips to Sintra" |
| Phone or messaging number | required | a number a lost visitor can call on the day |
| Email | required when booking is by email | |
| How to book | required | online, email, message, phone, "just turn up" |
| Languages the tours are given in | required | English, Spanish |
| Licence or qualification | optional, required where the law demands it (see Legal) | "licensed guide, number shown on request" |
| Short story, how long guiding | optional | "guiding since 2012" (only if the customer said it) |
| Social account | optional | |
| Office address | optional | many guides have none; the meeting point is the address that matters |

### Tour (the product)

| Field | Required | Example |
|---|---|---|
| Name | required | "Old Town and the Castle" |
| Type | required | walking, food, museum, bike, boat, day trip, private |
| What you will see or do | required | 3 to 6 stops in plain words |
| Length | required | 2 hours, 3.5 hours, full day |
| Meeting point | required | a place a stranger can find: name, address, a landmark, a map link |
| End point | optional, shown when it differs from the start | |
| Price per person | optional, see rule 3 | 25 |
| Price type | required when a price is shown | per adult, per child, per group (private), "pay what you wish", "from" |
| What is included | optional, required when food, tickets or transport are part of it | "6 tastings, wine at two stops, museum ticket" |
| What is not included | optional | "museum entry not included" |
| Group size, maximum | optional | 12 |
| Minimum to run | optional | "runs with 2 or more" |
| Language | required | per tour, or per departure if it varies |
| Walking distance and difficulty | optional, strongly advised | "about 3 km, two steep hills, not step-free" |
| Accessibility | optional | wheelchair, pushchair, step-free; "not suitable" is a valid answer |
| Age limits | optional | "children under 12 free", "18+ for wine" |
| Dietary options | required for food tours | vegetarian possible, gluten-free not possible |
| Weather policy | optional | "runs rain or shine" |
| Photos | optional | of the place and real groups (with consent) |
| Currently offered | required, default yes | |

### Departure (one tour on one date)

| Field | Required | Example |
|---|---|---|
| Tour | required | |
| Date and start time | required | Sat 10:30 |
| Seats left | required when booking is online | 4 |
| Status | required | scheduled, full, cancelled by guide, ran |
| Guide | optional | first name only |
| Language | required if not fixed by the tour | |

A recurring schedule ("every day at 10:30, March to November") generates departures. A closure or cancellation overrides it for one date.

### Booking (only when the product takes bookings)

| Field | Required | Example |
|---|---|---|
| Departure | required | |
| Number of adults, children | required | 2 adults, 1 child |
| Visitor name | required | |
| Visitor phone | required | to reach them on the day |
| Visitor email | optional, required for an emailed confirmation | |
| Dietary or access needs | optional | |
| Status | required | requested, confirmed, cancelled by visitor, cancelled by guide, no-show, attended |
| Paid, deposit, or pay on the day | required | |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Private tour request | dates, tour or theme, number of people, language, contact | Most small guides sell private tours by enquiry, not by a calendar |
| Review | text, first name or initials, date, source | Only real reviews with their source. The references show large review counts; a new guide has none, and none is invented |
| Policy | cancellation by visitor, cancellation by guide (weather, minimum not met), lateness, children, refunds | Shown before booking |
| Gift card | value or tour, expiry | Optional. Involves payments |
| Pre-trip guide or audio guide | title, place, price | Optional. A digital product; one reference sells these alongside tours |
| Partner stop | name of a restaurant, shop or site on the route | Optional. Naming one is a promise that it is still there |

## 2. Rules

1. Every tour has exactly one meeting point. A meeting point is described so a stranger can find it without the map: place name, street, a visible landmark.
2. A tour has a start time and a length. The end time is start plus length and is stated, so visitors can plan the rest of the day.
3. A price is optional, but its absence must be explicit: "price on request" or "pay what you wish", never a blank and never zero.
4. A price says what it is per: per adult, per child, per group. A "pay what you wish" tour says so plainly and does not show a fake price.
5. Every price shows its currency.
6. What is included is stated whenever money pays for more than the guiding (food, drinks, tickets, transport). If a ticket is not included, that is stated too.
7. A departure cannot be booked beyond its maximum group size. Seats left is computed from confirmed bookings, not typed by hand.
8. A departure cannot be booked in the past, and online booking closes a set time before the start (declared default).
9. If a tour needs a minimum number of people, the visitor is told before booking what happens if the minimum is not reached (moved, refunded).
10. If the guide cancels a departure, every booked visitor is told by a channel they gave, and the departure shows "cancelled" on the site.
11. A weather policy, if one exists, is shown before booking.
12. Walking distance, hills and steps are stated for walking tours, or the tour says "ask us about access". It never says "suitable for everyone" unless the customer stated it.
13. Food tours state what dietary needs can and cannot be handled. "Allergies can be catered for" is a claim only the customer may make.
14. Alcohol on a tour carries the legal age of the country; the age limit is stated.
15. Tours given in more than one language show the language per tour or per departure. A visitor never books a tour in a language that is not offered on that date.
16. A licence number, if the customer has one and the law requires it, is displayed where the law requires it.
17. A review is shown only if it is real, and it carries its source. A rating is never shown without its count and source.
18. Photos of recognisable people on tours are published only with consent.
19. The phone number for the day of the tour is reachable from the booking confirmation and from every page on a phone.
20. Times are in the local time of the tour, and the time zone is stated on confirmations sent to visitors who booked from abroad.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is your tour business called, or should it carry your own name?" | People recommend a name, not a description. |
| 2 | Where | "In which city or area do your tours happen?" | A visitor searches by place first. |
| 3 | Tours | "Which tours do you give? Describe each one as you would to a visitor." | Without the list there is nothing to choose. |
| 4 | Meeting point per tour | "Where exactly does each tour start? How would a stranger recognise the spot?" | A visitor who cannot find the start misses the whole tour. |
| 5 | Start times and days | "On which days and at what time does each tour leave? Is it all year?" | Without times people arrive at an empty square. |
| 6 | Length | "How long does each tour take, and where does it end?" | People plan lunch, trains and flights around it. |
| 7 | Price, or the decision not to show it | "What does each tour cost per person, and what does that include? If it is pay-what-you-wish, say so." | Price is the second question after "when". Hiding it is allowed; inventing it is not. |
| 8 | Languages | "In which languages do you guide?" | A visitor who books the wrong language has a wasted morning. |
| 9 | Contact for the day | "What number should a visitor call if they are late or lost on the day?" | On tour day, a phone that answers is the whole service. |
| 10 | How to book | "How do people book today: online, by email, by message, or do they just turn up?" | The site leads to this one action. |
| 11 | Who is the business legally | "What is the registered business name and number, for the legal pages? Do you hold a guide licence?" | Legal pages must name who is responsible; some places require a licence to guide. |

Needed only when the product takes online bookings:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 12 | Maximum group size | "What is the most people you take on one tour?" | Without it the tour is oversold. |
| 13 | Cancellation and weather | "What happens if a visitor cancels, if it rains, or if not enough people book?" | The visitor must know before paying, and you must be able to stand behind it. |
| 14 | Where booking alerts go | "Where should each new booking reach you: which phone or email?" | A booking nobody sees is a family waiting at a fountain with no guide. |
| 15 | Payment | "Do people pay when booking, pay a deposit, or pay you on the day?" | Decides whether the product handles money at all. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Tour card fields and order | name, type, length, meeting area, price, language | Seen across the references | "Suggested layout" |
| Missing price | "Price on request" | Says openly there is no number | Listed for the customer as "no price given" |
| Main action | "Message to book", using the day-of-tour phone | Works with zero setup; one reference books only by email | Labelled "default: message" |
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Booking cut-off | 2 hours before start | Estimate; not taken from a source | Setting, labelled "default" |
| How far ahead to book | 90 days | Estimate | Setting, labelled "default" |
| Reminder | one message the evening before, with the meeting point | Estimate | Off until a sending channel exists |
| Weather wording | none | A weather policy is a fact; no default is safe | Asked, not filled |
| Language of the site | the language of the conversation, plus English if the tours are in English | Visitors to tours are often foreign | Shown, changeable |
| Currency | the currency of the tour's country | Follows from the place | Next to every price |
| Legal page structure | headings only: who we are, what we collect, why, how long, your rights, contact | Structure is general; content is not | "Draft - not legal advice" |
| Empty optional sections | hidden | Missing reviews are better than placeholder reviews | Listed as "not shown yet" |

Never a default, whatever the customer left out: meeting points, start times, tour length, prices, what is included, group size, languages, licence status, dietary handling, accessibility, weather policy, "small groups", "skip the line", "best tour", review counts, ratings, press mentions.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Meeting point vague ("by the cathedral") | Wanders, arrives after the group left | A lost booking and a bad review | Rule 1; ask "how would a stranger recognise the spot?" |
| Meeting point moved, site not updated | Waits at the old spot | Same, for a whole group | Meeting point stored once and reused; prompt the customer when a tour is edited |
| Wrong time zone on confirmation | Arrives an hour late or early | Missed tour | Rule 20 |
| Departure oversold | 20 people for a 12-person tour | Refunds, angry guide | Rule 7, enforced when saving the booking |
| Booking saved, guide never told | Arrives; no guide knows they exist | The worst case in this domain | Mandatory fact 14; "requested" until confirmed; test alert at setup |
| Cancelled for rain, visitor not told | Stands in the rain at the start | Distrust; demands refund | Rule 10; cancellation alerts every booked contact |
| Ticket "included" when it is not | Asked to pay at the museum door | Argument, refund | Rule 6 |
| Not step-free, not said | Wheelchair user cannot follow the route | Exclusion, complaint | Rule 12 |
| Allergy not handled on a food tour | Cannot eat, or worse, reacts | Health risk, liability | Rule 13; ask the customer what can and cannot be handled |
| Language not available that day | Tour given in a language they do not understand | Wasted day | Rule 15 |
| Old schedule (winter vs summer) | Books a time that no longer runs | Lost visitor | Seasons as date ranges; "schedule valid until" |
| "Pay what you wish" shown with a price | Thinks it costs money, or that it is free when it is not | Confusion at the end of the tour | Rule 4 |
| Fake or unsourced review count | Notices the number does not match anywhere | Distrust; legal risk | Rule 17 |
| Day-of phone missing from confirmation | Lost, with no one to call | Missed tour | Rule 19 |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working guide in either language. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Tour guide | the person leading | מדריך טיולים / מורה דרך | مرشد سياحي |
| Licensed guide | guide holding an official licence | מורה דרך מוסמך (not verified as the formal term) | مرشد سياحي مرخّص (not verified) |
| Tour | the guided trip | סיור | جولة |
| Walking tour | tour on foot | סיור רגלי | جولة سيرًا على الأقدام (not verified as common usage) |
| Food tour | tastings along a route | סיור קולינרי | جولة طعام (not verified) |
| Day trip | full day outside the city | טיול יום | رحلة يومية |
| Private tour | only one party | סיור פרטי | جولة خاصة |
| Group tour | shared with strangers | סיור קבוצתי | جولة جماعية |
| Meeting point | where the tour starts | נקודת מפגש | نقطة الالتقاء |
| Itinerary, route | the list of stops | מסלול | مسار / برنامج الرحلة |
| Departure | one tour on one date and time | יציאה (not verified in this sense) | not verified |
| Pay what you wish, free tour | visitor decides the tip | סיור בתשלום לפי בחירה / "סיור חינם" | not verified |
| Skip the line | pre-booked entry | ללא תור (not verified) | not verified |
| Audio guide | recorded commentary | מדריך קולי | دليل صوتي |
| Group size | maximum people | גודל קבוצה | حجم المجموعة |
| Tip, gratuity | money given to the guide | טיפ | بقشيش |
| Cancellation policy | rules for cancelling | מדיניות ביטולים | سياسة الإلغاء |
| Accessibility | who can join | נגישות | إمكانية الوصول |

Notes on language:

- "Free tour" in the trade means tip-based. One reference explains that most of its tours are now ticketed and only some remain pay-what-you-wish. Say exactly which it is.
- "Expert", "historian", "archaeologist" are claims about a person's qualification. Use only what the customer states.
- Words to avoid unless the customer can back them: "best", "number one", "award-winning", "skip the line", "exclusive access", "secret", "hidden gems" (the last two are common and say nothing).

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file.

### Applies almost everywhere

- **Privacy notice** as soon as the site collects a name and phone. Booking data for foreign visitors may cross borders.
- **Health data**: dietary allergies and mobility needs may count as health data in many places. Collect only what the tour needs, and say why.
- **Terms** whenever the product takes bookings or money: cancellation by visitor, cancellation by the guide, weather, minimum numbers, lateness, refunds.
- **Photos of visitors** need consent before publication.
- **Reviews** must be real.
- **Insurance**: guides commonly carry public liability insurance. Whether it is required and whether it must be stated: not verified.

### Israel

- Guiding tourists in Israel is believed to require a licence from the Ministry of Tourism. Whether this applies to every kind of guided walk, and whether the licence must be shown on a website: not verified.
- Accessibility of the website: the Equal Rights for Persons with Disabilities Law and its service-accessibility regulations require an accessibility statement for businesses serving the public, with exemptions for very small businesses. Thresholds: not verified.
- Displayed prices to consumers include VAT; whether tours sold to foreign tourists are VAT-exempt and how prices must then be shown: not verified.
- Distance-selling cancellation under the Consumer Protection Law: how it applies to a dated tour: not verified.

### European Union and United Kingdom

- GDPR (EU) and UK GDPR apply to booking data; non-essential cookies need consent.
- The Consumer Rights Directive is believed to exclude leisure services booked for a specific date from the 14-day withdrawal right, so the operator's own cancellation terms govern. Believed; not verified against the text for this file.
- The Package Travel Directive (EU) 2015/2302 and the UK Package Travel Regulations may apply when a tour is sold together with accommodation or transport. A single-day guided tour is believed not to be a package. Not verified.
- Guide licensing differs by country and sometimes by site. Italy, Greece and others are believed to require a licensed guide inside certain monuments and museums. Not verified per country.
- European Accessibility Act: whether a small tour operator's booking page is in scope: not verified.

### United States

- Some cities have required tour-guide licences in the past and some of these rules were challenged in court. Current rules per city: not verified.
- ADA applied to websites by courts in many cases; no single federal technical standard for private businesses. Not verified.
- Sales tax on tours varies by state. Not verified.

### What the product does with this

- The product may generate the **structure** of privacy, terms and accessibility pages, marked as drafts that need review.
- The product never states that the site "complies with" a named law, and never displays a licence number the customer did not give.
- The product asks in which country the tours run before generating any legal page.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, tours (one page per tour with meeting point, length, price, what is included), about the guide, private tours, practical information (what to bring, accessibility, weather), contact, legal pages. With "message to book" as the only action, this is a complete product for a guide who books by message or email. One reference runs exactly like that: it publishes the schedule and asks visitors to email to book.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Tour list | cannot be empty (mandatory fact) | | One tour is a valid list |
| Price | "Price on request", never an empty cell | | Says what it is per |
| Schedule | "Private tours only - message us for dates" | | Shows the season it is valid for |
| Map of meeting point | text description always shown | if the map fails, text and a link remain | |
| Reviews | section hidden | | Never placeholders |
| Photos | section hidden | broken image hidden | Only real photos of the place or of consenting groups |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Private tour enquiry | stores dates, party size, interests, contact; alerts the guide | n/a | "sending" and cannot be pressed twice | "Not sent - please message us" with the number | "Received - we will reply within [stated time]" | visitor writes; only the guide reads |
| Departure calendar | schedule, closures, seats left | "No departures on this date - try another day or ask for a private tour" | placeholder, never an empty calendar that looks fully booked | "Could not load dates - message us" | n/a | public read |
| Booking with seats | departures, group size, existing bookings | as above | as above | "That departure just filled - here are the next ones" | confirmed only after the server saved it; confirmation contains meeting point, time, day-of phone | visitor: own booking; guide: own departures; owner: all |
| Cancel or change by visitor | personal link in the confirmation | no upcoming bookings: say so | | link expired: show the phone | frees seats at once, alerts the guide | only through the link |
| Guide cancels a departure | list of booked contacts | | | a failed message is shown to the guide, per person | departure shows "cancelled"; each visitor told | guide or owner only |
| Guide's day sheet | who is coming, how many, needs | "No bookings for this departure" | | never a stale list without saying it is stale | check-in marks attended or no-show | guide and owner, behind a login |
| Owner edits tours, times, prices | edit screen | | | failed save keeps what was typed | live on save | owner only |
| Reminder | sending channel and consent | | | failed send shown to owner | | only for confirmed, not cancelled, bookings |

### Needs accounts

- The owner always, as soon as anything is editable or stored.
- Each guide only if several guides run departures.
- Visitors should not need an account to book. A phone, an email and a link are enough.

### Needs payments

- Paid booking, deposit, gift cards, digital guides.
- Each brings refunds (especially guide-cancelled departures), receipts and failed-payment states.
- Default: no payments. Pay on the day or by the guide's existing method until the customer states a cancellation policy (mandatory fact 13).

### Using an existing booking system

Many tour businesses sell through an external booking system or through marketplaces. In that case the product is a content site whose action is that link, and the product owns no bookings. Ask before building a second calendar: two calendars selling the same seats is how a departure gets oversold.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio is an estimate from counts in the extracted text. Image counts include logos, icons and review-star images.

**Curation.** Chosen by the author from known tour operators in Europe and the US, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner. All are in English, in Latin script.

**Limit.** Two are one-city walking companies; four are multi-city companies. No single self-employed guide's site was verified. The skeletons describe a company; a one-person guide uses Skeleton A with fewer tours.

Verified: 6.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.paris-walks.com | 2026-11-22 | One-city walking company, small team, booking by email. Order: one-line identity with founding year - current information (from March to November at least one tour a day at a stated time and a stated price per adult; private tours on request by email with dates, tour and party size) - "why go on a walk" as a list of reasons (value, pace, guides' qualifications) - guides and quoted thank-you messages - where the company is recommended. Text-led. Extraction: 4 images, about 11,000 characters. |
| 2 | https://www.walks.com | 2026-11-22 | London walking company. Top row of practical tiles: how to go on a walk, "do we book or just turn up?", prices, "walks last 2 hours, we go rain or shine", schedule by date (a calendar). Then live outdoor and virtual tours - featured walks - news - popular walks as image tiles by theme - other tours (private, specials, food). Navigation lists walks by day of the week. Extraction: 4 images (more thumbnails load lazily), about 7,100 characters. |
| 3 | https://www.contexttravel.com | 2026-11-22 | Multi-city expert-led tours. Order: headline and one line of promise - category tabs (favourites, rare, beyond the city, families) - tour cards, each with topic, length, "private" and "group" with a separate price for each, and a review count - destinations - "expertly led" and "tours tailored for your party" - audio guides and pre-trip guides sold as digital products - a review section with a total count and individual reviews with city and date. Extraction: 11 images, about 99,000 characters, mostly tour cards. |
| 4 | https://www.eatingeurope.com | 2026-11-22 | Multi-city food tours. Order: offer banner - headline and "view food tours" - press logos - one paragraph of story - city tiles plus corporate, private and VIP - best sellers as long cards: name, review count, short description, then labelled fields "Duration", "Location", "Stops", "Group size: max 12", "From" price, "Book now", "View details", "upgrade to private" - reviews with date - why us - gift card. Extraction: 99 images, about 33,000 characters. |
| 5 | https://www.devourtours.com | 2026-11-22 | Multi-city food tours. Order: headline - one paragraph naming 18 cities in nine countries - city tiles - "consistent excellence" reasons - short videos of tours - blog posts with dates - inspiration. No prices on the home page. Extraction: 1 image returned and about 40 empty image placeholders, about 7,400 characters. |
| 6 | https://freetoursbyfoot.com | 2026-11-22 | Multi-city walking tours with a tip-based origin. Order: headline and "view cities" - popular destinations - all destinations grouped by region - "who we are", which explains that most tours are now ticketed and some pay-what-you-wish tours remain in named cities - press and trust statements. Shows how a company states a pricing-model change openly. Extraction: 20 images, about 11,200 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.thetourguy.com | 2026-11-22 | Loads. States that listings are "run by us and vetted partners", so part of it is a marketplace. Kept out under the own-site rule. |
| https://www.romewalks.com | 2026-11-22 | Did not load (404). Replaced. |

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the guide (one place, a few tours)

For a guide or small company in one city. Default for this domain.
From references 1 and 2, with the tour-card fields of 4.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action (book / message); on a phone the action stays reachable | action most prominent after the name | yes |
| 1 | Opening | one sentence: what kind of tours, where, in which languages; the main action | one heading, one line, one action | yes |
| 2 | Practical strip | four short answers: how to book, how long tours last, price or "on request", rain policy | four equal items, plain words | yes |
| 3 | Tours | one card per tour: name, type, length, meeting area, price and what it is per, language, group size | card heading over labelled fields | yes |
| 4 | Schedule | which tour leaves when, by day of the week or by date; season it is valid for | table or list | yes, unless private only |
| 5 | Private tours | what can be arranged and what to send (dates, party size, interests) | one paragraph, one action | optional |
| 6 | The guide | who leads, qualifications the customer stated, languages | one image if consented, short text | optional |
| 7 | What visitors say | real reviews with source and count | at most three | optional, hidden when empty |
| 8 | Before you book | meeting point rules, lateness, cancellation, weather, access, children | short list | required if any policy exists |
| 9 | Contact for the day | phone, email, how to reach the guide on tour day | must be complete without the map | yes |
| 10 | Footer | name, phone, licence if required; privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1 and 2 returned 4 images each against 7,000 to 11,000 characters). Text-led: about one image per four or five text blocks. The practical answers carry the page; images show the place. Not confirmed in a rendered view.

### Skeleton B: the tour company (many tours or cities)

For a company with many tours, several cities or bookable departures.
From references 3, 4, 5 and 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | navigation by city or category; search or "view tours"; book action | | yes |
| 1 | Opening | one promise line; one action to the tour list | | yes |
| 2 | Choose a place or theme | city tiles or category tabs | tiles of equal weight | yes |
| 3 | Best sellers | tour cards with labelled fields (length, location, stops, group size, price "from", book) | one card per tour, same field order on every card | yes |
| 4 | Private and group options | private tour and corporate entry points | short | optional |
| 5 | Why us | three to four reasons the customer can back | short statements | optional |
| 6 | Proof | review total with source, a few dated reviews; press logos only if real | | optional, hidden when empty |
| 7 | More to buy | gift cards, digital guides | | optional |
| 8 | Stories | blog or guides with dates | | optional |
| 9 | Footer | contact, cities, legal pages | | yes |

Image-to-text ratio: **estimate**. Image-led cards: reference 4 returned 99 images, mostly several photos per tour card. Each card is images plus short labelled fields. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working guide.
2. Every legal statement in section 7, especially guide licensing in Israel, EU countries and US cities, and whether day tours fall under package-travel rules.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view.
4. No awwwards.com category was consulted.
5. No self-employed single guide's site was verified.
6. Booking defaults in section 4 (2-hour cut-off, 90 days ahead, evening-before reminder) are estimates.
7. Tour sub-pages (meeting point descriptions, cancellation terms, booking flows) of the references were not fetched; observations are of home pages only.
8. The claim that many tour businesses sell through external systems or marketplaces is general knowledge, not checked for this file.
9. No references in Hebrew, Arabic or any non-Latin script.
