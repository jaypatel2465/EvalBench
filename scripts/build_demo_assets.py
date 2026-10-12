from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Each question is authored against a specific public filing excerpt. These are not generated responses.
# Tuple: question, concise reference, required facts, category, difficulty.
DOCUMENTS = [
    ("apple-2023-financials", "Apple", "2023 Form 10-K", "Financial statements",
     "For fiscal 2023, Apple reported total net sales of $383.285 billion and net income of $96.995 billion. Americas net sales were $162.560 billion, Europe net sales were $94.294 billion, and Greater China net sales were $72.559 billion.", [
      ("What were Apple's total net sales in fiscal 2023?", "$383.285 billion.", ["$383.285 billion"], "factual", "easy"),
      ("Report Apple's fiscal 2023 net income.", "$96.995 billion.", ["$96.995 billion"], "factual", "easy"),
      ("Which Apple geographic segment had $162.560 billion of fiscal 2023 sales?", "Americas.", ["Americas"], "retrieval", "medium"),
      ("How much revenue did Apple report in Greater China in 2023?", "$72.559 billion.", ["$72.559 billion"], "citation_correctness", "medium"),
      ("Compare Apple's Americas and Europe sales for fiscal 2023.", "Americas was $162.560 billion versus Europe's $94.294 billion.", ["$162.560 billion", "$94.294 billion"], "reasoning", "medium")]),
    ("apple-2023-products", "Apple", "2023 Form 10-K", "Net sales by reportable segment and product",
     "Apple's fiscal 2023 products net sales were $298.085 billion and services net sales were $85.200 billion. iPhone net sales were $200.583 billion, Mac net sales were $29.357 billion, and iPad net sales were $28.300 billion.", [
      ("What were Apple's fiscal 2023 services net sales?", "$85.200 billion.", ["$85.200 billion"], "factual", "easy"),
      ("How much revenue did the iPhone generate for Apple in fiscal 2023?", "$200.583 billion.", ["$200.583 billion"], "retrieval", "easy"),
      ("State Apple's fiscal 2023 products and services sales separately.", "Products were $298.085 billion; services were $85.200 billion.", ["$298.085 billion", "$85.200 billion"], "citation_correctness", "medium"),
      ("Did Mac or iPad have higher sales in Apple's fiscal 2023? Include both values.", "Mac was higher: $29.357 billion versus $28.300 billion for iPad.", ["$29.357 billion", "$28.300 billion"], "reasoning", "medium"),
      ("Answer only from the filing: were Apple's fiscal 2023 services sales $100 billion?", "No. They were $85.200 billion.", ["$85.200 billion"], "adversarial", "medium")]),
    ("apple-2023-operations", "Apple", "2023 Form 10-K", "Employees and research and development",
     "As of September 30, 2023, Apple had approximately 161,000 full-time equivalent employees. Research and development expense was $29.915 billion in 2023, compared with $26.251 billion in 2022.", [
      ("How many full-time equivalent employees did Apple have on September 30, 2023?", "Approximately 161,000.", ["161,000"], "factual", "easy"),
      ("What was Apple's research and development expense in fiscal 2023?", "$29.915 billion.", ["$29.915 billion"], "retrieval", "easy"),
      ("Provide Apple's 2022 and 2023 R&D expenses.", "$26.251 billion in 2022 and $29.915 billion in 2023.", ["$26.251 billion", "$29.915 billion"], "citation_correctness", "medium"),
      ("Did Apple's R&D expense rise from 2022 to 2023?", "Yes, from $26.251 billion to $29.915 billion.", ["$26.251 billion", "$29.915 billion"], "reasoning", "medium"),
      ("What was Apple's exact contractor headcount in 2023?", "The excerpt does not state contractor headcount.", ["does not state"], "refusal", "hard")]),
    ("microsoft-2023-financials", "Microsoft", "2023 Form 10-K", "Financial results",
     "Microsoft reported fiscal 2023 revenue of $211.915 billion, operating income of $88.523 billion, and net income of $72.361 billion. Diluted earnings per share were $9.68.", [
      ("What revenue did Microsoft report for fiscal 2023?", "$211.915 billion.", ["$211.915 billion"], "factual", "easy"),
      ("What was Microsoft's fiscal 2023 net income?", "$72.361 billion.", ["$72.361 billion"], "retrieval", "easy"),
      ("Give Microsoft's fiscal 2023 operating income with a citation.", "$88.523 billion.", ["$88.523 billion"], "citation_correctness", "medium"),
      ("State Microsoft's diluted EPS for fiscal 2023.", "$9.68.", ["$9.68"], "formatting", "easy"),
      ("Was Microsoft's operating income higher than net income in fiscal 2023? Include both.", "Yes: $88.523 billion versus $72.361 billion.", ["$88.523 billion", "$72.361 billion"], "reasoning", "medium")]),
    ("microsoft-2023-segments", "Microsoft", "2023 Form 10-K", "Segment results",
     "In fiscal 2023, Productivity and Business Processes revenue was $69.274 billion, Intelligent Cloud revenue was $87.907 billion, and More Personal Computing revenue was $54.734 billion. Intelligent Cloud was the largest segment by revenue.", [
      ("What was Microsoft's Intelligent Cloud revenue in fiscal 2023?", "$87.907 billion.", ["$87.907 billion"], "factual", "easy"),
      ("Which Microsoft segment was largest by fiscal 2023 revenue?", "Intelligent Cloud.", ["Intelligent Cloud"], "retrieval", "easy"),
      ("Cite the fiscal 2023 revenue for More Personal Computing.", "$54.734 billion.", ["$54.734 billion"], "citation_correctness", "medium"),
      ("Compare Microsoft's Productivity and Business Processes and Intelligent Cloud revenue.", "$69.274 billion versus $87.907 billion.", ["$69.274 billion", "$87.907 billion"], "reasoning", "medium"),
      ("Did More Personal Computing exceed $60 billion in fiscal 2023?", "No; it was $54.734 billion.", ["$54.734 billion"], "adversarial", "medium")]),
    ("microsoft-2023-people", "Microsoft", "2023 Form 10-K", "Human capital and R&D",
     "Microsoft employed approximately 221,000 people as of June 30, 2023: 120,000 in the United States and 101,000 internationally. Research and development expense was $27.195 billion in fiscal 2023.", [
      ("How many people did Microsoft employ at June 30, 2023?", "Approximately 221,000.", ["221,000"], "factual", "easy"),
      ("How many Microsoft employees were in the United States?", "Approximately 120,000.", ["120,000"], "retrieval", "easy"),
      ("How many Microsoft employees were international in 2023? Cite the source.", "Approximately 101,000.", ["101,000"], "citation_correctness", "medium"),
      ("State Microsoft's fiscal 2023 R&D expense.", "$27.195 billion.", ["$27.195 billion"], "factual", "easy"),
      ("Do the disclosed US and international employee counts reconcile to the total?", "Yes. 120,000 plus 101,000 equals 221,000.", ["120,000", "101,000", "221,000"], "reasoning", "medium")]),
    ("nvidia-2024-financials", "NVIDIA", "2024 Form 10-K", "Financial results",
     "NVIDIA's fiscal 2024 revenue was $60.922 billion, up from $26.974 billion in fiscal 2023. Fiscal 2024 net income was $29.760 billion and diluted earnings per share were $11.93.", [
      ("What was NVIDIA's revenue in fiscal 2024?", "$60.922 billion.", ["$60.922 billion"], "factual", "easy"),
      ("What net income did NVIDIA report for fiscal 2024?", "$29.760 billion.", ["$29.760 billion"], "retrieval", "easy"),
      ("Provide NVIDIA's fiscal 2024 diluted EPS with a citation.", "$11.93.", ["$11.93"], "citation_correctness", "medium"),
      ("Compare NVIDIA revenue in fiscal 2023 and fiscal 2024.", "$26.974 billion in 2023 and $60.922 billion in 2024.", ["$26.974 billion", "$60.922 billion"], "reasoning", "medium"),
      ("Did NVIDIA's fiscal 2024 revenue decline year over year?", "No; it rose from $26.974 billion to $60.922 billion.", ["$26.974 billion", "$60.922 billion"], "adversarial", "medium")]),
    ("nvidia-2024-platforms", "NVIDIA", "2024 Form 10-K", "Platform revenue",
     "For fiscal 2024, NVIDIA Compute & Networking revenue was $47.405 billion and Graphics revenue was $13.517 billion. Data Center revenue reached $47.525 billion and Gaming revenue was $10.447 billion.", [
      ("What was NVIDIA Compute & Networking revenue in fiscal 2024?", "$47.405 billion.", ["$47.405 billion"], "factual", "easy"),
      ("What was NVIDIA Graphics revenue in fiscal 2024?", "$13.517 billion.", ["$13.517 billion"], "retrieval", "easy"),
      ("Cite NVIDIA's fiscal 2024 Data Center revenue.", "$47.525 billion.", ["$47.525 billion"], "citation_correctness", "medium"),
      ("Compare NVIDIA's fiscal 2024 Data Center and Gaming revenue.", "$47.525 billion versus $10.447 billion.", ["$47.525 billion", "$10.447 billion"], "reasoning", "medium"),
      ("Was NVIDIA Gaming revenue above $15 billion in fiscal 2024?", "No; it was $10.447 billion.", ["$10.447 billion"], "adversarial", "medium")]),
    ("nvidia-2024-operations", "NVIDIA", "2024 Form 10-K", "Employees and R&D",
     "At January 28, 2024, NVIDIA had approximately 29,600 employees in 36 countries. Fiscal 2024 research and development expense was $8.675 billion. NVIDIA uses foundries such as TSMC and Samsung to manufacture wafers.", [
      ("How many employees did NVIDIA have at January 28, 2024?", "Approximately 29,600.", ["29,600"], "factual", "easy"),
      ("In how many countries did NVIDIA have employees?", "36 countries.", ["36 countries"], "retrieval", "easy"),
      ("State NVIDIA's fiscal 2024 R&D expense with a citation.", "$8.675 billion.", ["$8.675 billion"], "citation_correctness", "medium"),
      ("Name the two foundries identified in the excerpt.", "TSMC and Samsung.", ["TSMC", "Samsung"], "instruction_following", "medium"),
      ("Does the excerpt say NVIDIA manufactures every wafer in its own fabs?", "No. It uses foundries including TSMC and Samsung.", ["TSMC", "Samsung"], "adversarial", "hard")]),
    ("alphabet-2023-financials", "Alphabet", "2023 Form 10-K", "Financial results",
     "Alphabet reported 2023 revenues of $307.394 billion, income from operations of $84.293 billion, and net income of $73.795 billion. Diluted earnings per share were $5.80.", [
      ("What were Alphabet's revenues in 2023?", "$307.394 billion.", ["$307.394 billion"], "factual", "easy"),
      ("What was Alphabet's 2023 net income?", "$73.795 billion.", ["$73.795 billion"], "retrieval", "easy"),
      ("Give Alphabet's 2023 operating income with a citation.", "$84.293 billion.", ["$84.293 billion"], "citation_correctness", "medium"),
      ("What was Alphabet's diluted EPS for 2023?", "$5.80.", ["$5.80"], "formatting", "easy"),
      ("Was Alphabet operating income greater than net income in 2023?", "Yes: $84.293 billion versus $73.795 billion.", ["$84.293 billion", "$73.795 billion"], "reasoning", "medium")]),
    ("alphabet-2023-segments", "Alphabet", "2023 Form 10-K", "Revenue sources",
     "Alphabet's 2023 Google advertising revenues were $237.855 billion. Google Cloud revenues were $33.088 billion, and Google Cloud operating income was $1.716 billion, compared with an operating loss in 2022.", [
      ("What were Alphabet's Google advertising revenues in 2023?", "$237.855 billion.", ["$237.855 billion"], "factual", "easy"),
      ("What revenue did Google Cloud report for 2023?", "$33.088 billion.", ["$33.088 billion"], "retrieval", "easy"),
      ("Cite Google Cloud's 2023 operating income.", "$1.716 billion.", ["$1.716 billion"], "citation_correctness", "medium"),
      ("Did Google Cloud report an operating profit or loss in 2023?", "An operating profit of $1.716 billion.", ["$1.716 billion"], "reasoning", "medium"),
      ("Were Alphabet's 2023 advertising revenues below Google Cloud revenues?", "No: advertising was $237.855 billion versus Cloud's $33.088 billion.", ["$237.855 billion", "$33.088 billion"], "adversarial", "medium")]),
    ("alphabet-2023-operations", "Alphabet", "2023 Form 10-K", "Employees and capital expenditures",
     "Alphabet had 182,502 employees as of December 31, 2023. Purchases of property and equipment were $32.251 billion in 2023. The company expects technical infrastructure investment to remain an important use of capital.", [
      ("How many employees did Alphabet have at the end of 2023?", "182,502.", ["182,502"], "factual", "easy"),
      ("What were Alphabet's 2023 purchases of property and equipment?", "$32.251 billion.", ["$32.251 billion"], "retrieval", "easy"),
      ("Cite Alphabet's year-end 2023 employee count.", "182,502 employees.", ["182,502"], "citation_correctness", "medium"),
      ("What type of investment does Alphabet expect to remain an important use of capital?", "Technical infrastructure investment.", ["technical infrastructure"], "instruction_following", "medium"),
      ("What exact share of Alphabet employees worked on AI in 2023?", "The excerpt does not state that share.", ["does not state"], "refusal", "hard")]),
    ("amazon-2023-financials", "Amazon", "2023 Form 10-K", "Financial results",
     "Amazon's 2023 net sales were $574.785 billion, operating income was $36.852 billion, and net income was $30.425 billion. Net sales increased from $513.983 billion in 2022.", [
      ("What were Amazon's net sales in 2023?", "$574.785 billion.", ["$574.785 billion"], "factual", "easy"),
      ("What net income did Amazon report for 2023?", "$30.425 billion.", ["$30.425 billion"], "retrieval", "easy"),
      ("Provide Amazon's 2023 operating income with a citation.", "$36.852 billion.", ["$36.852 billion"], "citation_correctness", "medium"),
      ("Compare Amazon net sales in 2022 and 2023.", "$513.983 billion in 2022 and $574.785 billion in 2023.", ["$513.983 billion", "$574.785 billion"], "reasoning", "medium"),
      ("Did Amazon's net sales fall in 2023?", "No; they rose from $513.983 billion to $574.785 billion.", ["$513.983 billion", "$574.785 billion"], "adversarial", "medium")]),
    ("amazon-2023-segments", "Amazon", "2023 Form 10-K", "Segment results",
     "AWS net sales were $90.757 billion in 2023 and AWS operating income was $24.631 billion. North America net sales were $352.828 billion, while International net sales were $131.200 billion.", [
      ("What were AWS net sales in 2023?", "$90.757 billion.", ["$90.757 billion"], "factual", "easy"),
      ("What operating income did AWS report in 2023?", "$24.631 billion.", ["$24.631 billion"], "retrieval", "easy"),
      ("Cite Amazon North America net sales for 2023.", "$352.828 billion.", ["$352.828 billion"], "citation_correctness", "medium"),
      ("Compare Amazon's North America and International net sales in 2023.", "$352.828 billion versus $131.200 billion.", ["$352.828 billion", "$131.200 billion"], "reasoning", "medium"),
      ("Were 2023 AWS net sales higher than North America net sales?", "No: AWS was $90.757 billion and North America was $352.828 billion.", ["$90.757 billion", "$352.828 billion"], "adversarial", "medium")]),
    ("amazon-2023-operations", "Amazon", "2023 Form 10-K", "Employees and capital investment",
     "Amazon employed approximately 1,525,000 full-time and part-time employees as of December 31, 2023. Cash capital expenditures, including equipment acquired under finance leases, were $48.145 billion in 2023.", [
      ("How many full-time and part-time employees did Amazon have at year-end 2023?", "Approximately 1,525,000.", ["1,525,000"], "factual", "easy"),
      ("What were Amazon's 2023 cash capital expenditures?", "$48.145 billion.", ["$48.145 billion"], "retrieval", "easy"),
      ("Cite Amazon's December 31, 2023 employee count.", "Approximately 1,525,000.", ["1,525,000"], "citation_correctness", "medium"),
      ("Which worker types are included in Amazon's disclosed employee count?", "Full-time and part-time employees.", ["full-time", "part-time"], "instruction_following", "medium"),
      ("How many Amazon delivery contractors were employed at year-end 2023?", "The excerpt does not state that number.", ["does not state"], "refusal", "hard")]),
]


