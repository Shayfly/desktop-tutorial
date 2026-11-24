# Fitness trainer

Covers: people and small businesses that are paid to train other people's bodies: personal trainers (one to one, in a studio, a gym, a park or the client's home), small-group training, boutique class studios (HIIT, strength, boxing, Pilates, reformer, yoga, cycling) and online coaching.
Does not cover: physiotherapy, sports medicine, dietetics or anything diagnosed or treated (use `clinic.md`); selling supplements or sportswear as the main business (use `clothing-shop.md` or `catalogue-collection.md`); a one-off race or sports event (use `event.md`).
Written 2026-11-22. References checked 2026-11-22 (the brief named 2026-11-21; the fetches actually ran on 2026-11-22). Template: [README.md](README.md).

## 1. Objects

A trainer sells **attention and accountability over time**. A single session is rarely the product; a course of sessions, a pack, a membership or a programme is. Everything else follows: a session has a length and a capacity, a pack has a number of credits and an expiry, a membership renews, and a client has a starting point that must be known before training starts.

### Trainer or studio (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "North Strength Studio" |
| What kind of training | required | personal training, small group, classes, online coaching, or a mix |
| Who it is for | required | beginners, women over 50, athletes, pre- and post-natal, everyone |
| Where training happens | required | a studio address; "in a gym I rent space in"; "outdoors in a named park"; "at your home within an area"; "online only" |
| Phone or messaging number | required | a number people can call or message |
| How to start | required | message, call, free consultation request, book a class online, buy an intro offer |
| Availability or timetable | required | "Mon-Fri 06:00-20:00 by appointment", or a weekly class timetable |
| Email | optional | |
| Social account | optional | often where the videos already are |
| Qualifications and insurance | optional, never invented | only what the customer can name and show |
| Languages spoken | optional | |
| Facilities | optional | showers, lockers, towels, parking, step-free access |
| Year started, short story | optional | |

### Location (only when there is more than one, or when training moves)

Address, access note, opening hours and booking link, repeated per location. An outdoor location has a meeting point and a bad-weather rule instead of an address. A "comes to you" trainer has a service area (towns or a radius) instead of an address.

### Coach (team member)

| Field | Required | Example |
|---|---|---|
| Display name | required | first name is enough |
| Role | optional | head coach, trainer, Pilates instructor |
| What this person teaches | optional | not every coach teaches every class |
| Qualifications | optional, never invented | only as stated and evidenced by the customer |
| Working hours | optional on the page, required for one-to-one online booking | |
| Photo | optional | only with the person's consent |
| Short bio, specialities | optional | |
| Price level | optional | some businesses price senior coaches higher |
| Taking new clients | optional | |

A one-person business has one coach, and the Team section is replaced by an About section.

### Offer (what can be bought)

| Field | Required | Example |
|---|---|---|
| Name | required | "One-to-one session", "Small group (max 4)", "Reformer class", "12-week online programme" |
| Kind | required | single session, class, pack of credits, membership, programme, assessment, consultation |
| Format | required | in person, online live, online self-paced, outdoor |
| Length of one session in minutes | required for anything bookable | 45, 50, 60 |
| Group size | required for group offers | 1, up to 4, up to 20 |
| Price | optional, see rule 4 | 60 |
| Price type | required when a price is shown | per session, per pack, per month, per programme, "from", "on request" |
| What is included | optional | assessment, nutrition guidance, app access, check-ins |
| Level | optional | beginner, all levels, advanced |
| Who it is not for | optional | "not suitable during pregnancy without clearance" (only if the customer says so) |
| Intro offer | optional | first class price, first session free; one per person (rule 10) |
| Currently offered | required, default yes | an offer can be paused without being deleted |

### Pack and membership

| Field | Required | Example |
|---|---|---|
| Number of credits, or "unlimited" | required for a pack | 10 sessions |
| Which offers a credit can be used for | required | any class; one-to-one only |
| Expiry | required for a pack | 3 months from purchase; must be stated (rule 8) |
| Billing period | required for a membership | monthly |
| Minimum term | optional | 3 months |
| Renews automatically | required for a membership | yes or no; shown before purchase (rule 9) |
| Notice to cancel | required for a membership | 30 days; whatever the customer decides, shown before purchase |
| Freeze allowed | optional | injury, travel, pregnancy |

### Class type and class session (only for studios with a timetable)

| Object | Fields |
|---|---|
| Class type | name (required), description in one paragraph (required), length (required), level, what to bring, intensity, which coaches teach it |
| Class session | class type (required), date and start time in the studio's time zone (required), coach (required), room or location (optional), capacity (required), places booked (derived), status: scheduled, cancelled, coach changed |

