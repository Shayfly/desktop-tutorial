# 148AI: video, image and music providers: cost, quality and rights

Research by Claude Code, 2026-11-27. All pages were read on **2026-11-27** with a read-only page extractor. No account was opened and no paid service was called.
Labels used below: **[official]** means the figure was read on the provider's own page. **[estimate]** means it was derived or comes from a third party. **[not verified]** means no official page confirmed it.

---

## 1. Video cost by resolution (15 s and 30 s clips)

Target: a 15–30 s clip for under **$2 per build**.

| Provider / model | Native 480p? | $/s 480p | $/s 720p | $/s 1080p | 15 s clip | 30 s clip | Audio | Source |
|---|---|---|---|---|---|---|---|---|
| **Vertex AI Veo 3.1 Lite** | No (720p/1080p) | – | $0.03 silent / $0.05 audio | $0.05 / $0.08 | 720p+audio **$0.75** | 720p+audio **$1.50** | Yes | [official] cloud.google.com/vertex-ai/generative-ai/pricing |
| Vertex AI Veo 3.1 Fast | No | – | $0.08 / $0.10 | $0.10 / $0.12 | $1.50 (720p+audio) | $3.00 | Yes | [official] same page |
| Vertex AI Veo 3.1 (standard) | No | – | $0.20 / $0.40 | $0.20 / $0.40 | $6.00 (audio) | $12.00 | Yes | [official] same page |
| Gemini API: Gemini Omni 1.2 Flash (Google's video model, up to 15 s, native audio) | 360p ($0.023/s) | – | ~$0.07 | ~$0.104 (upsampled) | 720p **$1.04** | 2×15 s ≈ $2.08 | Yes | [official] ai.google.dev/gemini-api/docs/pricing (token-based; $/s is Google's own conversion) |
| **Runway API: Wan 3** | Yes | $0.05 | $0.10 | $0.20 | 480p $0.75 / 720p $1.50 | 480p **$1.50** / 720p $3.00 | not stated | [official] docs.dev.runwayml.com/guides/pricing/ ($0.01 per credit) |
| Runway API: Wan 3 Prime | Yes | $0.068 | $0.14 | $0.28 | $1.02 (480p) | $2.04 (480p) | not stated | [official] same |
| Runway API: Seedance 2.5 | Yes | $0.20 | $0.30 | $0.68 | $3.00 | $6.00 | ref. audio | [official] same |
| Runway API: Grok Imagine 1.5 Lite | Yes | $0.02 | $0.03 | $0.14 | $0.30 | $0.60 | not stated | [official] same |
| Runway API: Kling 3.0 Standard | No | – | $0.09 silent / $0.13 audio | – | $1.95 (audio) | $3.90 | Yes | [official] same |
| Runway API: Veo 3.1 Fast | No | – | $0.10 silent / $0.15 audio | – | $2.25 | $4.50 | Yes | [official] same |
| Runway API: Gen-4 Turbo / Gen-4.5 | n/a | – | $0.05 / $0.12 | – | $0.75 / $1.80 | $1.50 / $3.60 | No | [official] same |
| Replicate: Kling 4.0 (3–30 s) | No | – | $0.157 | $0.235 | $2.36 | $4.71 | not stated | [official] replicate.com/kwaivgi/kling-v4.0 |
| Replicate: Wan 2.1 i2v (WaveSpeed) | Yes | $0.09 | $0.25 | – | $1.35 | $2.70 | No | [official] replicate.com/pricing |
| Replicate: Wan 2.2 fast | Yes | $0.05 per 5 s video (~$0.01/s) | $0.10 per video | – | ~$0.15 (3 chained clips) | ~$0.30 | No | [official, older blog] replicate.com/blog/wan-22 |
| Replicate: Wan 3.0 | Yes (480/720/1080, 2–30 s) | not shown | not shown | ~$0.20 | – | ~$6.00 at 1080p | – | page shows no price; $12/min from Artificial Analysis **[estimate]** |
| Replicate: MiniMax H3 Lite | Yes (480P/768P, 4–15 s) | not shown | ~$0.08 (768p) | – | ~$1.20 | ~$2.40 | ref. audio | price not on page; $4.80/min (H3 768p) from Artificial Analysis **[estimate]**. Replicate banner says H3 Lite is 50% off until the end of the year |
| Replicate: Seedance 1 Lite / Pro Fast | Yes (480p/720p, 5 or 10 s) | not shown | not shown | – | – | – | No | price not extracted **[not verified]** |
| Replicate: LTX-2 Fast (6–10 s) | n/a | not shown | – | – | – | – | Yes | price not extracted **[not verified]** |
| **Luma API (Ray)** | 540p | 5 s $0.15 (≈$0.03/s); 10 s $0.45 | 5 s $0.30; 10 s $0.90 | 5 s $1.20; 10 s $3.60 | 540p ≈ $0.68 (10 s + 5 s) | 540p ≈ $1.35 | not stated | [official] lumalabs.ai/api/pricing |
| Pika API | aggregator | Seedance 2.0 480p ~$0.09/s | – | – | – | – | – | [official] pika.art/api ("prices recorded 10.24.26"). Pika's own Pika 2.5 price was not extracted **[not verified]** |

