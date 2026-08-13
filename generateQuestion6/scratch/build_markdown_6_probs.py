import json

with open('scratch/selected_6_problems.json', 'r', encoding='utf-8') as f:
    probs = json.load(f)

md = []
md.append("# 📌 프로젝트 수학 문제 변형 모음 (원본 2개 기준, 총 6개 문항)")
md.append("> **프로젝트**: 수학문제 변형&생성기  ")
md.append("> **구성**: 대표 원본 기출 문제 2개 × 원본당 변형 문제 3개 = 총 6개 문항  ")
md.append("> **포함 항목**: 원본 문제, 생성된 변형 문제, 정답, 상세 해설 (Step-by-step), 부분점수 채점 기준 (Rubric)  \n")
md.append("---")

# Group 1: run-4b083c5c
g1 = [p for p in probs if p['run_id'] == 'run-4b083c5c']
g1.sort(key=lambda x: x['candidate_id'])

md.append("\n# 📚 [원본 문항 1] 평행선과 도형의 넓이의 최솟값")
md.append("### 📄 원본 문제 출처: `[2023년 기출] 광명고1-2 중간 18번`")
md.append("> **원문**: " + g1[0]['source_text'])
md.append("\n---\n")

for idx, p in enumerate(g1):
    md.append(f"## 1️⃣-{idx+1} [변형 문제 1-{idx+1}] {p['blueprint_title']}")
    md.append(f"> **{p['problem_text']}**\n")
    md.append(f"* **🔑 정답**: `{p['final_answer_claim']}`\n")
    
    md.append("### 📝 상세 해설 (Solution)")
    for s in p['solution_steps']:
        md.append(f"{s['step_id'][-1]}. **[{s['step_id'].upper()}]** {s['statement']} *(근거: {s['justification']})*")
    md.append("")
    
    md.append("### 💯 채점 기준 및 부분점수 (Rubric)")
    md.append("| 단계 | 채점 항목 (Criteria) | 배점 |")
    md.append("| :---: | :--- | :---: |")
    for r in p['rubric']['items']:
        md.append(f"| **{r['node_id']}** | {r['description']} | {r['score']}점 |")
    md.append(f"| **합계** | **총점** | **{p['rubric']['total_points']}점** |")
    md.append("\n---\n")

# Group 2: run-77fcdc05
g2 = [p for p in probs if p['run_id'] == 'run-77fcdc05']
g2.sort(key=lambda x: x['candidate_id'])

md.append("\n# 📚 [원본 문항 2] 직선 위의 점과 좌표축/도형 넓이")
md.append("### 📄 원본 문제 출처: `직선 y=-x+3 및 삼각형 넓이 기출`")
md.append("> **원문**: " + g2[0]['source_text'])
md.append("\n---\n")

for idx, p in enumerate(g2):
    md.append(f"## 2️⃣-{idx+1} [변형 문제 2-{idx+1}] {p['blueprint_title']}")
    md.append(f"> **{p['problem_text']}**\n")
    md.append(f"* **🔑 정답**: `{p['final_answer_claim']}`\n")
    
    md.append("### 📝 상세 해설 (Solution)")
    for s in p['solution_steps']:
        md.append(f"{s['step_id'][-1]}. **[{s['step_id'].upper()}]** {s['statement']} *(근거: {s['justification']})*")
    md.append("")
    
    md.append("### 💯 채점 기준 및 부분점수 (Rubric)")
    md.append("| 단계 | 채점 항목 (Criteria) | 배점 |")
    md.append("| :---: | :--- | :---: |")
    for r in p['rubric']['items']:
        md.append(f"| **{r['node_id']}** | {r['description']} | {r['score']}점 |")
    md.append(f"| **합계** | **총점** | **{p['rubric']['total_points']}점** |")
    md.append("\n---\n")

final_md = "\n".join(md)

with open('scratch/full_notion_6_problems.md', 'w', encoding='utf-8') as f:
    f.write(final_md)

print("Generated full markdown with 6 problems to scratch/full_notion_6_problems.md")
