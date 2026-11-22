# Musician and band

Covers: solo musicians, bands, ensembles and DJs who want people to listen, come to shows, join a mailing list, buy music or merchandise, or book them. Includes both the **recording and touring artist** (releases and shows) and the **band for hire** (weddings, parties, corporate events).
Does not cover: music lessons (use `tutor-courses.md`); venues and festivals (use `event.md`); a merchandise shop as the main business (use `clothing-shop.md`); record labels and catalogues of many artists (use `catalogue-collection.md`).
Written 2026-11-22. References checked 2026-11-22 (the brief named 2026-11-21; the fetches actually ran on 2026-11-22). Template: [README.md](README.md).

## 1. Objects

A musician's site sells **attention to the music and presence at a moment**. Two shapes exist:

- **The artist**: the site points to releases (listen, pre-order) and shows (tickets). Time matters: a release has a date, a show has a date and a status, and yesterday's show must not look like tomorrow's.
- **The band for hire**: the site sells a performance at the visitor's event. The first step is "check your date"; the product is a line-up, a set length and what is included.

Many acts are both.

### Act (the artist or band)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "The Night Lanterns" |
| Shape | required | artist (releases and shows), band for hire, or both |
| What the music is, in one line | required | "soul and funk party band", "jazz trio", "indie four-piece" |
| Home base | optional | city or region |
| Members | optional | names and instruments, only with each member's consent; a band is not required to list members |
| Short bio | optional | |
| Official listening links | required for an artist | streaming profiles, video channel, own store |
| Contact routes | required | booking, management, press, label, general; each a role address, not a member's private address |
| Social accounts | optional | |
| Photos | optional | only photos the act may use, with the photographer's credit |

### Release

| Field | Required | Example |
|---|---|---|
| Title | required | |
| Type | required | single, EP, album, live recording |
| Release date | required | a past date means "out now"; a future date means pre-order or pre-save |
| Cover art | optional | with rights to use it |
| Tracks | optional | title, length, credits |
| Listening links | required once released | official profiles only |
| Pre-order or pre-save link | optional before release | |
| Formats for sale | optional | vinyl, CD, download, with prices if sold on the site |
| Label | optional | |
| Credits | optional | writers, producers, players |

### Show (gig)

| Field | Required | Example |
|---|---|---|
| Date | required | |
| Doors and stage time, in the venue's local time | optional | doors 19:00, on stage 20:30 |
| Venue name | required | |
| City and country | required | |
| Support act or guests | optional | |
| Ticket link | required unless free or "tickets at the door" | the official seller only (rule 6) |
| Ticket price | optional | if shown, says whether fees are included |
| Status | required | announced, on sale, few left, sold out, waitlist, cancelled, postponed, rescheduled (with the new date) |
| Age policy | optional | all ages, 14+, 18+ |
| Accessible tickets | optional | how to request them |
| Public or private | required | a private event (a wedding) is never listed publicly |

A **tour** is a named list of shows. Shows are grouped by tour, by region or by month.

### Booking enquiry (band for hire)

| Field | Required | Example |
|---|---|---|
| Event date | required | |
| Event location or venue | required | town, venue name if known |
| Event type | required | wedding, birthday, corporate, festival |
| Line-up wanted | optional | duo, six-piece, eight-piece |
| Timings | optional | arrival, sets, finish |
| Budget | optional | |
| Contact name, phone, email | required | |
| Status | required | new, available, not available, quoted, held, booked (contract and deposit), played, cancelled |

### Line-up and package (band for hire)

