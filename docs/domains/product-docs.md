# Product documentation

Covers: the written help for one product that people already have or are about to use: a software app, a device, a service with an account. Getting started, how-to guides, reference, troubleshooting, frequently asked questions, release notes. Public or for customers only.
Does not cover: selling the product (use `landing-page.md`); a forum where users answer each other (use `community.md`); courses with lessons and progress (use `tutor-courses.md`).
Written 2026-11-22. References checked 2026-11-22. Template: [README.md](README.md).

## 1. Objects

Documentation sells **a finished task**. A visitor arrives with one job to do ("connect the printer", "export my data", "why does it show error 42") and leaves when the job is done or when they give up. Everything follows from that: a page is about one task, a step is one action, and every page must be findable by the words the visitor already has in their head.

The first question is which of two kinds this is, because the language differs:

- **User help** (help centre, knowledge base, manual): for people using the product. No code. References 5, 6, 7, 8.
- **Developer documentation**: for people building on the product. Code samples, reference tables. References 1, 2, 4. Reference 3 mixes both.

### Product (the thing documented)

| Field | Required | Example (illustrative) |
|---|---|---|
| Product name | required | "Lumen Desk Lamp", "Shiftbook" |
| What it does, in one sentence | required | "A booking app for small studios" |
| Who uses it | required | studio owners and their staff |
| Platforms or models covered | required | iPhone, Android, web; or model numbers L1 and L2 |
| Current version | required for software, optional for a device | 3.2 |
| Company that makes it | required | the legal entity, for the footer and legal pages |
| Support route | required | email, form, chat, phone, community |
| Status page or service-status link | optional | only for online services |
| Languages the docs exist in | optional | English source, Spanish translation |
| Logo | optional | |

### Section (category)

| Field | Required | Example |
|---|---|---|
| Name | required | Get started, Guides, Reference, Troubleshooting, Billing, Release notes |
| Order | required | Get started first |
| Short description | optional | one line under the name on the docs home page, as in references 3 and 7 |
| Audience | optional | "for admins", "for team members" (reference 7 splits by audience) |
| Parent section | optional | one level of nesting is common; more is hard to navigate |

### Page (article)

| Field | Required | Example |
|---|---|---|
| Title | required | written as the task: "Export your bookings" |
| Section | required | Guides |
| Kind | required | getting started, how-to, concept (explanation), reference, troubleshooting, FAQ, release note |
| Summary | required | one sentence under the title saying what the page achieves |
| Body | required | text, numbered steps, images, tables, code |
| Applies to | optional, required when more than one version or platform exists | "version 3 and later", "Android only" |
| Prerequisites | optional | "You need an admin account" |
| Last updated | required | a date, shown on the page |
| Next page | optional | Reference 3 ends its start guide with "Next: Concepts" |
| Related pages | optional | |
| Search keywords | optional | other words people use: "download", "backup" for an export page |
| Owner | optional, internal | who keeps it correct |
| Status | required | draft, published, deprecated, archived |
| Previous addresses | derived | kept so old links redirect |

### Step

| Field | Required | Example |
|---|---|---|
| Number | derived | order in the page |
| Action | required | "Tap **Settings**, then **Export**." One action per step |
| Expected result | optional | "A file named bookings.csv is downloaded." |
| Image | optional | screenshot or photo of this step |
| Warning before the step | optional | "This deletes all bookings older than a year." |

Reference 2 numbers its steps 01 to 06, each with a heading, a sentence and a code block. Reference 1 links to step pages from a list ("Create a payment link", "Share a payment link", "Track a payment link").

### Image (screenshot, photo, diagram)

