# Catalogue or collection

Covers: a set of items shown one by one, each with its own record, where the visitor does **not** pay on the site. The visitor looks, filters, asks, finds a dealer or comes to see. Three kinds: a maker's catalogue of products made in many copies (furniture, lighting, tiles); a dealer's stock of one-off items (classic cars, antiques, vintage pieces); and a collection that is shown, not sold (a museum, an archive, a club or private collection).
Does not cover: a shop with a basket and checkout (use `clothing-shop.md` for the shop mechanics); one creator presenting their own work (use `portfolio.md` or `photographer.md`); property listings (use `real-estate-agent.md`).
Written 2026-11-22. References checked 2026-11-22. Template: [README.md](README.md).

## 1. Objects

A catalogue sells **attention to one item at a time**. Everything follows from that: every item needs a record that stands on its own (a name, a picture, the facts that decide interest), a status that is true today, and one clear next step.

The first question is which of three modes this is, because the rules differ:

| Mode | One record means | After a sale | Example (illustrative) |
|---|---|---|---|
| Multiple | a product made in many copies, often with variants | nothing changes; the record stays | a chair available in three woods |
| Unique | one physical object | the record becomes "sold" and leaves the live list | a 1971 car with one chassis number |
| Collection | one object that is not for sale | nothing is sold; status is "on display", "in store", "on loan" | a woodblock print in a museum |

### Owner (the business or institution)

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Northside Lighting" |
| Mode | required | multiple, unique or collection |
| What the visitor should do | required | enquire, find a dealer, visit the showroom, buy on a separate shop, just look |
| Contact for enquiries | required | phone, email, or a form that reaches a person |
| Where items can be seen | optional | showroom address and hours, stockists, museum galleries |
| Opening hours of the showroom or galleries | required if there is a place to visit | |
| Separate shop link | optional | some makers keep the catalogue and the shop on different sites |
| Trade or professional contact | optional | architects and designers often get their own entrance |
| Year founded, short story | optional | |
| Social account | optional | |

### Category (or collection, room, theme)

| Field | Required | Example |
|---|---|---|
| Name | required | Chairs, Tables, Lighting; or Paintings, Prints, Textiles |
| Order | required | |
| Parent category | optional | Chairs > Dining chairs |
| Short note | optional | "All tables can be made to size" |

An item belongs to one main category and may appear in several themes (by designer, by material, by period).

### Item

| Field | Required | Example |
|---|---|---|
| Name or title | required | "Oak bench, 1950s"; "Model 41 armchair" |
| Identifier | required, unique | model number, SKU, chassis number, museum accession number |
| Main image | required, or an explicit "no image yet" | |
| More images | optional | |
| Maker, designer or artist | optional; required when known and relevant | as the owner states it, with the right qualifier (see rule 9) |
| Date or year | optional | exact ("1971"), approximate ("about 1823"), or a range |
| Short description | optional | one or two sentences |
| Dimensions | optional; with units | 45 x 52 x 78 cm |
| Materials, finish | optional | |
| Category | required | |
| Price | optional, see rule 4 | 1,120 |
| Price type | required when a price is shown | fixed, "from", "price on request" |
| Status | required | see the status list below |
| Condition | required for unique second-hand items | as described by the owner |
| Provenance or history | optional; important for unique items | previous owners as the owner chooses to state them, service history, exhibitions |
| Documents | optional | data sheet, care guide, assembly guide, condition report |
| Image credit and rights | required when the image is not the owner's own | photographer, licence |
| Date added | required (system) | for "new arrivals" |

Status list (pick the ones that fit the mode):

- Multiple: available, made to order (with lead time), new, new colours, discontinued.
- Unique: available, coming soon, reserved or under offer, sold.
- Collection: on display (with where), in store (with how to see it), on loan, not currently viewable.

### Variant (multiple mode only)