| Field | Required | Example |
|---|---|---|
| Name | required | "Party band", "Jazz duo for drinks", "Ceremony piano" |
| Number of musicians and instruments | required | six: two vocals, guitar, keys, bass, drums |
| Set lengths | required | two 50-minute sets plus encores |
| What is included | required | PA, dancefloor lighting, playlists between sets, first dance learned, speech microphones |
| Price | optional, see rule 3 | "example package from", with the area it is based on |
| Travel | optional | "included within an area; quoted beyond" |
| Sound limits | optional | a quiet or silent set-up for venues with limiters |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Video | title, platform link or file, date | Live clips are the proof for a band for hire |
| Merchandise product | name, price, sizes, stock, shipping | If sold on the site, it is a shop with shop duties (see Legal) |
| Mailing list signup | email, country (optional), consent text, date | The single most valuable thing an artist collects; consent must be explicit (rule 11) |
| News item | title, date, text | Must carry its date; old news is archived |
| Press quote | quote, publication, date | Only real quotes with the publication named |
| Review or testimonial | text, first names or initials, event type, date, source | For hire acts. Only real, with consent |
| Song list | title, original artist | For hire acts. Cover songs; see Legal for recordings |
| Electronic press kit | bio, approved photos with credits, logo, technical rider, stage plot, contacts | Often a private page or file for promoters |
| Support or donation | amount, purpose, matching offers | Seen at a nonprofit ensemble (observed 2026-11-22) |

Relations: a release has tracks and links; a tour has shows; a show has one venue and one status; a booking enquiry may become a private booking but never a public show.

## 2. Rules

1. A show's date and time are shown in the venue's local time, with the day of the week, and the date format matches the site's language (day-month or month-day is never ambiguous: use the month's name).
2. A show whose date has passed moves to "past shows" automatically. It is never displayed under "upcoming".
3. A show's status is explicit. A sold-out show says "sold out", a cancelled show says "cancelled" and keeps no active ticket link, a rescheduled show gives the new date and says old tickets remain valid only if the customer says so.
4. A price is optional, but its absence is explicit: "ask for a quote", never blank and never zero. A ticket price says whether booking fees are included.
5. An example package price for a band for hire names what it includes and the area it assumes; travel outside it is "quoted".
6. Ticket links point only to the official seller the act or promoter named. Never to a resale or secondary site unless the act names it as the official resale.
7. Listening links point only to the act's official profiles, confirmed by the customer. An act with a common name is checked for a same-name artist.
8. A release with a future date shows "pre-order" or "pre-save" and the date; on the date it switches to "out now" with listening links.
9. A private booking (a wedding, a corporate party) never appears in the public show list.
10. A member's personal phone or email is never published. Contact goes to role addresses (booking, management, press).
11. A mailing-list signup states what will be sent and that the person can unsubscribe, and is not pre-ticked. A download or "unlock" in exchange for an email says so before the email is entered.
12. A photo is used only with the right to use it, and the photographer's credit is shown where the customer wants it.
13. A press quote or testimonial is real, attributed to its source, and not edited to change its meaning.
14. Recordings of cover songs are published only if the customer confirms they have the rights or a licence (see Legal). Lyrics are not reproduced without permission.
15. A band-for-hire availability answer is not a booking. "Available" means "free on that date today"; a booking exists only after the stated contract or deposit step.
16. Audio and video never play automatically with sound.
17. The main action (listen, tickets, or check your date) is reachable from every page without scrolling back to the top on a phone.
18. News and announcements carry their date. An announcement older than its event is archived.
19. Stock photographs of musicians or crowds are not presented as the act's own.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Act name | "What is the band or artist name, exactly as you write it?" | Without the exact name people cannot find you, and a misspelling sends them to someone else. |
| 2 | What the site is for | "What do you most want visitors to do: listen, come to shows, join your list, buy something, or book you for an event?" | The whole page is built around one main action. |
| 3 | The music in one line | "How would you describe your music to someone who has never heard it?" | A visitor decides in seconds whether to press play. |
| 4 | Where to listen | "Where can people hear you: give me the links to your official profiles or videos." | Without real links the site sends fans to nothing, or to a same-name stranger. |
| 5 | Contact for bookings | "Who should promoters or clients contact, and at which address or number?" | Without it nobody can book you. |
| 6 | Shows, or the decision not to list them | "Do you have shows coming up? For each: date, venue, city, and the official ticket link." | A wrong date or a broken ticket link sends a fan to the wrong night. |
| 7 | Photos | "Which photos may we use, and who took them?" | You need the right to publish them, and photographers expect credit. |
| 8 | Who is responsible legally | "What name should appear as responsible for the site and its mailing list?" | The privacy notice must name who collects fans' details. |

