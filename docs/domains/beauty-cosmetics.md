# Beauty and cosmetics

Covers: businesses that are paid to treat the surface of the body: nails (manicure, pedicure, gel, extensions), skin (facials, peels, non-medical devices), lashes and brows, waxing and threading, laser and light hair removal, make-up (in a studio or on location, including bridal), and day-spa treatments. Includes one-person studios and home-based practitioners.
Does not cover: hair cutting and colouring (use `hair-salon.md`); procedures that are medical in the customer's country, such as injections, prescription treatments and some lasers, when the business is a medical practice (use `clinic.md`); selling cosmetics as the main business (use `clothing-shop.md` or `catalogue-collection.md`).
Written 2026-11-22. References checked 2026-11-22 (the brief named 2026-11-21; the fetches actually ran on 2026-11-22). Template: [README.md](README.md).

## 1. Objects

A beauty business sells **a treatment on a person's body, done by a trained hand, in a set time**. Like a salon, the core is time with a practitioner. Unlike a salon, many treatments carry risk to the skin, eyes or health, so a treatment also has things that must be true before it can be done (no contraindication, a patch test, a consultation) and things the client must do after (aftercare).

### Business

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Studio Lumen" |
| What kind of place | required | nail studio, skin studio, lash and brow bar, beauty salon, day spa, mobile make-up artist, laser clinic |
| Address, or "by appointment at a private address", or "I come to you" with an area | required | street, number, city, floor |
| Phone or messaging number | required | |
| Opening hours per day of the week | required | Tue-Sat 10:00-19:00, closed Sun-Mon |
| How to book | required | call, message, online booking, walk-in |
| Email | optional | |
| Social account | optional | usually where the photos already are |
| Access, parking, floor | optional | |
| Payment methods | optional | |
| Languages spoken | optional | |
| Who may be treated | optional | adults only; women only; everyone (see Legal on discrimination) |
| Hygiene statement | optional, never invented | only what the customer actually does, for example "single-use files" |

### Location (only when there is more than one)

Address, phone, hours and booking link, repeated per location. One reference lists six studios, each with its own hours per day and phone; another lists about forty, each with its own "Book" button (observed 2026-11-22).

### Treatment category

| Field | Required | Example |
|---|---|---|
| Name | required | Nails, Skin, Lashes and brows, Waxing, Laser, Make-up, Massage |
| Order on the page | required | |
| Short note | optional | "All facials include a skin consultation" |

A large business may also group treatments by **concern** (acne, pigmentation, fine lines, unwanted hair). Concern is a second way into the same treatments, not a second list.

### Treatment

| Field | Required | Example |
|---|---|---|
| Name | required | "Gel manicure", "Classic lash extensions, full set", "30-minute facial" |
| Category | required | Nails |
| Price | optional, see rule 3 | 45 |
| Price type | required when a price is shown | fixed, "from", per area, per session, per course, "on consultation" |
| Duration in minutes | optional on the page, required for online booking | 45; some references show a range, such as 25-40 minutes |
| Body area | required for hair removal and some skin treatments | upper lip, underarm, full leg |
| What is included | optional | removal of old gel, cuticle care, hand massage |
| Course | optional | "6 sessions recommended, 4-6 weeks apart" |
| Needs a consultation first | optional | laser, peels, extensions |
| Needs a patch test first, and how long before | optional | lash tint, brow tint, lash extensions, laser |
| Contraindications | optional, never invented | "not during pregnancy", "not on sunburnt skin"; supplied by the customer |
| Aftercare | optional | "no sauna for 24 hours" |
| Who may perform it | optional | any therapist; a senior; a licensed or medically qualified practitioner only |
| Add-on to another treatment | optional | nail art, extra area |
| Currently offered | required, default yes | can be paused without being deleted |

### Practitioner (team member)

| Field | Required | Example |
|---|---|---|
| Display name | required | first name is enough |
| Role | optional | nail technician, lash artist, beauty therapist, esthetician, make-up artist, nurse |
| Treatments this person does | optional | not everyone does laser |
| Licence or qualification | optional, never invented | only what the customer names and can show |
| Working hours | optional on the page, required for online booking | |
| Photo | optional | only with consent |
| Price level | optional | |

A one-person studio has one practitioner, and the Team section becomes About.

