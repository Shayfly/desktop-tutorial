# Photographer

Covers: a photographer or small photo studio whose site shows their pictures and brings in work: weddings and events, portraits and headshots, families and newborns, commercial and product work, and fine-art photographers who sell prints, run workshops or give talks.
Does not cover: designers, illustrators and studios showing commissioned design work (use `portfolio.md`); a photo agency or archive of many photographers (use `catalogue-collection.md`); a wedding couple's own site (use `wedding.md`).
Written 2026-11-22. References checked 2026-11-22. Template: [README.md](README.md).

## 1. Objects

A photographer sells **one of two things**, and the site changes with it:

- **Time and a result** (a wedding day, a headshot session): dates are the stock. A date can only be sold once. References 5 and 6.
- **Pictures** (prints, editions, licences, books): images are the stock, and an edition can only be sold up to its size. References 2 and 7; references 1, 3 and 4 sell prints, workshops or talks alongside.

Either way the pictures are the proof, and each picture carries rights: who owns it, who is in it, and whether they agreed.

### Photographer (the business)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name as shown | required | a personal name or a studio name |
| Kind of photography | required | weddings and elopements; actor headshots; wildlife; product |
| Area served | required for services | "City and surroundings; travels worldwide" |
| Studio address | optional | only if clients come to a studio; reference 2 shows galleries with addresses, reference 4 a studio |
| Phone | optional | |
| Email or enquiry form | required | |
| How to book or buy | required | enquiry form, booking calendar, shop |
| About | optional | first-person story; reference 6 tells how the photographer came to the city |
| Style statement | optional | "documentary, unposed" (reference 6 explains its style in an FAQ answer) |
| Insurance | optional | reference 6 states it carries liability insurance |
| Social account | optional | |
| Languages | optional | |
| Booking-ahead note | optional | "now booking next year" (reference 6) |

### Service or package (for photographers who sell time)

| Field | Required | Example |
|---|---|---|
| Name | required | "Wedding day", "Couple session", "Executive headshot" |
| Who it is for | optional | reference 5 has separate sections for executives, personal branding and actors |
| What is included | required when a price is shown | hours of coverage, number of edited images, locations, outfits, second photographer |
| Price | optional, see rule 4 | "from 495" (reference 6 shows a starting price for one session type) |
| Price type | required when a price is shown | fixed, from, range, on request |
| Duration | optional | 15 minutes, 8 hours |
| Delivery time | required for booking | "6 to 8 weeks" (reference 6 states this in its FAQ) |
| Number of images delivered | optional | a range; reference 6 states one |
| Deposit or retainer | optional | percentage or amount; reference 6 states a 50% retainer and a signed contract |
| Travel fee | optional | |
| Add-ons | optional | film photography, album, prints, extra hour |

### Gallery (portfolio collection)

| Field | Required | Example |
|---|---|---|
| Name | required | Weddings, Portraits, a project title |
| Images | required | |
| Description | optional | references 3 and 7 write a statement per project |
| Order | required | |
| Kind | required | public portfolio, or private client gallery (below) |

### Image

| Field | Required | Example |
|---|---|---|
| File | required | |
| Alt text | required | |
| Title or caption | optional | reference 4 captions every animal with its species and where it was photographed |
| Place | optional | |
| Date | optional | |
| People in it | required to answer | none, recognisable adults, recognisable children |
| Consent or release | required when a person is recognisable and the image is published | yes, with date |
| For sale as a print | optional | links to a print item |
| Licensing allowed | optional | |
| Location data removed | required to answer | yes by default (rule 10) |

### Print or edition (for photographers who sell pictures)