Needed only for a band for hire:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 9 | Line-ups | "Which line-ups can people book: how many musicians, which instruments?" | Clients choose by size and sound. |
| 10 | Set lengths and what is included | "How long do you play, and what do you bring: sound system, lights, playlists, microphones for speeches?" | Clients compare bands on exactly this. A missing PA on the night is a disaster. |
| 11 | Area and travel | "Where are you based and how far do you travel? Is travel included?" | A quote that ignores distance is wrong. |
| 12 | Price approach | "Do you want to show prices, example packages, or only quotes?" | Price is the first question. Hiding it is allowed; inventing it is not. |
| 13 | How a booking is confirmed | "What makes a booking final: a contract, a deposit, both?" | The client must know when the date is really theirs. |
| 14 | Where enquiries go | "Where should I send each date enquiry?" | An enquiry answered late is a date given to another band. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the act.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Page order | Skeleton A for an artist, Skeleton B for a band for hire | Extracted from the references | Named as the default skeleton |
| Main action | artist: "Listen"; band for hire: "Check your date" | Matches the references | Labelled "default" |
| Empty shows list | "No shows announced - join the list to hear first" | Honest empty state | Shown in the customer's review |
| Past shows | moved automatically to a collapsed "past shows" section | Rule 2 | Setting, labelled "default" |
| Date format | month as a word, day of week, venue's local time | Avoids day-month confusion (rule 1) | Shown |
| Listening link labels | the platform's own name | Neutral | Editable |
| Mailing list | off until the customer names a sending service | Collecting emails nobody sends to breaks trust | Listed as "not shown yet: mailing list" |
| Missing price (for hire) | "Ask for a quote" | Says openly there is no number | Shown with "no price given" |
| Language and direction | the language of the conversation | The customer chose it | Shown, changeable |
| Legal page structure | headings only: who we are, mailing list, what we collect, your rights, contact; plus shop terms if merchandise is sold | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | Better than empty | Listed as "not shown yet: videos, press, merchandise" |