Notes:
- Clip-length limits matter more than price. Veo 3.x clips are a few seconds each (8 s per the docs as remembered; **not verified today**), Gemini Omni goes up to 15 s, Luma up to 10 s (V2V 20 s), and Kling 4.0 and Wan 3 up to 30 s. A 30 s clip on a short-clip model means chaining or extending, which adds cost and seams.
- **Under $2 for 30 s:** Veo 3.1 Lite 720p with audio ($1.50), Wan 3 480p on Runway ($1.50), Grok Lite ($0.60), Luma 540p (≈$1.35), Wan 2.2 fast. **Under $2 for 15 s:** in addition, Gemini Omni 720p ($1.04), Wan 3 720p ($1.50), Kling 3.0 Std with audio ($1.95).

## 2. Quality evidence and ranking

Artificial Analysis, AA-Video-T2V v2.1 (with audio), read 2026-11-27 at artificialanalysis.ai/video/leaderboard/text-to-video:
1. Wan 3.0, Elo 1175; 2. Utopai X, 1173 (no API); 3. MiniMax H3 (768p), 1164; 4. Hyperflow H3, 1156; 5. Dreamina Seedance 2.5, 1154; 6. Gemini Omni Flash 1.2, 1152; 7. MAGI-2, 1150.
On the silent board (T2V-Silent): HeyGen Video 1, 1147; MAGI-2, 1144; Wan 3.0, 1138.
Veo 3.1 Lite, Luma Ray and Kling 4.0 did not appear in the extracted top 7. Their ranks are **not verified**.

**Hebrew / RTL text:** no provider documents Hebrew text rendering. Wan 2.1 documents Chinese and English text (replicate.com/wavespeedai/wan-2.1-i2v-720p). **Not tested.** Recommendation: overlay Hebrew text in post-processing (ffmpeg/HTML), never inside the model.

| Rank | Model (route) | 30 s cost | Quality (AA Elo) | Audio | Commercial rights / indemnity |
|---|---|---|---|---|---|
| 1 | **Veo 3.1 Lite (Vertex)** | $1.50 at 720p with audio | not in the top 7 (lower than Veo 3.1) | Yes | Google claims no ownership; **Google indemnifies generated output on Vertex** (GA Veo) |
| 2 | **Wan 3.0 (Runway API / Replicate)** | $1.50 at 480p (Runway) | **1175, first place** | yes on the audio board | Runway: no ownership claimed, commercial use allowed, **but a perpetual licence for Runway to train on outputs**; no indemnity |
| 3 | Gemini Omni Flash 1.2 (Gemini API) | ≈$2.08 at 720p (2×15 s) | 1152 | Yes | No ownership claimed; Gemini API (not Vertex) is **not** on the indemnity list |
| 4 | MiniMax H3 Lite (Replicate) | ≈$2.40 **[estimate]** | 1164 (H3 768p) | ref. audio | Replicate grants rights in the output subject to the model's own terms; customer indemnifies Replicate |
| 5 | Luma Ray (540p) | ≈$1.35 | not verified | not stated | Luma assigns the output to the customer, **only during a paid subscription** |
| 6 | Kling 4.0 (Replicate) | $4.71 at 720p | not verified | – | Replicate + Kling terms |

**Recommendation:**
- **Primary: Veo 3.1 Lite on Vertex AI.** It costs $0.75 for 15 s and $1.50 for 30 s at 720p with audio, and it is the only one whose provider indemnifies the output. That matters given the owner's concern about liability.
- **Fallback: Wan 3.0.** It has the highest quality on the leaderboard, native 480p, and up to 30 s in a single generation. It costs $1.50 for 30 s at 480p, or $1.50 for 15 s at 720p, via the Runway API. Before production: confirm the price on Replicate (it is not shown on the model page), and decide whether Runway's licence to train on outputs is acceptable.

## 3. Rights and liability by provider