| Field | Required | Example |
|---|---|---|
| File | required | |
| Alt text | required | what the image shows, for people who cannot see it |
| Version it shows | required for screenshots of software | 3.2 |
| Caption | optional | |
| Highlight | optional | an arrow or box on the button to press |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Code sample | language, code, what it does, copy button, expected output | Developer docs only. Must run as shown (rule 11) |
| Callout | kind (note, tip, warning, danger), text | A warning comes before the step it is about |
| Glossary term | term, plain definition, synonyms | The product's own words explained once |
| Release note | version, date, what changed, what the user must do | Reference 4 opens with a banner announcing a new major version and an upgrade guide |
| Known issue | symptom, affected versions, workaround, status | A known issue is a fact from the customer, never guessed |
| Error message | exact text or code, meaning, fix | Visitors search by the exact error text |
| FAQ entry | question, short answer, link to the full page | |
| Feedback | page, helpful yes or no, optional comment, date | Reference 1 ends articles with "Was this page helpful? Yes / No" |
| Support contact | channel, hours, response time | Reference 8 names a support email on its home page |
| Language version | language, source page, translated date | Reference 5 offers the help in more than thirty languages |
| Redirect | old address, new address | Created when a page is renamed or moved |

### How objects relate

A product has sections; a section has pages; a page has steps, images and callouts. A page may apply to some versions or platforms only. A release note points to the pages it changed. A known issue points to the pages where the visitor will meet it. A translated page points to its source page and is out of date when the source changes after it.

## 2. Rules

1. Every published page belongs to exactly one section.
2. Every page has a title, a one-sentence summary and a "last updated" date that is shown to the visitor.
3. A page title says the task or the topic in the visitor's words ("Reset your password"), not the internal feature name, unless the feature name is what visitors search for.
4. One action per numbered step. Steps are numbered, not bulleted, when order matters.
5. A warning about data loss, cost, safety or an action that cannot be undone appears before the step it is about, never after.
6. A page that applies only to some versions, models or platforms says so at the top.
7. A screenshot shows the version the page describes. When the interface changes, affected screenshots are marked stale until replaced.
8. Documentation describes only what the product actually does. A feature, setting, limit or price is never written unless the customer supplied it.
9. A renamed or moved page keeps its old address as a redirect. No published link may lead to a missing page.
10. Every internal link points to a published page. Links are checked at publish time.
11. A code sample runs as shown. The copy button copies only the code, not prompts, line numbers or the output.
12. Search covers every published page and returns something useful for zero-result queries: a link to the support route.
13. Every page has a way to reach support, or to the support page, without going back to the home page.
14. A deprecated feature's page says it is deprecated, since when, and what to use instead. It is not deleted while the feature still exists for some users.
15. Release notes are in date order, newest first, each with a version and a date.
16. An error message is quoted exactly as the product shows it, so a search for it finds the page.
17. A translated page shows when it was translated, and is flagged when the source page has changed since.
18. Content behind a login says so on the public page that links to it; a visitor is never sent to a login wall without warning.
19. Every image has alt text. Text that matters is never only inside an image.
20. An automated answer feature (an "ask AI" box, as in references 1 and 6) answers only from the published pages and links to its source page. It is off by default (see section 4).

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed. Steps are the hardest: a builder that invents steps produces documentation that sends people to buttons that do not exist.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Product name | "What is the product called, exactly as your customers see it?" | People search for the name. A different spelling means they do not find the help. |
| 2 | What it does and for whom | "In one sentence, what does it do and who uses it?" | The first screen must tell a visitor they are in the right place. |
| 3 | Platforms, models or versions | "Which devices, models or versions should this help cover?" | A step that is right on a phone and wrong on a computer wastes the visitor's time. |
| 4 | The top tasks | "What are the five things people most often need help with?" | These become the first pages. Without them the docs answer questions nobody asked. |
| 5 | The real steps for each task | "Walk me through each of those, click by click or button by button, as you would on the phone with a customer." | The steps are the product of this domain. A guessed step sends people to a button that does not exist. |
| 6 | Support route | "When the help is not enough, how should people reach you, and how fast do you answer?" | A dead end at the bottom of a help page turns a question into an angry review. |
| 7 | Safety and data-loss warnings | "Is there anything that could hurt someone, damage the product, cost money or delete data if done wrong?" | A missing warning can injure a person or destroy their work. |
| 8 | Who is responsible | "What is the registered company name, for the footer and the legal pages?" | Visitors and regulators need to know who stands behind the instructions. |
| 9 | Public or private | "Should anyone be able to read this help, or only your customers after signing in?" | Public help brings people from search engines; private help needs accounts. |