### Appointment (only when the product takes bookings)

| Field | Required | Example |
|---|---|---|
| Treatment or treatments, with areas | required | |
| Practitioner, or "anyone available" | required | |
| Date and start time | required | |
| End time | derived | start plus total duration |
| Client name | required | |
| Client phone | required | to confirm and remind |
| Client email | optional | |
| Patch test date | required when the treatment needs one | must be before the appointment by the stated gap |
| Consultation form completed | required when the customer decides so | see client record |
| Status | required | requested, confirmed, cancelled by client, cancelled by business, completed, no-show |
| Deposit paid | optional | common for lash extensions and bridal make-up |

### Client record and consultation form (only when the product stores clients)

| Field | Required | Notes |
|---|---|---|
| Name and contact | required | |
| Date of birth or "is a minor" | required if age limits apply | some treatments have legal age limits (see Legal) |
| Medical history, medication, allergies, pregnancy, skin conditions | decided by the customer | Health data. Collected only with explicit consent, seen only by the practitioner. See Legal |
| Skin type, previous reactions | optional | |
| Patch test results | optional | date, product, result |
| Treatment notes per visit | optional | settings used, products used |
| Consent to treatment | required for risky treatments if the customer wants it | signed and dated |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Before/after photo | images (required), treatment, number of sessions, time between photos, consent (required), "unedited" | Proof of skill, and the most misused object in this domain (rule 16) |
| Course or package | treatment, number of sessions, price, validity, interval | Laser and skin courses are usually sold this way |
| Membership | monthly price, what it includes, renewal, cancellation | Three references sell monthly facial memberships (observed 2026-11-22) |
| Review | text, first name or initials, date, source, rating with count | Only real reviews |
| Closure | date or range | Overrides weekly hours |
| Policy | cancellation notice, late arrival, deposit, patch test, age, redo or fix-up period, aftercare | Each optional; if one exists it is shown before booking |
| Gift card | value or treatment, expiry | Involves payments |
| Product | name, brand, price, in stock | Optional. If it becomes the main thing, this is a shop |

Relations: every treatment belongs to one category and may be tagged with several concerns. A practitioner does some treatments. A course is a number of appointments of one treatment. A patch test belongs to one client and one product, and has a date.

## 2. Rules