### Booking

| Field | Required | Example |
|---|---|---|
| What: a class session or a one-to-one slot | required | |
| Client name | required | |
| Client phone or email | required | to confirm, remind and tell them about changes |
| Status | required | requested, confirmed, waitlisted, cancelled in time, late cancelled, no-show, attended |
| Paid with | required when payments exist | credit from a pack, membership, single payment, pay at the studio |
| Notes | optional | "first time", "knee injury - will tell the coach" (see Legal on health data) |

### Client and health screening (only when the product stores clients)

| Field | Required | Notes |
|---|---|---|
| Name and contact | required | |
| Emergency contact | optional | the customer decides |
| Health questionnaire (often called a PAR-Q) | decided by the customer | Health data. Collected only if the customer wants it, stored only with explicit consent, seen only by the coach. See Legal |
| Goals | optional | |
| Measurements and progress photos | optional | Health and body data. Never public. Never used in marketing without separate consent |
| Date of birth or "is a minor" | required if children are trained | a minor needs a parent's consent and contact |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Programme (online coaching) | weeks, workouts, exercises (name, sets, reps, rest, video), check-in schedule | Delivered through an app or a client area. A large feature; see Site vs app |
| Result story | text, client's chosen name, what changed, time taken, before/after photos, consent (required), date | Only real clients, with written consent. No health outcome claims unless the customer can back them (rule 15) |
| Review | text, first name or initials, date, source, rating with count | Only real reviews, with their source |
| Closure | date or range, reason (optional) | Holidays, coach away. Overrides the timetable or availability |
| Policy | cancellation window, late-cancel fee, no-show, waitlist, lateness, minimum age, what to bring, bad weather | Each optional. If one exists it is shown before booking |
| Gift card | value or offer, expiry, how to redeem | Optional. Involves payments |
| Product | name, price, in stock | Optional. Shakes, merchandise. If it becomes the main thing, this is a shop |

Relations: a class session is one instance of one class type, taught by one coach, at one location. A booking belongs to one client and one session or slot. A pack belongs to one client and is consumed by bookings. A coach teaches some class types and works at some locations.

## 2. Rules