Needed when they apply:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 10 | Exact error messages | "Which error messages do people see most, word for word, and what fixes each?" | People type the error into search. The page must contain the same words. |
| 11 | Known issues | "Is there anything that does not work right now, and what should people do meanwhile?" | Hiding a known problem makes people think the fault is theirs. |
| 12 | Version history | "What changed in the last few versions that users must know about?" | Release notes stop support from answering the same question a hundred times. |
| 13 | Languages | "Which languages do your users read?" | Help in the wrong language is no help. |
| 14 | Existing material | "Do you already have a manual, a PDF, an FAQ or support answers I can start from?" | Starting from real answers is safer than starting from nothing. |
| 15 | Where feedback goes | "If a reader says a page did not help, who should be told?" | Feedback nobody reads is worse than no feedback button. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the product.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Section names and order | Get started, Guides, Troubleshooting, FAQ, Release notes; plus Reference for developer docs | Seen across references 1 to 8; a common split | Editable list, labelled "suggested order" |
| Page kind per page | from the page title (a "how to" title becomes a how-to page) | Wrong kind is visible and easy to fix | Customer confirms |
| Page template | title, one-sentence summary, "applies to" if needed, steps, result, related pages, last updated, support link | Structure only, no content | Labelled "default template" |
| Getting-started path | a short numbered list of the first tasks, in order | Reference 5 does this with six numbered links | Customer confirms order |
| Navigation | sections in a side list on wide screens, a menu on phones; an "on this page" list for long pages | Seen in references 1, 2, 4, 5 | Named as Skeleton B |
| Search | on, covering all pages | Search is the main way into large docs; references 1, 5, 6 and 8 put it in the header | Setting, labelled "default" |
| Zero-result search | "Nothing found - contact support" with the support route | Says openly that there is no answer | Shown in the customer's review |
| "Last updated" date | set automatically on each save | A fact about the page, not about the product | Shown on every page |
| Feedback buttons | off until fact 15 is answered | A button that sends nowhere is a silent failure | Listed as "not shown yet: feedback" |
| Automated answers ("ask") | off | Can state things the docs do not say (rule 20) | Listed as "not enabled" |
| Code copy button | on, for developer docs | Copies only the code (rule 11) | Setting, labelled "default" |
| Language and direction | the language of the conversation | The customer chose it by speaking it | Shown, changeable |
| Legal page structure | headings only: who we are, what we collect (search terms, feedback, cookies), why, how long, your rights, contact | Structure is general; content is not | Marked "draft - not legal advice - review before publishing" |
| Empty optional sections | hidden | An empty "Release notes" page looks abandoned | Listed for the customer as "not shown yet" |