1. Every treatment belongs to exactly one category.
2. A treatment name appears once. Variants (areas, lengths, full set or infill) are price rows of one treatment, not separate treatments.
3. A price is optional, but its absence is explicit: "price on consultation" or "ask us", never blank and never zero.
4. A starting price says "from". A per-area price names the area. A course price names the number of sessions.
5. Every price shows its currency. A promotional price shows its end date; a "was" price must be a price really charged before (see Legal).
6. A duration is a positive number of minutes. A treatment booked online must have one; a range is allowed on the page but the booking uses the longest value.
7. An appointment's end time is start plus the total duration of its treatments.
8. Two confirmed appointments for the same practitioner may not overlap. Two appointments may not use the same room or device at the same time if the customer says there is only one.
9. An appointment may only start inside the practitioner's hours and the opening hours, and must end before closing.
10. A treatment that needs a patch test cannot be confirmed until a patch test is recorded at least the stated time before it. The visitor is told before booking, with the gap.
11. A treatment that needs a consultation cannot be booked online directly; the consultation is booked first.
12. Contraindications and aftercare are shown on the treatment, in plain words, before booking, when the customer has supplied them. They are never invented.
13. A treatment with a legal age limit cannot be booked for someone under that age; the age question is asked before the booking is confirmed.
14. A treatment the law reserves for a licensed or medical practitioner is offered only if the customer confirms who performs it and that they hold the licence. The product never adds such a treatment on its own.
15. No medical claim. The product does not write that a treatment cures acne, removes scars permanently, is "painless" or "risk-free", or gives permanent results, unless the customer supplies and can back the claim, and then it is flagged for review.
16. A before/after photo is published only with written consent, unedited, with the number of sessions and the time between photos.
17. A review is shown only if it is real, with its source. No star rating without a count and a source.
18. A deposit, a cancellation fee or a non-refundable part is shown before the visitor confirms.
19. Prices are not set by gender for the same treatment where the law forbids it; price by area or time instead (see Legal).
20. The main action (book, call, message) is reachable from every page without scrolling back to the top on a phone.
21. The phone number is a tappable link on a phone. The address opens a map.
22. Stock photographs of nails, skin or faces are not presented as the business's own work.
23. A product claim (vegan, cruelty-free, "free of" a list of chemicals) appears only if the customer supplies it.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Business name | "What is your studio called?" | Without a name people cannot find it or recommend it. |
| 2 | Kind of place | "What do you mainly do: nails, skin, lashes and brows, laser, make-up, or a mix?" | A visitor decides in seconds whether this place does what they want. |
| 3 | Where | "Where do clients come to? Give me the full address, or tell me if you work from home or travel to clients." | Without an address people cannot arrive. A home address may not be meant for the public. |
| 4 | Phone | "What number should clients call or message?" | Without it people cannot book or say they are late. |
| 5 | Opening hours | "Which days are you open, and from when to when on each day?" | Without hours people arrive at a closed door. |
| 6 | How to book | "How do clients book today: phone, message, an online system, or walk in?" | The whole page leads to this one action. |
| 7 | Treatments | "List the treatments you do, as you would say them to a client." | Without the list the visitor does not know whether to come. |
| 8 | Prices, or the decision not to show them | "What does each treatment cost? If you prefer not to show prices, say so." | Price is the most common question. Hiding it is allowed; inventing it is not. |
| 9 | Who performs regulated treatments | "Do you do any treatment that needs a licence or a medical professional, such as laser, peels, or injections? Who does them?" | If the law reserves a treatment, the site must not offer it without the right person behind it. |
| 10 | Who is the business legally | "What is the registered business name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only when the product takes online bookings:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 11 | Duration of each treatment | "How long does each treatment take, including set-up?" | Without it clients are booked on top of each other. |
| 12 | Patch tests and consultations | "Which treatments need a patch test or a consultation first, and how long before?" | Without it a client arrives and is turned away, or has a reaction. |
| 13 | Contraindications and aftercare | "Is there anyone you cannot treat, or anything clients must avoid before or after?" | The client must know before booking; it is about their safety. |
| 14 | Who works when | "Who works on which days, and who does which treatments?" | Without it a client is booked with someone who is not there or not trained for it. |
| 15 | Cancellation and deposit | "What happens if a client cancels late or does not show? Do you take a deposit?" | The client must know before booking, and you must be able to stand behind it. |
| 16 | Consultation form | "Do you want clients to fill in a health and consent form before their first visit?" | It protects the client and you, but it is health data. |
| 17 | Where booking alerts go | "Where should I send each new booking: which phone or email?" | A booking nobody sees is a client at the door with no chair. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Category names and order | the categories the customer's treatments fall into, in the order Nails, Skin, Lashes and brows, Waxing, Laser, Make-up | Standard structure in the references | Editable list, labelled "suggested order" |
| Which category a treatment falls in | by the treatment's name | Wrong placement is visible and easy to fix | Customer confirms the grouped list |
| Missing price | "Price on consultation" | Says openly that there is no number | Shown in the customer's review with "no price given" |
| Main action | "Call to book", using the phone number | Works with zero setup | Labelled "default: phone" |
| Page order | Skeleton A below; Skeleton B for skin and laser clinics | Extracted from the references | Named as the default skeleton |
| "Before you book" block | headings only: patch tests, consultations, cancellation, arriving late | General; content is the customer's | Marked "draft - confirm or remove" |
| Slot step for booking | 15 minutes | Estimate; not verified | Setting, labelled "default" |
| Earliest booking | 2 hours ahead | Estimate | Setting, labelled "default" |
| Latest booking | 60 days ahead | Estimate | Setting, labelled "default" |
| Reminder | one message 24 hours before | Estimate | Setting, labelled "default"; off until a sending channel exists |
| Language and direction | the language of the conversation | The customer chose it | Shown, changeable |
| Currency | the currency of the business's country | Follows from the address | Shown next to every price |
| Legal page structure | headings only: who we are, what we collect, health information, why, how long, your rights, contact | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing gallery is better than an empty one | Listed for the customer as "not shown yet: gallery, team, reviews" |

