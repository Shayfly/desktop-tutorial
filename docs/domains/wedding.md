# Wedding

Covers two kinds of customer: (a) a couple who want a wedding site for their guests (details, schedule, travel, RSVP); (b) a business whose main work is weddings: a wedding venue or a wedding planner.
Does not cover: wedding photographers (use `photographer.md`); hair and make-up (use `hair-salon.md` or `beauty-cosmetics.md`); a hotel where weddings are one product among many (use `hotel-guesthouse.md`); other celebrations and conferences (use `event.md`).
Written 2026-11-22. References checked 2026-11-22 (the brief named 2026-11-21; the fetches ran on 2026-11-22). Template: [README.md](README.md).

## 1. Objects

A wedding is **one day that a list of named people must reach, in the right clothes, at the right times, in the right places**. For the couple's site the visitor is a guest who already has an invitation and needs facts; for a venue or planner the visitor is a couple deciding where and with whom to spend a large sum. The two share most objects but not the main action: a guest answers an RSVP; a couple books a viewing or sends an enquiry.

### (a) The couple's wedding site

#### Wedding

| Field | Required | Example (illustrative) |
|---|---|---|
| How the couple want to be named | required | first names only, for example "Dana & Sam" |
| Date | required | Saturday 12 June 2027 |
| Town or region | required | |
| Language or languages of the guests | required | Hebrew and English |
| Welcome message | optional | in the couple's own words |
| Who to contact with questions | required | a phone or email of the couple or a helper |
| Access: public, link only, or password | required | default password, see section 4 |
| RSVP deadline | required when RSVP is collected | 1 May 2027 |

#### Part of the day (schedule item)

| Field | Required | Example |
|---|---|---|
| Name | required | welcome drinks, ceremony, reception, dinner, party, brunch the next day |
| Date and start time | required | 17:30 |
| End time | optional | |
| Place | required | linked venue |
| Who is invited to this part | optional | some parts are for close family only |
| Dress code | optional | "garden party - flat shoes advised" |
| Note | optional | "ceremony starts on time; doors close at 17:25" |

#### Venue

| Field | Required | Example |
|---|---|---|
| Name | required | |
| Address and map link | required | |
| Parking and transport | optional, strongly advised | shuttle times, nearest station, parking |
| Accessibility | optional | step-free, distance from parking, toilets |
| Indoor or outdoor, weather plan | optional | |

#### Guest and party

| Field | Required | Example |
|---|---|---|
| Party (household) name | required | "The Cohen family" |
| Guests in the party | required | names, adult or child |
| Plus-one allowed | optional | yes or no |
| Parts of the day invited to | optional | all, or ceremony only |
| RSVP status per guest | required when RSVP is collected | attending, not attending, no answer yet |
| Meal choice | optional | from the couple's list |
| Dietary needs | optional | |
| Song request, message | optional | |

#### Other objects

| Object | Fields | Notes |
|---|---|---|
| Accommodation | name, link, distance, booking code, booking deadline | Only places the couple chose; never invented |
| Travel | airport, train, taxis, shuttle | For guests from far away |
| Gifts | registry link, or a note about cash gifts or "no gifts" | The couple's own words; sensitive in many cultures |
| Children | welcome, not invited, or childcare provided | A frequent and delicate question |
| FAQ | question, answer | Practical: parking, dress, phones during the ceremony, photos |
| Photo sharing | link or upload, after the day | Consent and privacy apply |
| Story or about us | text, photos | Optional |

### (b) Wedding venue or planner (the business)

| Field | Required | Example |
|---|---|---|
| Business name | required | |
| Kind | required | venue (exclusive use, hotel, barn, garden), planner, both |
| Location | required | address for a venue; base and travel area for a planner |
| Phone, email | required | |
| How to start | required | book a viewing, send an enquiry, call |
| Capacity | required for a venue | seated dinner 50, ceremony 160 |
| Accommodation on site | optional | number of bedrooms and guests |
| Packages or hire options | optional | dry hire, all-inclusive packages, planning only |
| Prices | optional, see rule 13 | "from", estimator, "on request" |
| What is always included | optional | exclusive use, a coordinator, breakfast the next morning |
| Ceremony licence | optional | whether legal ceremonies can be held on site (country-specific) |
| Cultural and religious weddings | optional | what the venue or planner can host |
| Availability by date | optional | years taking bookings; specific dates only with a live calendar |
| Gallery | optional | real weddings, with the couple's consent |
| Reviews | optional | real, with source |
| Team | optional | |
| Registered company name and number | required for legal pages | |