Never a default, whatever the customer left out: steps, button names, menu paths, settings, limits, prices, plan names, supported devices, compatibility claims, error messages and their fixes, known issues, safety warnings, release dates, response times, security or privacy claims ("encrypted", "we never see your data"), certifications.

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| The interface changed, the steps did not | "Tap Settings" - there is no Settings | The visitor gives up or contacts support; trust in all other pages drops | "Last updated" date; stale flag when the customer reports a new version (rule 7); ask after each release |
| Screenshot shows an old version | The picture does not match the screen | Confusion, wrong button pressed | Version field on every screenshot (rule 7) |
| Invented step or setting | Follows the help to a feature that does not exist | Worse than no page: support load and a reputation for wrong help | Rule 8; mandatory fact 5; never filled from "products like this usually have" |
| Search finds nothing for the visitor's word | "No results" for "backup" when the page says "export" | Visitor concludes the product cannot do it | Search keywords field; zero-result default; review zero-result searches if analytics exist |
| Page renamed, old link breaks | A "page not found" from a link in an email or a forum | Every old link becomes a dead end | Rule 9; redirects created on rename |
| Wrong version or platform | Follows iPhone steps on Android | Wasted time, wrong settings changed | Rule 6; "applies to" at the top |
| Warning after the step | Data already deleted when the warning appears | Lost data; possibly harm with a device | Rule 5 |
| Error message paraphrased | Searches the exact error, finds nothing | Goes to support or leaves | Rule 16; mandatory fact 10 |
| No way to contact support | Reaches the end of a page with the problem unsolved and no next step | Angry review, cancelled subscription | Rule 13 on every page |
| Copy button copies extra characters | Pastes "$ npm install" and gets an error | Developer blames the product | Rule 11. Reference 2's extracted text shows each command duplicated, which is how a copy that includes hidden text would look; not confirmed in a browser |
| Translation out of date | Translated page describes the previous version | Wrong instructions in the visitor's own language | Rule 17; flag on source change |
| Automated answer invents something | A confident answer that is not in the docs | Visitor acts on a wrong answer | Rule 20; off by default; must cite a page |
| Docs behind a login without warning | Clicks a search result and lands on a sign-in form | Visitor without an account cannot even learn what the product does | Rule 18; mandatory fact 9 |
| Deprecated page deleted too early | Users still on the old version find nothing | Support load | Rule 14 |
| Wall of text | One very long page mixing five tasks | Visitor cannot find their step | One task per page; on-page contents list for long pages |
| Images with no alt text | Screen-reader user hears "image" | Excludes people; may break accessibility law | Rule 19 |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with a working technical writer in either language. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Documentation, docs | all the written help for a product | תיעוד | توثيق |
| Help centre, help center | the public home of user help | מרכז עזרה | مركز المساعدة |
| Knowledge base | a searchable set of help articles | מאגר ידע | قاعدة المعرفة |
| User guide, user manual | the full instructions for users | מדריך למשתמש | دليل المستخدم |
| Getting started, quick start | the first steps for a new user | תחילת עבודה (not verified as standard) | البدء (not verified as standard) |
| Tutorial | a guided lesson that builds something end to end | מדריך / הדרכה | برنامج تعليمي (not verified) |
| How-to guide | steps for one task | מדריך "איך ל..." (not verified) | not verified |
| Concept, explanation | a page that explains how something works, without steps | הסבר (not verified as a page type) | not verified |
| Reference | exact lists of settings, fields, commands | תיעוד עזר / רפרנס (not verified) | مرجع |
| API reference | the reference for programmers | תיעוד API | مرجع واجهة برمجة التطبيقات (not verified) |
| Troubleshooting | finding and fixing a problem | פתרון תקלות | استكشاف الأخطاء وإصلاحها |
| FAQ | frequently asked questions | שאלות נפוצות | الأسئلة الشائعة |
| Release notes, changelog | what changed in each version | הערות גרסה / הערות שחרור (not verified which is more common) | ملاحظات الإصدار |
| Known issue | a problem the maker knows about | בעיה ידועה | مشكلة معروفة (not verified) |
| Workaround | a way around a problem until it is fixed | פתרון עוקף | حل بديل (not verified) |
| Deprecated | still exists, will be removed | מיושן / יוצא משימוש (not verified) | مهمل (not verified) |
| Prerequisite | what you need before you start | דרישות מקדימות | المتطلبات المسبقة |
| Step | one action in a procedure | שלב | خطوة |
| Screenshot | a picture of the screen | צילום מסך | لقطة شاشة |
| Callout, admonition | a boxed note, tip or warning | תיבת הערה (not verified) | not verified |
| Warning | caution before a risky action | אזהרה | تحذير |
| Breadcrumb | the trail showing where a page sits | פירורי לחם | مسار التنقل (not verified) |
| Sidebar, navigation | the list of sections and pages | תפריט צד / ניווט | الشريط الجانبي |
| Search | finding a page by words | חיפוש | بحث |
| Version | a release of the product | גרסה | إصدار |
| Code sample, snippet | a short piece of code to copy | דוגמת קוד | مقتطف برمجي (not verified) |
| Localisation, translation | adapting docs to another language | לוקליזציה / תרגום | توطين / ترجمة |
| Technical writer | the person who writes docs | כותב/ת טכני/ת | كاتب تقني (not verified) |

