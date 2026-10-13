# Automated Editorial & Safety Audit Specification

## Quality Verification Rules

| Rule Name | Severity | Evaluation Logic |
| :--- | :--- | :--- |
| `forensic_leakage` | **BLOCKER** | Scans for LLM internal artifact leaks (`oaicite`, `turn1search`, `contentReference`, bracket placeholders `[Your Name]`). |
| `reveal_bridge` | **BLOCKER** | Matches formulaic AI transitions (`"Here's the kicker:"`, `"Let that sink in"`). |
| `sincerity_announcement` | **BLOCKER** | Detects artificial sincerity openings (`"Let me be honest"`, `"Confession:"`). |
| `hook_question_opener` | **BLOCKER** | Detects opening post with a question (`Have you ever`, `What if`, `?` on line 1). |
| `length_under_minimum` | **BLOCKER** | Total characters < 300. |
| `length_exceeds_maximum` | **BLOCKER** | Total characters > configured maximum (default 2,200). |
| `external_link_in_body` | **BLOCKER** | Regex detection of `http://` or `https://` URLs in post body. |
| `ai_vocab_density` | **BLOCKER** | 3 or more high-density AI marker words within a single paragraph. |
| `negative_parallelism` | **WARNING** | Detects `"It's not X, it's Y"` constructions. |
| `excessive_hashtags` | **WARNING** | Hashtag count exceeds 3. |