| Field | Required | Example |
|---|---|---|
| Item | required | |
| What varies | required | wood, colour, size, cable length |
| Value | required | oak, black, 120 cm |
| Price difference | optional | |
| Image | optional | |
| Available | required, default yes | |

### Maker, designer or artist (when credited)

| Field | Required | Example |
|---|---|---|
| Name | required | as published by the owner |
| Years or short note | optional | |
| Items | derived | |

Living designers and artists are named only as the owner has the right to name them (see Legal).

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Enquiry | item (required), visitor name, email or phone, message, consent | Always tied to an item, so the owner knows what the question is about |
| Dealer or stockist | name, address, country, phone, website, which ranges it carries | Multiple mode. Kept current; see failure modes |
| Story or journal entry | title, date, text, images, linked items | All six references carry stories next to items |
| Catalogue file (PDF) | title, season or year, file, date published | A dated file; old ones are marked as old |
| Viewing appointment | item or room, date, time, visitor | For unique stock and for objects in store |
| Sell-to-us request | visitor, item description, photos | Unique mode: dealers buy stock from the public (reference 4) |
| Visitor list (saved items) | items | Optional; see Site vs app |

## 2. Rules

1. Every item has exactly one identifier, and no two items share it.
2. Every item belongs to exactly one main category.
3. Every item has a main image, or says "image coming soon". A blank frame or a broken image is never shown.
4. A price is optional, but its absence is explicit: "price on request" or "ask us", never a blank and never zero.
5. A price that depends on the variant says "from". Every price shows its currency. Whether consumer prices must include tax is a legal question (see Legal).
6. Dimensions always carry units. The unit system follows the owner's country, and both may be shown.
7. An item's status is always one of the declared statuses for its mode. "Available" is never assumed; it is a fact the owner states.
8. A unique item marked "sold" can no longer be enquired about as if available. Its page either stays as "sold" (an archive is a proof of track record, as reference 4 shows with "Previously sold") or is removed with a redirect to its category.
9. Attribution is copied exactly, qualifiers included. "Attributed to", "workshop of", "in the style of" and "about 1823" must never be shortened into a firmer claim.
10. Claims about an item (original parts, low mileage, limited edition of N, matching numbers, a named previous owner) appear only when the owner stated them, and are shown as the owner's statement.
11. An image that is not the owner's own carries its credit line. Stock photographs are never presented as the item.
12. Every enquiry carries the item's identifier and name, so the owner sees which item it is about.
13. A filter or search that returns nothing says so, and offers to clear the filter. It never shows an empty grid.
14. A catalogue file (PDF) carries its year or season. When a newer one exists, the old one is marked or removed.
15. Each dealer entry says which country and which ranges. A dealer list with no date of last check is treated as stale.
16. "Coming soon" items do not carry a promised date unless the owner gave one.
17. A collection object's location ("on display in room 12", "in store, view by appointment") is true or not shown.
18. The next step (enquire, find a dealer, visit) is reachable from every item page without scrolling back to the top on a phone.
19. Removing an item never breaks links silently: its address leads to the category or to a "this item is no longer listed" page.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the name of your business or collection?" | Without a name nobody can find it again or tell a friend. |
| 2 | Mode | "Do you sell the same item many times, sell one-off items, or show things that are not for sale?" | It decides whether a sold item disappears, stays or was never for sale. |
| 3 | The next step | "When someone likes an item, what should they do: ask you, go to a shop that stocks it, come and see it, or buy it somewhere else?" | The whole site leads to this one action. If it is wrong, interest turns into nothing. |
| 4 | Enquiry contact | "Where should questions about an item go: which phone, email or person?" | A question nobody answers is a lost sale and a visitor who will not come back. |
| 5 | The items | "Send me the list of items: at least a name and a photo for each." | Without the items there is no catalogue. Inventing items is never allowed. |
| 6 | Prices, or the decision not to show them | "Do you want prices shown? If yes, what is the price of each item?" | Price is the first question people ask. Hiding it is allowed; inventing it is not. |
| 7 | How status stays true | "Who will mark an item as sold or no longer made, and how quickly?" | A sold item still shown as available sends people chasing something that is gone. |
| 8 | Image rights | "Did you take these photos, or do you have permission to use them?" | Using someone else's photos can bring a takedown demand or a bill. |
| 9 | Where to see items | "Can people see the items somewhere? Give me the address and opening hours, or say there is nowhere." | Without it people travel to the wrong place, or never know they could come. |
| 10 | Who is the business legally | "What is the registered name and number, for the legal pages?" | The privacy and terms pages must name who is responsible. |