| Provider | Who owns the output | Commercial use / resale | Passing rights to an end customer | Indemnity | Main prohibited uses | Source |
|---|---|---|---|---|---|---|
| Google, Gemini API (Veo / Omni / Imagen / Lyria via API) | "Google won't claim ownership"; Google may generate similar content for others | Allowed | Implied (148AI holds the output and can pass it on); 148AI is "responsible for … use of that content by anyone you share it with" | **None** in the Gemini API terms | Generative AI Prohibited Use Policy: CSAM, NCII, extremism, rights infringement, deception about human authorship, etc. | ai.google.dev/gemini-api/terms; policies.google.com/terms/generative-ai/use-policy |
| Google, Vertex AI (Veo, Imagen, Gemini) | Same (customer data/output) | Allowed | Yes | **Yes**: "Additional Google Indemnification Obligations" for GA Veo, Imagen and Gemini models. **Lyria does not appear in the list.** | Same policy | cloud.google.com/terms/generative-ai-indemnified-services |
| Replicate (Kling, Wan, Seedance, MiniMax, LTX, FLUX) | Replicate "grants to you all right, title and interest, if any, in and to Output, including … sale or publication", **subject to the model's Third Party Terms** | Allowed, subject to the model's terms | Yes, subject to the model's terms (e.g. the LTX licence, the BFL terms) | **The reverse:** the customer indemnifies Replicate for inputs and outputs. Replicate advises human review for copyright | Replicate AUP + per-model terms | replicate.com/terms |
| Runway | Claims no ownership; "does not restrict your commercial use" | Allowed | Yes | None found | Its own AUP. **Licence: Runway may use inputs and outputs to train its models (perpetual, transferable, sublicensable)** | runwayml.com/terms-of-use |
| Luma | **Assigns** all of its rights in the output to the customer | Only for output made during an active paid subscription; no sale through an external marketplace without a commercial subscription | Yes, with a commercial plan | None for Trials; for paid plans not found | Impersonation, political misinformation, sexualising minors, misrepresenting AI output as human-made, **giving a third party access to the model** | lumalabs.ai/legal/tos |
| Pika | Retains no rights and assigns any interest to the user; warns that output may not be copyrightable | Under the subscription plan | Yes | **No**: "use Outputs entirely at your own risk" | Per its ToS | pika.art/terms-of-service |
| Black Forest Labs (FLUX) | "We claim no ownership rights" | Allowed for output as the terms permit | Yes | Not found | Political campaigning or lobbying, presenting output as a real photo or as human-made, **training other models on output** | bfl.ai/legal/terms-of-service |
| ElevenLabs (TTS / Music) | "You retain all rights in … your Output" | Music: by plan (Exhibit A, "Music Commercial Rights Table") | Allowed, but **no building a music library and no Model Resale** without written approval | Not found | Infringing output, imitating a recording artist, hate, exploitation of minors | elevenlabs.io/terms-of-use; elevenlabs.io/music-terms |
| Google Lyria | As Gemini API / Vertex | Allowed | As above | **Not on the indemnity list** | Same policy | as above |

Important for 148AI:
- **148AI's API platform is itself the "customer"** of every provider. Rights pass to 148AI first, and 148AI assigns them on to its own customer. That works with every provider listed, but the restrictions travel with the output: Luma requires a commercial plan, ElevenLabs forbids music libraries, BFL forbids training on output, and Replicate depends on each model's licence.
- **Luma and ElevenLabs forbid giving a third party access to the model itself** (model resale). 148AI must present the output as the result of a build, not as a raw model API.
- Assigning rights does **not** clear 148AI of liability by itself. Providers (Replicate, Pika) pass the risk on to the API customer, which is 148AI. Hence the clauses below.

## 4. Draft clauses for 148AI's customer terms

> **This is a draft for review by a lawyer, not legal advice.** It has not been checked against Israeli law, US law or EU consumer law. A lawyer must adapt it.

### English (draft)

**1. Ownership of Output.** As between you and 148AI, you own all content generated for you through the Service ("Output"). To the extent 148AI acquires any right, title or interest in Output, 148AI hereby assigns it to you. 148AI makes no representation that Output is protectable by copyright, and similar Output may be generated for other users. Your rights in Output are subject to the third-party model terms listed at [link], which 148AI passes through to you.

**2. Your Inputs and Responsibility.** You are solely responsible for the prompts, files, images, audio, likenesses and other materials you submit ("Inputs") and for your use of Output. You represent and warrant that you own or have all necessary rights, licences and consents to the Inputs, including consent from any identifiable person, and that your Inputs and your use of Output will not infringe or violate any third party's rights or any law. You will indemnify and hold 148AI harmless from claims arising from your Inputs, your use of Output, or your breach of these terms.

**3. 148AI Is a Tool Provider.** 148AI provides software tools that use third-party AI models to generate content at your direction. 148AI does not author, select, review or endorse Output, and does not act as publisher of Output. Output is provided "as is". You must review Output before use and must not present it as made solely by a human where that would deceive.

**4. Prohibited Uses.** You must not use the Service to create content that is illegal, infringing, sexual content involving minors, non-consensual intimate imagery, impersonation of a real person, deceptive political content, or any use prohibited by the policies of our model providers [link].