1. Every offer has exactly one kind (single session, class, pack, membership, programme, assessment, consultation).
2. A bookable session or class has a length in positive minutes. The end time is start plus length.
3. A group offer or class session has a capacity. Confirmed bookings may never exceed it; this is checked when the booking is saved, not only in the display.
4. A price is optional, but its absence is explicit: "price on request" or "ask about prices", never blank and never zero. A free offer says "free" only if it really costs nothing and has no hidden commitment.
5. Every price shows its currency and what it is per (session, pack, month, programme).
6. A pack price shows the number of sessions. If the per-session price is shown, it is calculated from the pack, not typed in.
7. A class cannot be booked after it has started. How far ahead and how late a visitor may book are settings with declared defaults.
8. A pack has an expiry, stated before purchase. An expired credit is not silently removed; the client can see it expired and when.
9. A membership that renews automatically says so before purchase, with the price, the billing day, the minimum term and how to cancel. Cancelling is never harder than joining (see Legal).
10. An intro offer is limited to one per person if the customer says so; the limit is stated on the offer.
11. A cancellation inside the stated window frees the place and returns the credit. A late cancel or no-show follows the stated policy, and the policy is shown at the confirm step.
12. When a waitlisted client is moved into a class, they are told at once, and the time they have to cancel without penalty is stated. A client is never charged a late-cancel fee for a place they were never told about.
13. A cancelled class session tells every booked client, returns their credits, and stays visible as "cancelled" on the timetable.
14. A closure overrides the timetable and the weekly availability. On a closed day nothing can be booked.
15. No medical claim. The product does not write that training treats, cures or reverses a condition, or that a client came off medication, unless the customer supplies the claim and can back it, and even then it is flagged for review. Result stories carry the client's consent and the time taken.
16. A before/after photo is published only with the client's written consent, unedited, and labelled with the time between the photos.
17. A qualification, certification, insurance or award is shown only if the customer named it. Never filled in.
18. Health questionnaires, injury notes, measurements and progress photos are visible only to the client, their coach and the owner. They are never shown on a public page.
19. A minor can only be booked with a parent's or guardian's consent and contact details, if the business trains minors at all.
20. Times are shown in the studio's local time. Online live sessions also show the client's local time.
21. An outdoor session has a bad-weather rule, and a cancellation for weather reaches every booked client before they set out.
22. The main action (book, enquire, call or message) is reachable from every page without scrolling back to the top on a phone.
23. The phone number is a tappable link on a phone. The address opens a map; an outdoor meeting point has a map pin and a description.
24. Stock photographs of people training are not presented as the business's own clients or space.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Business name | "What is your training business called? If it is just you, is it your own name?" | Without a name people cannot find it or recommend it. |
| 2 | Kind of training | "What kind of training do you do: one-to-one, small groups, classes, online coaching?" | A visitor decides in seconds whether this is what they are looking for. |
| 3 | Who it is for | "Who do you train? Anyone in particular you are best for?" | People look for "someone like me". Without it the page speaks to nobody. |
| 4 | Where | "Where does training happen: a studio address, a gym, a park, the client's home, or online?" | Without it people cannot arrive, or do not know if you come to them. A home address may not be meant for the public. |
| 5 | Contact | "What number or address should people use to reach you?" | Without it nobody can ask a question or say they are running late. |
| 6 | How to start | "What should a new person do first: message you, book a consultation, book a class, buy a first session?" | The whole page leads to this one action. If it is wrong, the site produces nothing. |
| 7 | When | "When do you train people? Give me your days and hours, or your class timetable." | Without it people ask for times you do not work, or arrive to an empty studio. |
| 8 | Offers | "What can people buy from you? Single sessions, packs, memberships, programmes?" | Without the list the visitor does not know what they are signing up for. |
| 9 | Prices, or the decision not to show them | "What does each one cost? If you would rather discuss price in person, say so." | Price is the first question. Hiding it is allowed; inventing it is not. |
| 10 | Who is the business legally | "What is the registered business name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only when the product takes bookings or payments:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 11 | Session lengths and group sizes | "How long is each session or class, and how many people can join?" | Without it a class gets overbooked or a client is booked on top of another. |
| 12 | Cancellation and no-show | "What happens if someone cancels late or does not turn up?" | The client must know before booking, and you must be able to stand behind it. |
| 13 | Pack expiry and membership terms | "When do packs expire? Do memberships renew by themselves, and how does someone cancel?" | A surprise charge or an expired pack is the most common complaint in this trade. |
| 14 | Health questionnaire | "Do you ask new clients health questions before the first session? Do you want the site to do it?" | It protects the client and you, but it is health data and must be handled carefully. |
| 15 | Where booking alerts go | "Where should I send each new booking and cancellation: which phone or email?" | A booking nobody sees is a client standing at a locked door at 6 in the morning. |
| 16 | Minors | "Do you train anyone under 18?" | If yes, a parent must consent and be reachable. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the business.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Offer groups and order | One-to-one, Small group, Classes, Online coaching (only the groups the customer named) | Structure seen across the references | Editable list, labelled "suggested order" |
| Missing price | "Price on request" | Says openly that there is no number | Shown in the customer's review with "no price given" |
| Main action | "Message to get started", using the contact number | Works with zero setup | Labelled "default: message" |
| Page order | Skeleton A below for a trainer; Skeleton B for a class studio | Extracted from the references | Named as the default skeleton |
| "Before your first session" block | headings only: what to bring, when to arrive, tell your coach about injuries | General and harmless; the content is the customer's | Marked "draft - confirm or remove" |
| Booking opens | 7 days ahead for classes | Estimate; not verified | Setting, labelled "default" |
| Booking closes | at the class start time | Follows from rule 7 | Setting, labelled "default" |
| Waitlist | on, with a notice to the promoted client | Prevents failure mode "promoted but not told" | Setting, labelled "default" |
| Reminder | one message 24 hours before, if a sending channel exists | Estimate | Setting, labelled "default"; off until a channel exists |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Currency | the currency of the business's country | Follows from the address | Shown next to every price |
| Time zone | the business's location | Follows from the address | Shown on the timetable |
| Legal page structure | headings only: who we are, what we collect, health data, why, how long, your rights, contact | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing results section is better than an empty one | Listed for the customer as "not shown yet: results, team, reviews" |

