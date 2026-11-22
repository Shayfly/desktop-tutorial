# Hair salon

Covers: a place where people pay to have their hair cut, coloured or styled. Includes barbershops and one-person salons working from a rented chair or from home.
Does not cover: nails, skin, lashes, make-up as the main business (use `beauty-cosmetics.md`); selling hair products as the main business (use `clothing-shop.md` or `catalogue-collection.md`).
Written 2026-11-21. References checked 2026-11-21. Template: [README.md](README.md).

## 1. Objects

A salon sells **time with a person**. Everything else follows from that: a service has a length, a stylist has working hours, and an appointment is one service with one stylist at one time.

### Salon (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Studio North" |
| What kind of place | required | women's salon, barbershop, unisex, curly-hair specialist |
| Address, or "by appointment at a private address" | required | street, number, city, floor |
| Phone | required | a number people can call or message |
| Opening hours, per day of the week | required | Tue-Fri 09:00-19:00, Sat 09:00-14:00, closed Sun-Mon |
| How to book | required | call, message, online booking, walk-in only |
| Email | optional | |
| Social account | optional | usually where the photos already are |
| Parking, access, floor, lift | optional | "step-free entrance", "second floor, no lift" |
| Payment methods accepted in the salon | optional | cash, card, payment apps |
| Languages spoken | optional | |
| Year opened, short story | optional | |

### Location (only when there is more than one)

Same fields as address, phone, hours and booking link, repeated per location. Each location has its own hours and often its own phone. A stylist belongs to one or more locations.

### Service category

| Field | Required | Example |
|---|---|---|
| Name | required | Cut, Colour, Styling, Treatments, Barbering, Bridal |
| Order on the page | required | cuts first |
| Short note | optional | "All colour prices include a blow-dry" |

### Service

| Field | Required | Example |
|---|---|---|
| Name | required | "Cut and blow-dry" |
| Category | required | Cut |
| Price | optional, see rule 3 | 180 |
| Price type | required when a price is shown | fixed, "from", range, "by consultation" |
| Duration in minutes | optional on the page, required for online booking | 45 |
| Short description | optional | what is included (wash, blow-dry) |
| Who it is for | optional | by hair length, by adult or child; avoid pricing by gender where the law forbids it (see Legal) |
| Needs a consultation first | optional | colour correction, extensions |
| Needs an allergy patch test first | optional | colour services |
| Processing time inside the service | optional | 30 minutes while colour develops, when the stylist is free |
| Add-on to another service | optional | toner, treatment |
| Currently offered | required, default yes | a service can be paused without being deleted |

### Stylist (team member)

| Field | Required | Example |
|---|---|---|
| Display name | required | first name is enough |
| Role or level | optional | junior, senior, colourist, barber, director |
| Services this person does | optional | not every stylist does colour |
| Working days and hours | optional on the page, required for online booking | |
| Photo | optional | only with the person's consent |
| Short bio, specialities | optional | |
| Price level | optional | prices often differ by stylist level |
| Currently taking new clients | optional | |

A one-person salon has one stylist, and the Team section is replaced by an About section.

### Appointment (only when the product takes bookings)

| Field | Required | Example |
|---|---|---|
| Service or services | required | |
| Stylist, or "anyone available" | required | |
| Date and start time | required | |
| End time | derived | start + duration |
| Visitor name | required | |
| Visitor phone | required | to confirm and to remind |
| Visitor email | optional | |
| Notes | optional | "first visit", "long thick hair" |
| Status | required | requested, confirmed, cancelled by visitor, cancelled by salon, completed, no-show |
| Deposit paid | optional | |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Gallery item | image (required), caption, service, stylist, consent to publish (required when a person is recognisable) | Photos of work are the proof of skill in this domain |
| Review | text, first name or initials, date, source | Only real reviews, with their source. Never written by the builder |
| Closure | date or date range, reason (optional) | Holidays, vacation, training day. Overrides the weekly hours |
| Policy | cancellation notice, late arrival, deposit, patch test, children, redo guarantee | Each is optional. If one exists it must be shown before booking |
| Gift voucher | value or service, expiry, how to redeem | Optional. Involves payments |
| Retail product | name, brand, price, in stock | Optional. If it becomes the main thing, this is a shop, not a salon |