Never a default, whatever the customer left out: prices, durations, patch-test gaps, contraindications, aftercare, age limits, licences, qualifications, who may perform a treatment, hygiene claims, product claims (vegan, cruelty-free, "non-toxic", "free of"), "painless", "permanent", "suitable for all skin types", before/after photos, reviews, ratings, awards, press quotes, deposit and cancellation rules.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| No patch-test notice | Turned away at the door, or has a reaction | A wasted trip, or harm to a person | Rule 10; mandatory fact 12 |
| Contraindication not shown | Treated while pregnant or on a medication that reacts | Harm; liability | Rule 12; mandatory fact 13 |
| Under-age client booked for a restricted treatment | Refused at the door, or treated illegally | Legal risk | Rule 13 |
| Regulated treatment offered by an unqualified person | Possibly injured | Harm; legal risk; the business may be closed | Rule 14; mandatory fact 9 |
| Hours on the site are old | Arrives at a closed door | Lost client | Ask hours explicitly; show "hours last updated" |
| Price list old, or promotion expired but still shown | Pays more than the site said | Argument at the till; misleading pricing | Promotions carry an end date that hides them; one reference shows several dated offers on its home page (observed 2026-11-22) |
| "From" price read as the price | Bill much higher than expected | Distrust | Say what "from" depends on (area, length, practitioner) |
| Course price read as a single session | Thinks one session costs the course price, or the reverse | Dispute | Rule 4 |
| Double booking | Two clients for one chair or one laser | One leaves unhappy | Rule 8, at save time |
| Treatment too short in the system | Next client waits; lash set rushed | Late day, poor result | Rule 6 uses the longest duration |
| Booking saved, studio never told | Arrives; nobody expects them | The worst case in this domain | Mandatory fact 17; "requested" until confirmed |
| Deposit taken, policy unclear | Feels cheated by a late-cancel charge | Chargeback | Rule 18 |
| Before/after photo edited or not the studio's | Results do not match the pictures | Distrust; misleading advertising | Rules 16 and 22 |
| Health form exposed | Sees their medical details where others can | Privacy breach | Section 8 permissions |
| Medical or "permanent" claim | Expects a result the treatment cannot give | Complaint; advertising breach | Rule 15 |
| Gendered price list | Two prices for the same area by sex | Discrimination complaint in some places | Rule 19; one reference splits laser by "women" and "men" (observed 2026-11-22) |
| Shop leads, booking hidden | Cannot find how to book a treatment | Lost bookings | In Skeleton A the book action is never behind the shop; two references lead with products (observed 2026-11-22) |
| Booking button leads nowhere | Taps; nothing happens | Silent loss | Check the link at publish and on a schedule |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working practitioner in either language. Regional Arabic usage varies; the terms given are common Levantine or standard usage. Many trade words in both languages are English loanwords. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Beauty salon | the business | מכון יופי | صالون تجميل |
| Beautician, beauty therapist, esthetician (US) | treats skin and body | קוסמטיקאית | خبيرة تجميل (not verified) |
| Nail technician | does nails | מניקוריסטית | not verified |
| Manicure, pedicure | | מניקור, פדיקור | مانيكير, باديكير |
| Gel polish | long-wear polish cured under a lamp | לק ג'ל | جل (loanword; not verified) |
| Nail extensions | added length | בניית ציפורניים | تركيب أظافر (not verified) |
| Infill | maintenance of extensions | מילוי (not verified) | not verified |
| Facial | skin treatment of the face | טיפול פנים | تنظيف بشرة (common usage; not verified as exact) |
| Peel | chemical exfoliation | פילינג | تقشير |
| Microneedling | needle treatment for skin | מיקרונידלינג | not verified |
| Lash extensions | added lashes | הארכת ריסים / תוספות ריסים | تركيب رموش (not verified) |
| Lash lift | curling natural lashes | הרמת ריסים | not verified |
| Brow shaping | | עיצוב גבות | تحديد الحواجب (not verified) |
| Tint | colouring lashes or brows | צביעה | صبغ (not verified) |
| Threading | hair removal with thread | עיצוב בחוט | خيط (not verified) |
| Waxing | | שעווה / הסרת שיער בשעווה | إزالة الشعر بالشمع |
| Laser hair removal | | הסרת שיער בלייזר | إزالة الشعر بالليزر |
| Make-up artist | | מאפרת | خبيرة مكياج |
| Bridal make-up | | איפור כלה | مكياج عروس |
| Consultation | talk and skin check before treatment | ייעוץ | استشارة |
| Patch test | allergy test before treatment | בדיקת רגישות (not verified) | not verified |
| Contraindication | a reason not to treat | התווית נגד | موانع الاستعمال (not verified) |
| Aftercare | instructions after treatment | הוראות לאחר טיפול (not verified) | not verified |
| Course of treatments | several sessions | סדרת טיפולים | جلسات (not verified as a term) |
| Skin type | | סוג עור | نوع البشرة |
| Acne | | אקנה | حب الشباب |
| Pigmentation | dark patches | פיגמנטציה | تصبغ (not verified) |
| Injectables | botulinum toxin, fillers | הזרקות | حقن |
| Day spa | | ספא | سبا |