Notes on language:

- The trade often splits pages into four kinds: tutorials, how-to guides, reference and explanation. This split is known as the Diátaxis framework. The product uses the plain names in section 1, not the framework's name.
- Visitors do not say "documentation". They say "help", "instructions", "manual" or the error they got. Titles use their words.
- Words to avoid unless the customer said them and can back them: "simply", "just", "easy", "obviously" (they blame the reader when it is not easy), "seamless", "instant", "secure", "military-grade", "always", "never fails".
- Write button and menu names exactly as the product shows them, in bold, in the product's language.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file. Every item needs checking by someone qualified in the customer's country before it is relied on.

### Applies almost everywhere

- **Privacy notice.** Needed when the docs collect anything about a visitor: search terms tied to an account, feedback with an email, analytics cookies, a contact form. Plain public pages with no tracking collect little, but the hosting still logs addresses.
- **Instructions and product safety.** For a physical product, the instructions are often part of the product's legal safety duty, not just a courtesy. A missing warning can make the maker liable for harm. Which warnings are legally required: not verified, and differs by product category.
- **Copyright.** The customer must own or have permission for every screenshot, photo and diagram. Screenshots of third-party software or websites may need permission. Not verified.
- **Trademarks.** Naming other companies' products ("works with ...") is generally allowed to describe compatibility, but logos usually need permission. Not verified.
- **Open documentation.** If the docs are published as open source for contributions (references 5 and 8 say theirs are), a licence and contribution terms are needed. Which licence fits: a question for the customer.
- **Accuracy of claims.** Documentation that states a capability, a security property or a compliance status is a claim the company can be held to. Rule 8 applies with legal weight.

### Israel

- Accessibility: businesses serving the public must make websites accessible and publish an accessibility statement, under the Equal Rights for Persons with Disabilities Law and its service-accessibility regulations, with Israeli Standard 5568 (based on WCAG) as the technical reference. Whether a product's help centre counts as a "service to the public" in itself: believed yes when it is public; not verified.
- Instructions in Hebrew: consumer-protection rules are believed to require Hebrew instructions and warnings for many consumer goods sold in Israel. Which goods and what exactly: not verified.
- Privacy: the Protection of Privacy Law applies to any stored personal data (feedback with email, support tickets). Amendment 13 came into force in August 2025. What it requires of a small docs site: not verified.

### European Union and United Kingdom

- GDPR (EU) and UK GDPR apply to feedback, support forms and account-linked search. Non-essential cookies need consent (ePrivacy rules in the EU, PECR in the UK).
- Product safety: the EU General Product Safety Regulation (applies from December 2024) and sector rules (for example machinery, toys, electrical equipment) require instructions and safety information in a language easily understood by consumers in the member state where the product is sold. Exact duties per category: not verified.
- Accessibility: the European Accessibility Act (applies from June 2025) covers certain products and services and is believed to include the information and instructions supplied with in-scope products. Whether a given product is in scope, and the microenterprise exemption: not verified.
- Digital products: the EU Digital Content Directive is believed to require that a digital product matches its description, which includes documentation the trader supplies. Not verified.

### United States

- No general federal law requires product documentation. Sector rules do (for example medical devices, where "instructions for use" are regulated by the FDA). Not verified per sector.
- Accessibility: the Americans with Disabilities Act is applied by courts to business websites in many cases; Section 508 applies when selling to federal agencies. Not verified for a given company.
- Product liability: failure to warn is a recognised basis for liability in many states. Not verified per state.
- Privacy law is by state (for example California). Not verified.

### What the product does with this