**5. Notice and Takedown (DMCA).** If you believe content generated or hosted through the Service infringes your rights, send a notice to [designated agent / email] with: identification of the work; the location of the material; your contact details; a good-faith statement; a statement under penalty of perjury that the notice is accurate and that you are authorised; and your signature. We may remove or disable the material, notify the user, and terminate repeat infringers. Users may submit a counter-notice in the form required by law.

**6. Limitation of Liability.** To the maximum extent permitted by law, 148AI will not be liable for any indirect, incidental, special, consequential or punitive damages, or for loss of profits, data or goodwill, arising from the Service or Output. 148AI's total liability for any claim will not exceed the amounts you paid 148AI in the 12 months before the claim. Nothing in these terms limits liability that cannot be limited by law.

### עברית (טיוטה)

**1. בעלות בתוצר.** בינך לבין 148AI, כל תוכן שנוצר עבורך באמצעות השירות ("התוצר") שייך לך. ככל שיש ל-148AI זכות, בעלות או טובת הנאה כלשהי בתוצר, היא מומחית לך בזאת. 148AI אינה מצהירה שהתוצר מוגן בזכויות יוצרים, ותוצר דומה עשוי להיווצר גם למשתמשים אחרים. זכויותיך בתוצר כפופות לתנאי ספקי המודלים המפורטים ב-[קישור], ו-148AI מעבירה אותם אליך.

**2. הקלט שלך והאחריות עליו.** אתה לבדך אחראי להנחיות, לקבצים, לתמונות, לקולות, לדמויות ולכל חומר אחר שאתה מזין ("הקלט"), וכן לשימוש שלך בתוצר. אתה מצהיר ומתחייב שיש לך את כל הזכויות, הרישיונות וההסכמות הנדרשים לקלט, לרבות הסכמה של כל אדם שניתן לזהותו בו, ושהקלט שלך והשימוש שלך בתוצר אינם מפרים זכות של צד שלישי או דין כלשהו. אתה תשפה את 148AI ותפטור אותה מכל תביעה שנובעת מהקלט שלך, מהשימוש שלך בתוצר או מהפרה של תנאים אלה.

**3. 148AI היא ספקית כלי.** 148AI מספקת כלי תוכנה שמשתמשים במודלי בינה מלאכותית של צדדים שלישיים כדי ליצור תוכן לפי הנחייתך. 148AI אינה יוצרת את התוצר, אינה בוחרת אותו, אינה בודקת אותו ואינה מאמצת אותו, והיא איננה המפרסמת שלו. התוצר ניתן "כמות שהוא" (AS IS). עליך לבדוק את התוצר לפני שאתה משתמש בו, ואסור לך להציג אותו כיצירה אנושית בלבד באופן מטעה.

**4. שימושים אסורים.** אסור להשתמש בשירות ליצירת תוכן בלתי חוקי או מפר זכויות, תוכן מיני שמעורבים בו קטינים, דימויים אינטימיים ללא הסכמה, התחזות לאדם אמיתי, תוכן פוליטי מטעה, או כל שימוש שאסור לפי מדיניות ספקי המודלים שלנו [קישור].

**5. הודעה והסרה (DMCA).** אם אתה סבור שתוכן שנוצר או מתארח בשירות מפר את זכויותיך, שלח הודעה ל-[כתובת / נציג מוסמך] וכלול בה: זיהוי היצירה; מיקום החומר; פרטי התקשרות; הצהרה בתום לב; הצהרה, בידיעה שהצהרה כוזבת היא עבירה, שההודעה נכונה ושאתה מוסמך לשלוח אותה; וחתימה. אנו רשאים להסיר את החומר או לחסום את הגישה אליו, להודיע על כך למשתמש ולסיים את חשבונו של מפר חוזר. המשתמש רשאי להגיש הודעת נגד לפי הדין.

**6. הגבלת אחריות.** במידה המרבית שהדין מתיר, 148AI לא תישא באחריות לנזק עקיף, מקרי, מיוחד, תוצאתי או עונשי, ולא לאובדן רווחים, נתונים או מוניטין, שנובעים מהשירות או מהתוצר. האחריות הכוללת של 148AI בגין כל תביעה לא תעלה על הסכום ששילמת ל-148AI ב-12 החודשים שקדמו לתביעה. אין באמור כדי להגביל אחריות שהדין אינו מאפשר להגביל.

## 5. What is still open
- Replicate prices for Wan 3.0, MiniMax H3 Lite, Seedance 1 and LTX-2 were not shown on the extracted pages. The figures given are estimates.
- The Veo 3.1 Lite clip-length limit and its rank on Artificial Analysis were not verified.
- Hebrew text rendering: no documentation from any provider and no test was run.
- The Pika 2.5 price and the Imagen and Lyria prices were not extracted.
- The terms themselves need a lawyer, especially on passing provider restrictions on to the end customer, and on the DMCA agent designation (US) or its Israeli equivalent.