Never a default, whatever the customer left out: show dates, venues, ticket links, ticket prices, release dates, listening links, member names, bios, press quotes, testimonials, chart positions, play counts, follower numbers, "sold out" claims, awards, package prices, set lengths, what is included, travel area, song lists.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Past show listed as upcoming | Plans a night that already happened | Distrust; the act looks inactive | Rule 2 |
| Ambiguous date (03/04) | Goes on the wrong day | A missed show | Rule 1 |
| Cancelled show still selling | Buys a ticket for a show that will not happen | Refund chaos | Rule 3 |
| Ticket link to a reseller | Pays far above face value, or gets a void ticket | Harm to the fan; anger at the act | Rule 6. One reference warns that tickets bought elsewhere may be cancelled (observed 2026-11-22) |
| Listening link to a same-name artist | Hears someone else | Lost fan | Rule 7 |
| Site is an empty shell to anything but a full browser | A search preview or a slow phone shows only a menu | Lost visitors; looks abandoned | Serve shows, releases and contact as plain content. Three loaded band sites returned only navigation or one line of text (observed 2026-11-22) |
| Abandoned site injected with spam | Gambling links on the band's page | Reputation damage; search penalty | Keep the platform updated or take the site down; one loaded band site contained injected gambling links (observed 2026-11-22) |
| The obvious domain belongs to someone else | Types the band name and lands on an unrelated page | Lost fans | Ask the customer which domain they own; one tried domain showed an unrelated personal page (observed 2026-11-22) |
| Mailing list collected without consent | Receives emails they never asked for | Complaint; legal risk | Rule 11 |
| Private event shown publicly | Strangers turn up at a wedding | Real harm to the client | Rule 9 |
| Member's private number published | Calls at night from strangers | Harm to a person | Rule 10 |
| "Available" read as "booked" | Client assumes the date is held; band takes another booking | Lost wedding music | Rule 15 |
| Package price without area or inclusions | Quote much higher than the page | Distrust | Rule 5 |
| No PA or lighting stated | Venue has none on the night | Event without sound | Mandatory fact 10 |
| Autoplaying audio | Sound blares in an office or on a bus | Leaves at once | Rule 16 |
| Enquiry form fails silently | Thinks they asked; never hears back | Lost booking | A failed send says so and shows a direct contact |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working musician in either language. Many music-industry words are English loanwords in both languages. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Band | | להקה | فرقة موسيقية |
| Musician | | מוזיקאי / מוזיקאית | موسيقي |
| Singer | | זמר / זמרת | مغني / مغنية |
| Gig, show, concert | a live performance | הופעה | حفلة |
| Tour | a run of shows | סיבוב הופעות | جولة (not verified as the music term) |
| Venue | where the show happens | מקום ההופעה | مكان الحفل (not verified) |
| Tickets | | כרטיסים | تذاكر |
| Sold out | | אזל / נמכר עד תום (not verified) | نفدت التذاكر (not verified) |
| Support act | plays before the main act | מופע חימום | not verified |
| Doors | time the venue opens | פתיחת דלתות (not verified) | not verified |
| Album | | אלבום | ألبوم |
| Single | one released song | סינגל | أغنية منفردة (not verified) |
| EP | short release | EP / מיני-אלבום (not verified) | not verified |
| Release date | | תאריך יציאה (not verified) | تاريخ الإصدار (not verified) |
| Pre-order, pre-save | | הזמנה מוקדמת (pre-save: not verified) | not verified |
| Streaming | | סטרימינג (loanword) | بث (not verified as the music term) |
| Merchandise (merch) | | מרצ'נדייז (loanword; not verified) | not verified |
| Mailing list | | רשימת תפוצה | قائمة بريدية |
| Manager | | מנהל אישי | مدير أعمال |
| Booking agent | sells the act's shows | סוכן הופעות (not verified) | not verified |
| Press kit (EPK) | material for promoters and press | not verified | not verified |
| Technical rider, stage plot | technical needs and stage layout | ריידר (loanword; not verified) | not verified |
| Set, setlist | a block of songs; the list | סט, רשימת שירים (setlist: not verified) | not verified |
| Cover song | someone else's song | קאבר | not verified |
| Line-up | who is playing | הרכב | تشكيلة (not verified) |
| Wedding band | | להקה לחתונות / להקת אירועים | فرقة أعراس (not verified) |
| First dance | | ריקוד ראשון (not verified) | not verified |
| DJ | | די ג'יי | دي جي |
| Sound system (PA) | | הגברה | نظام صوت (not verified) |

Notes on language:

- Fans say "tickets" and "when are they playing near me"; the trade says "dates" and "on sale". Use both on the shows section.
- UK and US English differ: gig/show, colour/color, "on sale"/"tickets available". Pick one by the act's country.
- Words to avoid unless the customer said them and can back them: "legendary", "award-winning", "number one", "sold out" (unless it is), "as heard on", play counts and follower numbers.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the act's country before it is relied on.

### Applies almost everywhere