Needed only in some modes:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 11 | Dealers (multiple mode, when items are sold through others) | "Which shops sell your items, in which countries?" | A visitor who cannot find where to buy gives up. |
| 12 | Condition (unique second-hand items) | "How would you describe the condition of each item, honestly?" | A buyer who travels and finds a worse item than described feels cheated. |
| 13 | Credits (collections, or items by named designers) | "Who made each item, and exactly how do you want them credited?" | A wrong attribution misleads the visitor and can be a legal problem. |
| 14 | Viewing rules (objects in store, unique stock) | "Can people book to see an item? How?" | The visitor needs to know whether "come and see it" is possible. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the items.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Category names | grouped by item type from the item names | Wrong grouping is visible and easy to fix | Customer confirms the grouped list |
| Order inside a category | newest added first | Matches the "new arrivals" pattern in references 1, 3, 4 | Setting, labelled "default order" |
| Card fields | image, name, maker if known, year if known, price or "price on request", status label | Every reference card carries a subset of these | Shown as "fields on each card - change them" |
| Unique-mode card fields | as above plus the three or four facts that decide interest for this kind of item (for cars: year, mileage, body style, colours) | Reference 4 shows a fixed set per card | The customer chooses the facts |
| Missing price | "Price on request" | Says openly there is no number | Listed for the customer as "no price given" |
| Status labels | the list in section 1 for the chosen mode | Domain vocabulary, not a fact | Editable list |
| Sold items | kept as "sold" in an archive page, not in the live list | Reference 4 keeps "Previously sold" | Setting; customer may choose removal |
| Items per page | 24 (estimate) | Keeps pages light on a phone | Setting, labelled "default" |
| Image alt text | the item's name and main material | Better than none; never invents | Marked "draft description - check it" |
| Enquiry form fields | name, email or phone, message; item filled in automatically | The minimum to answer | Shown to the customer before publishing |
| Units | metric, or imperial for the United States | Follows the country | Shown, changeable |
| Currency | the owner's country | Follows the address | Shown next to every price |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Legal page structure | headings only: who we are, what we collect, why, how long, your rights, image credits, contact | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | A missing journal is better than an empty one | Listed as "not shown yet: stories, dealers, downloads" |

