# Domains

Status: phase 1, started 2026-11-21. Owner brief of 2026-11-21.

## What a domain file is

A skeleton says where to put a menu. A domain says a menu is a list of dishes, each with an optional price, and a dish can be sold out.

A domain file is everything 148AI must know about one kind of business or project before it builds a product for a customer who has no technical knowledge. It answers four questions:

1. What exists in this world, and what is true about it?
2. What must we ask the customer, and what may we fill in ourselves?
3. What goes wrong, and what does the law require?
4. What do good real sites in this domain look like?

One domain, one file: `docs/domains/<slug>.md`. The slug is the one in the table below.

A domain file is a document. It does not authorize building anything. It is input for the intake conversation, the builder and the acceptance checks.

## Words used in every file

- **The customer**: the person talking to 148AI (for example the salon owner).
- **The visitor**: the customer's customer (the person who wants a haircut).
- **Fact**: something only the customer can know (a phone number, a price). Never invented.
- **Default**: something the domain may fill in when the customer said nothing. Always shown to the customer as a default, and the customer can change it.
- **Not verified**: the author believes it but did not check a source. Treat as a question, not as knowledge.
- **Estimate**: a number without a source.

## The template

Every domain file uses exactly these headings, in this order. Do not rename, reorder or drop one. If a section has nothing to say, keep the heading and write "Nothing for this domain" with one line of reason.

```
# <Domain name>
## 1. Objects
## 2. Rules
## 3. Mandatory facts
## 4. Declared defaults
## 5. Failure modes
## 6. Professional language
## 7. Legal
## 8. Site vs app
## 9. References
## 10. Skeletons
## 11. Not verified
```

What goes under each heading:

| Heading | What goes there |
|---|---|
| `# <Domain name>` | Three lines at most: what this domain covers, what it does not cover, and which neighbouring domain file to use instead. Then the date written and the date references were checked. |
| `## 1. Objects` | What exists in this world. One table per object: field, required or optional, a plain example. Say how objects relate (a service belongs to a category; a stylist offers some services). |
| `## 2. Rules` | What is allowed, forbidden and mandatory in this world, as short numbered statements that a check could test. Business rules, not design rules. |
| `## 3. Mandatory facts` | What the product cannot be built without. For each: the one plain-language question to ask the customer, and the human reason ("a phone number - without it people cannot call"). Nothing here may ever be guessed. |
| `## 4. Declared defaults` | What may be filled in from the domain when the customer said nothing. Each default says what it is, why it is safe, and how it is marked so the customer sees it is a default. Facts about the specific business are never defaults. |
| `## 5. Failure modes` | What breaks, and how it looks to the visitor. One row each: what went wrong, what the visitor sees, what it costs the customer, how to prevent it. |
| `## 6. Professional language` | The domain's own terms in English, with Hebrew and Arabic equivalents where the author is confident. Anything else says "not verified". Also words to avoid. |
| `## 7. Legal` | Privacy, terms, accessibility statement, and regulation specific to the domain. Every statement names its jurisdiction. Anything the author is unsure of is marked "not verified". This section is a checklist of questions for a lawyer, not legal advice. |
| `## 8. Site vs app` | Which parts are content pages, and which need data, accounts or payments. For every part that needs data: empty state, loading state, error state, save, and permissions (who may see and change what). |
| `## 9. References` | 5 to 8 real sites, following the reference rules below. For each: URL, date checked, what was observed. Also list sites that were loaded and rejected, with the reason. |
| `## 10. Skeletons` | One or two page skeletons extracted from the references: which sections, in which order, the hierarchy, the image-to-text ratio, and which reference each part came from. |
| `## 11. Not verified` | Every open item from the sections above, in one list, so a reader can see at once what still needs checking. |

## Reference rules

1. **5 to 8 real sites** of real businesses or projects in the domain. Curated by a person or an agent who read them, not taken blindly from a search result.
2. **Each one must actually load.** Fetch it on the day. Record the date. A site that fails is replaced, not listed.
3. **The business's own site.** Not a directory, an article, a marketplace listing, a booking-platform profile or a template demo.
4. **Not blocked.** If the fetch returns a block page, a captcha or an empty shell, it does not count.
5. **Prefer international English-language sites of high design quality.** Name the curation source where one was used, for example awwwards.com/websites/hotel-restaurant, awwwards.com/websites/photography, awwwards.com/websites/portfolio.
6. **Latin script only in this phase.** Each other script (Hebrew, Arabic, Cyrillic and so on) gets its own references later, because layout, direction and type behave differently.
7. **For each reference write:** the URL, the date checked, and what was observed (sections in order, what the main action is, how prices and contact details are shown).
8. **Say how it was checked.** A text fetch and a rendered browser view are different evidence. If only the text was fetched, the image-to-text ratio is an estimate and must be labelled so.
9. **Never copy** colours, logos, photographs or text. Extract structure only: sections, order, hierarchy, ratio.
10. **If fewer than 5 could be verified,** write how many were verified and say so plainly. Never list a site that was not loaded.
11. **No personal data of private individuals.** Business names, business addresses and business phone numbers published by the business are allowed; names of private people are not needed and are left out.

## Writing rules

- Plain English. Short sentences. No padding.
- A number without a source is labelled "estimate".
- "Not verified" is said openly, with the reason.
- An example is marked as an example, so nobody mistakes it for a fact about a real business.

## Phase-1 domains

| # | Slug | Domain | Status |
|---|---|---|---|
| 1 | hair-salon | Hair salon and barbershop | written 2026-11-21: [hair-salon.md](hair-salon.md) |
| 2 | food-stall | Food stall, kiosk, food truck | not written |
| 3 | restaurant | Restaurant | not written |
| 4 | cafe-bakery | Cafe and bakery | not written |
| 5 | butcher-deli | Butcher and delicatessen | not written |
| 6 | kindergarten | Kindergarten and daycare | not written |
| 7 | clinic | Clinic (general and specialist practice) | not written |
| 8 | dentist | Dentist | not written |
| 9 | lawyer | Lawyer and law firm | not written |
| 10 | accountant | Accountant and bookkeeper | not written |
| 11 | garage | Car garage and repair shop | not written |
| 12 | clothing-shop | Clothing shop | not written |
| 13 | catalogue-collection | Catalogue or collection | not written |
| 14 | tour-guide | Tour guide | not written |
| 15 | hotel-guesthouse | Hotel and guesthouse | not written |
| 16 | event | Event | not written |
| 17 | wedding | Wedding | not written |
| 18 | community | Community | not written |
| 19 | product-docs | Product documentation | not written |
| 20 | portfolio | Portfolio | not written |
| 21 | personal-site | Personal site | not written |
| 22 | photographer | Photographer | not written |
| 23 | fitness-trainer | Fitness trainer | not written |
| 24 | beauty-cosmetics | Beauty and cosmetics | not written |
| 25 | real-estate-agent | Real-estate agent | not written |
| 26 | tutor-courses | Tutor and courses | not written |
| 27 | craftsman-renovation | Craftsman and renovation | not written |
| 28 | nonprofit | Nonprofit | not written |
| 29 | musician-band | Musician and band | not written |
| 30 | landing-page | Landing page | not written |

The status column is edited by hand in this phase. It is not a derived status file and no generator covers it.

A file counts as "written" only when all eleven headings are filled and the references section lists only sites that were loaded on the stated date.
