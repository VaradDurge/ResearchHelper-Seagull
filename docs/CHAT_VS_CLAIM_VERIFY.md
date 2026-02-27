# Chat vs Claim Verification — What’s the difference?

## Why you don’t see changes in “Chat with PDF”

**Chat with PDF was not changed.** It still uses the same flow:

- You type a question → we retrieve relevant chunks → the LLM writes a **prose answer** (paragraphs).
- That’s **normal RAG**: one retrieval, one summary-style answer.

So when you chat with a PDF, behavior and UI are the same as before. No changes there.

---

## What the new system is: Claim Verification

The new **Evidence Confidence Scoring Engine** is a **separate feature**, not a replacement for chat:

| | **Chat with PDF (existing)** | **Claim Verification (new)** |
|---|-----------------------------|------------------------------|
| **Purpose** | Answer questions with a written summary | Check whether a **single factual claim** is supported or contradicted by your papers |
| **Input** | Free-form question (e.g. “What did the authors find about anxiety?”) | One **atomic claim** (e.g. “Coffee reduces anxiety in adults”) |
| **Output** | Paragraph(s) of text + citations | **Structured result only**: support/contradict/neutral counts, confidence score, evidence strength, no long prose |
| **Flow** | Retrieve → 1 LLM answer | Retrieve → classify each chunk (SUPPORT/CONTRADICT/NEUTRAL) → score evidence → aggregate → JSON |
| **Where** | **Chat** tab (`/chat`) | **Claim Verify** tab (`/claim-verify`) |

So:

- **Chat** = “Summarize / answer from my documents.”
- **Claim Verify** = “Audit this one claim: how much support vs contradiction, and how confident?”

---

## Where to see the new results

1. **In the app**  
   Open the **Claim Verify** page (sidebar: “Claim Verify”).  
   Enter a single claim (e.g. “Coffee reduces anxiety in adults”) and click **Verify**.  
   You’ll see the **new** results: confidence label, support/contradict/neutral counts, evidence strength, and per-chunk evidence (support/contradict/neutral + scores).

2. **Via API**  
   `POST /api/v1/verify/claim` with body:  
   `{ "claim": "Your atomic claim here", "paper_ids": null }`  
   (null = use all papers in the current workspace.)  
   Response is JSON only (no paragraphs).

---

## Summary

- **Chat with PDF** = unchanged RAG; you won’t see any difference there.
- **Claim Verification** = new, separate feature: audit one claim and get structured support/contradiction/confidence.
- **Where to see it:** use the **Claim Verify** page in the UI (or call the verify API directly).