## 2. Rules

1. Every service belongs to exactly one category.
2. A service name appears once. Variants (short, medium, long hair) are price rows of one service, not separate services.
3. A price is optional, but its absence must be explicit. A service with no price shows "price on consultation" or "ask us", never a blank and never zero.
4. A price shown as a starting price must say "from". A fixed price must be what the visitor actually pays for the described service.
5. Every price shows its currency. Whether prices must include tax is a legal question (see Legal).
6. A duration is a positive number of minutes. A service that can be booked online must have one.
7. An appointment's end time is start plus the total duration of its services.
8. Two confirmed appointments for the same stylist may not overlap. The only exception is a declared processing time inside a colour service, and only when the salon said it works that way.
9. An appointment may only start inside the stylist's working hours and inside the salon's opening hours, and must end before closing.
10. An appointment cannot be made in the past. How far ahead a visitor can book, and how close to the time, are settings with declared defaults.
11. A stylist can only be booked for services that stylist offers.
12. A closure date overrides the weekly hours. On a closed day no slots are offered and the hours display says "closed", with the date.
13. Opening hours are stated per day of the week, in the salon's local time, with the closed days named.
14. A cancelled or no-show appointment frees its slot. It is not deleted; the record stays.
15. A photo of a recognisable person is published only with that person's consent. Photos of children need a parent's consent.
16. A review is shown only if it is real, and it carries its source. No star rating is displayed without a count and a source.
17. If a deposit or a cancellation fee exists, the visitor sees it before confirming, not after.
18. If colour services need a patch test, the visitor is told before booking a colour service, with how long before the appointment it must be done.
19. The main action (book, call or message) is reachable from every page without scrolling back to the top on a phone.
20. The phone number is a tappable link on a phone. The address opens a map.
21. Stock photographs of hair are not presented as the salon's own work.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Business name | "What is your salon called?" | Without a name people cannot find it or recommend it. |
| 2 | Kind of place | "Who do you cut for: women, men, everyone, children? Any speciality?" | A visitor decides in seconds whether this place is for them. |
| 3 | Where | "Where do clients come to? Give me the full address, or tell me if you work from home or travel to clients." | Without an address people cannot arrive. If it is a home address the customer may not want it public. |
| 4 | Phone | "What number should clients call or message?" | Without it people cannot book or say they are late. |
| 5 | Opening hours | "Which days are you open, and from when to when on each day?" | Without hours people arrive at a closed door. |
| 6 | How to book | "How do clients get an appointment today: phone, message, an online system, or do they just walk in?" | The whole page leads to this one action. If it is wrong, the site produces nothing. |
| 7 | Services | "What do you actually do? List the services as you would say them to a client." | Without the list the visitor does not know whether to come. |
| 8 | Prices, or the decision not to show them | "What does each service cost? If you prefer not to show prices, say so." | Price is the most common question. Hiding it is allowed; inventing it is not. |
| 9 | Who is the business legally | "What is the registered business name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only when the product takes online bookings:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 10 | Duration of each service | "How long does each service take?" | Without it two clients get booked on top of each other. |
| 11 | Who works when | "Who works on which days and hours, and who does which services?" | Without it a client is booked with someone who is not there. |
| 12 | Cancellation and deposit | "What happens if a client cancels late or does not show up? Do you take a deposit?" | The client must know before booking, and you must be able to stand behind it. |
| 13 | Where booking alerts go | "Where should I send you each new booking: which phone or email?" | A booking nobody sees is a client standing at the door with no chair. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Category names and order | Cut, Colour, Styling, Treatments (Barbering instead of Styling for a barbershop) | Standard structure seen across the references | Editable list, labelled "suggested order" |
| Which category a service falls in | by the service's name | Wrong placement is visible and easy to fix | Customer confirms the grouped list |
| Missing price | "Price on consultation" | Says openly that there is no number | Shown in the customer's review with "no price given" |
| Main action | "Call to book", using the phone number | Works with zero setup | Labelled "default: phone" |
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Slot step for booking | 15 minutes | Estimate; common in booking tools, not verified | Setting, labelled "default" |
| Earliest booking | 2 hours ahead | Estimate; gives the salon time to see it | Setting, labelled "default" |
| Latest booking | 60 days ahead | Estimate | Setting, labelled "default" |
| Reminder | one message 24 hours before | Estimate | Setting, labelled "default"; off until a sending channel exists |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Currency | the currency of the salon's country | Follows from the address | Shown next to every price |
| Legal page structure | headings only: who we are, what we collect, why, how long, your rights, contact | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing gallery is better than an empty one | Listed for the customer as "not shown yet: gallery, team, reviews" |