- **Privacy notice.** Needed as soon as the site collects an email (mailing list, ticket alerts, downloads) or an enquiry. It names who collects, what, why, how long and how to unsubscribe or ask for deletion.
- **Mailing-list consent.** Marketing emails generally need prior opt-in in the EU, UK and Israel; the US uses an opt-out model with conditions. An email gate for a free download is a marketing signup and must say so.
- **Copyright in the music.** Publishing a recording of a cover song generally needs a licence from the song's publisher (often a mechanical or synchronisation licence for video). Embedding official players from streaming services is generally how artists share music without hosting files. Not verified per country.
- **Lyrics** are protected text; reproducing them needs permission from the publisher.
- **Photos** belong to the photographer unless assigned; publishing needs a licence and usually a credit.
- **Ticket resale.** Many countries regulate secondary ticketing and above-face-value resale. One reference states that transfer and resale are only through the official face-value platform (observed 2026-11-22).
- **Merchandise sold on the site** makes the act a shop: prices with tax as required, delivery, returns, a withdrawal right for distance sales in some places. One reference's footer carries terms, returns and exchanges, shipping and a "withdrawal request" link (observed 2026-11-22).
- **Performing for hire**: a written contract with deposit, cancellation, timings, power and space needs, sound limits and what happens if the band cannot play.

### Israel

- Accessibility: websites of businesses serving the public must be accessible, with an accessibility statement and a contact, under the Equal Rights for Persons with Disabilities Law and its regulations, with Israeli Standard 5568 as the technical reference. Whether a musician's site counts as a business serving the public, and small-business exemptions: not verified.
- Privacy: the Protection of Privacy Law applies to a mailing list; Amendment 13 came into force in August 2025. Not verified for a musician's list.
- Marketing messages: the "spam law" (section 30A of the Communications Law) requires prior consent for advertising by email or SMS. Believed to apply to a band's newsletter; not verified.
- Copyright: the Copyright Act 2007; collective licensing through ACUM for authors and composers. How it applies to cover recordings on a band's site: not verified.

### European Union and United Kingdom

- GDPR and UK GDPR apply to mailing lists and enquiries. Cookies: consent for non-essential cookies (ePrivacy, PECR); embedded players may set cookies. Not verified in detail.
- UK: the Consumer Rights Act 2015 sets information duties on secondary ticket resale. Believed true; not verified.
- Distance-selling withdrawal rights apply to merchandise; tickets for a dated event are usually excluded. Not verified.
- Copyright collecting societies (for example PRS for Music in the UK) license performance and recording rights. Not verified for a band's own site.
- Accessibility: the European Accessibility Act from June 2025 covers some e-commerce; microenterprise exemption; scope for a band's merch store: not verified.

### United States

- CAN-SPAM sets rules for commercial email (identification, opt-out, physical address). Believed true; not verified in detail.
- Text-message signups (one reference shows a text-message number on its home page, observed 2026-11-22) fall under the TCPA, which requires prior express consent for marketing texts. Not verified.
- Mechanical licences for cover recordings are available under a statutory licence. Not verified in detail.
- Several states regulate ticket resale and ticket-price disclosure (all-in pricing). Not verified per state.
- State privacy laws (for example California) may apply above thresholds. Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page (with a mailing-list heading), shop terms if merchandise is sold, booking terms for a band for hire, and an accessibility statement, each marked as a draft that needs review.
- The product never states that the site "complies with" a named law.
- The product asks which country the act is based in before generating any legal page, and asks about rights before publishing any recording or photo.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, music (with official embedded players or links), about, videos, shows as a list, press, contact, song list and line-ups (for hire), legal pages. With an email or phone link as the only action, this is a complete and honest product for most acts.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Upcoming shows | "No shows announced - join the list to hear first" (or a contact line if there is no list) | n/a | Past shows move away automatically (rule 2), which needs either data or a date check at build time |
| Past shows | collapsed; a year with no shows is not listed | | One reference lists years with "no dates", which reads as an archive of nothing (observed 2026-11-22) |
| Music | cannot be empty for an artist (mandatory fact 4) | if an embedded player fails, a plain link remains | No autoplay |
| Videos | hidden | if the embed fails, a link remains | |
| Press, testimonials | hidden | | Never placeholders |
| Contact | cannot be empty (mandatory fact 5) | | Role addresses only |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Shows list, maintained by the act | shows with dates, statuses, links | as above | placeholder rows, never an empty list that looks like "no shows" | "Could not load shows" with a link to the official ticket seller | an edit appears publicly right after saving; status changes (sold out, cancelled) take effect at once | public read; act edits |
| Mailing-list signup | email, consent, sending service | n/a | button shows "joining" | "Could not sign you up - try again"; nothing stored on failure | "You are on the list" and what will arrive; a confirmation email if the customer chooses double opt-in | visitor writes; act reads; the visitor can unsubscribe from every email |
| Date check and enquiry (for hire) | date, place, event type, contact; alerts the band | n/a | "sending" | "Not sent - email us at" the address | "We have your date and will reply by" a time the customer sets | visitor writes; band reads |
| Enquiry pipeline (for hire) | statuses from new to booked | "No enquiries yet" | | | every change saved with time | band members the customer names |
| Availability calendar (for hire) | held and booked dates | | | | a date marked booked is never shown as free | private; public sees only "check your date" |
| Merchandise shop | products, stock, payments, shipping | "Nothing in the store right now" | | failed payment stated plainly | order confirmed only after payment | buyer sees own order; act sees all |
| Pre-save or download gate | email, consent, file | | | file fails: link to the release instead | | as mailing list |
| Act edits content | edit screen for shows, releases, news | | | failed save keeps what was typed | public right after saving | act only |