Notes on language:

- "Treatment menu" is the trade's word for the price list. Visitors say "prices".
- UK and US English differ: beautician or beauty therapist (UK), esthetician (US); colour/color. Pick one by the business's country.
- Words to avoid unless the customer said them and can back them: "painless", "permanent", "risk-free", "guaranteed", "medical-grade", "clinically proven", "dermatologist-approved", "non-toxic", "organic", "best".
- Medical words (treats, cures, heals, removes scars, diagnoses) turn a beauty claim into a health claim. Do not write them.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the business's country before it is relied on.

### Applies almost everywhere

- **Privacy notice.** Needed as soon as the site collects a name and phone.
- **Consultation forms are health data.** Medical history, medication, allergies, pregnancy and reactions are health data, specially protected in many places. Default: the product does not collect them unless the customer decides to, and then only behind a login with per-practitioner access.
- **Photos of clients** need consent before publication; before/after photos need separate, written consent.
- **Who may perform what.** In many countries some treatments (injections, prescription-strength peels, some lasers) are reserved for licensed or medical practitioners, and advertising some of them to the public may be restricted. Rules differ widely by country.
- **Age limits** exist for some treatments in some countries.
- **Terms**: cancellation, deposit, refund, course validity and fix-up period, shown before the visitor commits.
- **Price promotions**: "was" prices and limited-time offers are regulated in many places.
- **Marketing messages** generally need prior agreement.
- **Reviews and before/after photos** must be real. Edited results are misleading advertising in many jurisdictions.

### Israel

- Accessibility: websites of businesses serving the public must be accessible, with an accessibility statement and a contact for accessibility requests, under the Equal Rights for Persons with Disabilities Law and its regulations, with Israeli Standard 5568 as the technical reference. Small-business exemptions exist. Not verified in detail.
- Privacy: the Protection of Privacy Law applies; Amendment 13 came into force in August 2025. Health information is sensitive. Not verified for a one-person studio.
- Injections (botulinum toxin, fillers): believed to be restricted to physicians (and in some cases dentists). Not verified.
- Laser and light devices for hair removal: believed to be regulated by the Ministry of Health (device approval and operator requirements). Not verified.
- Whether a beautician needs a licence, and whether a beauty salon needs a municipal business licence: not verified.
- Pricing by gender for the same service may be prohibited discrimination under the Prohibition of Discrimination in Products, Services and Entry into Places of Entertainment and Public Places Law. Safer: price by area. Not verified.
- Displayed consumer prices must include VAT: believed true; not verified. Spam law (section 30A of the Communications Law) for marketing messages: not verified in detail.

### European Union and United Kingdom

- GDPR and UK GDPR: consultation-form data is special-category health data. Believed true; details not verified.
- Cookies: consent for non-essential cookies (ePrivacy in the EU, PECR in the UK).
- England: the Botulinum Toxin and Cosmetic Fillers (Children) Act 2021 bans these procedures for under-18s for cosmetic purposes. Believed true; details not verified.
- UK: prescription-only medicines (which includes botulinum toxin) may not be advertised to the public; the advertising regulator enforces this against clinics. Believed true; not verified.
- UK: a licensing scheme for non-surgical cosmetic procedures was enabled by the Health and Care Act 2022. Whether and when it applies: not verified. Sunbed use under 18 is banned in the UK: believed true; not verified.
- UK clinics doing regulated medical activities are registered with the Care Quality Commission (England) and equivalents in Wales and Scotland; one reference states it is regulated by all three (observed 2026-11-22).
- Distance-selling cancellation rights, with exceptions for services on a specific date: whether a booked treatment falls under it is not verified.
- Accessibility: the European Accessibility Act from June 2025, microenterprise exemption; scope for a studio booking page not verified.