Never a default, whatever the customer left out: opening hours, prices, durations, address, phone, staff names, reviews, ratings, awards, years of experience, photos of work, cancellation policy, "all hair types welcome", "organic", "vegan" or any other claim.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Hours on the site are old | Arrives at a closed door | A lost client who tells others | Ask for hours explicitly; show "hours last updated"; prompt the customer before holidays |
| A holiday is not marked | Books or arrives on a closed day | An angry call, a wasted trip | Closure object overrides weekly hours (rule 12) |
| Price list is old | Pays more than the site said | An argument at the till; in some places a legal problem | Date on the price list; "from" where true; yearly prompt |
| "From" price read as the price | Bill is double the expectation | Distrust | Say what "from" depends on (length, stylist level) |
| Double booking | Two people arrive for one chair | One leaves, publicly unhappy | Rule 8, enforced at save time, not only in the display |
| Booking saved but salon never told | Arrives; the salon knows nothing | The worst case in this domain | Mandatory fact 13; show "requested" until the salon confirms; test the alert on setup |
| Service too short in the system | The next client waits 40 minutes | A late day for everyone | Ask durations per service; colour gets its real length |
| Stylist left, still on the site | Asks for someone who is gone | Awkward, looks neglected | Stylist can be hidden without deleting history |
| Booking button leads nowhere | Taps, nothing happens or a broken external page | Silent loss; the customer never finds out | Check the link at publish and on a schedule |
| Phone number not tappable or wrong | Cannot call | Silent loss | Rule 20; customer confirms the number by reading it back |
| No patch-test notice | Told at the door that colour cannot be done today | A wasted visit | Rule 18 |
| Deposit taken, policy unclear | Feels cheated when a late cancellation is charged | Dispute, chargeback | Rule 17; policy shown at the confirm step |
| Stock photos as own work | The result does not look like the pictures | Distrust | Rule 21 |
| Photo published without consent | Sees their own face on the site | Complaint; a privacy problem | Rule 15; consent field on every gallery item |
| Map pin wrong, or no floor or entrance note | Wanders the street, arrives late | Late start, lost slot | Ask "how do people find the door?" |
| Site only in one language in a mixed area | Cannot read the price list | Lost clients | Ask which languages the clients speak |
| Reminder sent in the wrong time zone or for a cancelled slot | Confusing message | Looks careless | Reminders read the live status at send time |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working stylist in either language. Regional Arabic usage varies; the terms given are common Levantine or standard usage. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Hair salon | the business | מספרה | صالون |
| Barbershop | men's cuts and beards | מספרת גברים / ברבר שופ | صالون حلاقة |
| Stylist, hairdresser | the person cutting | ספר / ספרית, מעצב/ת שיער | مصفف شعر / كوافير |
| Barber | cuts and shaves men | ספר | حلاق |
| Colourist | specialises in colour | צבעי/ת (not verified as common usage) | not verified |
| Appointment | a booked time | תור | موعد |
| Walk-in | no appointment needed | ללא תור מראש | بدون موعد |
| Consultation | a talk before a big change | ייעוץ | استشارة |
| Cut | haircut | תספורת | قص شعر |
| Trim | a small cut to tidy | קיצוץ קצוות (not verified) | not verified |
| Fringe (UK), bangs (US) | hair cut over the forehead | פוני | غرّة |
| Blow-dry (UK), blowout (US) | wash and dry into a style | פן | سشوار |
| Updo | hair pinned up for an event | תסרוקת ערב (not verified) | not verified |
| Bridal hair | wedding styling | תסרוקת כלה | تسريحة عروس |
| Colour, tint | all-over colour | צבע | صبغة |
| Root touch-up, regrowth | colouring only the new growth | צבע שורשים | صبغة جذور (not verified) |
| Highlights | lighter strands | גוונים | هايلايت (loanword; not verified) |
| Balayage | hand-painted lightening | בלייאז' | بالياج (loanword; not verified) |
| Toner, gloss | adjusts the shade after lightening | טונר | not verified |
| Bleach, lightening | removing colour | הבהרה | تفتيح (not verified) |
| Colour correction | fixing a colour that went wrong | תיקון צבע | not verified |
| Patch test, skin test | allergy test before colour | בדיקת רגישות (not verified) | not verified |
| Straightening, smoothing, keratin | long-lasting smoothing treatment | החלקה | تمليس / كيراتين |
| Perm | long-lasting curl | סלסול | not verified |
| Extensions | added hair | תוספות שיער | وصلات شعر (not verified) |
| Treatment, mask | conditioning care | טיפול / מסכה | علاج (not verified) / ماسك |
| Fade | men's cut, short to shorter | פייד | not verified |
| Beard trim | shaping the beard | עיצוב זקן | تحديد لحية (not verified) |
| Hot-towel shave | traditional wet shave | גילוח (not verified for the full term) | حلاقة ذقن (not verified) |
| Price list, menu | the list of services and prices | מחירון | قائمة الأسعار |
| No-show | booked and did not come | הברזה (slang; not verified for formal use) | not verified |
| Chair rental | a stylist renting a place in a salon | השכרת עמדה / כיסא | not verified |