Never a default, whatever the customer left out: an item, a price, a status of "available", a date, an attribution, a maker's name, a dimension, a material, a condition, a mileage, an edition size, provenance, a dealer, an award, a review, or any claim about originality.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Sold item still shown as available | Asks or travels for something already gone | Distrust; a wasted trip | Rule 8; mandatory fact 7; owner can mark sold in one step |
| Discontinued product still listed | Orders through a dealer, is told it no longer exists | The dealer and the visitor both blame the maker | "Discontinued" status; yearly prompt to review the list |
| Price on the site is old | Pays more than the site said | An argument; in some places a legal problem | Date on prices; yearly prompt |
| "From" price read as the price | The chosen variant costs far more | Distrust | Say what the price depends on |
| Wrong image on an item | Asks about one thing, gets another | A confused enquiry, a lost buyer | Image tied to the identifier, not to the position in a list |
| Attribution stated more firmly than the owner said | A buyer relies on a claim that is not true | A dispute; possibly a legal claim | Rule 9; copy qualifiers exactly |
| Filter returns nothing and shows an empty grid | Thinks the catalogue is broken or empty | Leaves | Rule 13 |
| Search cannot find a model number | A professional with a spec sheet cannot find the item | A lost trade order | Search covers identifiers, not only names |
| Enquiry form sends to nobody | Waits for an answer that never comes | The worst case: interest wasted silently | Mandatory fact 4; test the form at publish and on a schedule |
| Enquiry arrives without the item | Owner cannot tell what the visitor wants | Slow, awkward reply | Rule 12 |
| Dealer list out of date | Goes to a shop that no longer stocks it | A wasted trip; a dealer complains | Rule 15; date of last check |
| Old catalogue PDF | Plans a room with a range that has changed | Wrong orders | Rule 14 |
| Removed item's link breaks | A shared link leads to an error page | Looks neglected | Rule 19 |
| Large images not resized | Pages crawl on a phone; images appear late | Leaves before seeing anything | Resize on upload; placeholder while loading |
| Image used without permission | (The visitor sees nothing wrong) | A takedown demand or a bill | Mandatory fact 8; credit field |
| Template text left on the page | Sees placeholder words instead of content | Looks unfinished; distrust | Check every published page for unfilled fields; seen on two business sites loaded for the craftsman and real-estate files |
| Units missing or mixed | Measures the wrong size | A returned item or a piece that does not fit | Rule 6 |
| Collection object shown as "on display" but in store | Visits to see it and cannot | A disappointed visit | Rule 17 |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a curator, dealer or furniture maker in either language. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Catalogue | the list of items | קטלוג | كتالوج |
| Collection | a set of objects kept together; also a product range | אוסף; קולקציה (for a product range) | مجموعة |
| Item, object, piece | one record | פריט | قطعة |
| Product range | a family of related products | סדרה / קו מוצרים | تشكيلة (not verified) |
| SKU, item number | the seller's code | מק"ט | رمز المنتج (not verified) |
| Model | a named design | דגם | موديل / طراز |
| Variant, option | colour, size, finish | גרסה / אפשרות | خيار (not verified) |
| Finish | surface treatment | גימור | تشطيب |
| Dimensions | sizes | מידות | أبعاد / مقاسات |
| In stock | ready now | במלאי | متوفر في المخزون |
| Made to order | made after ordering | בהזמנה אישית / לפי הזמנה | حسب الطلب |
| Lead time | time from order to delivery | זמן אספקה | مدة التوريد (not verified) |
| Discontinued | no longer made | הופסק ייצורו (not verified) | متوقف عن الإنتاج (not verified) |
| Sold | gone | נמכר | مُباع |
| Reserved, under offer | held for a buyer | שמור (not verified for trade use) | محجوز |
| Price on request, POA | no public price | מחיר לפי פנייה (not verified as standard wording) | السعر عند الطلب (not verified) |
| Dealer, stockist, retailer | a shop that sells the maker's items | משווק / מפיץ / חנות מורשית | وكيل / موزّع |
| Trade, professionals | architects, designers, contractors | אנשי מקצוע | مهنيون (not verified) |
| Data sheet, spec sheet | technical facts | דף מפרט / מפרט טכני | ورقة المواصفات (not verified) |
| Limited edition | a fixed number made | מהדורה מוגבלת | إصدار محدود |
| Designer | who designed it | מעצב/ת | مصمم/ة |
| Maker | who made it | יוצר/ת; יצרן (for a company) | صانع |
| Provenance | ownership history | פרובננס / היסטוריית בעלות (not verified as common usage) | not verified |
| Attribution | who is believed to have made it | ייחוס | not verified |
| Condition | state of a used item | מצב | حالة |
| Accession number | a museum's object number | מספר רישום (not verified) | not verified |
| On display | can be seen in the galleries | מוצג | معروض |
| In store | kept in storage | במחסן / בשמירה (not verified for museum use) | في المخزن (not verified) |
| On loan | lent to another place | בהשאלה | مُعار (not verified) |
| New arrival | recently added | חדש במלאי / הגיע לאחרונה | وصل حديثاً (not verified) |
| Previously sold | archive of sold stock | נמכרו בעבר | not verified |
| Left-hand drive | car with the wheel on the left | הגה שמאלי | مقود على اليسار (not verified) |