### Needs accounts

- The act (or its manager) needs one as soon as shows, news or the mailing list are edited on the site.
- Fans do not need one. A mailing-list signup is not an account.
- Buyers in a merchandise shop can check out without an account.

### Needs payments

- Merchandise, music downloads, tickets for self-promoted shows, deposits for hire bookings, donations for nonprofit ensembles.
- Default: no payments. Tickets are sold through the official seller and linked (rule 6). Merchandise is often run on a separate store platform; two references link out to their store (observed 2026-11-22).

### Using existing services

Most artists already have streaming profiles, a ticket seller and often a merchandise store elsewhere. The product links to them and owns no ticket or order data. The failure mode is a link going stale silently: a sold-out or cancelled show still linking to "buy", or a store link pointing at an empty shop.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returned the page's text only, with no image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate. Several artist sites load tour dates and players from embedded services that a text extraction does not see; where the extraction showed no dates, that is noted.

**Curation.** References 1 to 6 were chosen by the author from known artists and ensembles. References 7 and 8 (bands for hire) were found through a web search for wedding and party bands, then each home page was read in full and chosen because it is the band's own site, not an agency or directory. awwwards.com/websites/music was loaded on 2026-11-22; its listing shows mostly agency, festival and portfolio sites and gives no site addresses in the extraction, so no reference was taken from it. None of these is claimed as an award winner. All eight are in English, in Latin script, though reference 1 links to a Japanese-language FAQ.

**Limit.** References 1 to 6 are well-known acts with teams behind their sites; most of 148AI's customers will be smaller. Only two band-for-hire sites were verified, both in the UK. No solo singer-songwriter at the start of a career, no DJ and no classical soloist site was verified.