Notes on language:

- "Service menu" is the trade's word for the price list. Visitors say "prices".
- UK and US English differ: fringe/bangs, blow-dry/blowout, colour/color, tint/color. Pick one by the salon's country.
- Words to avoid unless the customer said them and can back them: "best", "number one", "award-winning", "organic", "chemical-free", "damage-free", "guaranteed".
- Medical words (treats hair loss, cures dandruff) turn a salon claim into a health claim. Do not write them.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the salon's country before it is relied on.

### Applies almost everywhere

- **Privacy notice.** Needed as soon as the site collects a name and phone (a contact form or a booking). It says who collects, what, why, how long it is kept and how to ask for deletion.
- **Appointment history is personal data.** Notes about a client (allergies, a skin reaction, a medical condition affecting hair) may count as health data, which is more strictly protected in many places. Default: do not collect notes of that kind through the product.
- **Photos of clients** need consent before publication.
- **Terms.** If the product takes bookings or money: cancellation, deposit, refund and late-arrival rules, shown before the visitor commits.
- **Marketing messages** (offers by SMS or email) generally need the person's prior agreement. Appointment reminders are a different thing from marketing; keep them separate.
- **Reviews** must be real. Invented or selectively edited reviews are treated as misleading advertising in many jurisdictions.

### Israel

- Accessibility: businesses serving the public are required to make their websites accessible and to publish an accessibility statement with a contact for accessibility requests, under the Equal Rights for Persons with Disabilities Law and its service-accessibility regulations, with Israeli Standard 5568 (based on WCAG 2.0 AA) as the technical reference. Exemptions exist for very small businesses by turnover. The exact thresholds and current standard version: not verified.
- Privacy: the Protection of Privacy Law applies; Amendment 13 came into force in August 2025 and widened enforcement. What it requires of a one-person salon: not verified.
- Prices: consumer law requires displayed prices to be the full price including VAT. Whether and how this applies to a "from" price on a website: not verified.
- Marketing messages: the "spam law" (section 30A of the Communications Law) requires prior consent for advertising by SMS or email, with an easy way to unsubscribe. Details: not verified.
- Cancellation of a transaction made at a distance (online prepayment, vouchers): the Consumer Protection Law gives cancellation rights with capped fees. How this applies to a booked service slot: not verified.
- Gift vouchers: there are rules on minimum validity. Details: not verified.
- Licensing: whether a hair salon or barbershop needs a municipal business licence today: not verified.
- Pricing by gender for the same service may be prohibited discrimination under the Prohibition of Discrimination in Products, Services and Entry into Places of Entertainment and Public Places Law. Safer default: price by hair length or by time. Not verified.