## 2. Rules

For (a), the couple's site:

1. The date is shown with the weekday and the year. Times are local.
2. Every part of the day has a place and a start time. A guest can see the whole day in one list.
3. A part of the day for a limited group is shown only to guests invited to it.
4. The site is not public by default. A guest list, home towns or children's names are never shown on a public page.
5. An RSVP is one answer per guest, not per link: a party of four can answer "two attending, two not".
6. A guest can change their RSVP until the deadline. After the deadline the form says so and shows who to contact.
7. The couple can see every answer and when it was given. A guest sees only their own party.
8. A meal choice is offered only from the couple's list, and dietary needs are free text that the couple can export for the caterer.
9. Accommodation, transport and gift information are only what the couple gave. Nothing is suggested from search results without the couple's approval.
10. A change to time or place after invitations went out is shown as a change ("updated 3 May: the ceremony now starts at 17:00") and guests who answered are told.
11. A plus-one can be added only where the couple allowed one.
12. Photos of guests are shared only in a closed space, and anyone can ask to have a photo removed. Photos of children need the parent's consent.

For (b), the venue or planner:

13. A price is optional, but its absence must be explicit: "prices on request", a "from" price with what it includes, or an estimator whose inputs are shown. A "from" price says what it depends on (date, season, number of guests).
14. A venue states capacity for each format it offers (ceremony, seated dinner, standing).
15. "Exclusive use" is stated only if the couple really has the whole property, and the site says what that means in practice (which rooms, which nights).
16. Availability is never implied: "now booking 2027-2030" is a statement the customer must confirm; specific free dates need a live calendar.
17. Photos of real weddings are published only with the couple's consent; supplier credits are given where the customer has them.
18. Press quotes name the publication. Award lines name the award and year. Reviews carry their source.
19. A third-party feed (social media) that fails must disappear, not show an error. (One reference displayed a visible feed error on its home page.)
20. The enquiry or viewing action is reachable from every page on a phone.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

### (a) The couple's site

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Names as shown | "How should your names appear on the site?" | Guests must know they are on the right page; some couples do not want surnames online. |
| 2 | Date | "What is the date of the wedding?" | Guests book flights and leave from work for this date. |
| 3 | The parts of the day | "What happens when, and where: ceremony, reception, party, anything the day before or after?" | Without times and places guests arrive late or at the wrong door. |
| 4 | Addresses | "What is the full address of each place?" | Guests must arrive; taxis need an address. |
| 5 | Contact for guests | "Who should guests call or message with questions, and on the day?" | Someone lost on the day needs a person, not a form. |
| 6 | Who can see the site | "Should the site be open to anyone, only to people with the link, or protected by a password?" | A public page with a date and an address tells strangers when your home is empty. |
| 7 | RSVP or not | "Do you want guests to answer on the site? By what date? Do you want meal choices?" | Without numbers the caterer cannot plan; without a deadline the couple waits forever. |
| 8 | Guest list, if RSVP | "Can you give me the list of invited people grouped by household, and who may bring a plus-one?" | An RSVP without a list lets anyone answer, and couples get strangers on the count. |
| 9 | Languages | "Which languages do your guests read?" | A guest who cannot read the page misses the bus. |

