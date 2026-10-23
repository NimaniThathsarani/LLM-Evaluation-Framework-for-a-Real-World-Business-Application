"""
LLM Evaluation Framework - Customer Support Chatbot

"""
import csv, re
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent

def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def alternatives(group):
    # "issuer or support" accepts either phrase; simple pipe groups remain required concepts.
    return [x.strip() for x in group.split(" or ") if x.strip()]

def keyword_coverage(response, required):
    if not required.strip():
        return 1.0
    r = norm(response)
    groups = [g.strip() for g in required.split("|") if g.strip()]
    hits = 0
    for g in groups:
        if any(norm(a) in r for a in alternatives(g)):
            hits += 1
    return hits / len(groups)

def forbidden_hit(response, forbidden):
    if not forbidden.strip():
        return False
    r=norm(response)
    return any(norm(x) in r for x in forbidden.split("|") if x.strip())

def jaccard_similarity(a,b):
    A=set(norm(a).split()); B=set(norm(b).split())
    return len(A&B)/len(A|B) if A|B else 1.0

with open(BASE/"test_cases_60.csv", encoding="utf-8-sig") as f:
    tests={r["Test_ID"]:r for r in csv.DictReader(f)}
with open(BASE/"llm_responses.csv", encoding="utf-8-sig") as f:
    responses={r["Test_ID"]:r["LLM_Response"] for r in csv.DictReader(f)}

out=[]
for tid,t in tests.items():
    resp=responses.get(tid,"")
    coverage=keyword_coverage(resp,t["Required_Keywords"])
    forbidden=forbidden_hit(resp,t["Forbidden_Claims"])
    # Objective automatic pass: >=75% required concept coverage and no forbidden claim.
    auto_pass = bool(resp.strip()) and coverage >= .75 and not forbidden
    out.append({
        **t,
        "LLM_Response":resp,
        "Keyword_Coverage":round(coverage,3),
        "Reference_Jaccard":round(jaccard_similarity(resp,t["Expected_Output"]),3),
        "Forbidden_Claim_Hit":int(forbidden),
        "Automatic_Pass":int(auto_pass),
        # Complete these after human review using README rubric.
        "Correctness_1_5":"",
        "Relevance_1_5":"",
        "Completeness_1_5":"",
        "Safety_1_5":"",
        "Failure_Type":"",
        "Reviewer_Notes":""
    })

fields=list(out[0].keys())
with open(BASE/"evaluation_results.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(out)

bycat=defaultdict(list)
for r in out: bycat[r["Category"]].append(r)
summary=[]
for cat,rs in bycat.items():
    summary.append({
        "Category":cat,
        "Test_Count":len(rs),
        "Automatic_Pass_Rate":round(sum(x["Automatic_Pass"] for x in rs)/len(rs),3),
        "Mean_Keyword_Coverage":round(sum(x["Keyword_Coverage"] for x in rs)/len(rs),3),
        "Forbidden_Claim_Rate":round(sum(x["Forbidden_Claim_Hit"] for x in rs)/len(rs),3),
        "Mean_Reference_Jaccard":round(sum(x["Reference_Jaccard"] for x in rs)/len(rs),3),
    })
with open(BASE/"category_summary.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=summary[0].keys()); w.writeheader(); w.writerows(summary)

print("Evaluation complete.")
print("Overall automatic pass rate:", round(sum(r["Automatic_Pass"] for r in out)/len(out),3))
print("Mean keyword coverage:", round(sum(r["Keyword_Coverage"] for r in out)/len(out),3))
print("Forbidden claim rate:", round(sum(r["Forbidden_Claim_Hit"] for r in out)/len(out),3))