Verified: 8.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.radiohead.com | 2026-11-22 | The home page was a tour announcement. Order: one sentence announcing the shows - dates grouped by venue and city, with country - sold-out status per country - a ticket FAQ: how to get a ticket, prices including fees, fixed and not dynamic pricing, a charity amount included, transfer and resale only through the official face-value facility, tickets from other sites may be cancelled, accessible tickets by a request form, ID checks in one country - a link to the full FAQ in Japanese - mailing-list link - links to the act's archive and other projects. About 4,300 characters. |
| 2 | https://www.phoebebridgers.com | 2026-11-22 | Artist site, release and tour. Order: images and a release date - pre-order and pre-save - a photographer credit line - tour list, each row: date, venue, city and country, guest act, then "Tickets" or "Sold out - join waitlist" - newsletter form with a consent sentence - footer: home, contact, privacy - a free ringtone gated behind an email, with its own consent sentence and download instructions per phone type. About 6,000 characters. |
| 3 | https://www.bonobomusic.com | 2026-11-22 | Artist site, release-first. Order: new album "out now" - shop with the formats (vinyl editions, CD) - two tour blocks by region, each "tickets on sale now" with a poster - contact - privacy. The individual tour dates did not appear in the extracted text (likely an image or an embed). Very short. |
| 4 | https://www.arcticmonkeys.com | 2026-11-22 | Merchandise-led artist site. Order: merchandise grid with prices, one record marked sold out - "visit the store" - videos - past dates listed by year, many years showing "no dates" - newsletter with a success message - social and streaming links - store footer: terms, privacy and cookies, help, returns and exchanges, shipping, contact, withdrawal request. |
| 5 | https://www.kronosquartet.org | 2026-11-22 | Nonprofit string quartet. Order: upcoming events, each with venue and presenting organisation (dates not in the extracted text) - upcoming albums - learn more - ways to support, with a donation-matching banner - find us - one-sentence about - newsletter - buy and listen. Shows the donation path of a nonprofit ensemble. |
| 6 | https://www.gogopenguin.co.uk | 2026-11-22 | Jazz trio, artist site. Order: new release "out now" - video - about paragraph naming the members and instruments - music grid of release covers - live - contact block split into management and booking agents by territory, with role addresses - label - photo credit and site credit. A clear model of a contact block with routes by purpose and territory. |
| 7 | https://www.hotjazzbiscuits.co.uk | 2026-11-22 | Wedding and party band, enquiry-first. "Check your date" in the header and repeated. Order: one-line promise - who they are and the genres - base town and "playing UK-wide" - welcome story - testimonials with event type, linking to more reviews on Google - how they choose songs - phone-filmed clips of real performances - one public show with a ticket link - "what you actually get": live band, two 50-minute sets plus encores, two lead voices, live first dance, PA and lighting, playlists, speech microphones - song list link - five line-ups (party band, drinks reception jazz, show band, ceremony, silent band for sound-limited venues) - two example packages with prices, inclusions and the area the prices assume - travel area - "check your date" form introduced by the person who answers. |
| 8 | https://www.downforthecount.co.uk | 2026-11-22 | Swing big band that both tours and plays private events. Header: social links, gig list, album store, and the next public show with date and city. Order: press quotes, each attributed to a publication - one-paragraph description - links to live dates, news, album, store - a list of recorded tracks and videos - three line-ups, each with size and repertoire - achievements list - "as seen at" - dated news posts. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.coldplay.com | 2026-11-22 | Loads (store link, album, dated news, tour app, newsletter), but very short; left out to keep within eight references. |
| https://www.vampireweekend.com | 2026-11-22 | Loads, but returned one line: an album date, a listen link, a text-message number, tour, store and a vinyl club. Too little to describe structure. |
| https://www.bigthief.net | 2026-11-22 | Loads, but returned only the navigation (music, tour dates, live archive, videos, songwriting workshops, contact, store, mailing list) repeated three times. Empty shell to a text fetch. |
| https://www.wolfalice.co.uk | 2026-11-22 | Loads, but returned only a hidden tracking frame and six navigation words. Empty shell. |
| https://www.ezracollective.com | 2026-11-22 | Loads, but returned only a country selector and one line. Empty shell. |
| https://www.lcdsoundsystem.com | 2026-11-22 | Loads, but the page contains a long run of injected gambling and spam links after the footer. Compromised; not a reference. Used as a failure mode in section 5. |
| https://www.alt-j.com | 2026-11-22 | Loads, but shows an unrelated personal page, not the band. |

Failed to load, not counted: https://www.fleetfoxes.co, https://www.khruangbin.com, https://www.thesmile.band, https://www.porticoquartet.com, https://www.snarkypuppy.com (2026-11-22, fetch failed).

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the artist (release and shows)