### European Union and United Kingdom

- GDPR (EU) and UK GDPR apply to booking data. Consent is needed for non-essential cookies (ePrivacy rules in the EU, PECR in the UK). One reference, Hare & Bone, shows a cookie-consent table on its home page (observed 2026-11-21).
- Displayed consumer prices must include VAT: believed true in both; not verified.
- Distance-selling cancellation rights have an exception for services booked for a specific date in some sectors. Whether a salon appointment falls under it: not verified.
- Allergy patch tests before colour: commonly required by colour manufacturers' instructions and by salon insurers, typically 48 hours before. Whether it is a legal duty: not verified.
- Accessibility: the European Accessibility Act applies from June 2025 to certain consumer services with an exemption for microenterprises. Whether a salon booking page is in scope: not verified.
- Hairdressing is not a licensed profession in the UK; it is in several EU countries (for example a master qualification in Germany). Not verified.

### United States

- Cosmetology and barbering require a state licence, and the salon usually needs an establishment licence. Rules differ by state. Some states expect the licence number to be displayed. Not verified per state.
- The Americans with Disabilities Act is applied by courts to business websites in many cases; there is no single federal technical standard for private businesses. Not verified.
- Privacy law is by state (for example California). Small businesses are often below the thresholds. Not verified.
- Text-message marketing needs prior express consent under the TCPA. Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page, a terms page and an accessibility statement. It marks each as a draft that needs review.
- The product never states that the site "complies with" a named law.
- The product asks which country the salon is in before generating any legal page.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, services and prices, team, gallery, about, how to find us, contact details, policies, legal pages. These work with a phone link as the only action. This is a complete and honest product for a salon that books by phone or message.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Price list | "Prices on request - call us", never an empty table | n/a | Shows the date it was last updated |
| Gallery | section hidden | broken image hidden, not shown as a broken icon | |
| Team | section hidden; for one person, About instead | | |
| Reviews | section hidden | | Never filled with placeholders |
| Hours | cannot be empty (mandatory fact) | | "Open now / closed now" needs the salon's time zone |
| Map | address as text always shown | if the map fails, the text address and a link remain | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Contact or callback form | stores name, phone, message; alerts the salon | n/a | button shows "sending" and cannot be pressed twice | "Not sent - please call" with the phone number | visitor sees "received", and what happens next | visitor writes; only the salon reads |
| Booking request (salon confirms by hand) | stores the request; alerts the salon | no free times this week: "Nothing free this week - call us or see next week" | slots show a placeholder, never an empty calendar that looks like "fully booked" | "Could not load times - call us" | status "requested", told plainly it is not confirmed yet | visitor sees only their own request; salon sees all |
| Live booking (instant confirmation) | services with durations, stylists with hours, closures, existing appointments | same as above | same | if the slot was taken meanwhile: "That time was just taken - here are the nearest" | confirmed only after the server saved it; the visitor gets a confirmation they can keep | visitor: own appointments; stylist: own diary; owner: everything |
| Cancel or change by the visitor | a way to identify the visitor without a password (a link in the confirmation) | no upcoming appointments: say so | | link expired: show the phone | cancellation frees the slot at once and alerts the salon | only through the personal link |
| Owner's diary | list of the day and week | "No appointments today" | | never show a stale diary without saying it is stale | every change saved at once, with who changed it | owner and staff only, behind a login |
| Owner edits content (prices, hours, closures) | an edit screen | | | a failed save says so and keeps what was typed | visible on the public site right after saving | owner only |
| Reminders | a sending channel (SMS, email or a messaging app) and consent | | | a failed send is shown to the owner | | sent only for confirmed, not cancelled, appointments |