| Field | Required | Example |
|---|---|---|
| Image | required | |
| Title | required | |
| Edition type | required | open edition, limited edition (reference 2 sells both) |
| Edition size | required for limited editions | 50 |
| Number sold | required for limited editions, internal | 12 |
| Signed, numbered | optional | only if true |
| Sizes and prices | required | |
| Paper, framing | optional | |
| Ships to | required | |
| Returns policy | required | |
| Availability | required | available, final pieces, sold out, retired (reference 2 "vaults" works no longer sold) |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Enquiry | date of the event or session, place, kind, guest count, budget, name, email, phone, message | For weddings the date comes first; it decides everything |
| Booking | service, date, time, place, client, status, deposit, contract signed | Status: enquiry, held, booked (deposit paid and contract signed), completed, cancelled |
| Client gallery | client, images, password or private link, expiry, download allowed, print ordering | Reference 6 says clients and guests order prints through the gallery |
| Contract | terms, cancellation, image rights, delivery, signature | The photographer's own document; the product does not write it |
| Testimonial | text, first name or initials, date, source, permission | Reference 6 quotes clients; reference 5 shows client portraits with names |
| FAQ | question, answer | Reference 6 answers delivery time, number of images, posing, insurance, editing, prints, second shooter, how far ahead to book |
| Workshop or course | title, place, dates, price, seats, how to book | Reference 1 lists a six-day workshop with two date ranges |
| Talk or speaking | topic, how to book | Reference 3 has "Book Joel to speak" |
| Book | title, cover, where to buy | |
| News or event | title, date, place | Reference 1 lists a book signing with date and address |
| Gallery location | name, address, opening hours | Reference 2 has two physical galleries |
| Licence | image, use, territory, duration, price | Commercial use of an image; usually quoted on request |
| Image usage guidelines | text | Reference 3 links to its own guidelines in the footer |

### How objects relate

A photographer has galleries; a gallery has images; an image may have a consent record and may be offered as a print. A service is booked by a client for a date; the booking produces a client gallery after the event. A limited edition belongs to one image and has a fixed size.

## 2. Rules