Never a default, whatever the customer left out: prices, session lengths, class capacity, timetable, cancellation window, late-cancel fee, pack expiry, membership terms, qualifications, insurance, years of experience, client numbers, success percentages, result stories, before/after photos, reviews, ratings, "free" anything, "suitable for all levels", "safe during pregnancy", any health or weight-loss claim.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Timetable is old | Arrives for a class that no longer runs | A lost client who tells others | Ask for the timetable explicitly; show "timetable updated on"; prompt the customer each month |
| Class overbooked | More people than bikes or reformers | Someone is sent home, publicly unhappy | Rule 3, enforced at save time |
| Waitlist promotion not told | Charged a late-cancel fee for a class they did not know they were in | Dispute, chargeback, bad review | Rule 12 |
| Class cancelled, clients not told | Arrives at a dark studio at 06:30 | Anger; credit disputes | Rule 13; cancellation sends a message to every booking |
| Membership renewed by surprise | A charge they did not expect | Chargeback; in some places a legal problem | Rule 9; renewal terms on the confirm step and in the receipt |
| Pack expired silently | Credits vanish | Distrust; refund demand | Rule 8; expiry date shown in the client's view; reminder before expiry |
| Cancel is hard | Must phone or email to cancel a membership joined online | Complaint; regulatory risk | Rule 9; online cancel where online join exists |
| No health screening, client injured | Hurt in the first session | Harm to a person; liability | Mandatory fact 14; "tell your coach about injuries" on the first-visit block |
| Health data exposed | Sees their injury or weight on a shared screen or public page | Privacy breach | Rule 18; permissions in section 8 |
| Online class time in the wrong zone | Joins an hour late | Lost session | Rule 20 |
| Outdoor session cancelled for rain, not told | Stands in a wet park | Lost trust | Rule 21 |
| Health claim on the page | Expects a medical result | Disappointment; misleading advertising | Rule 15 |
| Fake or stock "transformation" | Results do not match what was shown | Distrust; legal risk | Rules 16 and 24 |
| Booking button leads to a broken external page | Taps, nothing happens | Silent loss; the customer never finds out | Check the link at publish and on a schedule |
| Payment failed but booking shown as confirmed | Turns up; not on the list | Awkward at the door | Confirmed only after payment succeeded; failed payment shown plainly |
| Enquiry form fails silently | Thinks they asked; never hears back | Lost client | A failed send says so and shows the phone number (Third Space's form carries a visible error text, observed 2026-11-22) |
| Offer ended, still on the page | Asks for a price that no longer exists | An argument at the door | Every promotion has an end date that hides it |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working trainer in either language. Regional Arabic usage varies; the terms given are common Levantine or standard usage. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Personal trainer (PT) | trains one client at a time | מאמן כושר אישי / מאמנת כושר אישית | مدرب شخصي |
| Coach, instructor | leads a session or class | מאמן / מדריך | مدرب |
| Session | one paid training time | אימון | حصة تدريبية (not verified) |
| Class | a group session on a timetable | שיעור | حصة |
| Studio | small dedicated space | סטודיו | استوديو |
| Gym | large equipped space | חדר כושר | نادي رياضي / صالة رياضية |
| Timetable, schedule | weekly class list | מערכת שעות | جدول الحصص (not verified) |
| Membership | recurring access | מנוי | اشتراك |
| Class pack, punch card | prepaid number of sessions | כרטיסייה | not verified |
| Drop-in | a single class without a membership | שיעור בודד (not verified) | not verified |
| Intro offer, trial | first-time price | שיעור ניסיון | حصة تجريبية (not verified) |
| Consultation | first talk before starting | פגישת היכרות / ייעוץ | استشارة |
| Assessment | measuring the starting point | אבחון / הערכה (not verified) | تقييم (not verified) |
| Health questionnaire (PAR-Q) | health questions before training | הצהרת בריאות | استبيان صحي (not verified) |
| Waitlist | queue for a full class | רשימת המתנה | قائمة انتظار |
| Late cancel | cancelling inside the window | ביטול מאוחר (not verified) | not verified |
| No-show | booked and did not come | אי הגעה (not verified) | not verified |
| Freeze | pause a membership | הקפאת מנוי | تجميد الاشتراك (not verified) |
| Strength training | lifting weights | אימון כוח | تدريب القوة |
| HIIT | high-intensity intervals | אימון אינטרוולים בעצימות גבוהה (HIIT) | not verified |
| Functional training | movement-based training | אימון פונקציונלי | تدريب وظيفي (not verified) |
| Pilates, reformer | method; the machine | פילאטיס, רפורמר | بيلاتس; reformer not verified |
| Yoga | | יוגה | يوغا |
| Boxing | | אגרוף | ملاكمة |
| Small-group training | 2 to about 6 people | אימון בקבוצות קטנות | not verified |
| Online coaching | remote programme with check-ins | ליווי אונליין (not verified) | تدريب عن بعد (not verified) |
| Warm-up, cool-down | | חימום, שחרור | إحماء, تهدئة (not verified) |
| Set, rep | groups and repetitions of an exercise | סט, חזרה | مجموعة, تكرار (not verified) |
| Nutrition plan | eating guidance | תפריט תזונה | خطة غذائية (not verified) |
| Body composition | fat and muscle proportions | הרכב גוף | تكوين الجسم (not verified) |

Notes on language:

- Visitors say "price" and "how much a month". The trade says "investment"; avoid it, it hides the number.
- "Session" and "class" are not the same thing. A session is usually one-to-one; a class is on a timetable with others.
- Words to avoid unless the customer said them and can back them: "guaranteed results", "lose X kg in Y weeks", "best", "number one", "elite", "certified" (without naming by whom), "doctor-approved", "safe for everyone".
- Medical words (rehab, treat, cure, reverse, diagnose, therapy) turn a training claim into a health claim. Do not write them. Physiotherapy belongs in `clinic.md`.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the business's country before it is relied on.

### Applies almost everywhere

- **Privacy notice.** Needed as soon as the site collects a name and contact (an enquiry form, a booking, a newsletter). It says who collects, what, why, how long it is kept and how to ask for deletion.
- **Health data.** A health questionnaire, injury notes, measurements, weight and progress photos are health or body data. In many places this is a specially protected category that needs explicit consent and stricter security. Default: the product does not collect it unless the customer decides to, and then only behind a login with per-client access.
- **Photos and videos of clients** need consent before publication. Before/after photos need separate, written consent.
- **Terms.** If the product takes bookings or money: cancellation window, late-cancel and no-show fees, pack expiry, membership renewal and cancellation, refunds. Shown before the visitor commits.
- **Recurring payments.** Automatic renewal is regulated in many places: clear disclosure before purchase, a reminder before renewal in some places, and cancellation as easy as sign-up. Details differ by country.
- **Liability waivers.** Common in this trade. Whether a waiver is enforceable, and what it can exclude, depends on the country and the state. Not verified anywhere.
- **Marketing messages** generally need prior agreement. Class reminders are not marketing; keep them separate.
- **Reviews and results** must be real. Invented results or reviews, or "typical" claims that are not typical, are misleading advertising in many jurisdictions.

### Israel

- Accessibility: businesses serving the public must make their websites accessible and publish an accessibility statement with a contact for accessibility requests, under the Equal Rights for Persons with Disabilities Law and its service-accessibility regulations, with Israeli Standard 5568 as the technical reference. Exemptions for very small businesses by turnover exist. Thresholds and current version: not verified.
- Sport Law: believed to require that a person training at a fitness institute provides a medical certificate or a signed health declaration before training. Whether it applies to a personal trainer working outside an institute, and the current form: not verified.
- Qualifications: whether a fitness instructor needs a recognised certificate by law today, after reforms of recent years: not verified.
- Privacy: the Protection of Privacy Law applies; Amendment 13 came into force in August 2025. Health information is treated as sensitive. What it requires of a one-person trainer: not verified.
- Consumer protection: rules on cancelling ongoing (continuing) transactions, such as memberships, and on cancelling distance transactions with capped fees. How they apply to class packs and memberships: not verified.
- Prices must be shown including VAT for consumers: believed true; not verified for "from" prices.
- Marketing messages: the "spam law" (section 30A of the Communications Law) requires prior consent. Not verified in detail.
- Business licence: whether a fitness studio needs a municipal business licence: not verified.

### European Union and United Kingdom

- GDPR (EU) and UK GDPR: health data is special-category data; processing needs a specific legal condition, usually explicit consent. Believed true; details not verified.
- Cookies: consent for non-essential cookies (ePrivacy in the EU, PECR in the UK). Several references show consent managers (Ultimate Performance, Matt Roberts Evolution, observed 2026-11-22).
- Distance contracts: a 14-day cancellation right for many online purchases, with exceptions for leisure services on a specific date. Whether a booked class or a pack falls under it: not verified.
- UK subscription contracts: new rules on subscription contracts under the Digital Markets, Competition and Consumers Act 2024 (reminders, easy exit). Commencement date and scope: not verified.
- Personal training is not a regulated profession in the UK; voluntary registers and certifications exist. Not verified for each EU country.
- Accessibility: the European Accessibility Act applies from June 2025 to some consumer services, with an exemption for microenterprises. Whether a studio booking page is in scope: not verified.

### United States

- No federal licence for personal trainers; certifications are private. Not verified per state.
- Many states have "health club" or "health spa" laws that regulate memberships (cooling-off periods, cancellation on moving or disability, bonding). Not verified per state.
- Automatic-renewal laws exist in several states (for example California). A federal "click-to-cancel" rule was adopted by the FTC in 2024 and, as far as the author knows, vacated by a court in 2025. Current state: not verified.
- One reference (solidcore) shows a California privacy notice and a "Your privacy choices" link; another (Ultimate Performance) shows a "Do Not Sell or Share My Personal Information" control (observed 2026-11-22).
- HIPAA generally covers health providers and insurers, not trainers. Not verified.
- The Americans with Disabilities Act is applied by courts to business websites in many cases. Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page, terms, a cancellation policy page and an accessibility statement. Each is marked as a draft that needs review.
- The product never states that the site "complies with" a named law.
- The product asks which country the business is in before generating any legal page.
- The product does not build a health questionnaire unless the customer asks for one and has answered mandatory fact 14.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, offers and prices, how it works, about the trainer or team, class descriptions, results (real, consented), reviews, where we train, first-visit information, policies, legal pages. These work with a message or phone link as the only action. This is a complete and honest product for a trainer who books by message.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Offers and prices | "Ask about prices - message us", never an empty table | n/a | Date last updated |
| Timetable (as a static list) | "Timetable coming soon - message us for times" | n/a | Shows "updated on"; becomes stale quietly, so prefer data (below) once it changes weekly |
| Results | section hidden | broken image hidden | Never filled with placeholders or stock photos |
| Team | section hidden; for one person, About instead | | |
| Reviews | section hidden | | Never filled with placeholders |
| Where we train | cannot be empty (mandatory fact) | if the map fails, text address or meeting point and a link remain | Outdoor: meeting point plus weather rule |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Enquiry or consultation request | stores name, contact, goal, message; alerts the trainer | n/a | button shows "sending" and cannot be pressed twice | "Not sent - please message us" with the number | visitor sees "received" and what happens next | visitor writes; only the trainer reads |
| Class timetable | class types, sessions, coaches, capacity, closures | "No classes this week" with the next week link | placeholder rows, never an empty grid that looks like "nothing on" | "Could not load the timetable - message us" | n/a | public read; owner and coaches edit |
| Class booking | timetable plus bookings, credits or payments | class full: "Full - join the waitlist" | | if the place was taken meanwhile: "That class just filled up - join the waitlist or pick another" | confirmed only after the server saved it; confirmation the client can keep | client: own bookings; coach: own classes' lists; owner: everything |
| Waitlist | ordered list per session; message channel | | | promotion message failed: shown to the owner | promotion is saved with a time stamp; client told (rule 12) | client sees own position; owner sees all |
| One-to-one booking | offers with lengths, coach hours, closures, existing bookings | "Nothing free this week - message us" | | as above | as above | as above |
| Packs and credits | purchases, credits used, expiry | "No active pack" with a buy link | | failed payment: "Payment did not go through - you have not been charged" | balance updates at once after booking or cancellation | client sees own balance and history; owner sees all |
| Membership | recurring billing, terms, cancellation | | | failed renewal shown to client and owner | cancel takes effect on the stated date and is confirmed in writing | client manages own; owner sees all |
| Health questionnaire | form, explicit consent, secure storage | | | a failed save says so and keeps what was typed | stored once, editable by the client | client and assigned coach only; never public; owner only if the customer decides |
| Online programme | workouts, exercises, videos, check-ins | "Your programme starts on <date>" | | video fails: text instructions remain | progress saved per workout | client sees own; coach sees assigned clients |
| Progress tracking | measurements, photos | "No entries yet" | | | each entry dated | client and coach only; photos never public |
| Owner edits content (offers, prices, timetable, closures) | an edit screen | | | a failed save says so and keeps what was typed | visible on the public site right after saving | owner only; coaches may edit their own classes if the customer wants |
| Reminders | a sending channel and consent | | | a failed send is shown to the owner | | sent only for confirmed, not cancelled, bookings |

### Needs accounts

- The owner always needs one, as soon as anything is editable or any booking is stored.
- Coaches need one only if they manage their own classes or clients.
- Clients need one for packs, memberships, online programmes and progress tracking. A single class booking can work with a phone number and a link.

### Needs payments

- Single classes, intro offers, packs, memberships with recurring billing, online programmes, gift cards, products.
- Each brings refunds, receipts, failed-payment states, renewal notices and the consumer law of the business's country (see Legal).
- Default: no payments. Payments are added only when the customer asks and has answered mandatory facts 12 and 13.

### Using an existing booking system

Most studios in the references send "Book" to a separate system or app: solidcore's "Book now" leads to an authenticated schedule, BXR's classes link to a separate booking site, Barry's and solidcore push an app (observed 2026-11-22). In that case the product is a content site, the main action is that link, and the product owns no booking data. Ask before building a second timetable. The failure mode is the link breaking silently (see section 5).

## 9. References

**How these were checked.** Each URL was fetched on the date shown with a page-extraction tool that returns the page's text and, for some sites, image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate. Image counts are only given where the extraction returned image references; several sites returned none, which does not mean they have no images.

**Curation.** Chosen by the author from known London and US training businesses, not from a search-result list. No awwwards.com category was consulted for this file; none of these is claimed as an award winner. All seven are in English, in Latin script.

**Limit.** All seven are multi-site or premium businesses in the UK and the US. No solo personal trainer's own site and no outdoor or home-visit trainer was verified. The skeletons below are a ceiling for structure, not a picture of the typical customer.

Verified: 7.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.ultimateperformance.com | 2026-11-22 | Personal-training gym group, enquiry-first. Navigation: personal training (in person, online), why us, client results, locations by region, "your goal" (fat loss, muscle, health, events), blog, gift. Order: headline and "Enquire now" - outcome statistics with their own claimed sources (a review count from Google) - four method blocks (training, nutrition, coaching, data) - a press quote - client stories with first names, age and kilograms lost, some naming health outcomes - "more than a gym" - goal cards - review block with score and count, each review linking to its Google source - locations - press logos - enquiry form - footer with terms, privacy, cookie policy and a modern slavery statement. An intro package with a price appears as an overlay. A US-style "Do Not Sell or Share" cookie control. Extraction: 44 images, about 31,000 characters. |
| 2 | https://www.thirdspace.london | 2026-11-22 | London health-club group. Navigation: clubs, membership, classes (timetable, on demand), personal training (find a trainer, performance lab), nutrition, sports medicine, spa, journal. Order: tagline and two actions (find your club, become a member) - four offer blocks (classes, facilities, personal training, nutrition) - list of all clubs, each with postcode and full address - class types, each a name and one paragraph - wellness services - membership enquiry with a booking-option selector. The page text includes the enquiry form's error message. Extraction: 4 images, about 9,700 characters. |
| 3 | https://www.barrys.com | 2026-11-22 | Class studio chain, first-class-first. "Book your first class" appears in the header, the middle and the end. Order: app banner - headline - "what to expect in your first workout" - the two halves of the class explained, with an alternative for people who do not run - format, pace, community - instructors: tell them before class if you are new or injured - amenities (shakes, locker rooms, shop) - community size - reviews with first names - newsletter - footer with an accessibility statement, terms, privacy, cookies, and a language selector (eight languages including Arabic). Extraction: 16 images, about 7,600 characters. |
| 4 | https://www.bxrlondon.com | 2026-11-22 | Boxing gym, membership by enquiry. Order: "Enquire" and a separate pay-per-class booking site - about paragraph - four locations as tiles - retreats - "more than a gym" (lab, clinic, personal training) - store - community posts, some with weekly class times in the subtitle. Very little text per block. |
| 5 | https://www.solidcore.co | 2026-11-22 | Reformer-based class chain, booking-first. Order: headline, "Book now" to an authenticated schedule, class length stated (50 minutes) - "new to us" link to a first-timer page - three differentiators - a new format announcement - a members-only challenge with dates - a monthly muscle-focus calendar - app download - "find a studio" - footer: FAQs, contact, manage membership, cancellation policy, privacy, gift cards, offers, paying with health savings accounts, terms, California privacy notice, privacy choices. |
| 6 | https://www.mattroberts.co.uk | 2026-11-22 | Premium personal-training and longevity club. Order: headline - "featured in" - founder story - two testimonials with first name and age - club concept - a "lab" of tests (cardiovascular, blood, bone, skin, strength, mobility, hormones, gut), each with a "learn more" - services grid (personal training, nutrition, physiotherapy, Pilates, medical concierge and tests) - tailored programmes marked "coming soon" - podcast - consent manager. Shows how a training business drifts into medical services, where claims need a clinician (see `clinic.md`). The extraction returned no image references. |
| 7 | https://www.equinox.com | 2026-11-22 | Large club chain, used as an upper bound. Order: two actions (visit a club, join today) - a time-limited joining offer with its own terms link - club count - one membership explained - class names as a list - "experiences": personal training (first session free), studio Pilates, spa, shop. The extraction ended in a loading state. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.1rebel.com | 2026-11-22 | Loads, but the home page is only a country chooser (two countries). No content to describe. |

Failed to load, not counted: https://www.roarfitness.com (2026-11-22, fetch failed).

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the trainer (enquiry-first)

For a personal trainer or a small team whose site has one job: get the visitor to make contact or book a first session. Default for this domain.
From references 1, 3 and 6: the outcome-led opening and goal cards of 1, the "what to expect" block of 3, the "how it works" steps implied by 1 and 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; one action button (message / book a consultation / call); on a phone the action stays reachable | action is the most prominent element after the name | yes |
| 1 | Opening | one sentence: what kind of training, for whom, where; the main action; a quieter link to prices | one heading, one line, two actions | yes |
| 2 | Who it is for | two to four goal or audience cards, each a heading and one sentence | equal cards | optional |
| 3 | How it works | three steps: first contact or consultation, starting point (assessment, health questions), regular sessions | numbered, one line each | yes |
| 4 | Offers and prices | each offer on one line: name, format, length, group size, price and what it is per, or "on request"; packs show the session count | offer name over details; price aligned at the end | yes |
| 5 | About the trainer, or the team | short paragraph; qualifications only as stated; faces if consented | one heading, short text | yes |
| 6 | Results | real result stories with consent and time taken | at most three; no health claims | optional, hidden when empty |
| 7 | What clients say | real reviews with source and count | at most three shown | optional, hidden when empty |
| 8 | Before your first session | what to bring, where to go, tell the coach about injuries, cancellation policy | short list, plain words | yes if any policy exists |
| 9 | Where we train | studio address, or meeting point with map and weather rule, or service area, or "online"; hours or availability | must be complete without the map | yes |
| 10 | Final action | the main action again | one line, one button | yes |
| 11 | Footer | name, contact, location again; privacy, terms, accessibility statement; social link | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only (reference 1 returned 44 image references against about 31,000 characters; reference 3 returned 16 against about 7,600). Roughly one image for every one to two short text blocks: photographs of real sessions carry the feeling, text carries the offer, the price and the practical details. Not confirmed in a rendered view.

### Skeleton B: the class studio (timetable-first)

For a studio that sells classes on a timetable. Use only when the customer runs scheduled classes.
From references 2, 3 and 5: the two-action opening of 2, the first-timer block of 3 and 5, the class-type list and location list of 2, the policy-rich footer of 5.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; "Book a class" always visible; app link if one exists | book action never hidden in a menu | yes |
| 1 | Opening | one line on the kind of class and its length; two actions: book a class, first-timer offer | two actions | yes |
| 2 | New here | what to expect, what to bring, how early to arrive, alternatives for injuries or levels | short steps | yes |
| 3 | Class types | each a name, length, level and one paragraph | list or cards | yes |
| 4 | Timetable | this week's sessions with coach and places left, or a link to the booking system | day headings over rows | yes |
| 5 | Prices | intro offer, single class, packs with expiry, memberships with renewal terms | a table; terms beside each price | yes |
| 6 | Coaches | first names, what they teach, consented photos | grid | optional |
| 7 | Locations | each with address, access note and link to its timetable | one block per location | yes |
| 8 | Facilities | showers, lockers, what is provided | short list | optional |
| 9 | What clients say | real reviews with source | at most three | optional, hidden when empty |
| 10 | Footer | FAQs, cancellation policy, manage membership, privacy, terms, accessibility statement, contact | small, grouped | yes |

Image-to-text ratio: **estimate**. Reference 2 returned only 4 image references against about 9,700 characters, mostly the club address list; reference 3 returned 16. A studio page is more text-heavy than a trainer page because the timetable, prices and locations are text. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working trainer in either language. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file. Items marked "not verified" are the least certain; the rest are also unconfirmed. In particular: the Israeli Sport Law health-declaration requirement and its scope, instructor certification in Israel, UK subscription rules commencement, the status of the US federal click-to-cancel rule.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view. Several extractions returned no image references at all.
4. No awwwards.com category was consulted; design quality is the author's prior judgement.
5. No solo personal trainer, home-visit trainer, outdoor bootcamp or online-only coach reference was verified. All seven references are premium multi-site businesses in the UK and US.
6. Booking defaults in section 4 (7 days ahead, 24-hour reminder) are estimates, not taken from a source.
7. The claim that most studios use an external booking system rests on the references' "Book" links, whose targets were not followed.
8. Sub-pages of the references (timetables, price pages, first-timer pages, cancellation policies) were not fetched; observations are of home pages only.
9. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