### (b) Venue or planner

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 1 | Name and kind | "What is the business called, and are you a venue, a planner, or both?" | A couple searches for one or the other. |
| 2 | Where | "Where are you, or where do you work?" | Couples choose by region first. |
| 3 | Contact and first step | "How should a couple start: book a viewing, send an enquiry, call?" | The site leads to this one action. |
| 4 | Capacity (venue) | "How many guests can you host for a ceremony, a seated dinner, and a party?" | A couple with 150 guests skips a venue for 80 at once; finding out late wastes everyone's time. |
| 5 | Prices or the decision not to show them | "Do you show prices, a starting price, or 'on request'? What does a starting price include?" | Price is the first filter; hiding it is allowed, inventing it is not. |
| 6 | What is included | "What is always included, and what is extra?" | Couples compare like for like. |
| 7 | Legal identity | "What is the registered business name and number?" | Legal pages must name who is responsible. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the wedding or the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Access to the couple's site | password protected, password shared on the invitation | The safer choice for private people; the couple can open it | Shown at setup: "your site is private - change this?" |
| Search engines | not indexed for the couple's site | Same reason | Setting, labelled "default" |
| Page order (couple) | Skeleton A below | Built from the domain (see section 10 on its source) | Named as the default skeleton |
| Page order (business) | Skeleton B below | Extracted from the references | Named as the default skeleton |
| RSVP form fields | name per guest, attending yes or no, dietary needs (free text) | The least data that lets a caterer plan | "Suggested fields - add meal choice if you offer one" |
| RSVP deadline reminder | none | Messaging guests is the couple's decision | Asked |
| Schedule wording | the couple's names for each part | Customs differ by culture and language | The couple names each part |
| Missing venue price | "Prices on request" | Honest | Listed as "no price given" |
| Language and direction | the language of the conversation | The customer chose it | Shown, changeable; second language on request |
| Legal pages for the couple's site | a short privacy note: what RSVP data is kept, who sees it, when it is deleted | Guests give personal data | "Draft - review before publishing" |
| Data deletion for RSVPs | 90 days after the wedding | Estimate; reduces what is kept | Setting, labelled "default" |
| Empty optional sections | hidden | An empty gift page is awkward | Listed as "not shown yet" |

Never a default, whatever the customer left out: the date, times, places, the guest list, who may bring a plus-one, whether children are invited, the dress code, gift wording, accommodation suggestions, venue capacity, prices, packages, "exclusive use", awards, reviews, press, available dates.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Wrong date or time | Guest arrives after the ceremony | Hurt feelings that last years | Rule 1; couple confirms each time read back |
| Public site with date and home town | Strangers know when the house is empty; guest names indexed | Burglary risk; privacy complaint | Mandatory fact 6; password default |
| RSVP open to anyone with the link | Unknown names on the count | Wrong numbers to the caterer | Rule 5 with a guest list (fact 8) |
| RSVP saved, couple never sees it | Guest answered; couple thinks they did not | Awkward calls, wrong seating | Couple's view of all answers; export tested at setup |
| Part of the day for family only shown to all | Guests who were not invited see it | Offence | Rule 3 |
| Change of time not announced | Guests follow the old time | Late arrivals | Rule 10 |
| Hotel block expired, still shown | Guest finds no room at the price | Annoyance | Booking deadline field; hidden after it |
| Gift wording careless | Guests feel asked for money | Embarrassment | Couple's own words only (rule 9) |
| Only one language in a mixed family | Grandparents cannot read the schedule | Exclusion | Mandatory fact 9 |
| Venue "from" price far below real cost | Couple feels misled at the quote | Lost trust | Rule 13 |
| Venue capacity unclear | Couple visits, then learns it does not fit | Wasted viewing | Rule 14 |
| Social feed error on the home page | Sees an error message | Looks neglected | Rule 19 |
| Venue closed or moved, site not updated | Couple enquires at a place that no longer hosts weddings | Wasted time | One reference was closed for events; prompt the customer yearly |
| Real-wedding photos without consent | A couple sees their wedding in an advert | Complaint; privacy problem | Rule 17 |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with wedding professionals in either language. Customs and words differ widely by community; where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Wedding | the event | חתונה | زفاف / عرس |
| Bride, groom | | כלה, חתן | عروس, عريس |
| Couple | | זוג | العروسان (in the wedding sense) |
| Ceremony | the marriage itself | טקס / חופה (Jewish ceremony) | مراسم الزفاف / عقد القران (contract; not verified for all communities) |
| Reception | the celebration after | קבלת פנים | حفل الاستقبال |
| Save the date | early notice of the date | שמרו את התאריך | احفظوا التاريخ (not verified) |
| Invitation | | הזמנה | دعوة |
| RSVP | please reply | אישור הגעה | تأكيد الحضور |
| Plus-one | a guest's companion | +1 / מלווה | مرافق |
| Dress code | | קוד לבוש | قواعد اللباس (not verified) |
| Gift registry | list of wished gifts | רשימת מתנות | قائمة الهدايا (not verified) |
| Venue | | אולם / גן אירועים / מקום האירוע | قاعة أفراح |
| Exclusive use | the whole venue for one wedding | שימוש בלעדי (not verified as trade usage) | not verified |
| Dry hire | venue only, own suppliers | השכרת מקום בלבד (not verified) | not verified |
| Wedding planner | | מפיק/ת אירועים / מתכנן/ת חתונות | منظم حفلات زفاف |
| Viewing, site visit | couple visits the venue | סיור במקום | زيارة المكان (not verified) |
| Henna night | pre-wedding celebration in some communities | חינה | ليلة الحناء |
| Seating plan | who sits where | סידורי הושבה | ترتيب الجلوس (not verified) |

