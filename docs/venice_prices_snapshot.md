# venice_prices_snapshot — צילום מחירון Venice (טקסט)

| שדה | ערך |
|---|---|
| מקור | `https://docs.venice.ai/overview/pricing.md` |
| נשלף | 2026-10-19, 01:1x Asia/Jerusalem |
| שיטה | WebFetch עם הנחיה "Return ONLY the raw markdown table rows (verbatim)". הצלבה מול `https://docs.venice.ai/es/overview/pricing.md` |
| היקף | טבלת מודלי הטקסט: 132 מודלים, ושורות מחיר מדורג (↳). **ללא** cache write, context ו-privacy (ראו "מה לא כאן") |
| sha256 של טבלת הנתונים | `fee1d19bc939b0ed505a65e6f7ae6d492e6828a84e675c34eef3040320ad00bd` (מחושב על הקובץ `docs/venice_prices_snapshot.tsv`, שנשמר לצד המסמך) |

## ⚠ גבולות הצילום (קריאה חובה)

- **זה לא byte-exact.** ה-proxy של הסשן חוסם הורדה ישירה (`curl` → ‏`CONNECT tunnel failed, response 403`). התוכן הגיע דרך WebFetch, שמעביר את העמוד דרך מודל שפה. המודל התבקש להחזיר את השורות verbatim, וההצלבה מול העמוד הספרדי הסכימה בכל השורות שהושוו. **ובכל זאת אי אפשר לשלול שינוי שעשה המודל.**
- **מה הצילום כן מאפשר:** השוואה עתידית. כל מי שמוריד שוב את העמוד יכול להשוות אותו לקובץ הזה ולזהות שינוי מחיר.
- **צילום byte-exact** (מומלץ, ממכונה שיש לה גישה):
  `curl -fsS https://docs.venice.ai/overview/pricing.md -o venice_pricing_$(date +%F).md && sha256sum venice_pricing_*.md`
  ולשמור את הקובץ ואת ה-hash לצד המסמך הזה.

לכן המסמך **משדרג** את מצב המחירים ב-`MODEL_PRICES.md` מ"נבדק ידנית, לא ניתן לשחזור" ל"**ניתן להשוואה מול צילום טקסט**". הוא **לא** מצדיק VERIFIED מלא, כל עוד אין צילום byte-exact.

## מה לא כאן

עמודות cache write, ‏context ו-privacy הושמטו מהקובץ הזה. הן מופיעות בעמוד המקור, ו-cache write מתועד בתיאור ב-`MODEL_PRICES.md`. גם מחירי media לא כאן: מקורם בשליפה הספרדית בלבד.

## טבלה (סדר העמודות כמו במקור: Input, ‏Output, ‏Cache Read; ‏USD ל-1M טוקנים)