### Needs accounts

- The owner always needs one, as soon as anything is editable or any booking is stored.
- Staff need them only if each stylist manages their own diary.
- Visitors should not need one to book. A phone number and a link are enough. A visitor account is justified only for repeat-booking features.

### Needs payments

- Deposit on booking, prepaid services, gift vouchers, retail products.
- Each brings refunds, receipts, failed-payment states and the cancellation law of the salon's country (see Legal).
- Default: no payments. A deposit is added only when the customer asks for it and has stated the policy (mandatory fact 12).

### Using an existing booking system

Many salons already use an external booking system; several of the references link out to one from a "Book" button. In that case the product is a content site, the main action is that link, and the product owns no appointment data. Ask before building a second diary. The failure mode is the link breaking silently (see section 5).

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-21 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos, icons and navigation thumbnails.

**Curation.** Chosen by the author from known London, US and UK salon businesses, not from a search-result list. No awwwards.com category was consulted for this file; none of these is claimed as an award winner. All seven are in English, in Latin script.

**Limit.** All seven are multi-location or upmarket businesses in the UK and the US. No single-chair neighbourhood salon site was verified. The skeletons below are therefore a ceiling for structure, not a picture of the typical customer.

Verified: 7.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.spokeandweal.com | 2026-11-21 | US salon group, booking-first. Order: headline with the list of services and two actions (schedule online, see the menu) - strip of city names - mission paragraph - ten numbered principles - founder - services as five numbered cards, each with a price range and a "Book" link - press - social feed prompt - booking block that explains a card holds the appointment and is charged after the visit - flagship address and typical hours. Prices are shown as ranges and "by consultation". Extraction: 7 images, about 4,800 characters. |
| 2 | https://www.larryking.co.uk | 2026-11-21 | London salon group with its own product line. Top navigation splits Salons / Shop / About / Discover; "Book an appointment" is repeated in the navigation and the hero. Order: two-way choice (book the salon, shop the range) - short salon description - location tiles - a press quote - founder - longer press quotes - social - newsletter signup with a discount - new product - blog. Service pages are split into colour, styling, treatments. Extraction: 31 images, about 11,000 characters. |
| 3 | https://www.bullerandrice.com | 2026-11-21 | Three London salons. Order: images - one-sentence positioning - "Our salons" with a short paragraph per location followed by full address, landline, mobile and email for each - lifestyle store - footer repeating all three addresses and booking emails - press logos. Contact details per location are in plain text on the home page. Extraction: 8 images, about 3,400 characters. |
| 4 | https://www.taylortaylorlondon.com | 2026-11-21 | London salon group. Order: award line and one-sentence invitation - four image-led blocks, each one heading and one sentence (salons, services, about, media) - own product line - social feed - footer with salons, company, contact, and a combined terms-and-privacy link. Very little text per block. Extraction: 26 images, about 8,200 characters including navigation. |
| 5 | https://www.hareandbone.co.uk | 2026-11-21 | UK salon group. Order: three image-and-statement blocks (vision, colour, individuality) - three action tiles (services, contact a salon, book online or by phone) - newsletter - footer with disclaimer, terms, privacy. States that salons and pricing are gender neutral. A cookie-consent table is present on the page. Extraction: 10 images, about 3,200 characters. |
| 6 | https://www.hershesons.com | 2026-11-21 | London salons with a large product shop. Navigation is product categories first, then Stores, then Book Now. Order: hero with two actions (shop, book) - mission - "our spaces" with a book action - a review score with its count and source - a long run of press quotes, each with an image. Shows how a salon site changes when retail leads. Extraction: 92 images, about 27,000 characters, most of it shop navigation. |
| 7 | https://www.ruffians.co.uk | 2026-11-21 | UK barbershop group with products. Order: product grid - one featured product - "Book now" with a choice of location - story - products summary naming the four shop locations. Almost all images, very little text. Extraction: 69 images, about 5,800 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.sallyhershberger.com | 2026-11-21 | Loads, but the extracted home page contains leftover site-builder placeholder text and almost no content. Not a quality reference. |
| https://www.edwardsandco.com.au | 2026-11-21 | Loads, but the extraction returned only a fragment (founder line, three reviews, one product). Not enough to describe the structure. |
| https://www.blindbarber.com | 2026-11-21 | Loads. Product catalogue dominates; the barbershop is one navigation item ("Visit"). Kept out to avoid a third retail-led example. |

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the salon (booking-first)