- The product may generate the **structure** of a privacy page and an accessibility statement. It marks each as a draft that needs review.
- The product never writes a safety warning itself. It asks for warnings (mandatory fact 7) and places them before the step (rule 5).
- The product never states that the docs or the product "comply with" a named law or standard.
- The product asks which countries the product is sold in before generating any legal page.

## 8. Site vs app

### Content pages (no data, no accounts)

Docs home, section pages, every article, release notes, glossary, FAQ, support page, legal pages. A small product's complete documentation can be a static site with a phone or email link as the only action. This is a complete and honest product.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Docs home | cannot be empty: at least the getting-started path | n/a | Lists sections with one line each |
| Section page | section hidden until it has a page | | Never a section with "coming soon" |
| Article | cannot be published without title, summary, body | a missing image is hidden, its alt text shown | "Last updated" always shown |
| Release notes | hidden until the first note | | Newest first |
| On-page contents list | hidden on short pages | | Built from the page's headings |
| Language switcher | hidden with one language | if a page has no translation, say so and offer the source language | |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Search | an index of all published pages, rebuilt on publish | no results: "Nothing found for '...' - contact support" with the route | results area shows a placeholder, never "no results" while still searching | "Search is not working right now" plus the section list | n/a | anyone who can read the docs |
| Feedback on a page | stores page, yes or no, optional comment; alerts the owner | n/a | button disabled while sending | "Not sent" and the support route | visitor sees "Thanks - sent to the team" | visitor writes; only the owner reads |
| Support or contact form | stores the message; alerts the support address | n/a | "sending", cannot be pressed twice | "Not sent - email us at ..." | visitor sees what happens next and when | visitor writes; only support reads |
| Version switcher | each page tagged with versions | a page missing for a version says so and links to the nearest version | | | visitor's choice remembered on the device | anyone |
| Customer-only docs | accounts for readers | | | session expired: sign in again and return to the same page | | signed-in customers only; public pages say what is behind the login (rule 18) |
| Owner edits pages | an editor with draft and publish | "No pages yet - start with getting started" | | a failed save says so and keeps what was typed | published version visible at once; previous version kept | owner and named editors only |
| Link and redirect check | list of all internal links and old addresses | | | broken links listed to the owner before publish | | owner |
| Search-terms report | stored search terms, no personal data | "No searches yet" | | | | owner only |
| Automated answers | an answering service limited to the published pages | | "looking in the docs" | "No answer found in the docs" and the support route; never an answer without a source link | | off by default (section 4) |

### Needs accounts

- The owner always needs one as soon as pages are edited in the product.
- Editors need them only if more than one person writes.
- Readers need them only for customer-only docs (mandatory fact 9). Public help should not need an account.

### Needs payments

- Nothing for this domain. Documentation is not sold here. A paid manual or course belongs to another domain.

### Using an existing docs tool

Many products already publish docs through a hosted docs or help-desk tool. Reference 5 is built with the maker's own publishing service (its footer says "Powered by Obsidian Publish"); reference 1's article footer says "Powered by Markdoc". If the customer has one, ask before building a second copy. The failure mode is two sets of help that disagree.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. So: section order and wording are observed; visual quality, layout and the image-to-text ratio are **not** observed, and any ratio below is an estimate from the extracted text. Image counts include logos and icons; the extraction misses images loaded late by scripts.

**Curation.** Chosen by the author from the documentation of well-known software products, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner. All eight are in English, in Latin script. Reference 5 also offers other languages.

**Limit.** All eight document software. No documentation for a physical product (a manual for a device or an appliance) was verified. The skeletons below are therefore taken from software help; a device manual will add safety pages and model numbers.