Notes on language:

- In Israel the venue trade uses "אולם" (hall) and "גן אירועים" (garden venue); price is often per guest (מחיר למנה). Not verified as universal.
- "Exclusive use" and "dry hire" are UK trade terms seen in the references. US usage differs; not verified.
- Words to avoid unless the customer can back them: "best venue", "award-winning", "dream wedding guaranteed", "affordable" (one reference uses it; it is a claim only the business may make), "fully accessible".

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file.

### Applies almost everywhere

- **Guest data is personal data of private people.** Names, households, dietary needs (possibly health data), attendance. Collect the least, protect the page, delete after the wedding.
- **A couple is a private person, not a business.** Data-protection law often exempts purely personal activity, but publishing personal data on an open website may fall outside that exemption. Treat guests' data as if the law applies. Not verified per jurisdiction.
- **Children**: names and photos of children deserve extra care; a parent's consent before publishing.
- **Cash gifts by payment link** may involve payment-service rules and tax questions. Not verified.
- **For venues and planners**: privacy notice, terms (deposits, cancellation, date changes, damage, noise and curfew), and consumer law on advertised prices.

### Israel

- A business website serving the public needs an accessibility statement under the Equal Rights for Persons with Disabilities Law regulations, with size exemptions. Whether a couple's private site is in scope: believed not, not verified.
- Event venues need a business licence and have capacity limits set by authorities. Not verified.
- Prices advertised to consumers must include VAT. Per-guest pricing displays: not verified.
- Privacy Protection Law, Amendment 13 (in force August 2025): what it requires of a venue's enquiry form: not verified.
- Legal validity of a marriage ceremony is governed separately (religious authorities, recognition of marriages abroad). The site never states that a ceremony is legally binding. Not verified.

### European Union and United Kingdom

- GDPR and UK GDPR for venue enquiries and, likely, for a couple's public RSVP site (see "private person" above). Not verified.
- UK: legal ceremonies may be held only at approved premises (England and Wales rules changed recently to allow outdoor ceremonies at approved venues). Whether a venue states it holds a licence is a fact to ask. Not verified.
- Consumer rights on venue deposits and cancellation: national rules; withdrawal-right exceptions for dated leisure services are believed to apply. Not verified.
- UK drip-pricing rules (DMCC Act 2024): how they apply to venue "from" prices: not verified.

### United States

- State law on deposits and cancellation; venue alcohol licensing; no single federal rule for a couple's site. Not verified.
- ADA applies to venues as public accommodations. Not verified for websites.

### What the product does with this

- For a couple: a private site by default, a short privacy note, and deletion of RSVP data after a set time.
- For a venue or planner: the **structure** of privacy and terms pages, marked as drafts.
- The product never says a ceremony is legal or a venue is licensed unless the customer stated it.

## 8. Site vs app

### Content pages (no data, no accounts)