For a salon whose site has one job: get the visitor to book or call. Default for this domain.
From references 1, 3, 5, with the price presentation of 1 and the contact block of 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action button (book / call); on a phone the action stays reachable | action is the most prominent element after the name | yes |
| 1 | Opening | one sentence saying what kind of place this is and where; the main action; a second, quieter link to prices | one heading, one line, two actions | yes |
| 2 | Services and prices | categories in order; each service on one line: name, short note, price or "from" or "on consultation"; duration if known | category heading over rows; price aligned at the end of the row | yes |
| 3 | The place and the people | one short paragraph; team with first names and roles, or an About block for one person | one heading, short text, faces if consented | optional |
| 4 | Work | gallery of the salon's own work | images only, optional captions | optional, hidden when empty |
| 5 | What clients say | real reviews with source and count | at most three shown | optional, hidden when empty |
| 6 | Before you book | cancellation, deposit, patch test, late arrival | short list, plain words | required if any policy exists |
| 7 | Find us | address as text, map link, phone, hours per day with closed days named, parking and entrance note; repeated per location if several | this block must be complete without the map | yes |
| 8 | Final action | the main action again | one line, one button | yes |
| 9 | Footer | name, phone, address again; privacy, terms, accessibility statement; social link | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1, 3 and 5 returned 7 to 10 images each against roughly 3,000 to 5,000 characters). Roughly one image for every two to three short text blocks. Text carries the prices and the practical details; images carry the proof. The first screen can be one large image with a single line over it, or text only if the salon has no good photo. Not confirmed in a rendered view.

### Skeleton B: the salon with a shop

For a salon that also sells products or vouchers online. Use only when the customer actually sells online; otherwise Skeleton A with a short "products we use" line.
From references 2, 6, 7; the two-way opening is from 2 and 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | navigation in two groups, Salon and Shop; the book action stays visible in both | book action never hidden behind the shop menu | yes |
| 1 | Opening | two equal choices: book an appointment, shop | two actions of equal weight | yes |
| 2 | The salon | one paragraph; locations as tiles, each leading to address, hours and booking | tile per location | yes |
| 3 | Services | categories as links to service pages with prices | short on the home page, full on its own page | yes |
| 4 | Proof | a review score with count and source, or press quotes with the publication named | one strong item first, more below | optional |
| 5 | Shop highlights | a few products or a voucher | image, name, price | yes for this skeleton |
| 6 | Founder or team | who is behind it | one image, a few lines | optional |
| 7 | Find us and book | as section 7 of Skeleton A | | yes |
| 8 | Footer | as Skeleton A, plus delivery and returns for the shop | | yes |

Image-to-text ratio: **estimate**. Image-led: references 6 and 7 returned 92 and 69 images. Most blocks are an image with a name and a price or a single sentence. Not confirmed in a rendered view.

Risk seen in references 6 and 7: when the shop leads, the route to booking gets longer. If the customer's income is mainly from appointments, use Skeleton A.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working stylist in either language. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file. The items marked "not verified" are the least certain; the rest are also unconfirmed.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. No single-chair or neighbourhood salon reference was verified. No barbershop reference other than reference 7.
6. Booking defaults in section 4 (15-minute step, 2 hours ahead, 60 days ahead, 24-hour reminder) are estimates, not taken from a source.
7. The claim that many salons use an external booking system is from the references' "Book" links, whose targets were not followed.
8. Sub-pages of the references (service menus, team pages, booking flows) were not fetched; observations are of home pages only.
9. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