### United States

- Estheticians, nail technicians and cosmetologists need state licences, and salons usually an establishment licence. Rules differ by state. Not verified per state.
- "Med spas" offering injections or medical lasers are subject to state medical-practice rules (supervising physician, who may inject). Not verified per state.
- Cosmetic versus drug claims: a product or treatment claimed to treat a condition may be regulated as a drug or device by the FDA. Not verified for services.
- Gender-based pricing for the same service is prohibited in some states and cities (for example California, New York). Not verified in detail.
- Privacy law is by state; one reference shows a privacy policy and contraindications page in the footer (observed 2026-11-22). Text-message marketing needs prior express consent under the TCPA. Not verified.
- The Americans with Disabilities Act is applied by courts to business websites in many cases; one reference shows an "Enable Accessibility" control (observed 2026-11-22). Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page, terms, an aftercare page and an accessibility statement, each marked as a draft that needs review.
- The product never states that the site "complies with" a named law, and never states that a treatment is "safe", "approved" or "regulated" unless the customer supplies the evidence.
- The product asks which country the business is in before generating any legal page, and before showing any treatment the law may reserve (mandatory fact 9).

## 8. Site vs app

### Content pages (no data, no accounts)

Home, treatments and prices, before you book (patch tests, contraindications, aftercare), team, gallery of the studio's own work, about, how to find us, policies, legal pages. With a phone link as the only action this is a complete and honest product for a studio that books by phone or message.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Treatment menu | "Prices on request - call us", never an empty table | n/a | Shows the date it was last updated |
| Before/after gallery | section hidden | broken image hidden | Each item carries consent and session count |
| Aftercare and contraindications | hidden only if the customer supplied none; then the treatment says "ask us before booking" | | Never invented |
| Team | section hidden; for one person, About instead | | |
| Reviews | section hidden | | Never placeholders |
| Promotions | hidden after the end date | | Never shown without an end date |
| Map | address as text always shown | text address and link remain if the map fails | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Contact or callback form | stores name, phone, message; alerts the studio | n/a | button shows "sending" and cannot be pressed twice | "Not sent - please call" with the number | visitor sees "received" and what happens next | visitor writes; only the studio reads |
| Booking request (confirmed by hand) | stores the request; alerts the studio | no free times: "Nothing free this week - call us" | placeholder, never an empty calendar that looks fully booked | "Could not load times - call us" | status "requested", told plainly it is not confirmed | visitor sees only their own request |
| Live booking | treatments with durations, practitioners with hours, patch-test rules, closures, existing appointments | as above | as above | slot taken meanwhile: "That time was just taken - here are the nearest" | confirmed only after the server saved it; a confirmation the client can keep, including aftercare and patch-test reminders | client: own; practitioner: own diary; owner: everything |
| Patch test tracking | test date per client and product | "No patch test on record - book one first" | | | stored with date | client sees own; practitioner and owner see all |
| Consultation and consent form | form, explicit consent, secure storage | | | a failed save keeps what was typed | signed and dated; editable only by creating a new version | client and practitioners only; never public |
| Courses and packages | purchases, sessions used, validity | "No active course" | | | balance updates after each visit | client sees own; owner sees all |
| Memberships | recurring billing, terms, cancellation | | | failed renewal shown to client and owner | cancel confirmed in writing with the effective date | client manages own |
| Owner's diary | day and week view | "No appointments today" | | never show a stale diary without saying so | every change saved with who changed it | owner and staff only |
| Owner edits content | an edit screen | | | a failed save says so and keeps what was typed | visible on the public site right after saving | owner only |
| Reminders | channel and consent | | | failed send shown to owner | | only for confirmed appointments |

### Needs accounts

- The owner always needs one, as soon as anything is editable or any booking is stored.
- Staff need one only if each practitioner manages their own diary or reads client forms.
- Clients do not need one to book a single appointment. A client account is justified for courses, memberships and stored consultation forms.

### Needs payments

