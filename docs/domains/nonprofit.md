# Nonprofit

Covers: an organisation that exists for a cause rather than for profit and asks the public for support: a registered charity, a nonprofit association, a foundation, a campaign group. Its site asks for money, time or a voice, and proves what it does with them.
Does not cover: a club or group whose site is mainly about meeting (use `community.md`); a single fundraising gala (use `event.md` for the event page); a social business that sells products (use the domain of what it sells).
Written 2026-11-22. References checked 2026-11-22 (the brief named 2026-11-21; the fetches ran on 2026-11-22). Template: [README.md](README.md).

## 1. Objects

A nonprofit sells **trust**. A donor gives money to people they will never meet, for results they will never see directly. Everything on the site either earns that trust (who you are, registration, where the money goes, proof of results) or spends it (a vague claim, a wrong tax promise, a story told without the person's consent). The donation is the main action, but proof is the main content.

### Organisation

| Field | Required | Example (illustrative) |
|---|---|---|
| Name | required | "Clean Rivers Fund" |
| Mission in one sentence | required | "We remove plastic from rivers before it reaches the sea" |
| Where it works | required | countries, regions or "online" |
| Legal form | required | registered charity, nonprofit association, foundation, unregistered group |
| Registration number(s) | required when registered | charity number, association number, tax ID; one per country where registered |
| Registered address | required | |
| Contact email | required | |
| Phone | optional | |
| Tax status of gifts | required | which donors, in which countries, can claim tax relief; "not tax-deductible" is a valid answer |
| Year founded | optional | |
| Leadership and board | optional, often expected | roles; names only with consent |
| Annual reports and accounts | optional, strongly advised | documents with year |

### Programme (what the money does)

| Field | Required | Example |
|---|---|---|
| Name | required | "River barriers" |
| What it does | required | plain words |
| Where | required | |
| Results | optional | linked impact figures |
| Accepts restricted gifts | optional | a donor can choose this programme |
| Status | required | active, completed, planned |

### Donation

| Field | Required | Example |
|---|---|---|
| Amount and currency | required | 25 EUR |
| Frequency | required | one-off, monthly, yearly |
| Designation | optional | general fund, a programme, an appeal |
| Donor name, email | required | for receipt |
| Donor address | optional, required for some tax schemes | |
| Tax relief declaration | optional | country-specific (for example a UK Gift Aid declaration) |
| In honour or memory of | optional | name of the honoured person, a message, notify someone |
| Public recognition | required choice | show my name, show "anonymous", do not list |
| Payment status | required | pending, paid, failed, refunded |
| Receipt sent | required | |

### Other objects

| Object | Fields | Notes |
|---|---|---|
| Appeal or campaign | title, goal amount (optional), deadline (optional), raised so far, story | "Raised so far" is computed, never typed |
| Peer fundraiser | owner, title, goal, page, donations | A supporter raises money on the organisation's behalf; one reference offers this |
| Impact figure | number, what it counts, period, source, date | Facts, never defaults |
| Story | person or place, text, photos, consent record | About beneficiaries; dignity and consent (see rules) |
| Volunteer opportunity | role, where, time, requirements, how to apply | |
| Partner or funder | name, logo, kind (corporate, foundation, government) | Shown with agreement |
| Report | title, year, file | Accounts, impact reports, audits |
| Legacy gift information | how to leave a gift in a will | Optional |
| Other ways to give | cheque, bank transfer, stock, payroll giving, company matching | Country-specific; seen in three references |
| Newsletter | email, consent | |

## 2. Rules

1. The legal name and, where registered, the registration number are shown on every page (usually in the footer). A group that is not registered says so plainly.
2. A tax-relief statement says which donors, in which country, may claim it. "Tax-deductible" without a country is never shown. (One reference states that only eligible US taxpayers may deduct, and sends UK donors to a separate UK entity.)
3. A claim about where money goes ("100% of your donation funds projects") is shown only if true and explained: who pays for operations, and how. Two references make such a claim and each explains it next to the claim.
4. A gift designated to a programme or appeal is used for that purpose, or the donation page says before payment how designated gifts are handled if the programme is fully funded.
5. Impact numbers carry what they count, the period and a source or method. A live counter is computed from real data, never animated from an invented starting point.
6. "Raised so far" and goal bars are computed from paid donations, not typed by hand, and show the date of the last update.
7. A monthly donation can be cancelled by the donor without calling anyone, and the way to cancel is in every receipt.
8. A receipt is sent for every paid donation, with the organisation's legal name, registration number, amount, date, and the tax wording that applies to that donor's country.
9. Suggested amounts are allowed. Each suggested amount that claims a result ("25 buys two nets") must be true at the stated cost; the source of the cost is the customer's.
10. A donor's name is public only if the donor chose it. "Anonymous" is always offered. (One reference publishes a list of recent donors with amounts, where some appear as "Anonymous".)
11. A beneficiary's story, name, photo or location is published only with recorded consent, and with care for the person's dignity and safety. Children's faces and full names are not published without a guardian's consent; in some contexts not at all. (One reference publishes an article on telling stories of poverty without exploitation.)
12. A third-party quote (press, evaluator) names its source.
13. Card details are handled only by a payment provider, never stored by the product.
14. The donate action is reachable from every page on a phone, and the donation page states what happens next (receipt, how the gift is used).
15. Marketing messages to donors need consent; receipts and legally required notices are separate from marketing.
16. A peer fundraiser's page states clearly that the money goes to the organisation, not to the person running the page.

## 3. Mandatory facts

The product is not built until each of these has an answer from the customer. None may be guessed.

| # | Fact | The one question to ask | Why (the human reason) |
|---|---|---|---|
| 1 | Name | "What is the organisation's name, exactly as registered?" | Donors check the name against registers before they give. |
| 2 | Mission | "In one sentence, what do you do and for whom?" | A visitor decides in seconds whether it is a cause they care about. |
| 3 | Where you work | "Where does your work happen?" | Donors give to places they feel connected to. |
| 4 | Legal form and number | "Are you registered? Under what number, in which country?" | Without it many donors will not give, and some payment providers will not pay out. |
| 5 | Tax status | "Can donors get tax relief? Which donors, in which countries?" | A wrong tax promise costs the donor money and the organisation trust. |
| 6 | How people can help | "What do you want visitors to do: give once, give monthly, volunteer, sign a petition?" | The site leads to these actions in order. |
| 7 | Where money goes | "What does a gift pay for? Do you want to say anything about costs and overheads?" | The second question every donor asks. |
| 8 | Contact | "Which email answers donors and volunteers?" | A donor with a question who gets no answer cancels. |
| 9 | Proof | "What results can you show, and where do the numbers come from?" | Proof is what earns the next gift. If there are none yet, the site says what you are starting. |

Needed only when the product takes donations:

| # | Fact | The one question to ask | Why |
|---|---|---|---|
| 10 | Payment account | "Which payment provider or bank account receives donations, in whose name?" | Money must reach the organisation, in its own name. |
| 11 | Receipts | "What must a receipt say for your donors' tax purposes?" | A receipt without the right wording is useless to the donor. |
| 12 | Suggested amounts and what they buy | "Which amounts should we suggest, and is there a true example of what each buys?" | Specific amounts raise more, but only true examples may be used. |
| 13 | Designated gifts | "Can donors choose a programme? What happens if it is fully funded?" | Donor intent must be honoured. |
| 14 | Recognition | "Do you want to thank donors publicly? Only with their choice?" | Publishing names without consent is a privacy breach. |

## 4. Declared defaults

Each default is shown to the customer as "we filled this in - change it if it is wrong". None of them is a fact about the organisation.

| Default | Value | Why it is safe | How it is marked |
|---|---|---|---|
| Page order | Skeleton A below | Extracted from the references | Named as the default skeleton |
| Main action label | "Donate" | Standard across all references | Labelled "default" |
| Frequency on the donation form | one-off and monthly offered, one-off selected | Monthly pre-selection can be seen as pressure; estimate of good practice, not verified | Setting, labelled "default" |
| Suggested amounts | none until the customer gives them | An amount implies a result; facts only | Asked (fact 12) |
| Donor recognition | "do not list" pre-selected | Privacy first | Setting |
| Story consent field | required for every story | Rule 11 | Cannot be switched off |
| Impact section when no numbers | "What we are working on" instead of numbers | Honest for a new organisation | Shown to the customer as "no numbers given" |
| Footer contents | legal name, registration number, address, privacy, terms, accessibility statement | Rule 1 | Fields required |
| Receipt structure | legal name, number, amount, date, tax wording field (empty until given) | Rule 8 | "Draft - tax wording needed" |
| Language | the language of the conversation | The customer chose it | Shown, changeable |
| Empty optional sections | hidden | Empty "news" looks abandoned | Listed as "not shown yet" |
| Legal page structure | headings only | Structure is general | "Draft - not legal advice" |

Never a default, whatever the customer left out: registration numbers, tax status, "100%" claims, overhead percentages, impact numbers, what an amount buys, beneficiary stories, partners, evaluator ratings, press quotes, goals and "raised so far", board members, "transparent", "effective", "trusted".

## 5. Failure modes

| What went wrong | What the visitor sees | What it costs | Prevention |
|---|---|---|---|
| Registration number missing or wrong | Donor checks the register and finds nothing | Lost gift; suspicion of fraud | Facts 1 and 4; read back the number |
| Wrong tax promise | Donor claims relief and is refused | Donor's money, the organisation's name | Rule 2 |
| "100%" claim without explanation | Journalist or donor asks who pays rent | Reputation | Rule 3 |
| Goal bar typed by hand, out of date | Bar says "almost there" for months | Distrust | Rule 6 |
| Payment fails silently | Donor thinks they gave; organisation has nothing | Lost gift, confused donor | Donation saved only after the provider confirms; clear failure message |
| No receipt | Donor cannot claim relief | Complaint | Rule 8 |
| Monthly gift hard to cancel | Donor calls the bank, files a chargeback | Fees, angry donor, possible regulator complaint | Rule 7 |
| Donor named publicly without asking | Sees their name and amount online | Privacy breach | Rule 10 |
| Beneficiary shown without consent | A person sees their hardship used in an advert | Harm to the person; reputation | Rule 11 |
| Designated gift used elsewhere | Donor learns their gift went to something else | Trust, possibly legal | Rule 4 |
| Counters read 0 without scripts | "0 people helped" | Looks dead | Rule 5; render real numbers |
| Peer fundraiser looks like a personal collection | Donors unsure who receives the money | Distrust, possible misuse | Rule 16 |
| Donate page only, no proof | Visitor leaves to "think about it" | Silent loss | Proof sections in the skeleton |
| Near-empty home page | Visitor sees one line and a button | Weak trust | One reference returned under 1,000 characters on its home page; keep mission, proof and registration on the home page |

## 6. Professional language

Hebrew and Arabic terms are the author's knowledge and were not checked with fundraising professionals in either language. Where the cell says "not verified", do not use a guess.

| English | Meaning | Hebrew | Arabic |
|---|---|---|---|
| Nonprofit, charity | the organisation | עמותה / ארגון ללא כוונת רווח / ארגון צדקה | منظمة غير ربحية / جمعية خيرية |
| Registered charity | officially registered | עמותה רשומה | جمعية خيرية مسجلة |
| Donation | | תרומה | تبرع |
| Donor | | תורם | متبرع |
| Monthly donation, recurring gift | | הוראת קבע / תרומה חודשית | تبرع شهري |
| Fundraising | | גיוס כספים | جمع التبرعات |
| Appeal, campaign | a fundraising drive | קמפיין גיוס | حملة تبرعات |
| Beneficiary | person the work helps | מוטב / נתמך (not verified as preferred usage) | مستفيد |
| Volunteer | | מתנדב | متطوع |
| Impact | results of the work | השפעה / אימפקט | الأثر |
| Overheads, operating costs | | הוצאות הנהלה וכלליות / הוצאות תפעול | التكاليف التشغيلية |
| Tax receipt | | קבלה לצורכי מס (סעיף 46) | إيصال ضريبي (not verified) |
| Restricted gift | given for one purpose | תרומה מיועדת (not verified) | تبرع مخصص (not verified) |
| Legacy gift, bequest | gift in a will | צוואה לטובת עמותה / עיזבון | وصية خيرية (not verified) |
| In honour, in memory | | לכבוד / לזכר / לעילוי נשמת | تكريمًا لـ / إحياءً لذكرى (not verified) |
| Matching gift | an employer or funder doubles the gift | תרומה תואמת / מצ'ינג | تبرع مطابق (not verified) |
| Gift Aid (UK) | UK tax scheme adding to gifts | not verified | not verified |
| Zakat, sadaqah | Islamic obligatory and voluntary giving | not applicable | زكاة, صدقة |
| Tzedakah | Jewish charitable giving | צדקה | not applicable |

Notes on language:

- Religious giving terms (zakat, tzedakah, ma'aser) carry specific rules. Use them only if the customer does and can say the organisation's gifts qualify. Not verified.
- Words to avoid unless the customer can back them: "most effective", "100%", "zero overhead", "transparent" (show, do not claim), "every penny", "save a life" (unless the evidence exists), "the poor" as a label for people.

## 7. Legal

A checklist of questions, not legal advice. The author is not a lawyer and did not read the statutes for this file.

### Applies almost everywhere

- **Fundraising is regulated** in most countries: who may ask for money, what must be disclosed, and how donor data is used.
- **Donor data**: names, addresses, amounts, payment history are personal data; giving to some causes can reveal beliefs or health, which are sensitive data in many places.
- **Beneficiary data and images**: consent, dignity and safety; stricter for children and for people in danger.
- **Card payments**: handled by a payment provider so the product never touches card numbers.
- **Accessibility statement** where the law requires it.
- **Lotteries, raffles and prize draws** for fundraising are regulated separately in many countries. Not verified.

### Israel

- A nonprofit association (עמותה) is registered with the Registrar of Associations. A "proper management" certificate (אישור ניהול תקין) is commonly expected by donors and funders. What must appear on a website: not verified.
- Donors to institutions approved under section 46 of the Income Tax Ordinance can claim a tax credit. The receipt wording and approval number requirements: not verified.
- Website accessibility statement under the Equal Rights for Persons with Disabilities Law regulations; exemptions by size. Not verified for small associations.
- Privacy Protection Law, Amendment 13 (in force August 2025): duties for donor databases. Not verified.
- Fundraising messages by SMS or email need consent under Communications Law section 30A; whether nonprofits have an exemption: not verified.

### European Union and United Kingdom

- GDPR and UK GDPR for donor and volunteer data.
- England and Wales: registered charities above an income threshold are believed to be required to state that they are registered on their website and fundraising materials. Threshold and wording: not verified.
- UK: the Fundraising Regulator's Code of Fundraising Practice applies to fundraising in England, Wales and Northern Ireland; Scotland has its own regulator. Not verified in detail.
- UK Gift Aid requires a donor declaration with specific information. Exact wording: not verified.
- EU: tax relief for cross-border giving varies by country. Not verified.

### United States

- 501(c)(3) status allows deductible gifts for eligible US taxpayers. Donors are believed to need a written acknowledgement for single gifts of 250 US dollars or more. Not verified.
- Many states require registration before soliciting donations from their residents. Not verified per state.
- COPPA if the site collects data from children under 13.

### What the product does with this

- The product generates the **structure** of privacy, terms, donation terms and accessibility pages, marked as drafts.
- The product never writes a tax-relief statement, a registration number or a "100%" claim that the customer did not give.
- The product asks in which countries the organisation is registered and where donors live before generating any donation page.

## 8. Site vs app

### Content pages (no data, no accounts)

Home, about (mission, history, team), programmes, impact, stories, reports and accounts, volunteer, other ways to give, contact, legal pages. With a donation link to the organisation's existing provider, this is a complete product.

States still needed on content pages:

| Part | Empty | Error | Notes |
|---|---|---|---|
| Impact | "What we are working on" | | Never invented numbers |
| Stories | hidden | broken image hidden | Consent per story |
| Reports | hidden for a new organisation; "first report due [year]" if known | broken link check | |
| Partners | hidden | | |
| News | hidden | | Dated |
| Counters | hidden if no real data | real number rendered without scripts | Rule 5 |

### Needs data

| Part | What it needs | Empty state | Loading | Error | Save | Permissions |
|---|---|---|---|---|---|---|
| Donation form | payment provider, amounts, designations, tax declaration fields per country | n/a | "processing" and cannot be pressed twice | "Your donation did not go through - you have not been charged" (only if true) with what to try | recorded only after the provider confirms; thank-you page and receipt | donor: own receipts; staff: donations |
| Monthly donation management | donor link, provider subscription | "You have no active monthly gifts" | | "Could not update - email [address]" | change or cancel takes effect at once, with confirmation | donor through a personal link; staff |
| Appeal progress | paid donations for the appeal | "Be the first to give" | | hide the bar on failure, never show a wrong number | computed | public read |
| Peer fundraiser pages | owner account, goal, donations | "No donations yet" | | | page states the money goes to the organisation | owner edits own page; staff approve |
| Donor recognition list | donors who opted in | hidden | | | | public read of opted-in names only |
| Volunteer application | role, contact, availability | "No roles open right now - leave your email" | | "Not sent - email us" | "Received - we reply within [time]" | applicant writes; staff read |
| Newsletter sign-up | email, consent | | | | double opt-in if the law requires | staff |
| Staff donation view | all donations, export | "No donations yet" | | | | staff only, behind a login; access logged |

### Needs accounts

- Staff, as soon as anything is stored.
- Donors do not need an account to give. Monthly donors manage their gift through a personal link; an account is optional.
- Peer fundraisers need an account for their page.

### Needs payments

- One-off and monthly donations, event tickets, shop.
- Each brings receipts with country-specific tax wording, refunds, failed recurring payments, chargebacks.
- Default: the product links to the organisation's existing donation provider until facts 10 and 11 are answered.

### Using an existing donation platform

Many nonprofits use an external donation platform. The product is then a content site whose action is that link, and the platform issues receipts. The failure mode is a link to a closed campaign.

## 9. References

**How these were checked.** Each URL was fetched on 2026-11-22 with a page-extraction tool that returns the page's text and image references. No browser was used and no screenshot was taken. Section order and wording are observed; visual quality and the image-to-text ratio are **not** observed, and every ratio is an estimate from counts in the extracted text. Image counts include logos and icons.

**Curation.** Chosen by the author from known international nonprofits with strong public websites, not from a search-result list. No awwwards.com category was consulted; none is claimed as an award winner. All are in English, in Latin script.

**Limit.** All six are large, well-funded organisations. No small local association was verified. The skeletons are a ceiling for structure; a small organisation uses Skeleton A with fewer sections.

Verified: 6.

| # | Site | Checked | What was observed |
|---|---|---|---|
| 1 | https://www.charitywater.org | 2026-11-22 | Water charity. Order: mission headline with donation entry - other ways to give (cheque, international, stock) with practical rules (receipts mailed in four to six weeks; only eligible US taxpayers may deduct; a separate UK charity for UK donors) - impact figures (people served, projects funded, countries) - why water - "100% of your donation" claim explained next to it (private donors fund operations) and "proof" for each project - ready to take action: monthly giving, sponsor a project, start a fundraiser, give to a fundraiser, legacy giving, brand partner, honour someone, a children's programme, newsletter. Registration type and tax ID shown. Extraction: 5 images, about 7,500 characters. |
| 2 | https://www.givedirectly.org | 2026-11-22 | Cash-transfer nonprofit. Order: one-line mission - donation box with an amount field and a monthly suggestion - "giving cash is simple" - independent reviews and press quotes with sources - people reached, with a country selector - highlights from the field (studies, risk reporting, an article on telling poverty stories ethically) - recipients' quotes with amounts - closing donation call. Navigation includes major gifts, legacy gifts, donation methods. Extraction: 41 images, about 14,700 characters. |
| 3 | https://theoceancleanup.com | 2026-11-22 | Environmental nonprofit. Order: cookie preferences - newsletter prompt - headline and mission - the problem - the goal with a year - a cities programme - people affected, with named stories (not repeated here) - join: donate, work with us, stay informed - partners - a long list of dated news. Extraction: 100 images, about 51,800 characters, most of it news. |
| 4 | https://www.againstmalaria.com | 2026-11-22 | Malaria-net charity. Top: total funds raised as a number; menu with cost-effectiveness, allocating donations, donation statistics, recurring donations, monitoring costs, "donation to distribution", tax deductibility. Order: gifts - malaria - nets - follow-up - latest participants - latest sponsors and donors (a public list of names and amounts, some "Anonymous") - latest net distributions - photos and video - what we do (stating that 100% of public donations buys nets, with the unit cost) - how we do it - what people say - how you can help (fundraise, donate, volunteer). Transparency-led. Extraction: 30 images, about 23,600 characters. |
| 5 | https://www.roomtoread.org | 2026-11-22 | Education nonprofit. Order: mission headline - "we know how to solve" section - girls' stories - life skills programme - free digital library - one large reach figure - latest articles. Donate and give monthly in the navigation. Extraction: 20 images, about 12,300 characters. |
| 6 | https://www.crisis.org.uk | 2026-11-22 | UK homelessness charity. The extracted home page is short: a seasonal donation appeal - one paragraph of what the charity does and where - three figures, each with what it counts and the year (people supported, volunteers, campaign actions) - donate. Extraction: 10 images, about 1,000 characters; navigation and footer not returned, so the full structure was not observed. |

Loaded and not used: none. All six loaded. Reference 6 is kept with its limitation stated, because its three figures show rule 5 (what is counted, and when) in a compact form.

## 10. Skeletons

Structure only. No colours, logos, photographs or wording were taken from any reference.

### Skeleton A: the cause and the gift

For most nonprofits: one mission, a few programmes, donations as the main action. Default for this domain.
From references 1, 2, 5 and 6.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; "Donate" always reachable; secondary links (about, programmes, volunteer) | donate is the most prominent element after the name | yes |
| 1 | Opening | mission in one sentence; donate action; one image of the work | one heading, one line, one action | yes |
| 2 | The problem and what you do | two or three short paragraphs | | yes |
| 3 | Proof | impact figures with what they count and when; or "what we are working on" | figures large, labels plain | yes |
| 4 | Where the money goes | the customer's true statement about costs; designations | short, next to the donate action | yes |
| 5 | Stories | consented stories with dignity | image and short text | optional |
| 6 | Ways to help | give monthly, give once, fundraise, volunteer, legacy, other ways to give | list of entries | yes |
| 7 | Independent proof | press or evaluator quotes with source; reports and accounts | | optional |
| 8 | Newsletter | email with consent | | optional |
| 9 | Footer | legal name, registration number, address, tax status by country, privacy, terms, accessibility statement | small, complete | yes |

Image-to-text ratio: **estimate**, from extraction counts only (references 1, 5 and 6 returned 5 to 20 images against 1,000 to 12,300 characters). Roughly one image per two to three text blocks; figures and short statements carry the proof. Not confirmed in a rendered view.

### Skeleton B: the transparency-led nonprofit

For an organisation whose case rests on showing every number: where each gift went, costs, distributions.
From references 4 and 1 (the "proof for every project" approach), with the news archive pattern of 3.

| Order | Section | Content | Hierarchy | Required |
|---|---|---|---|---|
| 0 | Header | name; donate; a total raised figure if real and computed | | yes |
| 1 | Opening | mission and unit cost ("one X costs Y") if true | | yes |
| 2 | Live activity | latest donations (opt-in names or "anonymous"), latest distributions or projects | lists with dates | yes for this skeleton |
| 3 | How we work | allocation, monitoring, follow-up | short sections with links to detail | yes |
| 4 | Costs | what operations cost and who pays | table or short text | yes |
| 5 | Photos and video from the field | consented | | optional |
| 6 | What others say | sourced | | optional |
| 7 | How you can help | donate, fundraise, volunteer | | yes |
| 8 | News | dated | | optional |
| 9 | Footer | as Skeleton A | | yes |

Image-to-text ratio: **estimate**. Mixed: reference 4 returned 30 images against about 23,600 characters, mostly lists and tables. Text and numbers lead. Not confirmed in a rendered view.

## 11. Not verified

1. All Hebrew and Arabic terms in section 6, and whether religious giving terms apply to a given organisation.
2. Every legal statement in section 7, especially section 46 receipts in Israel, UK registration-statement thresholds, Gift Aid wording, US acknowledgement thresholds and state registration.
3. Image-to-text ratios and visual quality: text extraction only.
4. No awwwards.com category was consulted.
5. No small local association was verified.
6. Reference 6's extraction was short; its navigation and footer were not observed.
7. Donation flows, receipts and sub-pages of the references were not fetched; observations are of home pages only.
8. The donation-frequency default (one-off pre-selected) is the author's judgement, not from a source.
9. No references in Hebrew, Arabic or any non-Latin script.
