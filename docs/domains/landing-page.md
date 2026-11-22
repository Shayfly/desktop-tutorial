# Landing page

Covers: one page with one goal for one offer: buy or preorder a product, sign up for an app, join a waiting list, download a guide, register for a launch, back a campaign. Everything on the page leads to one action.
Does not cover: a whole business site with many pages (use the business's own domain file, for example `restaurant.md`); a shop with many products and a basket (use `clothing-shop.md`); an event with a programme, venues and tickets (use `event.md`); help for a product people already have (use `product-docs.md`).
Written 2026-11-22. References checked 2026-11-22. Template: [README.md](README.md).

## 1. Objects

A landing page sells **one decision**. Everything follows from that: there is one offer, one main action repeated down the page, and every section either answers a doubt that stops the decision or is removed. Because a landing page persuades, it is also where invented claims do the most harm: every claim, number and quote must come from the customer.

### Offer (what the page is for)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Pocket Planter", "The Freelancer's Tax Guide" |
| Kind | required | physical product, app or software, digital download, service, waiting list, event registration |
| The promise, in one sentence | required | what the visitor gets, in their words |
| Who it is for | required | "people who forget to water plants" |
| Price | optional, required when the action is a purchase | 229 |
| What the price includes | required when a price is shown | "includes 24 games; shipping not included" (reference 1 states both) |
| Taxes and shipping | required for physical products | "plus taxes and shipping" (reference 1) |
| Availability | required | available now, preorder with ship date, waiting list, sold out, ended (reference 2 marks an accessory "Out of Stock") |
| Ship or start date | required for preorders and events | |
| Free trial or free tier | optional | reference 3 offers a free trial download; reference 6 says "no credit card required" |
| Campaign end date | optional | if the offer ends |
| Platforms or requirements | optional | reference 3 lists each device with requirements and price |
| Maker | required | the company or person; reference 1 ends with "who made it" |

### Main action (call to action)

| Field | Required | Example |
|---|---|---|
| Label | required | "Preorder", "Join the waiting list", "Get the guide", "Download free trial" |
| Kind | required | buy, preorder, sign up, download, join list, book a call, register |
| Destination | required | a checkout, a payment link, a form, an app store, a sign-up page |
| Repeated | derived | the same action appears at the top, after key sections and at the end (reference 7 repeats one signup action three times) |
| Secondary action | optional | one quieter action: "Watch the video", "See features" (reference 3) |

### Section (block on the page)

| Field | Required | Example |
|---|---|---|
| Kind | required | opening, problem, how it works, benefits, features, proof, pricing, specifications, FAQ, about the maker, final action |
| Heading | required | |
| Body | required | short text, list, image, video, table |
| Order | required | |
| Purpose | internal | which doubt it answers ("will it work for me?", "is it worth the price?") |

### Proof

| Object | Fields | Notes |
|---|---|---|
| Testimonial | quote, person's name or initials, role, date, source, permission | Real only. References 5 and 7 show named users with roles |
| Press or award quote | publication, quote, date, link | Reference 3 shows design-award mentions and quotes from named publications |
| Customer logos | logo, company, permission | Reference 6 shows "used by" logos |
| Number | value, what it counts, source, date | "Rated 4.7 on the App Store" (reference 5): a number with its source |
| Case result | customer, result, source | Reference 6 states one customer's time saving; only with permission and a source |
| Demonstration | video, live demo, screenshots | Reference 6 shows an interactive booking preview |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Plan or tier | name, price, period, what is included, main action | Only when there is more than one; otherwise one price |
| Specification | name, value | Physical products; references 1 and 2 end with full specification lists |
| FAQ entry | question, answer | Reference 7 answers objections ("is this another fad?"); reference 6 answers plain product questions |
| Form | fields, consent checkbox, destination, confirmation message | Ask only for what is needed (rule 10) |
| Lead (form submission) | fields, consent, date, source page, campaign | Personal data; see Legal |
| Media | hero image or video, poster frame, captions | Video without sound by default |
| Footnote | number, text | Reference 2 uses numbered footnotes to qualify claims (battery estimate, compatibility, trademarks) |
| Tracking | campaign name, source parameters, consent state | Only with consent where required |
| Newsletter | signup, what and how often | Reference 3 says its newsletter goes out only a few times a year |

### How objects relate

One page has one offer and one main action. Sections are ordered so each answers the next doubt. Proof items belong to sections. A form, if any, produces leads. A plan belongs to the offer; a specification belongs to a physical product.

## 2. Rules

1. A landing page has exactly one main action. Other links (to the maker's site, to help) are quieter and few.
2. The main action is visible on the first screen and reachable from every point of the page on a phone without scrolling back to the top.
3. The main action works: its destination loads and completes. A broken action is the worst failure of this domain.
4. Every claim, number, quote, logo, award and result on the page comes from the customer, with its source. Nothing is invented, rounded up or "typical".
5. A testimonial is shown only if real, with the person's permission, and attributed as the person agreed (name and role, or initials).
6. A logo of a customer, partner or publication is shown only with permission or a real basis ("as seen in" only if it was).
7. A price shows its currency, what it includes, and whether taxes and shipping are extra. The price at checkout matches the page.
8. Availability is true at the moment of viewing: sold out shows sold out and does not take money; a preorder shows its expected ship date.
9. A countdown, "only N left" or deadline is shown only if real and driven by real data. When the deadline passes, the offer actually ends or the page changes.
10. A form asks only for the fields needed to deliver what was promised. An email is enough for a waiting list.
11. A consent checkbox for marketing is unticked by default and separate from accepting the offer.
12. After the action, the visitor sees what happens next ("Check your email", "Your order number is ...", "We ship in March").
13. When the campaign ends, the page says so and offers the next step (waiting list, the maker's site). It never silently keeps selling something that is not available.
14. Footnotes qualify claims that need it (estimates, conditions, compatibility). An estimate is labelled as an estimate on the page.
15. Video does not play with sound on its own; the page works without the video.
16. Every image has alt text. Text that matters is never only inside an image.
17. Tracking scripts that need consent load only after consent.
18. The maker is named, with a contact route and the legal pages.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | The offer | "What exactly are you offering on this page?" | A page that tries to sell two things sells neither. |
| 2 | Who it is for | "Who is this for, and what problem does it solve for them?" | The first line must make the right person stop and the wrong person leave. |
| 3 | The one action | "What is the one thing a visitor should do: buy, preorder, sign up, download, join a list?" | The whole page leads to this one action. |
| 4 | Where the action goes | "Where should that button take people: your shop, a payment link, an app store, a form? Who receives the result?" | A button that leads nowhere loses every visitor silently. |
| 5 | Price and what it includes | "What does it cost, and what is included or extra (tax, shipping)?" | A different price at checkout feels like a trick. Hiding the price is allowed for some offers; inventing it is not. |
| 6 | Availability and dates | "Is it available now? If not, when will it ship or start? Does the offer end?" | People who pay for something that will not arrive ask for their money back, loudly. |
| 7 | The proof you really have | "What can you show that it works: real reviews, press, numbers, customers who agreed to be named? It is fine to have none." | Proof helps only when it is real. Invented proof is fraud. |
| 8 | What happens after | "After someone clicks, what happens: an email, a download, a shipment, a call?" | The visitor needs to know the next step, or they think it failed. |
| 9 | Who is responsible | "What is the registered business name and contact, for the legal pages?" | Visitors paying or leaving an email need to know who they are dealing with. |

Needed when they apply:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 10 | Key benefits and features | "What are the three things it does best? What can it not do?" | Benefits come from the customer, never from "products like this". |
| 11 | Specifications | "For a physical product: size, weight, battery, what is in the box, requirements." | Buyers compare specifications; a wrong one becomes a return. |
| 12 | Plans | "Is there more than one plan or version? What is in each?" | A comparison that does not match the real plans misleads. |
| 13 | Refunds and returns | "Can people return it or cancel? How?" | Buyers look for this before paying; the law often requires it (see Legal). |
| 14 | Questions people ask | "What do people ask you most before buying?" | These become the FAQ; they answer doubts that stop the decision. |
| 15 | Where leads go | "Which email or tool should receive each signup?" | A signup nobody sees is a lost customer. |
| 16 | Countries | "Which countries can buy or sign up?" | Shipping, tax and consent rules differ by country. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the offer.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Page order | Skeleton A for apps, downloads and lists; Skeleton B for physical products | Extracted from the references | Named as the default skeleton |
| Main action label | by kind: "Buy now", "Preorder", "Join the waiting list", "Get the guide", "Sign up free" | Describes the action plainly | Editable, labelled "default label" |
| Action repetition | top, after the benefits, at the end; sticky on phones | Seen in references 1, 3 and 7 | Setting |
| Secondary action | "See how it works" scrolling to the how-it-works section | No external dependency | Editable |
| Form fields | email only for waiting lists and downloads | Rule 10 | Customer confirms |
| Marketing consent | separate unticked checkbox | Rule 11 | Shown |
| Confirmation message | "Thanks - check your email" for lists; order number for purchases | Rule 12 | Editable |
| Missing proof | proof section hidden | Rule 4; an empty or invented proof section is worse than none | Listed as "not shown: proof" |
| FAQ | hidden until fact 14 is answered | Questions are facts about the customer's buyers | Listed as "not shown yet" |
| After the deadline | page switches to "This offer has ended" with a waiting-list form | Rule 13 | Setting; shown to the customer with the end date |
| Hero media | one product image; no autoplay video | Rule 15; faster on phones | Setting |
| Analytics | cookie-free page counts; marketing pixels off until the customer adds them with consent | Rule 17 | Setting, labelled "default" |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Currency | the currency of the customer's country | Follows from the address | Shown next to every price |
| Legal page structure | headings only: who we are, what we collect, why, how long, your rights, contact; terms of sale if selling | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |

Never a default, whatever the customer left out: the promise, benefits, features, specifications, prices, discounts, "was" prices, deadlines, stock numbers, ship dates, testimonials, ratings, customer counts, logos, press mentions, awards, guarantees, "money-back", "free shipping", "limited time", "bestselling", "#1", "doctor recommended" or any other claim.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Main action broken | Taps "Buy", nothing happens or an error page | Every visitor lost, silently; ad money wasted | Rule 3; check the destination at publish and on a schedule |
| Signups go nowhere | "Thanks!" - and no email, no follow-up | The whole campaign's leads lost | Fact 15; test a real signup at setup |
| Price differs at checkout | Higher total than the page said | Abandoned checkout; complaints; possibly unlawful | Rule 7 |
| Sold out, still selling | Pays, then learns it will not arrive | Refunds, chargebacks, angry reviews | Rule 8; availability from real stock |
| Campaign over, page still live | Signs up for something that ended | Confusion; trust lost | Rule 13 |
| Fake countdown | The timer resets on reload | Distrust; possibly unlawful | Rule 9 |
| Invented testimonial or number | A claim the visitor can check and disprove | Credibility gone; regulator interest | Rules 4 and 5 |
| Logos without permission | A company asks for its logo to be removed | Embarrassment; legal letter | Rule 6 |
| Action hidden on phones | Scrolls a long page and cannot find the button | Lost decisions | Rule 2; sticky action on phones |
| Heavy video at the top | Blank screen, then sound | Leaves before the first line | Rule 15 |
| Too many choices | Five buttons to five places | No decision | Rule 1 |
| Form asks too much | Phone, address and company for a free guide | Most leave the form | Rule 10 |
| Pre-ticked marketing box | Receives emails never agreed to | Complaints; unlawful in many places | Rule 11 |
| The page sends people elsewhere | Arrives for one product, is pushed to another | Confusion about what is on offer | Reference 8 now leads with a different product from the same maker and a notice that the original receives only limited updates. Honest, but the page's own offer is no longer the main action. When the offer changes, the page changes with it |
| Tracking before consent | (invisible) | Regulatory risk in the EU and UK | Rule 17 |
| Specification wrong | Buys, finds it does not fit or work with their device | Returns | Fact 11; footnotes for conditions (reference 2) |
| Generic page | Could be about any product | Nobody feels it is for them | Fact 2; the first line names the visitor's problem |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with marketers in either language. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Landing page | a one-goal page | דף נחיתה | صفحة هبوط |
| Call to action (CTA) | the main button and its words | קריאה לפעולה | دعوة إلى اتخاذ إجراء |
| Hero, above the fold | the first screen | אזור הפתיחה / מעל לקפל (not verified as common) | القسم الرئيسي (not verified) |
| Headline | the main line | כותרת | عنوان رئيسي |
| Value proposition | why this offer is worth it | הצעת ערך | عرض القيمة |
| Benefit | what the visitor gains | תועלת | فائدة / ميزة |
| Feature | what the product does or has | פיצ'ר / תכונה | خاصية |
| Social proof | evidence that others use and like it | הוכחה חברתית | الدليل الاجتماعي |
| Testimonial | a quote from a real user | המלצה | شهادة / توصية |
| Lead | a person who left contact details | ליד | عميل محتمل |
| Conversion | a visitor doing the main action | המרה | تحويل |
| Conversion rate | the share of visitors who convert | יחס המרה | معدل التحويل |
| Waiting list, waitlist | sign up to hear when available | רשימת המתנה | قائمة الانتظار |
| Preorder | pay or reserve before release | הזמנה מוקדמת | طلب مسبق |
| Free trial | use free for a limited time | תקופת ניסיון חינם | تجربة مجانية |
| Pricing table, plans | comparison of plans | טבלת מחירים, מסלולים | جدول الأسعار، الباقات |
| Sold out, out of stock | not available | אזל מהמלאי | نفد من المخزون |
| A/B test | comparing two versions | בדיקת A/B | اختبار A/B |
| Opt-in | agreeing to receive messages | הסכמה לקבלת דיוור (not verified as exact) | الموافقة على الاشتراك (not verified) |
| Unsubscribe | stop receiving messages | הסרה מרשימת תפוצה | إلغاء الاشتراك |
| Campaign | a time-bound marketing effort | קמפיין | حملة |
| Lead magnet | a free thing given for an email | מגנט לידים | not verified |
| Footnote, fine print | qualifying small text | הערת שוליים, אותיות קטנות | حاشية، الشروط الدقيقة (not verified) |

Notes on language:

- The trade says "conversion", "funnel", "CTA"; the customer and the visitor do not. Use plain words in the conversation and on the page.
- Words to avoid unless the customer said them and can back them: "revolutionary", "best", "#1", "guaranteed", "risk-free", "clinically proven", "limited time", "only a few left", "trusted by thousands", "free" (when there are conditions).
- The main action label describes what happens ("Preorder for 229"), not a vague "Submit" or "Click here".

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the customer's country before it is relied on.

### Applies almost everywhere

- **Advertising claims.** A landing page is advertising. Claims must be true and backed. Misleading claims, hidden conditions and fake urgency are regulated in most jurisdictions.
- **Reviews and endorsements.** Testimonials must be real and represent typical experience or say they do not; paid or gifted endorsements must be disclosed. Rules differ; not verified per jurisdiction.
- **Prices.** Total price, taxes and extra charges must be clear before purchase in most consumer-protection regimes.
- **Distance selling.** Buying online usually brings a cancellation or withdrawal right, with exceptions (for example custom-made goods, digital content once downloaded with consent). Not verified per jurisdiction.
- **Preorders.** Taking money for goods not yet available brings delivery-date duties and refund duties in many places. Not verified.
- **Privacy notice.** Needed for any form, any signup and any tracking.
- **Marketing consent.** Email and SMS marketing generally needs prior agreement and an easy unsubscribe.
- **Cookies and pixels.** Advertising pixels and analytics cookies need consent in the EU and UK.
- **Trademarks.** Other companies' names and logos (customers, press, compatible products) need permission or a clear descriptive basis. Reference 2 states in a footnote that trademarks belong to their owners.

### Israel

- Consumer protection: the Consumer Protection Law prohibits misleading a consumer, including in advertising, and gives cancellation rights for distance transactions (generally 14 days, with a capped cancellation fee). Details and exceptions: not verified.
- Prices: displayed prices to consumers must include VAT. Not verified in detail.
- Marketing messages: section 30A of the Communications Law (the "spam law") requires prior explicit consent for advertising by email, SMS and similar, with unsubscribe in every message. Not verified in detail.
- Accessibility: businesses serving the public must make websites accessible and publish an accessibility statement, with Israeli Standard 5568 as the reference. Exemptions for very small businesses: not verified.
- Privacy: the Protection of Privacy Law applies to lead data. Amendment 13 came into force in August 2025. Not verified in detail.

### European Union and United Kingdom

- EU: the Unfair Commercial Practices Directive bans misleading actions and omissions and lists banned practices, including false claims that an offer is available only for a very limited time. Believed correct; not verified for this file.
- EU: the Omnibus Directive (from May 2022) requires that a claimed price reduction show the lowest price of the prior 30 days, and requires traders to say whether and how they check that reviews come from real buyers. Believed correct; not verified.
- EU: the Consumer Rights Directive gives a 14-day withdrawal right for most distance contracts, with exceptions. Believed correct; not verified per product type.
- UK: the Digital Markets, Competition and Consumers Act 2024 is believed to ban fake reviews and drip pricing from April 2025, enforced by the Competition and Markets Authority. Not verified.
- GDPR and UK GDPR apply to leads; ePrivacy rules (EU) and PECR (UK) require consent for marketing emails to individuals and for non-essential cookies.
- Accessibility: the European Accessibility Act (from June 2025) applies to e-commerce services, with a microenterprise exemption. A landing page with checkout could be in scope. Not verified.

### United States

- The FTC Act prohibits unfair or deceptive advertising; the FTC's Endorsement Guides govern testimonials and disclosure of material connections. The FTC adopted a rule against fake reviews and testimonials in 2024. Believed correct; not verified for this file.
- CAN-SPAM governs commercial email (unsubscribe, postal address, honest subject lines). Not verified.
- The FTC's Mail, Internet, or Telephone Order Merchandise Rule requires shipping within the stated time (or 30 days) and notice and refund options when delayed; relevant to preorders. Not verified.
- Text-message marketing needs prior express written consent under the TCPA. Not verified.
- State privacy laws (for example California) may apply above thresholds. Not verified.
- Automatic renewal laws (federal and state) govern free trials that turn into paid subscriptions. Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page, terms of sale and an accessibility statement. It marks each as a draft that needs review.
- The product never writes a claim, testimonial, rating, discount or deadline that the customer did not supply (section 4).
- The product never states that the page "complies with" a named law.
- The product asks which countries can buy before generating any legal page or price display.

## 8. Site vs app

### Content pages (no data, no accounts)

The page itself, the legal pages, and a thank-you page. If the action goes to an existing checkout, payment link or app store, the landing page is pure content and owns no data. This is a complete and honest product.

States still needed on content:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Main action | cannot be empty (fact 3) | if the destination is down, show "Not available right now - try again later" and a contact; never a dead button | Checked at publish and on a schedule |
| Proof | section hidden | | Never placeholders |
| FAQ | hidden | | |
| Specifications | hidden for non-physical offers | | |
| Hero media | text-only opening if no image | broken image hidden, alt text shown | |
| Availability | cannot be empty (fact 6) | | "Sold out" and "Ended" are real states with their own wording |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Waiting list or signup form | stores email and consent; alerts or exports to the customer | n/a | "sending", cannot be pressed twice | "Not saved - please try again" (and a contact email) | visitor sees what happens next (rule 12); confirmation email if double opt-in | visitor writes own; only the customer reads the list |
| Download behind a form | the file, a form, a delivery email or link | n/a | | "The file could not be sent - here is a direct link" | link expires as set | anyone who submitted the form |
| Purchase or preorder | product, price, stock, payments, shipping, tax | "Sold out" replaces the action | checkout shows progress; the page never shows "sold out" while loading stock | payment failure keeps the visitor's details and says why | order confirmed only after payment; stock decremented in the same step | buyer: own order; customer: all orders |
| Stock or seats counter | a real count | | | if the count cannot be read, hide the counter rather than guess | | anyone sees the count; only the customer changes it |
| Deadline | a real end time in a named time zone | | | | at the end the page switches automatically (rule 13) | customer sets |
| Customer edits the page | an editor with preview and publish | | | a failed save says so and keeps what was typed | published at once | customer only |
| Leads list | stored leads with consent and source | "No signups yet" | | | export available | customer only, behind a login |

### Needs accounts

- The customer needs one as soon as the page is editable or any lead or order is stored.
- Visitors never need one to sign up or buy on a landing page. An app's own sign-up happens on the app's side.

### Needs payments

- Purchases, preorders, deposits, paid downloads.
- Each brings refunds, receipts, failed-payment states, tax and consumer law (see Legal).
- Default: no payments built into the page. The action links to the customer's existing payment link or shop when one exists; payments are built only when the customer asks.

### Using existing tools

Most landing pages send the action somewhere else: an app store (reference 3), a store page (references 1 and 2), a sign-up page (references 4, 5, 6). Ask where the action goes before building anything. The failure mode is a link that breaks when the other tool changes its address.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from the extracted text. Image counts include logos and icons; script-loaded images are missed.

**Curation.** Chosen by the author from well-known single-product pages and product home pages that work as landing pages, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner here, although reference 3 states its own design awards. All eight are in English, in Latin script.

**Limit.** Six of eight are software or apps; two are physical products (references 1 and 2); one is a book-and-course funnel (reference 7). No local-business campaign page (a single offer from a shop or clinic) was verified.

Verified: 8.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://play.date | 2026-11-22 | A small handheld game device. Order: preorder banner - one-sentence intro and "Shop now" - the system (screen, processor) - the design - the crank - the season of included games, listed with their makers - the game catalogue - make your own games - mirror app - education discount - price block: the price, what is included, "does not include shipping" - an accessory with its price - specifications (battery, CPU, storage, size, included, wireless, sound, display, inputs, cost "plus taxes and shipping") - photos - the idea in one quote - who made it - stay in touch - help, contact, FAQ. Each section is a heading, a short paragraph and an image. |
| 2 | https://www.analogue.co/pocket | 2026-11-22 | A handheld game device. Order: one-line promise and a paragraph - the display - display modes - adapters, each with a code and a paragraph - the dock (marked "Out of Stock") - music features and cables - operating system features - developer platform - technical specification lists for the device, the dock and the adapters - price and "Available now" - ten numbered footnotes qualifying claims (battery estimate, compatibility, trademarks). |
| 3 | https://culturedcode.com/things/ | 2026-11-22 | A to-do app. Order: one-sentence description and "watch introduction video" - features with "see features" - "Get Things": one block per device, each with requirements, price and a download action (free trial for one) - what people are saying - press and award quotes, each with publication and author - newsletter, stated as sent only a few times a year. About 5,700 characters, 25 images. |
| 4 | https://www.raycast.com | 2026-11-22 | A launcher app for computers. Navigation: store, pro, AI, iOS, Windows, teams, enterprise, blog, pricing, log in. Order: one-line promise and one sentence - its keyboard product - four qualities (fast, ergonomic, personal, reliable with a crash-free percentage) - extensions with examples by category - AI assistant with a worked example - "built for professionals": named users with their handles - snippets, quicklinks, hotkeys - "what else can it do" list. About 9,000 characters, 97 images. |
| 5 | https://readwise.io | 2026-11-22 | A reading-highlights app. Order: a banner for a new product - a wall of book highlights - one-line promise and "Get started for free" - three steps (import, review, remember) - feature blocks with headings - integrations - "Rated 4.7 on the App Store" - a wall of public posts from users, each with date and engagement counts. About 14,000 characters; no images in the extraction. |
| 6 | https://cal.com | 2026-11-22 | Scheduling software. Order: an interactive booking preview - one line about scale - "Sign up with email. No credit card required." - customer logos - one customer result - AI assistant with a sample answer - feature demonstrations (share a link, routing form, round-robin, reminders, embed) - integrations, each with one line - agent connection - case studies - events - enterprise (single sign-on, audit log, encryption, hosting regions) - FAQ - a closing line with the free plan and the steps. About 8,600 characters, 78 images. |
| 7 | https://www.buildingasecondbrain.com | 2026-11-22 | A method sold through a free guide, books and courses. Order: banner for a new book - one-line promise - offer of a free quickstart guide with one action - "featured in" - three questions naming the visitor's problem - the problem explained - the method - six outcomes as a list - the action again - one testimonial - the author's story in the first person - products (books, courses, membership, template), each with its own action - six testimonials with names and roles - FAQ answering objections - closing paragraph and the action a third time - footer. |
| 8 | https://arc.net | 2026-11-22 | A web browser. Order: a banner introducing the maker's newer browser with "Try" - a note that this browser now receives only limited updates and pointing to the newer one for security patches - one-line promise - three features (spaces, setup, privacy with a link) - user quotes with handles. About 1,200 characters. Shows a page whose own offer has been overtaken by another. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://linear.app | 2026-11-22 | Loads; the extraction is short (about 1,200 characters) and the page is a broad product home with many features, not a single-offer page. |
| https://superhuman.com | 2026-11-22 | Loads. A suite of several products (mail, docs, assistant) rather than one offer. |
| https://www.tella.tv | 2026-11-22 | Loads, but the extraction begins mid-page (viewer analytics) without the opening section. Not enough to describe the order. |

## 10. Skeletons

Structure only. No colours, logos, images or wording were taken from any reference.

### Skeleton A: the sign-up page (app, download, waiting list)

For an offer whose action is free or low-commitment: sign up, download, join a list, get a guide. Default for this domain when nothing is shipped.
From references 3, 5, 6 and 7: the three-step explanation of 5, the device-by-device action block of 3, the problem questions and repeated action of 7, the FAQ of 6 and 7.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; the main action; at most one or two other links | action is the most prominent element after the name | yes |
| 1 | Opening | one line: the promise in the visitor's words; one sentence of who it is for; the main action; a quiet secondary action | one heading, one line, one button | yes |
| 2 | The problem | two or three short lines naming the visitor's problem | short text | optional |
| 3 | How it works | three steps, each a heading and a sentence | three equal blocks | yes |
| 4 | Benefits | three to six benefits from fact 10, each a heading, a sentence and an image or screenshot | alternating image and text | yes |
| 5 | Proof | real testimonials, ratings with source, press | one strong item, then a few more | optional, hidden when empty |
| 6 | Action again | the main action with what happens next | one line, one button | yes |
| 7 | About the maker | who is behind it, one paragraph | short | optional |
| 8 | FAQ | answers to the questions from fact 14 | question and answer list | optional, hidden when empty |
| 9 | Final action | the action a third time | one line, one button | yes |
| 10 | Footer | maker, contact; privacy, terms, accessibility statement | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only. Balanced: references 3, 4 and 6 returned 25 to 97 images (many are icons and logos) against 5,700 to 9,000 characters; reference 5 returned none (script-loaded). Roughly one screenshot or illustration per benefit block. Not confirmed in a rendered view.

### Skeleton B: the product page (buy or preorder a physical product)

For one physical product sold or preordered from the page. Use when the action is a purchase of something shipped.
From references 1 and 2: the feature-by-feature sections of both, the price block with inclusions of 1, the specification lists and numbered footnotes of 2.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; the buy or preorder action with the price | | yes |
| 1 | Opening | product image; one-line promise; price; availability or ship date; main action | image first, then heading, then price and button | yes |
| 2 | Feature sections | one section per main feature: heading, short paragraph, image | alternating image and text | yes |
| 3 | What you get | what is in the box, what is included (content, service), what is not | short list | yes |
| 4 | Proof | real reviews, press | | optional, hidden when empty |
| 5 | Price block | price, currency, what is included, taxes and shipping, availability, the action | one block, the action prominent | yes |
| 6 | Accessories or plans | each with its own price and availability | small blocks | optional |
| 7 | Specifications | a full list: size, weight, battery, requirements, connectivity, included | two-column list | yes |
| 8 | Who made it | the maker, one paragraph | short | optional |
| 9 | Help | FAQ, contact, shipping and returns | links | yes |
| 10 | Footnotes | numbered qualifications of claims marked in the page | small | required when claims need them (rule 14) |
| 11 | Footer | maker, contact; privacy, terms of sale, accessibility statement | small | yes |

Image-to-text ratio: **estimate**. Image-led: each feature section in references 1 and 2 pairs one image with a short paragraph; reference 1's text describes a closing row of six photos. Roughly one large image per feature section. Not confirmed in a rendered view; the extraction returned only one image each for references 1 and 2 because their images load by script.

Risk seen in reference 8: when the maker's attention moves to another product, the page's first screen sells that product. If the customer's offer changes, rebuild the page around the new offer rather than stacking banners on the old one.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with marketers in either language. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file. Items marked "not verified" are the least certain; the rest are also unconfirmed.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view. References 1, 2 and 5 load their images by script, so their image counts are not meaningful.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. No local-business campaign page was verified; six of eight references are software.
6. The checkout, sign-up and download flows behind the references' actions were not followed; whether their prices match at checkout was not checked.
7. The brief asked for references dated 2026-11-21. The fetches ran on 2026-11-22, and that is the date recorded.
8. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