(a) Couple: home with date and place, schedule, venue and travel, accommodation, dress code, FAQ, gifts, story. With RSVP by phone or message, this is a complete product.
(b) Venue or planner: home, the venue or services, spaces and capacity, packages and prices, accommodation, gallery, team, reviews, contact, legal pages. With "book a viewing" as an email or phone link, this is a complete product.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Schedule | cannot be empty (fact 3) | | Shows "updated" when changed |
| Accommodation | section hidden | | Hidden after the booking deadline |
| Gifts | section hidden | | Never a default wording |
| Gallery | hidden | broken image hidden | Consent per wedding |
| Reviews, press | hidden | | Never placeholders |
| Social feed | hidden | hidden on failure, never an error message | Rule 19 |
| Map | address text always shown | text and link remain | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Password gate (couple) | one shared password | | | "That password is not right - check your invitation or ask [contact]" | | anyone with the password |
| RSVP | guest list by party, deadline, meal list | "We could not find your name - check spelling or ask [contact]" | "looking you up" | "Not saved - please try again or message [contact]" | per-guest answers saved; summary shown back; change possible until deadline | guest: own party only; couple: all |
| Couple's RSVP dashboard | answers, counts per part of the day, dietary list | "No answers yet" | | never a stale count without a time stamp | export for caterer and seating | couple and helpers they invite, behind a login |
| Messages to guests | guest contacts, consent, channel | | | failed sends listed | | couple only |
| Photo sharing after the day | upload space | "No photos yet" | upload progress per photo | failed upload kept for retry | | guests upload; couple moderates; never public by default |
| Venue enquiry | date wished, guest count, contact, message | n/a | "sending" | "Not sent - please call [phone]" | "Received - we reply within [time]" | couple writes; venue reads |
| Venue availability calendar | live bookings | "This date is taken - nearby free dates" | placeholder | "Could not load dates - ask us" | | public read of free or taken only |
| Cost estimator (venue) | the venue's real price rules | | | | estimate shown with its inputs and "estimate" label | public |

### Needs accounts

- The couple (and helpers they invite) as soon as RSVPs are stored.
- Guests never need an account; name lookup behind the password is enough.
- Venue or planner staff for enquiries and calendars.

### Needs payments

- Venue deposits, packages, cash gifts.
- Each brings refunds, receipts and the cancellation law of the country.
- Default: no payments. A couple's gift link points to the couple's own chosen service; a venue takes deposits outside the product until terms are stated.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality and the image-to-text ratio are **not** observed, and every ratio is an estimate from counts in the extracted text. Some extractions return only part of a page.

**Curation.** Chosen by the author from known wedding venues and planners in the UK and the US, plus one venue found through a search and then loaded directly (reference 2). No awwwards.com category was consulted; none is claimed as an award winner. All are in English, in Latin script.

**Why no couple's wedding site is referenced.** A couple's site is made by private individuals and lists their names, date, places and often guests. The reference rules forbid personal data of private individuals and template demos. So no couple's site was loaded. Skeleton A is therefore built from the domain, not extracted from references, and is labelled so.

**Limit.** All five references are upmarket UK and US venues and planners. No neighbourhood wedding hall, no Israeli or Arab-world venue (non-Latin script comes later), and no couple's site was verified.

Verified: 5.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.hedsor.com (and /weddings/) | 2026-11-22 | Exclusive-use country-house venue near London. Home: name and one paragraph (house, grounds, distance from London, "exclusive and utterly private"). Weddings page order: dry hire or three packages - "always included" as four items (exclusive use, a dedicated wedding specialist, overnight accommodation for up to 26 plus a cottage the night before, breakfast the morning after) - press quotes naming two magazines - pricing and packages - cultural weddings - the cottage - the team - testimonials - phone, email, full address - registered company name and number - "come and visit us" viewing action. Extraction: home 22 images; weddings page fetched as text only. |
| 2 | https://www.logiecountryhouse.co.uk | 2026-11-22 | Exclusive-use castle venue in Scotland. Order: headline with "exclusive use" - award line with years - bedrooms, acreage, distance from the nearest city - two-night midweek or three-night weekend - features list - capacity (50 in the dining room, 160 in the ballroom) - support for couples planning from abroad with virtual viewings - "now taking bookings for 2027-2030" - "book your private viewing" - a cost estimator - reviews summarised as repeated phrases, with a link to full reviews - a chat assistant. Extraction: 1 image, long text. |
| 3 | https://www.sarahhaywood.com | 2026-11-22 | London-based wedding and party planner. Order: one heading - paragraph on approach and clientele - weddings - parties - destinations (types of places listed) - "the experience" as four qualities. Text-led, no prices, no client names. Extraction: 3 images. |
| 4 | https://www.colincowie.com | 2026-11-22 | Event and wedding planner with offices in several cities. Navigation: events (weddings, private, corporate, non-profit, destinations), services, inquiry, about. Order: anniversary line - one long paragraph - a new office abroad - "featured in" with a magazine named - a social feed block that showed a visible feed error in the extraction - locations, each with phone and email. Extraction: 7 images. |
| 5 | https://www.mindyweiss.com (and /about/) | 2026-11-22 | US wedding and event planner. Home: a line of press accolades naming the publications - one paragraph (team size, kind of events) - "meet" link. About page: approach, base city, kinds of events, books and products. Very little text on the home page; image-led. Extraction: home 7 images. The about page names famous clients; they are not repeated here. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.aynhoepark.co.uk | 2026-11-22 | Loads, but states it is now closed for events and points to another venue. Kept as an example of failure mode "venue closed, site not updated" - here handled correctly. |
| https://www.rushtonhall.com | 2026-11-22 | Loads. A hotel where weddings are one tile among rooms, dining, spa and offers. Belongs to `hotel-guesthouse.md`. |

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the couple's wedding site