- Deposits (common for extensions and bridal), prepaid courses, memberships, gift cards, products.
- Each brings refunds, receipts, failed-payment states and consumer law (see Legal).
- Default: no payments. A deposit is added only when the customer asks and has stated the policy (mandatory fact 15).

### Using an existing booking system

Several references send "Book" to an external booking flow or app and keep a "Manage appointments" or "Login" link (observed 2026-11-22). In that case the product is a content site whose main action is that link, and it owns no appointment or client data. Ask before building a second diary. The failure mode is the link breaking silently.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and, for some sites, image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate. Image counts are given only where the extraction returned image references.

**Curation.** Chosen by the author from known UK and US beauty businesses, not from a search-result list. No awwwards.com category was consulted for this file; none is claimed as an award winner. All seven are in English, in Latin script.

**Limit.** All seven are multi-location businesses, five of them in the US. No single-room studio, no lash or brow specialist and no make-up artist's own site was verified. Two of the seven lead with a product shop. The skeletons are a ceiling for structure, not a picture of the typical customer.

Verified: 7.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.skinlaundry.com | 2026-11-22 | US laser-facial chain. Header: "Book now" and "Login". Navigation: treatments (each with a one-line description), enhancements (add-ons), memberships, results (before and after, including a teen-acne gallery), locations, shop, blog. Body: several dated promotions, each showing a price against a stated value - a list of about forty locations, each with full address, phone and its own "Book now" - "what makes us different" - memberships - products - client stories - blog - footer: about, locations, contraindications, terms, shipping and returns, FAQs, privacy. About 29,000 characters; the extraction returned no image references. |
| 2 | https://www.heydayskincare.com | 2026-11-22 | US facial studios. An "Enable accessibility" control at the top. First-facial offer, with "pricing varies by studio". Header: book and manage appointments. Order: offer - new treatment - "book a facial" - four claims about practitioners (licensed, trained), customisation, results, home products - process - practitioner first names - membership perks - "explore my location". A full product shop by category, concern and brand sits in the navigation. Extraction: 42 images, about 16,000 characters. |
| 3 | https://www.glowbar.com | 2026-11-22 | US studios with one product: a 30-minute facial. Order: one-line positioning - what the facial is (licensed practitioners, no add-ons) - membership, with the non-member price in one sentence - find a studio - studios coming soon with full addresses - home products - press quotes with the publication named - client quotes. Extraction: 34 images, about 6,900 characters. A clear example of a single-treatment menu. |
| 4 | https://www.sknclinics.co.uk | 2026-11-22 | UK dermatology and aesthetic clinic group, trust-first. Order: headline - four trust figures (award, regulated, number of clinics, patient rating) - why us: medical staff, years in operation, evidence-based treatment, regulated by the three UK regulators named - clinic finder - "an advisor will call you back to book your consultation". No prices and no booking calendar on the home page. A short page: roughly 2,000 characters of text (counted by eye, estimate). |
| 5 | https://www.townhouse.co.uk | 2026-11-22 | UK and US nail salons with their own polish range. The home page leads with product kits and prices, then a lookbook, press logos, services as four tiers each with a duration range and no price, products, polish claims, a review score with count and a few short reviews, a founder story, and a first-booking discount code. Shows a duration range per service instead of a single number. |
| 6 | https://www.dearsundays.com | 2026-11-22 | New York nail studios with a product line. Order: first-visit discount - "Book appointment" - press quotes - product promises (vegan and "free of" claims) - shop by category - "visit our salons": six studios, each with address, hours per day and phone - product reviews - products - stockists - Instagram. Mixes salon and shop on one page. |
| 7 | https://www.therapieclinic.com | 2026-11-22 | US arm of a laser and med-spa chain, offer-first. Order: sale banner - deals with current and "was" prices - referral programme - treatment categories, with laser hair removal split into separate entries for women and for men, and cosmetic injections - "book a free consultation" - scale figures - social posts - story - featured treatments - locations - press - newsletter - app - accepted payment methods including pay-later. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.chillhouse.com | 2026-11-22 | Loads, but the home page is a product shop (press-on nails, polish) with 152 image references; the nail studio is mentioned only as history. Not a service reference. |
| https://www.vanityprojects.com | 2026-11-22 | Loads, but the domain now shows an unrelated architecture-marketing business. Not the nail salon expected. |