Notes on language:

- "Collection" means two things: a museum's holdings, and a season's product range. Ask which the customer means.
- "Lot" belongs to auctions. Do not use it for a catalogue item.
- Words to avoid unless the customer said them and can back them: "original", "authentic", "rare", "museum quality", "investment", "one of only", "mint", "concours", "iconic". Each is a claim.
- Design names can be trademarks. Use them exactly as the owner does.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the owner's country before it is relied on.

### Applies almost everywhere

- **Image rights.** Every photograph has an author. Using one requires permission or a licence. Museum images often carry their own licence terms, which differ between institutions. Not verified per institution.
- **Designer and artist names, design names and logos** can be protected as trademarks or by design right. Use only what the owner has the right to use.
- **Privacy notice.** Needed as soon as the site collects a name and contact (an enquiry form, a viewing request, a saved-items account).
- **Descriptions must not mislead.** Condition, age, attribution and claims such as "original" are treated as part of the offer in most consumer-protection law. Not verified per country.
- **Marketing messages** (newsletters) generally need prior agreement and an easy way to unsubscribe.
- **Reviews and press quotes** must be real and correctly attributed.

### Israel

- Accessibility: businesses serving the public are required to make their websites accessible and to publish an accessibility statement, under the Equal Rights for Persons with Disabilities Law and its service-accessibility regulations, with Israeli Standard 5568 as the technical reference. Exemptions and thresholds: not verified.
- Privacy: the Protection of Privacy Law applies; Amendment 13 came into force in August 2025. What it requires of a small catalogue site: not verified.
- Prices: consumer law requires displayed prices to include VAT. Whether a catalogue that does not sell online must show prices at all: not verified.
- Antiquities: dealing in antiquities is regulated under the Antiquities Law and needs a licence from the Israel Antiquities Authority. What a dealer's site must display: not verified.
- Marketing messages: section 30A of the Communications Law requires prior consent for advertising by SMS or email. Details: not verified.

### European Union and United Kingdom

- GDPR (EU) and UK GDPR apply to enquiry data. Non-essential cookies need consent (ePrivacy rules in the EU, PECR in the UK).
- Consumer prices, when shown as an offer, are believed to have to include VAT in both. Whether a catalogue with "price on request" is an offer at all: not verified.
- UK: copyright protection for mass-produced artistic designs (relevant to replica furniture) was extended in 2020 when an older time limit was repealed. Exact scope: not verified.
- UK: the Ivory Act 2018 restricts dealing in items containing elephant ivory, with narrow exemptions that must be registered or certified. Not verified in detail.
- Export of cultural goods out of the EU or UK can need an export licence above value and age thresholds. Not verified.
- Selling used cars to consumers: the Consumer Rights Act 2015 (UK) applies to dealers; offering finance requires authorisation for credit broking by the Financial Conduct Authority. Not verified. One reference (4) offers vehicle finance.
- Accessibility: the European Accessibility Act applies from June 2025 to certain consumer services, with a microenterprise exemption. Whether a catalogue without checkout is in scope: not verified.

### United States

- The Americans with Disabilities Act is applied by courts to business websites in many cases; no single federal technical standard for private businesses. Not verified.
- Used-car dealers are subject to the FTC Used Car Rule (the buyers guide) for vehicles offered for sale. How it applies to a website listing: not verified.
- State privacy laws apply above thresholds. Not verified.
- Prices are generally shown before sales tax. Not verified per state.

### What the product does with this