**Source: domain knowledge, not extracted from references** (see section 9). The practical blocks (accommodation, travel, "always included" style lists) mirror the information types the venue references publish for their own guests. To be checked against real couple sites only with their owners' permission, or against a curated, consented set, in a later pass.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Gate | password, with the contact for help | one field | yes by default |
| 1 | Opening | names as the couple chose; date with weekday; town; one welcome line | names largest; date second | yes |
| 2 | RSVP | answer by name; deadline | one clear action | yes if collected |
| 3 | The day | parts of the day in order: time, name, place, dress note | a vertical timeline | yes |
| 4 | Getting there | addresses, map links, parking, shuttles, accessibility | must be complete without the map | yes |
| 5 | Where to stay | chosen places, codes, deadlines | | optional |
| 6 | Good to know | children, dress code, phones, photos | short list | optional |
| 7 | Gifts | the couple's own words | | optional |
| 8 | Our story | text and photos | | optional |
| 9 | Footer | contact for questions; privacy note | small | yes |

Image-to-text ratio: **estimate**, not from references. One opening photo if the couple supplies one; the rest is text, because guests come for facts.

### Skeleton B: the wedding venue or planner

From references 1, 2, 3 and 4.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; "book a viewing" or "enquire"; phone | action always reachable | yes |
| 1 | Opening | one paragraph: what and where (distance from a city), the one thing that makes it different | large image, one line | yes |
| 2 | Key facts | capacity per format, bedrooms, nights included, years now booking | short list | yes for a venue |
| 3 | Always included | three to five items | equal items | optional |
| 4 | Options and prices | packages or dry hire; "from" price with what it depends on, or "on request"; estimator if real | | yes (may say "on request") |
| 5 | Spaces or services | ceremony, dinner, party spaces; or planning services | image and short text each | yes |
| 6 | Weddings we host | cultural and religious weddings, destination support | short | optional |
| 7 | Proof | real reviews with source, press with publication named, awards with year | | optional, hidden when empty |
| 8 | Team | who will look after the couple | | optional |
| 9 | Visit and contact | viewing action, phone, email, address, how to get there | complete without the map | yes |
| 10 | Footer | registered name and number, privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**. Mixed: reference 1 returned 22 images on its home page with short text; reference 2 returned 1 image with long text; reference 3 is text-led. Image-led for the opening and spaces, text for facts and prices. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6; customs vary by community.
2. Every legal statement in section 7, especially whether data-protection law applies to a couple's site, ceremony licensing, and venue licensing in Israel.
3. Skeleton A is not extracted from any reference; it is domain knowledge.
4. Image-to-text ratios and visual quality: text extraction only.
5. No awwwards.com category was consulted.
6. No neighbourhood wedding hall and no venue outside the UK and US was verified.
7. Defaults in section 4 (90-day RSVP deletion) are estimates.
8. Sub-pages of the references (packages, pricing, estimators, enquiry forms) were not fetched, except Hedsor's weddings page and Mindy Weiss's about page.
9. No references in Hebrew, Arabic or any non-Latin script.
