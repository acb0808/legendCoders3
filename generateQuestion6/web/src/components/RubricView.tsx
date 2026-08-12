import { LatexText } from "@/lib/latex";
import type { Rubric } from "@/lib/types";

/** 채점 루브릭 — 검증된 SolutionGraph 에서 파생된 부분점수 기준. */
export function RubricView({ rubric }: { rubric: Rubric | null | undefined }) {
  if (!rubric || rubric.items.length === 0) {
    return (
      <section aria-label="채점 기준" className="rubric-panel">
        <p className="rubric-empty">채점 기준 없음</p>
      </section>
    );
  }

  return (
    <section aria-label="채점 기준" className="rubric-panel">
      <h4 className="card-section-title">
        채점 기준 <span className="rubric-total">총 {rubric.total_points}점</span>
      </h4>
      <ol className="rubric-list">
        {rubric.items.map((item) => (
          <li key={item.node_id} className="rubric-item">
            <div className="rubric-item-head">
              <span className="rubric-score">{item.score}점</span>
              <span className="rubric-description">
                <LatexText text={item.description} />
              </span>
            </div>
            {item.equivalent_expressions?.length ? (
              <p className="rubric-meta">
                동치 표현:{" "}
                {item.equivalent_expressions.map((expression, index) => (
                  <span key={index} className="rubric-chip">
                    <LatexText text={expression} />
                  </span>
                ))}
              </p>
            ) : null}
            {item.common_errors?.length ? (
              <p className="rubric-meta">대표 오류: {item.common_errors.join(", ")}</p>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