1. Every image shown as the photographer's work was taken by the photographer (or their named team). Stock images are never presented as their work.
2. A recognisable person appears in a published image only with that person's consent; a child only with a parent's or guardian's consent. Consent for a client gallery is not consent for the public portfolio.
3. A client named in a testimonial or caption is named only with permission. Reference 6's captions and testimonials use couples' first names; the product asks before publishing any name.
4. A price is optional, but its absence is explicit: "price on request" or "get pricing" (reference 5's action), never a blank and never zero.
5. A "from" price says "from" and says what makes it rise (hours, travel, second photographer).
6. Every price shows its currency and whether tax and travel are included.
7. A date that is booked cannot be offered again for a service that needs the photographer in person. A date is held only for a stated time.
8. A booking is "booked" only when the deposit and contract conditions the photographer set are both met. Until then it is "held" or "enquiry".
9. Delivery time and what is delivered are stated before booking, and the photographer can stand behind them.
10. Location data (GPS) is removed from published images by default, especially images of homes and children.
11. A limited edition never sells more than its edition size. "Signed" and "numbered" are shown only if true.
12. An edition shown as sold out or retired cannot be bought. "Final pieces" or similar scarcity wording is shown only if the stock number supports it.
13. Client galleries are private: reachable only with the link or password, never listed, never indexed by search engines.
14. A client gallery's expiry date is shown to the client in advance, with a reminder.
15. Copyright remains with the photographer unless the contract says otherwise; the site's licensing text must match the contract.
16. The enquiry action is reachable from every page without scrolling back to the top on a phone.
17. Images are resized for the screen; full-resolution files are not sent to the public site.
18. Every image has alt text. A caption that matters is text, not part of the image.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name as shown | "What name should be on the site?" | Clients find and recommend a photographer by name. |
| 2 | Kind of photography | "What do you photograph, and what do you want to be hired for?" | A couple looking for a wedding photographer leaves a page full of landscapes. |
| 3 | Your best pictures | "Which 20 to 40 pictures best show your work? Only your own." | The pictures are the whole case. Someone else's pictures are fraud. |
| 4 | Consent for people in them | "Did everyone recognisable in these pictures agree to be shown? Any children?" | Publishing a person without consent can hurt them and break the law. |
| 5 | Where you work | "Where are you based, and how far will you travel?" | Clients need to know you will come to them. |
| 6 | How clients reach you | "How should people enquire: a form, email, phone, a booking calendar?" | The whole site leads to this one action. |
| 7 | Prices, or the decision not to show them | "What do your services cost, or would you rather send prices on request?" | Price is the first question. Hiding it is allowed; inventing it is not. |
| 8 | Who is responsible | "What is the registered business name and number, for the legal pages?" | Privacy and terms pages must name who is responsible. |

Needed when the photographer sells time (sessions, events):

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 9 | What each service includes | "For each service: how long, how many edited pictures, and what else is included?" | Clients compare packages. A missing detail becomes an argument after the wedding. |
| 10 | Delivery time | "How long after the session do clients get their pictures?" | The first question after the day is "when?". |
| 11 | Deposit and contract | "Do you take a deposit and use a contract? What happens if a client cancels?" | Clients must know before booking, and you must be able to stand behind it. |
| 12 | Where enquiries go | "Which email or phone should each new enquiry go to?" | An enquiry nobody sees is a lost wedding. |

Needed when the photographer sells pictures:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 13 | Prints on offer | "Which pictures are for sale, in which sizes and prices? Open or limited editions? How many in each edition?" | A limited edition that sells one more than promised breaks trust with every collector. |
| 14 | Shipping and returns | "Where do you ship, how long does it take, and do you accept returns?" | Buyers abroad need to know the full cost and their rights. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the photographer.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Page order | Skeleton A for services, Skeleton B for print sellers | Extracted from the references | Named as the default skeleton |
| Gallery order | the order the customer chose their pictures in | Fact 3 asks for the best | Editable, labelled "your order" |
| Images on the home page | 8 to 15 | Estimate; references 5 and 6 show long runs of images, reference 1 five | Setting, labelled "default" |
| Missing price | "Price on request" with the enquiry action | Says openly that there is no number | Shown in the customer's review |
| Main action | "Check your date" for events; "Book a session" for sessions; "Get in touch" otherwise | Matches the kind of photography | Labelled "default action" |
| Enquiry form fields | name, email, date, place, kind of session, message; phone optional | The minimum to reply with availability | Customer confirms |
| Date hold | none; enquiries only | A hold is a business promise; only the customer sets it | Setting, off |
| Location data on images | removed | Rule 10 | Not shown to the customer |
| Right-click or download blocking | off | Does not stop copying and harms accessibility; watermarking is the customer's choice | Setting, labelled "default: off" |
| Client galleries | private link, no indexing, expiry not set until the customer sets one | Rule 13 | Setting |
| FAQ topics | delivery time, number of images, travel, deposit, prints - only answered ones shown | Reference 6's FAQ covers these | Listed as "questions to answer" |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Currency | the currency of the photographer's country | Follows from the address | Shown next to every price |
| Legal page structure | headings only: who we are, what we collect, why, how long, your rights, contact; plus image usage | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | An empty "Testimonials" section looks worse than none | Listed for the customer as "not shown yet" |

Never a default, whatever the customer left out: pictures, prices, packages, hours, number of images, delivery time, deposit and cancellation terms, travel fees, edition sizes, "signed", "numbered", "award-winning", testimonials, client names, publications, insurance, years of experience, availability dates, "only a few dates left".

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Heavy images | A blank screen on a phone for several seconds | The visitor leaves before seeing one picture | Rule 17 |
| Someone else's pictures shown | Later, the real photographer or a client notices | Reputation destroyed; legal claim | Rule 1; fact 3 |
| Person shown without consent | Finds themselves or their child on a stranger's site | Complaint, takedown, possible legal action | Rule 2; fact 4 |
| Double booking of a date | Two couples both believe they booked | One wedding without a photographer | Rule 7, enforced when a booking is saved |
| Enquiry form goes nowhere | "Thanks" - and no reply ever | A lost wedding, silently | Fact 12; test the form at setup |
| No price signal at all | Couple cannot tell if this is in budget | Many enquiries the photographer cannot take, or none | Fact 7; "from" price or "price on request" with a short note |
| Delivery time missing or unrealistic | Waits months, writes angry messages | Bad reviews | Fact 10; rule 9 |
| Client gallery public | Strangers find a family's private photos by search | Privacy breach | Rule 13 |
| Client gallery expires without warning | The client returns for their wedding photos and finds nothing | Heartbreak and a dispute | Rule 14 |
| Edition oversold | Collector buys number 51 of 50 | Trust and possibly a legal claim | Rule 11 |
| False scarcity | "Final opportunity" that never ends | Distrust; possibly unlawful | Rule 12. Reference 2 uses final-availability wording; the product shows such wording only from stock data |
| GPS left in images | A newborn shoot reveals the family's home location | Real-world safety risk | Rule 10 |
| Interactive gallery that needs a gesture | A visitor is asked to rotate the phone or allow motion sensors | Many leave; keyboard users stuck | Reference 7 opens with an orientation prompt and a drag-to-navigate experience; offer a plain gallery as well |
| Near-empty home page | Only a name and an address | Visitor learns nothing | Reference rejected for this reason (section 9); the opening always has a line of text and pictures |
| Testimonials with private names | A couple's names appear without asking | Privacy complaint | Rule 3 |
| Shop totals surprise | Import tax or shipping added at checkout | Abandoned purchase, chargeback | Rule 6; reference 2 lists payment methods; state taxes and shipping up front |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with working photographers in either language. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Photographer | the person | צלם / צלמת | مصوّر / مصوّرة |
| Photo studio | the place or business | סטודיו לצילום | استوديو تصوير |
| Photo shoot, session | a booked time of photographing | צילומים / סשן צילום | جلسة تصوير |
| Wedding photography | photographing weddings | צילום חתונות | تصوير الأعراس |
| Elopement | a very small wedding, often just the couple | חתונה אינטימית (not verified as equivalent) | not verified |
| Engagement shoot, pre-wedding | photos of the couple before the wedding | צילומי טרום חתונה / צילומי זוגיות | جلسة تصوير قبل الزفاف (not verified) |
| Second shooter | a second photographer at an event | צלם נוסף / צלם שני | مصوّر ثانٍ (not verified) |
| Portrait | a photo of a person | פורטרט / דיוקן | بورتريه / صورة شخصية |
| Headshot | a head-and-shoulders portrait for work | תמונת פרופיל / צילום תדמית (not verified as exact) | صورة شخصية مهنية (not verified) |
| Newborn photography | photos of new babies | צילום ניו בורן | تصوير المواليد (not verified) |
| Product photography | photos of products for sale | צילום מוצרים | تصوير المنتجات |
| Package, collection | a priced set of services | חבילה | باقة |
| Retainer, deposit | money paid to hold the date | מקדמה | عربون |
| Contract | the written agreement | חוזה / הסכם | عقد |
| Edit, retouch | adjusting images after the shoot | עריכה, ריטוש | تعديل، رتوش |
| Proof | a preview image for choosing | not verified | not verified |
| Client gallery | private online delivery of photos | גלריית לקוח (not verified as standard) | معرض العميل (not verified) |
| Album | a printed book of the photos | אלבום | ألبوم |
| Print | a printed photograph | הדפס | طبعة / صورة مطبوعة |
| Fine-art print | a print sold as art | הדפס אמנותי | طبعة فنية (not verified) |
| Limited edition | a fixed number of prints | מהדורה מוגבלת | إصدار محدود |
| Open edition | prints without a fixed number | מהדורה פתוחה (not verified) | not verified |
| Signed and numbered | each print signed and given its number | חתום וממוספר | موقّع ومرقّم (not verified) |
| Model release | a person's written consent to use their image | טופס הסכמה / שחרור זכויות (not verified as standard) | not verified |
| Licence, licensing | permission to use an image, often for a fee | רישיון שימוש | ترخيص |
| Copyright | the right to the image | זכויות יוצרים | حقوق الطبع والنشر |
| Watermark | a mark over an image to deter copying | סימן מים | علامة مائية |
| Golden hour | the light just after sunrise or before sunset | שעת הזהב | الساعة الذهبية |
| On location | outside a studio | צילומי חוץ | تصوير خارجي (not verified) |
| Workshop | a hands-on class | סדנה | ورشة عمل |

Notes on language:

- Visitors say "photos" and "how much"; the trade says "collections", "coverage" and "investment". Use the visitor's words on buttons.
- UK and US English differ: colour/color, enquiry/inquiry, licence (noun, UK)/license. Pick one by the photographer's country.
- Words to avoid unless the customer said them and can back them: "award-winning", "best", "number one", "published in", "featured in", "only a few dates left", "final opportunity", "museum-quality", "investment grade".

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the photographer's country before it is relied on.

### Applies almost everywhere

- **Copyright.** The photographer usually owns copyright in their photos unless a contract transfers it. Clients typically receive a licence for personal use. Not verified per jurisdiction.
- **People in photos.** Publishing recognisable people for marketing generally needs their consent, especially children. Rules differ widely between countries; some protect a person's image strongly (for example France, Germany). Not verified.
- **Privacy notice.** Needed as soon as the site collects enquiries, bookings, newsletter emails or analytics.
- **Client galleries** contain personal data (faces, homes, events) and must be protected accordingly.
- **Contracts.** Booking terms (deposit, cancellation, delivery, image rights) belong in the photographer's contract and must match what the site says.
- **Consumer law for prints.** Prices with tax, delivery costs, returns and cancellation rights for distance sales. A made-to-order print may be exempt from return rights in some places. Not verified.
- **Scarcity and pricing claims.** "Last chance" and limited-edition claims must be true; misleading claims are regulated as unfair or misleading practices in many jurisdictions.
- **Drones.** Aerial photography is regulated by aviation authorities in most countries. Not verified per country.

### Israel

- Accessibility: businesses serving the public must make websites accessible and publish an accessibility statement, under the Equal Rights for Persons with Disabilities Law and its regulations, with Israeli Standard 5568 as the reference. Exemptions for very small businesses by turnover: not verified.
- Privacy: the Protection of Privacy Law applies; publishing a person's photograph in a way that could humiliate them, or using their image for profit without consent, is believed to be an infringement. Amendment 13 came into force in August 2025. Not verified in detail.
- Copyright: under the Copyright Law 2007, the owner of a commissioned portrait or event photograph is believed to be the person who commissioned it, unless agreed otherwise. This differs from many other countries and changes what the photographer may show. Not verified; ask the customer what their contracts say.
- Distance sales cancellation (prints, prepaid sessions): the Consumer Protection Law gives cancellation rights with capped fees. How it applies to a booked date: not verified.
- Marketing messages: section 30A of the Communications Law requires prior consent. Not verified in detail.

### European Union and United Kingdom

- GDPR (EU) and UK GDPR: photographs of identifiable people are personal data. Publishing them in a portfolio needs a lawful basis, usually consent. Non-essential cookies need consent (ePrivacy, PECR).
- Distance-selling rules: services for a specific date (leisure-related) may be exempt from the 14-day withdrawal right; whether a photo session falls under that exemption: not verified.
- Displayed consumer prices must include VAT: believed true; not verified.
- Accessibility: the European Accessibility Act (from June 2025) covers e-commerce services with a microenterprise exemption. A photographer with an online shop and more than ten staff or the turnover threshold could be in scope. Not verified.
- UK: the commissioner of a photograph has a limited right not to have it published (privacy in certain photographs and films under the Copyright, Designs and Patents Act 1988). Not verified.

### United States

- Copyright stays with the photographer unless transferred in writing. Registration with the Copyright Office matters for enforcement. Believed correct; not verified.
- Right of publicity (using a person's likeness commercially) is state law. Not verified per state.
- Some states regulate limited-edition print disclosures (for example California and New York have fine-print laws). Not verified.
- The Americans with Disabilities Act is applied by courts to business websites in many cases. Not verified.
- Sales tax on prints and sometimes on photography services varies by state. Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page, terms page, image-usage page and accessibility statement. It marks each as a draft that needs review.
- The product never writes the photographer's contract and never states that the site "complies with" a named law.
- The product asks about consent for people in pictures (fact 4) before publishing any gallery.
- The product asks which country the photographer works in before generating any legal page.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, portfolio galleries, services and prices, about, FAQ, testimonials, contact details, legal pages, image-usage page. With an email or phone link as the only action this is a complete and honest product for many photographers.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Portfolio | cannot be empty (fact 3) | a missing image is skipped, not shown as a broken icon | Images load progressively; a placeholder keeps the layout from jumping |
| Services | "Prices on request - get in touch", never an empty table | | Shows what is included |
| Testimonials | section hidden | | Never placeholders |
| FAQ | only answered questions shown | | |
| Map for a studio | address as text always shown | text and link remain if the map fails | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Enquiry form | stores the enquiry; alerts the photographer | n/a | "sending", cannot be pressed twice | "Not sent - email us at ..." | visitor sees "Received - I reply within ..." only if the customer gave a reply time | visitor writes; only the photographer reads |
| Date availability check | a calendar of booked and held dates | "This date is available - send an enquiry to hold it" (only a hold, never a booking) | placeholder, never "booked" while loading | "Could not check - send an enquiry" | | visitor sees available or not, never other clients' details |
| Booking with deposit | services, calendar, contract acceptance, payment | | | if the date was taken meanwhile: say so and offer alternatives | "booked" only after payment and contract (rule 8); confirmation the client can keep | client: own booking; photographer: all |
| Client gallery | stored images, private link or password, expiry | "Your photos are being edited - expected by [date]" | thumbnails first | expired link: "This gallery has expired - contact ..." | favourites and downloads saved per client | only the client and people they share the link with; never indexed |
| Print shop | prints, sizes, stock, edition counts, payments, shipping | "Sold out" per edition | | payment failure keeps the basket | order confirmed only after payment; edition count decremented in the same step (rule 11) | buyer: own orders; photographer: all |
| Photographer edits | editor for galleries, services, prices, FAQ | | upload progress | a failed save says so and keeps what was typed | visible after saving | photographer only |
| Workshop sign-up | dates, seats, payment | "Full - join the waiting list" | | | seat confirmed only after payment | participant: own; photographer: all |

### Needs accounts

- The photographer needs one as soon as anything is editable or any booking, gallery or order is stored.
- Clients should reach their gallery by private link or password, not by creating an account.
- Buyers in a print shop can check out as guests.

### Needs payments

- Deposits or retainers, prepaid sessions, prints, editions, workshops, gift vouchers, licences.
- Each brings refunds, receipts, failed-payment states and consumer law (see Legal).
- Default: no payments. Added only when the customer asks and has given the terms (facts 11, 13, 14).

### Using existing tools

Many photographers already use a client-gallery service, a print lab's shop or a booking tool. Reference 6 says clients order prints through its gallery; a rejected reference was a hosted-portfolio page with no content (section 9). Ask before building a second gallery or shop. The failure mode is the site's links into those tools breaking silently.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate. Photographers' sites often load images by script, so image counts in the extraction are far lower than what a visitor sees; image captions in the text were used as a second signal.

**Curation.** Chosen by the author from well-known working photographers' own sites, not from a search-result list. No awwwards.com category was consulted (awwwards.com/websites/photography is the named source for a later pass); none is claimed as an award winner. All seven are in English, in Latin script. Several sites name their clients or subjects; none of those names are reproduced here.

**Limit.** Five of seven are internationally known photographers; references 5 and 6 are the closest to the typical customer (a headshot studio and a wedding photographer). No newborn, family or product photographer was verified.

Verified: 7.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.stevemccurry.com | 2026-11-22 | Documentary photographer. Order: name and cart - a run of large images, the first linked to "Fine Art Prints" - news: a book signing with date and bookshop address, a six-day workshop with two date ranges, an online course with an enrol link. Little text. 1 image in the extraction (script-loaded gallery). |
| 2 | https://www.lik.com | 2026-11-22 | Landscape photographer's print business. Order: a notice that some images are being retired from sale - open editions - one featured image with a paragraph of its story, shown framed in a room - new releases - his two physical galleries, each with a short description - the "vault" of works at final availability - best sellers - a related property venture - open editions again - his portrait and a first-person quote about why he photographs - limited editions (signed and numbered) - newsletter - footer with collections, customer service, galleries, and accepted payment methods. 23 images. |
| 3 | https://www.joelsartore.com | 2026-11-22 | Wildlife photographer and speaker. Order: name and one-line role - "I'm Joel Sartore" with a first-person paragraph about his long-running project to photograph species in human care - a press quote - a wall of animal portraits, each captioned with species and the zoo or centre where it was taken - speaking engagements with a quote and "Book Joel to speak" - the project with "Explore" - more captioned portraits - news - follow and email list - footer with an image-usage guidelines link. 5 images in the extraction, and dozens of captioned images in the text (not counted exactly). |
| 4 | https://www.nickbrandt.com | 2026-11-22 | Fine-art photographer working in series. Order: the current series' title and chapter - one image with the subject's first name, place and year - a long statement about the series and its subjects - a note that part of print proceeds goes to the people photographed - "Click here to view work". Project-led: the home page is one series. 1 image in the extraction. |
| 5 | https://peterhurley.com | 2026-11-22 | Headshot and portrait studio. Order: "Get pricing" - headline and one line naming the city and the client types - three service sections (personal branding, executives, actors), each two paragraphs and "Book a session" - a long gallery of client portraits, each captioned with the client's name (public figures and others; not reproduced here). Price is behind "Get pricing". 3 images in the extraction, and dozens of captions (not counted exactly). |
| 6 | https://www.sachinkhona.com | 2026-11-22 | Wedding photographer. Order: a run of wedding images with venue captions - "Vancouver wedding photographer" and a short statement of approach - third-person bio with places worked - "Now booking" next two years - venue gallery - a client testimonial - "view portfolio" and "view pricing and collections" - first-person story - services: weddings (pricing on request via brochure) and couple sessions (a "starting at" price) - another testimonial - film and digital galleries - numbers (images per wedding, cameras, weddings since a year, awards, reviews) - FAQ (delivery time, number of images, posing, insurance, editing, prints and albums, second shooter, how far ahead, retainer and contract) - social feed - cookie notice. Captions and testimonials use couples' first names; not reproduced here. |
| 7 | https://jimmynelson.com | 2026-11-22 | Photographer of peoples and cultures; an interactive experience. Order: a prompt to use the phone's orientation sensor and "drag to navigate" - a sequence of cards, one per people photographed, each with a print, an illustration and a progress percentage - project names - a notice about the companion app - newsletter signup with a monthly prize. Shows the risk of an experience that needs a gesture before any content. 4 images in the extraction. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.platonphoto.com | 2026-11-22 | Loads, but the extraction returned only the name, a studio address and a copyright line. Not enough to describe the structure. |
| https://www.chrisburkard.com | 2026-11-22 | Loads, but returned only the hosting platform's footer ("Powered by SmugMug", owner log in). An empty shell in the extraction. |
| https://www.magnumphotos.com | 2026-11-22 | Loads. A cooperative agency of many photographers with editorial stories, a shop and learning; not one photographer's business. Closer to `catalogue-collection.md`. |

Failed to load (not counted, not used): https://josevilla.com, https://www.elizabethmessina.com, https://www.annegeddes.com - each returned "Failed to fetch url" on 2026-11-22.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the photographer who sells time (sessions and events)

For a wedding, portrait, headshot, family or event photographer whose site has one job: get an enquiry for a date. Default for this domain.
From references 5 and 6: the per-audience service sections of 5, the services, FAQ and booking note of 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; links: Portfolio, Services, About, FAQ; the enquiry action stays reachable on a phone | action is the most prominent element after the name | yes |
| 1 | Opening | one large picture or a short run; one line: what kind of photographer, where; the main action ("Check your date" / "Book a session") | picture first, then one heading and one line | yes |
| 2 | Portfolio highlights | 8 to 15 best pictures, a link to full galleries | images only, optional short captions | yes |
| 3 | Services | each service: who it is for, what is included, price or "from" or "on request", delivery time | one block per service, the price at the end | yes |
| 4 | About | first-person paragraph and an optional portrait | short | optional |
| 5 | What clients say | real testimonials with permission | at most three | optional, hidden when empty |
| 6 | FAQ | delivery time, number of images, travel, deposit and contract, posing, prints | question and answer list | optional; only answered questions |
| 7 | Enquiry | the form (date first), area served, email, phone | the form is the block | yes |
| 8 | Footer | name, email, area; privacy, terms, image usage, accessibility statement; social link | small | yes |

Image-to-text ratio: **estimate**, from structure and captions, not from a rendered view. Image-led at the top (one large image, then a gallery of 8 to 15) and text-led lower down (services, FAQ, form). References 5 and 6 each list dozens of image captions (not counted exactly) against a few thousand words of text. Roughly one screen of images for every screen of text. Not confirmed in a rendered view.

### Skeleton B: the photographer who sells pictures (prints, projects, talks)

For a fine-art, documentary or wildlife photographer who sells prints, runs workshops or gives talks. Use only when the customer sells pictures or talks; otherwise Skeleton A.
From references 2, 3, 4 and 1: the print collections of 2, the first-person mission and speaking block of 3, the series statement of 4, the workshops and news of 1.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; Work (series), Prints, Workshops or Speaking, About; cart if a shop exists | | yes |
| 1 | Opening | one image full width with the series or the photographer's one line | image first | yes |
| 2 | Current series | title, a few images, a short statement, "view the series" | image, title, paragraph | yes |
| 3 | Prints | collections: open editions, limited editions with edition size; final pieces only when stock supports it | image, title, price from, edition note | yes for print sellers |
| 4 | Mission or story | first-person paragraph, portrait | short | optional |
| 5 | Workshops, talks, events | dates, places, booking links | list with dates | optional, hidden when empty |
| 6 | Galleries (physical) | address and hours per gallery | blocks | optional |
| 7 | Newsletter | what and how often | one line and a field | optional |
| 8 | Footer | as Skeleton A, plus shipping, returns, image usage, payment methods | small | yes |

Image-to-text ratio: **estimate**. Image-led: reference 2 returned 23 images and each block is one image with a paragraph; reference 3's text lists dozens of captioned portraits. Roughly one large image per section plus a print grid. Not confirmed in a rendered view.

Risk seen in reference 7: a full-screen interactive experience before any content. If used at all, it sits behind a plain gallery, never in front of it.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with working photographers in either language. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7, including the Israeli rule on ownership of commissioned photographs, which changes what a photographer may show. None was checked against a statute or an official source for this file.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view. Image counts are much lower than what a visitor sees.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. No newborn, family, product or event photographer reference was verified.
6. Defaults in section 4 (8 to 15 home-page images) are estimates, not taken from a source.
7. Booking, gallery and print-shop flows of the references were not followed; observations are of home pages only. Reference 5's pricing page and reference 6's brochure were not fetched.
8. Three candidate sites failed to load and were replaced (section 9).
9. The brief asked for references dated 2026-11-21. The fetches ran on 2026-11-22, and that is the date recorded.
10. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