- The product may generate the **structure** of a privacy page, a terms page, an image-credits page and an accessibility statement. It marks each as a draft that needs review.
- The product never states that the site "complies with" a named law.
- The product asks which country the owner is in before generating any legal page, and asks whether any item contains regulated material (ivory, antiquities, protected species) before publishing such an item.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, about, how to buy or where to see items, contact, stories, legal pages. A small catalogue of up to a few dozen items that rarely change can be a content site with each item as a fixed page and a phone or email link as the action. This is a complete and honest product for a maker who updates twice a year.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Item page | cannot be empty: no item, no page | missing image shows "image coming soon", never a broken icon | |
| Category page | category hidden when it has no items | | |
| Stories | section hidden | | Never filled with placeholders |
| Dealers | section hidden; the enquiry contact stays | | Shows the date the list was last checked |
| Downloads | hidden | a missing file is removed, not linked | Each file shows its year |
| Map of a showroom | address as text always shown | text address and a link remain if the map fails | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Item list with filters and search | items, categories, statuses | "Nothing matches - clear filters" with a button (rule 13) | placeholders in the shape of cards, never an empty grid that looks like "no items" | "Could not load items - try again", with the contact | n/a | everyone reads; only the owner changes |
| Item page | one item, its images, variants, documents | n/a | images load progressively; text first | "This item is no longer listed" with a link to its category (rule 19) | n/a | everyone reads |
| Enquiry form | stores the enquiry with the item; alerts the owner | n/a | button shows "sending" and cannot be pressed twice | "Not sent - please email or call", with both | visitor sees "received" and when to expect a reply | visitor writes; only the owner reads |
| Viewing request | items or rooms, available times | "No times this week - contact us" | | "Could not load times - contact us" | status "requested" until the owner confirms | visitor sees only their own request |
| Dealer finder | dealers with country and location | "No dealer in this country yet - contact us directly" | | if location lookup fails, a country list remains | n/a | everyone reads |
| Saved items | a list per visitor | "Nothing saved yet" | | | kept in the browser by default; an account only if the owner wants lists across devices | visitor only |
| Owner's item editor | items, images, statuses | "No items yet - add the first" | upload progress per image | a failed save says so and keeps what was typed | visible on the public site right after saving; "mark as sold" is one action | owner and named staff, behind a login |
| Import from a spreadsheet | a column map | | progress shown | rows that failed are listed by row number, never skipped silently | a preview before publishing | owner only |
| Visitor-made sets (collections) | accounts, sets of objects | "You have no sets yet" | | | | each visitor owns their own sets; public only if they choose (reference 6) |

### Needs accounts

- The owner always needs one as soon as items are editable.
- Visitors do not need one to look or enquire. A visitor account is justified only for saved lists across devices, trade price lists, or visitor-made sets.
- A trade area (prices for professionals, technical files) needs trade accounts, approved by the owner. References 1 and 3 both show a separate professional entrance.

### Needs payments