| ID | Input | Output | Cache Read |
|---|---|---|---|
| `abliteration-abliterated-model-large-v2` | $3.00 | $5.00 | $0.30 |
| `aion-labs-aion-3-0` | $3.75 | $7.50 | $0.94 |
| `aion-labs-aion-3-0-mini` | $0.88 | $1.75 | $0.23 |
| `aion-labs-aion-3-5` | $3.75 | $7.50 | $0.94 |
| `aion-labs-aion-3-5-mini` | $0.88 | $1.75 | $0.23 |
| `claude-fable-5` | $10.00 | $50.00 | $1.00 |
| `claude-fable-5-1` | $10.00 | $50.00 | $0.25 |
| `claude-haiku-5-5` | $0.10 | $0.50 | $0.01 |
| ↳ >100K Context | $0.50 | $2.50 | $0.05 |
| `claude-opus-4-5` | $5.00 | $25.00 | $0.50 |
| `claude-opus-4-6` | $5.00 | $25.00 | $0.50 |
| `claude-opus-4-7` | $5.00 | $25.00 | $0.50 |
| `claude-opus-4-8` | $5.00 | $25.00 | $0.50 |
| `claude-opus-4-8-fast` | $10.00 | $50.00 | $1.00 |
| `claude-opus-5` | $5.00 | $25.00 | $0.50 |
| `claude-opus-5-fast` | $10.00 | $50.00 | $1.00 |
| `claude-opus-5-5` | $4.00 | $20.00 | $0.20 |
| `claude-opus-5-5-fast` | $8.00 | $40.00 | $0.40 |
| `claude-sonnet-4-6` | $3.00 | $15.00 | $0.30 |
| `claude-sonnet-5` | $2.00 | $10.00 | $0.20 |
| `claude-sonnet-5-5` | $2.00 | $10.00 | $0.10 |
| `e2ee-deepseek-v4-flash` | $0.18 | $0.37 | $0.04 |
| `deepseek-v4-flash` | $0.14 | $0.28 | $0.03 |
| `deepseek-v4-flash-0731` | $0.13 | $0.26 | $0.03 |
| `deepseek-v4-flash-0731-fast` | $0.35 | $0.70 | $0.09 |
| `deepseek-v4-pro` | $1.65 | $3.30 | $0.33 |
| `deepseek-v4-pro-0813` | $1.65 | $4.95 | $0.17 |
| `deepseek-v4-1-flash` | $0.30 | $1.20 | $0.0075 |
| `deepseek-v4-1-flash-1017` | $0.30 | $1.20 | $0.0075 |
| `gemini-3-flash-preview` | $0.70 | $3.75 | $0.07 |
| `gemini-3-1-pro-preview` | $2.50 | $15.00 | $0.50 |
| ↳ >200K Context | $5.00 | $22.50 | $0.50 |
| `gemini-3-5-flash` | $1.55 | $9.45 | $0.15 |
| `gemini-3-5-flash-lite` | $0.38 | $3.13 | $0.04 |
| `gemini-3-6-flash` | $0.94 | $4.69 | $0.09 |
| `gemini-3-7-flash` | $0.94 | $4.69 | $0.09 |
| `gemini-3-8-flash` | $0.94 | $4.69 | $0.09 |
| `gemini-4-argon` | $2.50 | $12.50 | $0.13 |
| `e2ee-gemma-4-26b-a4b-uncensored-p` | $0.19 | $0.88 | - |
| `gemma-4-uncensored` | $0.16 | $0.50 | - |
| `zai-org-glm-4.6` | $0.43 | $1.75 | $0.08 |
| `zai-org-glm-4.7` | $0.55 | $2.65 | $0.11 |
| `olafangensan-glm-4.7-flash-heretic` | $0.07 | $0.40 | $0.04 |
| `zai-org-glm-5` | $1.00 | $3.20 | $0.20 |
| `z-ai-glm-5-turbo` | $1.20 | $4.00 | $0.24 |
| `zai-org-glm-5-1` | $1.54 | $4.84 | $0.29 |
| `zai-org-glm-5-2` | $1.40 | $4.40 | $0.26 |
| `e2ee-glm-5-2-p` | $1.75 | $5.75 | $0.30 |
| `z-ai-glm-5-3` | $1.75 | $5.50 | $0.33 |
| `e2ee-glm-5-3-p` | $1.75 | $5.50 | $0.33 |
| `z-ai-glm-5-3-flash` | $0.15 | $0.50 | $0.03 |
| `e2ee-glm-5-3-flash` | $0.16 | $0.54 | $0.04 |
| `z-ai-glm-5v-turbo` | $1.50 | $5.00 | $0.30 |
| `google-gemma-3-27b-it` | $0.12 | $0.20 | - |
| `google-gemma-4-26b-a4b-it` | $0.13 | $0.40 | $0.05 |
| `google-gemma-4-31b-it` | $0.12 | $0.36 | $0.09 |
| `e2ee-gpt-oss-120b-p` | $0.13 | $0.65 | - |
| `openai-gpt-4o-2024-11-20` | $2.50 | $10.00 | $1.25 |
| `openai-gpt-4o-mini-2024-07-18` | $0.15 | $0.60 | $0.07 |
| `openai-gpt-52` | $1.75 | $14.00 | $0.17 |
| `openai-gpt-53-codex` | $1.75 | $14.00 | $0.17 |
| `openai-gpt-54` | $2.50 | $15.00 | $0.25 |
| ↳ >272K Context | $5.00 | $22.50 | $0.50 |
| `openai-gpt-54-mini` | $0.75 | $4.50 | $0.07 |
| `openai-gpt-54-pro` | $30.00 | $180.00 | - |
| ↳ >272K Context | $60.00 | $270.00 | - |
| `openai-gpt-55` | $5.00 | $30.00 | $0.50 |
| ↳ >272K Context | $10.00 | $45.00 | $1.00 |
| `openai-gpt-55-pro` | $30.00 | $180.00 | - |
| ↳ >272K Context | $60.00 | $270.00 | - |
| `openai-gpt-56-luna` | $0.20 | $1.20 | $0.02 |
| ↳ >272K Context | $0.40 | $1.80 | $0.04 |
| `openai-gpt-56-luna-pro` | $0.20 | $1.20 | $0.02 |
| ↳ >272K Context | $0.40 | $1.80 | $0.04 |
| `openai-gpt-56-sol` | $4.00 | $20.00 | $0.40 |
| ↳ >272K Context | $8.00 | $30.00 | $0.80 |
| `openai-gpt-56-sol-pro` | $4.00 | $20.00 | $0.40 |
| ↳ >272K Context | $8.00 | $30.00 | $0.80 |
| `openai-gpt-56-terra` | $2.00 | $12.00 | $0.20 |
| ↳ >272K Context | $4.00 | $18.00 | $0.40 |
| `openai-gpt-56-terra-pro` | $2.00 | $12.00 | $0.20 |
| ↳ >272K Context | $4.00 | $18.00 | $0.40 |
| `openai-gpt-6-astra` | $10.00 | $50.00 | $1.00 |
| ↳ >272K Context | $20.00 | $75.00 | $2.00 |
| `openai-gpt-6-astra-pro` | $10.00 | $50.00 | $1.00 |
| ↳ >272K Context | $20.00 | $75.00 | $2.00 |
| `openai-gpt-6-luna` | $0.10 | $0.50 | $0.01 |
| ↳ >272K Context | $0.20 | $0.75 | $0.02 |
| `openai-gpt-6-sol` | $2.00 | $10.00 | $0.20 |
| ↳ >272K Context | $4.00 | $15.00 | $0.40 |
| `openai-gpt-61-sol` | $2.00 | $10.00 | $0.10 |
| ↳ >272K Context | $4.00 | $15.00 | $0.20 |
| `openai-gpt-61-sol-ultrafast` | $12.00 | $60.00 | $0.60 |
| ↳ >272K Context | $24.00 | $90.00 | $1.20 |
| `grok-4-20` | $1.42 | $2.83 | $0.23 |
| ↳ >200K Context | $2.83 | $5.67 | $0.45 |
| `grok-4-20-multi-agent` | $1.42 | $2.83 | $0.23 |
| ↳ >200K Context | $2.83 | $5.67 | $0.45 |
| `grok-4-3` | $1.42 | $2.83 | $0.23 |
| ↳ >200K Context | $2.83 | $5.67 | $0.45 |
| `grok-4-5` | $2.27 | $6.80 | $0.34 |
| ↳ >200K Context | $4.53 | $13.60 | $0.68 |
| `grok-4-6` | $2.27 | $6.80 | $0.57 |
| ↳ >200K Context | $4.53 | $13.60 | $1.13 |
| `grok-4-7` | $2.27 | $6.80 | $0.57 |
| ↳ >200K Context | $4.53 | $13.60 | $1.13 |
| `grok-build-0-1` | $1.00 | $2.00 | $0.20 |
| ↳ >200K Context | $2.00 | $4.00 | $0.40 |
| `hermes-3-llama-3.1-405b` | $1.10 | $3.00 | - |
| `hy4-preview` | $1.04 | $3.13 | $0.05 |
| `inkling` | $1.25 | $5.06 | $0.21 |
| `kimi-k2-5` | $0.56 | $3.50 | $0.22 |
| `kimi-k2-6` | $0.75 | $3.50 | $0.16 |
| `e2ee-kimi-k2-6` | $0.87 | $4.12 | $0.44 |
| `kimi-k2-7-code` | $0.75 | $3.50 | $0.16 |
| `kimi-k3` | $3.75 | $18.75 | $0.38 |
| `e2ee-kimi-k3-p` | $3.75 | $18.75 | $0.38 |
| `kimi-k3-fast-api` | $4.50 | $22.50 | $0.45 |
| `llama-3.2-3b` | $0.15 | $0.60 | - |
| `llama-3.3-70b` | $0.70 | $2.80 | - |
| `mercury-2` | $0.31 | $0.94 | $0.03 |
| `mercury-2-5` | $0.25 | $0.94 | $0.03 |
| `xiaomi-mimo-v2-5` | $0.40 | $2.00 | $0.08 |
| `xiaomi-mimo-v2-6-flash` | $0.17 | $0.35 | $0.0037 |
| `minimax-m25` | $0.27 | $0.95 | $0.03 |
| `minimax-m27` | $0.38 | $1.50 | $0.07 |
| `minimax-m3-preview` | $0.30 | $1.20 | $0.06 |
| `mistral-small-3-2-24b-instruct` | $0.09 | $0.25 | - |
| `muse-spark-open` | $1.56 | $5.31 | $0.19 |
| `muse-wonder` | $5.00 | $25.00 | $0.25 |
| `nvidia-nemotron-3-nano-30b-a3b` | $0.07 | $0.30 | - |
| `nvidia-nemotron-3-ultra-550b-a55b` | $0.63 | $3.13 | $0.19 |
| `nvidia-nemotron-3-5-super-vl-120b-a12b` | $0.25 | $1.25 | $0.13 |
| `openai-gpt-oss-120b` | $0.07 | $0.30 | - |
| `e2ee-qwen-2-5-7b-p` | $0.05 | $0.13 | - |
| `qwen3-235b-a22b-instruct-2507` | $0.15 | $0.75 | - |
| `qwen3-235b-a22b-thinking-2507` | $0.45 | $3.50 | - |
| `qwen3-coder-480b-a35b-instruct-turbo` | $0.35 | $1.50 | $0.04 |
| `qwen3-next-80b` | $0.35 | $1.90 | - |
| `qwen3-5-35b-a3b` | $0.15 | $1.00 | $0.05 |
| `qwen3-5-397b-a17b` | $0.75 | $4.50 | - |
| `qwen3-6-27b` | $0.33 | $3.25 | - |
| `qwen3-6-35b-a3b` | $0.10 | $1.00 | - |
| `e2ee-qwen3-6-35b-a3b` | $0.18 | $1.18 | $0.06 |
| `qwen-3-6-plus` | $0.63 | $3.75 | $0.06 |
| ↳ >256K Context | $2.50 | $7.50 | $0.06 |
| `qwen-3-7-max` | $2.70 | $8.05 | $0.27 |
| `qwen-3-7-plus` | $0.50 | $2.00 | $0.05 |
| ↳ >256K Context | $1.50 | $6.00 | $0.15 |
| `qwen-3-8-2-4t-a95b` | $2.50 | $7.50 | $0.31 |
| `qwen-3-8-27b` | $0.45 | $3.20 | - |
| `e2ee-qwen3-8-27b` | $0.47 | $3.53 | $0.05 |
| `qwen-3-8-flash` | $0.14 | $0.49 | $0.01 |
| `qwen-3-8-max` | $2.50 | $7.50 | $0.31 |
| `qwen3-vl-235b-a22b` | $0.21 | $1.90 | $0.10 |
| `e2ee-qwen3-vl-30b-a3b-p` | $0.25 | $0.90 | - |
| `seed-2-1-turbo` | $0.63 | $3.13 | $0.13 |
| `venice-uncensored-role-play` | $0.50 | $2.00 | - |
| `venice-uncensored-1-2` | $0.20 | $0.90 | - |