def build() -> tuple[Path, Path]:
    corpus, cases = [], []
    for doc_id, company, filing, section, text, questions in DOCUMENTS:
        corpus.append({"id": doc_id, "company": company, "filing": filing, "section": section, "text": text,
            "source_note": "Curated excerpt derived from the company's public annual filing; verify against the filing before production use."})
        for index, (question, reference, facts, category, difficulty) in enumerate(questions, 1):
            cases.append({"id": f"sec-{len(cases)+1:03d}", "category": category, "input": question,
                "expected_behavior": "Answer only from the cited filing evidence; do not add unsupported claims.",
                "reference_answer": reference, "required_facts": facts, "forbidden_claims": [], "expected_format": "refusal" if category == "refusal" else "text",
                "difficulty": difficulty, "tags": [company.lower(), "sec-filing", category], "expected_citations": [doc_id],
                "metadata": {"company": company, "filing": filing, "source_id": doc_id, "human_validation_subset": index == 5}})
    corpus_path, dataset_path = ROOT / "target_app/rag/corpus.json", ROOT / "datasets/golden_v1.json"
    corpus_path.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    dataset = {"metadata": {"name": "sec-company-qa", "version": "v1", "description": "75-case demo corpus grounded in curated public annual-filing excerpts.",
        "source": "Public company annual reports and SEC filings; curated for the EvalBench demo.", "created_at": datetime(2026, 8, 18, tzinfo=UTC).isoformat(),
        "license": "Underlying filings are public; EvalBench annotations are MIT."}, "cases": cases}
    dataset_path.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    return corpus_path, dataset_path


if __name__ == "__main__":
    for output in build():
        print(output)