Verified: 8.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://docs.stripe.com | 2026-11-22 | Developer and business docs for a payments company. Header: search with "Ask AI", create account, sign in, "APIs & SDKs", "Help". Home order: heading and one line - two actions (get started, explore all products) - a test card number to copy - three task groups (Payments, Revenue, Developers), three links each - a live "try it out" command with its full response - "browse by product" grid, each product with a one-line description. An article page (/payments/payment-links) was also fetched: breadcrumb - title - one-line summary - "Ask about this page", "Copy for LLM", "View as Markdown" - features table - "Get started" links - comparison table - "Was this page helpful? Yes / No" - support, community and changelog links. |
| 2 | https://tailwindcss.com/docs/installation | 2026-11-22 | Developer docs for a styling framework; an article page. Top links: Docs, Play, Blog, Showcase. Order: breadcrumb (Getting Started > Using Vite) - title and two sentences - list of installation methods - numbered steps 01 to 06, each with a heading, one sentence and a code block - an "Are you stuck?" box linking to framework guides - copyright line. The extracted text shows each code block twice, likely visible text plus a hidden copy for highlighting. About 3,000 characters, 1 image. |
| 3 | https://linear.app/docs | 2026-11-22 | Help for a project-planning app (users and developers). Order: breadcrumb - sign up and open-app actions - title and one line - "Popular" (four cards: start guide, import, agent, MCP) - "Explore" (eight feature cards, each a name and one line). The start-guide page was also fetched: breadcrumb - title - one paragraph - short sections (demo, create a workspace, getting the most out of it split by admins and team members, videos, customer stories) - "Next: Concepts". About 1,100 characters on the home page, no images in the extraction. |
| 4 | https://docs.astro.build/en/getting-started/ | 2026-11-22 | Developer docs for an open-source web framework. Order: links to code host and chat - banner announcing a new major version with an upgrade link - title and one line - two actions (install, learn the features) - contributor credit with a wall of avatar images - starter themes - guided tutorial - "start a new project" with one command - two columns of "Learn" links - community and contribute links. About 41 images, almost all contributor avatars. |
| 5 | https://help.obsidian.md | 2026-11-22 | User help for a note-taking app (redirects to obsidian.md/help). Language picker with more than thirty languages, including Hebrew and Arabic. Side list of sections (getting started, import notes, interface, editing, linking, files, plugins, sync, publish, licences and payment, teams). Home order: title and one paragraph with a link to separate developer docs - "Get started" as six numbered links (install, create a vault, first note, link notes, import, sync) - "Extend" as a list with one line each - add-on services - "Contribute" with a link to the docs' public repository - credits - "Powered by Obsidian Publish". No images in the extraction except the logo. |
| 6 | https://docs.github.com/en | 2026-11-22 | User and developer docs for a code-hosting platform. Header: "Search or ask Copilot". Home order: title and one line - search box - a long list of all docs grouped by area (get started, account, collaborative coding, Copilot, CI/CD, security, client apps, project management, enterprise, developers, community, more docs). Text-only list; 1 image (the social card). |
| 7 | https://support.1password.com | 2026-11-22 | User help for a password manager. Order: welcome line - two "get started" paths split by audience (for yourself or family; as a team member) - topic cards (using the app, families, billing, businesses, service providers, developers, agents, other products) - troubleshooting and security cards - one card per app platform (Mac, iOS, Windows, Android, Linux, ChromeOS, command line) - featured articles - link to the support community. About 2,000 characters, 23 images (icons). |
| 8 | https://help.kagi.com/kagi/ | 2026-11-22 | User help for a paid search engine. Order: welcome paragraph pointing to quick start and FAQ, with a support email and a feedback site - three ways to use the docs (click, search, a search shortcut) - where to send feedback about the docs - short "about" paragraphs for the two products - "Contributing": the docs are open source with a contribution guide. About 1,500 characters, 1 image. |

Loaded and not used:

| Site | Checked | Why not |
|---|---|---|
| https://obsidian.md/help/vault | 2026-11-22 | The fetch failed. Only the help home (reference 5) is used. |
| https://support.1password.com/getting-started-1password/ | 2026-11-22 | Returned "404 page not found" (a guessed address). Only the support home (reference 7) is used. |

## 10. Skeletons