Failed to load, not counted: https://www.paintboxnails.com, https://www.blinkbrowbar.com, https://www.ever-body.com (2026-11-22, fetch failed).

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the beauty studio (booking-first)

For a nail, lash, brow, waxing or general beauty studio whose site has one job: get the visitor to book or call. Default for this domain.
From references 3, 5 and 6: the single clear offer of 3, the duration per service of 5, the per-location hours and phone of 6, and the contraindications link of 1.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action button (book / call); stays reachable on a phone | action most prominent after the name | yes |
| 1 | Opening | one sentence: what kind of studio and where; the main action; a quieter link to prices | one heading, one line, two actions | yes |
| 2 | Treatments and prices | categories in order; each treatment on one line: name, short note, duration, price or "from" or "on consultation"; areas as price rows | category heading over rows; price at the end of the row | yes |
| 3 | Before you book | patch tests (with the gap), consultations, contraindications and aftercare links, deposit, cancellation | short list, plain words | yes if any applies |
| 4 | Work | gallery of the studio's own work, with consent | images only, optional captions | optional, hidden when empty |
| 5 | The people | first names, roles, licences as stated; About for one person | short | optional |
| 6 | What clients say | real reviews with source and count | at most three | optional, hidden when empty |
| 7 | Find us | address as text, map link, phone, hours per day with closed days named, entrance note; per location if several | complete without the map | yes |
| 8 | Final action | the main action again | one button | yes |
| 9 | Footer | name, phone, address; privacy, terms, aftercare, accessibility statement; social link | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (reference 3 returned 34 image references against about 6,900 characters). Image-heavy: work photographs are the proof in this domain, and the price list is the main text. Roughly one image per short text block. Not confirmed in a rendered view.

### Skeleton B: the skin or laser clinic (consultation-first)

For a business selling skin treatments, laser or courses where the first step is a consultation and trust comes before price. Use when mandatory fact 9 names regulated treatments or when most treatments need a consultation.
From references 1, 2, 4 and 7: the trust line of 4, the concern-based entry of 1 and 2, the call-back consultation of 4 and 7, the results gallery and contraindications of 1.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; "Book a consultation" always visible | | yes |
| 1 | Opening | one line on what the clinic does; consultation action | one heading, one action | yes |
| 2 | Why trust us | who performs treatments and their qualifications as stated; regulator registration only if real | three or four short facts, each with its source | yes |
| 3 | Treatments | by category, with a second way in by concern; each treatment: what it is, sessions usually needed, price type | cards linking to a treatment page | yes |
| 4 | How it works | consultation, patch test if needed, treatment, aftercare, follow-up | numbered steps | yes |
| 5 | Results | before/after with consent, sessions and time between photos | gallery | optional, hidden when empty |
| 6 | Prices | from-prices, per area, per course; membership if any, with renewal terms | table | yes, or "on consultation" |
| 7 | Safety | contraindications, aftercare, who cannot be treated | short list, link to full page | yes |
| 8 | Locations | address, hours, phone per clinic | one block each | yes |
| 9 | Footer | privacy, terms, contraindications, accessibility statement, contact | small | yes |

Image-to-text ratio: **estimate**. Reference 4 is text-led (roughly 2,000 characters, estimate; no image references returned); reference 2 returned 42 image references against about 16,000 characters. A clinic page carries more text than a studio page because safety and qualifications are text. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working practitioner in either language. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file. In particular: who may inject or operate lasers in Israel, the England under-18 ban details, UK advertising of prescription-only medicines, the UK licensing scheme status, US state licensing and gender-pricing rules.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view. Several extractions returned no image references.
4. No awwwards.com category was consulted; design quality is the author's prior judgement.
5. No single-room studio, home-based practitioner, lash or brow specialist, threading bar or make-up artist reference was verified.
6. Booking defaults in section 4 (15-minute step, 2 hours ahead, 60 days ahead, 24-hour reminder) are estimates.
7. Booking-link targets in the references were not followed; the claim that studios use external booking systems rests on the "Book" and "Manage appointments" links only.
8. Sub-pages (treatment menus, aftercare, contraindications, membership terms) were not fetched; observations are of home pages only.
9. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