- Nothing in this domain needs payments by definition. Deposits to reserve a unique item, paid viewings or a print shop are additions, and each brings refunds and the cancellation law of the owner's country.
- When the owner sells online as well, either link to the existing shop (reference 2 keeps the shop on a separate site) or use the shop mechanics of `clothing-shop.md`.
- Default: no payments.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and every ratio below is an estimate from counts in the extracted text. Image counts include logos, icons and navigation thumbnails; the tool appears to cap at 100. Character counts are approximate, after removing link targets. Only home pages (or the collection's front page) were fetched.

**Curation.** Chosen by the author from Scandinavian design makers, a London classic-car dealer and two national museums' online collections, all believed to be the owner's own site. No awwwards.com category was consulted; none is claimed as an award winner. All six are in English, in Latin script.

**Limit.** All six are large or well-known organisations. No small maker, no antiques shop and no private or club collection was verified. Two of the six (3 and partly 2) also sell online, which blurs the line with a shop. The skeletons are a ceiling for structure, not a picture of the typical customer.

Verified: 6.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.fredericia.com | 2026-11-22 | Danish furniture maker, multiple mode. Navigation by product type (chairs, lounge chairs, sofas, tables, coffee tables, storage, accessories), then "By designer", then inspiration (care guide, cases, catalogues, material guide), impact, and a separate "For Professionals" group (media library, technical files, catalogues, B2B platform, partner area). "Where to buy" and "Dealers" in the header. Home: one product focus - one sentence on who the company is and when it was founded - six category tiles - "three most beloved designs", each card with the designer's name - stories. No prices on the home page. Extraction: 100 images (cap), about 9,000 characters, mostly navigation. |
| 2 | https://www.artek.fi/en | 2026-11-22 | Finnish furniture maker, multiple mode. Navigation: company, products (fourteen categories), spaces, reading room, where to buy, own stores, and "Shop online" pointing to a separate shop site. Home: a heritage line - six story blocks, each image, heading, two sentences and "Read the story" (a textile collection, one chair's history, a collaboration, forestry, a care guide) - "most iconic products": six cards, each name, designer and year - "Show all products". No prices on the catalogue site. Extraction: 13 images, about 3,500 characters. |
| 3 | https://www.louispoulsen.com | 2026-11-22 | Danish lighting maker; catalogue and shop on one site (payment-method icons in the footer; US region path). Top: "Sign up for trade" and a professional "Toolbox". Order: a limited-edition hero - a row of products, each name and a "From" price in dollars, some labelled "New" or "New colors" - three campaign blocks - a full-collection block - a social feed prompt - categories, including spare parts. Extraction: 16 images, about 2,500 characters. |
| 4 | https://www.hexagonclassics.com | 2026-11-22 | London classic and sports car dealer, unique mode. Phone and email in the header. Stock navigation by make, plus "Left Hand Drive Cars", "Previously Sold" and "Coming Soon"; also servicing, restoration, facilities, "Sell Your Car". Home: positioning with a stated stock size - four tiles (stock, service, news, coming soon) - "New Arrivals": twelve cards, each a title (make, model, year, one key claim), one line of specification, then the same five labelled facts (body style, year, mileage, exterior colour, interior colour) and "More details" - no prices on the cards - "Sell Your Car" - dated news posts. Extraction: 13 images, about 4,500 characters. |
| 5 | https://collections.vam.ac.uk | 2026-11-22 | A national museum's online collection, collection mode. Order: a search with the collection size stated - most searched - a trending theme - browse by theme - "In our venues" (see objects in person; some not on display can be viewed by appointment) - "Order an Object" in three steps (choose an object, decide when, visit free) - the museum shop - the header image's credit line, giving title, technique, series, maker, an approximate date ("about 1823"), place, museum number and copyright holder. Extraction: 100 images (cap), about 1,000 characters. |
| 6 | https://www.rijksmuseum.nl/en/collection | 2026-11-22 | A national museum's online collection, collection mode. Order: "Discover" (a featured object, an artist, a theme, a "what do you love?" explorer) - an artworks grid of twelve objects with titles - "Visitor stories": sets made by visitors, each with a title, a date, a count of artworks and the visitor's username - "Create your own" - getting-started links - "About the collection online". Shows a collection site that has become an app with visitor accounts. Extraction: 18 images, about 2,300 characters. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://www.carlhansen.com | 2026-11-22 | Loads and is the maker's own site, but the extraction returned only campaign lines and a footer with webshop contacts (about 1,200 characters). Too thin to describe the structure. |
| https://www.benchmarkfurniture.com | 2026-11-22 | Loads; the extraction returned only the navigation (about 140 characters). |
| https://www.mosaicdelsur.com | 2026-11-22 | Loads, but the page is in Spanish and has a basket: a shop, and not an English-language reference. |

Tried and did not load (not counted): collection.cooperhewitt.org, andtradition.com (404), gubi.com, vitra.com/en-gb/home.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the maker's catalogue (multiple mode)

For a maker or brand whose items are made in many copies and bought through dealers, a showroom or on request. Default for multiple mode.
From references 1, 2 and 3; the category tiles from 1, the item cards with designer and year from 2, the "new" labels from 3, the professional entrance from 1 and 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; categories; "where to buy" or "enquire" always visible; a quieter link for professionals if there is a trade area | the next step is never more than one tap away | yes |
| 1 | Opening | one featured item or range with one sentence; one line on who the maker is | one image, one heading, one line | yes |
| 2 | Categories | tiles by item type | image and name per tile | yes |
| 3 | Featured items | a short row of items: image, name, designer or maker, year, price or "price on request", status label | card per item | yes |
| 4 | Stories | a few stories about how things are made or used, each linked to items | image, heading, two sentences, link | optional, hidden when empty |
| 5 | Where to buy or see | showrooms with address and hours; dealer finder; or the enquiry contact | complete without a map | yes |
| 6 | For professionals | downloads (data sheets, catalogue files with year), trade contact | links only | optional |
| 7 | Footer | name, contact, care and warranty pages, privacy, terms, accessibility statement, image credits | small | yes |

Item page (domain knowledge; no reference item page was fetched): images - name and identifier - maker or designer and year - short description - variants - dimensions with units - materials - price or "price on request" - status - next step - documents - related items.

Image-to-text ratio: **estimate**, from extraction counts only. Image-led: references 2 and 3 returned 13 and 16 images against about 2,500 to 3,500 characters, mostly short headings and two-sentence blurbs; reference 1 hit the tool's cap of 100 images. Roughly one image per block, with the text doing naming and facts, not persuasion. Not confirmed in a rendered view.

### Skeleton B: the stock list or collection (unique and collection modes)

For a dealer of one-off items or for a collection shown to the public. The visitor arrives looking for something specific, so finding comes first.
From references 4, 5 and 6; the fixed card facts and the "previously sold" archive from 4, the search-first opening and the "see it in person" block from 5, the discover row from 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; search; stock or collection by category; contact (phone and email for a dealer) | search is the largest control | yes |
| 1 | Opening | one sentence on what this is and its size (stated by the owner); the search | heading, one line, search | yes |
| 2 | New arrivals or featured | cards with image, title, and the same three to five facts on every card; status label | identical card layout so items can be compared | yes |
| 3 | Browse | by category, period, maker or theme | links or tiles | yes |
| 4 | See it in person | address, hours, how to book a viewing or order an object from store | plain steps | yes if there is a place to visit |
| 5 | Archive | "previously sold" (dealer) or "not currently on display" (collection) | quieter than the live list | optional |
| 6 | Sell to us (dealer only) | what the dealer buys and how to offer an item | one paragraph and an action | optional |
| 7 | Stories | dated posts | short list | optional, hidden when empty |
| 8 | Footer | name, address, contact; privacy, terms, accessibility statement; image rights and credits | small | yes |

Item page for unique mode (domain knowledge): images - title - status - the fixed facts - description in the owner's words - condition - provenance or history as stated - price or "price on request" - enquire or book a viewing, with the item filled in.

Image-to-text ratio: **estimate**. Mixed: reference 4 returned 13 images against about 4,500 characters, with most text in the repeated card facts; references 5 and 6 are image grids with almost no running text. For a dealer, the facts on each card matter as much as the picture. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a curator, dealer or maker. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source. This includes the Israeli antiquities licence, the UK ivory and design-copyright statements, export licences, the FCA and FTC statements, and whether a catalogue without checkout must show prices.
3. Image-to-text ratios and visual quality of all references: text extraction only, no rendered view. Image counts of 100 are the tool's cap.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. Only 6 references, all large organisations. No small maker, antiques shop, private or club collection.
6. No item page, filter result, enquiry form or dealer finder of any reference was fetched. The item-page orders in section 10 are domain knowledge.
7. References were checked on 2026-11-22, one day after the date given in the brief (2026-11-21), because that is when they were loaded.
8. The default of 24 items per page is an estimate.
9. Stock sizes, collection sizes and other numbers mentioned in the reference notes are what the pages stated on the day.
10. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