For a musician or band whose site exists to get people listening and to shows. Default for an artist.
From references 2, 3, 6 and 1: the release-first opening of 2 and 3, the tour row of 2, the ticket FAQ of 1, the contact routes of 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | act name; "Listen" and "Shows" links; reachable on a phone | name first, then two actions | yes |
| 1 | Current release | title, type, date or "out now", cover; listen, pre-order or pre-save | one large image, one line, one to three actions | yes for an artist with a release |
| 2 | Shows | upcoming shows: date with weekday, venue, city, country, guests, status and ticket action; past shows collapsed | one row per show; status beside the action | yes; empty state if none |
| 3 | Listen | official profiles and embedded players, no autoplay | short | yes |
| 4 | Videos | a few official videos | grid | optional, hidden when empty |
| 5 | About | one paragraph; members only with consent | short | yes |
| 6 | Mailing list | what will be sent; email; consent sentence | one field, one button | optional, hidden until a sending service exists |
| 7 | Store | formats or merchandise, or a link to the store | a few items or one link | optional |
| 8 | Contact | booking (by territory if several), management, press, label | role addresses grouped by purpose | yes |
| 9 | Footer | privacy, store terms if any, accessibility statement, photo credits | small | yes |

Image-to-text ratio: **estimate**, from structure only (no image references returned). Image-led at the top (cover art or a photograph), then text-led for shows and contact, which must be readable and scannable. Not confirmed in a rendered view.

### Skeleton B: the band for hire (check your date)

For a band whose income is private events. Use when the customer's main action is a booking enquiry.
From references 7 and 8: the repeated date check, the "what you get" list, the line-ups and example packages of 7, the attributed press quotes and line-up sizes of 8.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; "Check your date" always visible | action most prominent after the name | yes |
| 1 | Opening | one line on what the band plays and for which events; base and travel area; the main action; a quieter "watch" link | one heading, one line, two actions | yes |
| 2 | Proof | real testimonials with event type, or press quotes with the publication named | at most three | optional, hidden when empty |
| 3 | Hear us live | real clips from real events, no autoplay | grid of videos | yes; the main proof in this shape |
| 4 | What you get | set lengths, live or backing, vocals, first dance, PA, lighting, playlists, speech microphones | short list with one line each | yes |
| 5 | Line-ups | each with size, instruments and when it suits (drinks, ceremony, party, quiet venue) | cards | yes |
| 6 | Packages and prices | example packages with inclusions, or "ask for a quote"; the area prices assume; travel rule | two or three cards | yes, or the quote line |
| 7 | Songs | link to the song list; how requests work | one block | optional |
| 8 | Public shows | if any, with ticket links | one line each | optional, hidden when none |
| 9 | Check your date | form: date, place, event type, contact; who will answer and by when | form | yes |
| 10 | Footer | contact, privacy, booking terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from structure only. Reference 7 is long and text-rich (each line-up and package explained in full) with a photograph or clip beside most blocks: roughly one image or video per text block. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a working musician in either language. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file. In particular: licensing of cover recordings in each country, UK secondary-ticketing duties, whether the Israeli accessibility rules apply to a musician's site.
3. Image-to-text ratios and visual quality: text extraction only, no image references returned, no rendered view. Tour dates on references 3 and 5 were not visible to the extraction.
4. awwwards.com/websites/music was loaded but not used as a source of references; design quality is the author's prior judgement.
5. Only two band-for-hire references, both in the UK. No DJ, solo singer-songwriter, classical soloist or cover-band-for-bars reference was verified.
6. The claim that most artists use external ticket sellers and stores rests on the references' links, whose targets were not followed.
7. Sub-pages (tour pages, song lists, store pages, press kits) were not fetched; observations are of home pages only.
8. The empty-shell findings (Big Thief, Wolf Alice, Ezra Collective) describe what a text fetch saw; those sites may render fully in a browser. They show the failure mode, not a judgement of the sites.
9. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