Structure only. No colours, logos, illustrations or wording were taken from any reference.

### Skeleton A: the docs home (help centre)

The first page of the documentation. Its job: get the visitor to the right page in one or two clicks. Default for this domain.
From references 1, 5, 7 and 8, with the numbered getting-started path of 5, the audience split of 7 and the support line of 8.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | product name; search box; link back to the product's main site; sign-in only if docs are private | search is the most prominent element after the name | yes |
| 1 | Opening | one line: "Help for [product]: how to set it up, use it and fix problems"; the support route as a quiet link | one heading, one line | yes |
| 2 | Get started | 3 to 6 numbered links to the first tasks, in order | numbered list | yes |
| 3 | Choose your path | when audiences differ (owner vs staff, user vs developer, platform): one card each | cards with a name and one line | optional |
| 4 | Sections | every section with a one-line description | cards or a list | yes |
| 5 | Popular or featured | the most-needed pages (from mandatory fact 4) | short list | optional |
| 6 | What's new | latest release note with date, link to all | one line | optional, hidden when empty |
| 7 | Still need help | support route, hours, response time; community link if any | one short block | yes |
| 8 | Footer | company name; privacy, terms, accessibility statement; language switcher if more than one language | small | yes |

Image-to-text ratio: **estimate**, from extraction counts only. Text-led: references 3, 5, 6 and 8 returned 0 to 1 content images; reference 7's 23 images are icons on cards. Roughly no photographs; at most one small icon per card. The first screen is text and a search box. Not confirmed in a rendered view.

### Skeleton B: the article page

One task or one topic. Used for every page under Skeleton A.
From references 1, 2 and 3: breadcrumb and summary from 1 and 3, numbered steps from 2, the "was this helpful" ending from 1, the "next" link from 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header and side list | as Skeleton A; on wide screens the section list on one side and "on this page" on the other; on phones both in menus | the article is the widest column | yes |
| 1 | Breadcrumb | Docs > Section > Page | small | yes |
| 2 | Title and summary | the task as the title; one sentence saying what the page achieves | one heading, one line | yes |
| 3 | Applies to and prerequisites | versions, platforms, what you need first | short note | required when it applies (rule 6) |
| 4 | Warning | anything risky in the steps below (rule 5) | callout, before the steps | required when it applies |
| 5 | Steps | numbered; one action each; expected result; screenshot or code where it helps | step number and heading, then a sentence, then the image or code | yes for how-to pages |
| 6 | Result | what the visitor should see when done | one line | optional |
| 7 | If it did not work | common problems with the exact error text and the fix | short list | optional |
| 8 | Related and next | links to the next task and related pages | list | optional |
| 9 | Feedback and support | "Did this help? Yes / No" (only when fact 15 is answered); support route | one line | support route required |
| 10 | Last updated | the date | small | yes |

Image-to-text ratio: **estimate**. Reference 2 has one code block per step and no images in its steps; reference 1's article has one image and two tables. Roughly one screenshot or code block per step for how-to pages, none for concept pages. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6: author's knowledge, not checked with a technical writer in either language. Cells marked "not verified" must not be filled by guessing.
2. Every legal statement in section 7. None was checked against a statute or an official source for this file. Items marked "not verified" are the least certain; the rest are also unconfirmed.
3. Image-to-text ratios, layout and visual quality of all references: text extraction only, no rendered view.
4. No awwwards.com category was consulted; design quality of the references is the author's prior judgement.
5. No documentation for a physical product was verified. Safety-warning placement and model-number structure are from general knowledge, not from a reference.
6. The observation that reference 2's code appears twice in the extraction is about the extracted text; whether the copy button copies extra characters was not tested.
7. Only the home pages of references 4 to 8 were fetched; reference 1 and 3 each had one article page fetched as well. Two other article fetches failed (section 9).
8. The brief asked for references dated 2026-11-21. The fetches ran on 2026-11-22, and that is the date recorded.
9. No references in Hebrew, Arabic or any non-Latin script. These come in a later phase.
