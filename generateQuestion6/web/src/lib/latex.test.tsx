import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LatexText } from "./latex";

describe("LatexText (KaTeX 렌더링)", () => {
  it("$...$ 인라인 수식을 KaTeX 구조로 렌더링한다", () => {
    const { container } = render(<LatexText text="원 $x^2 + y^2 = 25$ 의 접선" />);

    expect(container.textContent).toContain("원");
    expect(container.textContent).toContain("의 접선");
    expect(container.querySelector(".math-inline .katex")).not.toBeNull();
  });

  it("$$...$$ 블록 수식은 displayMode 로 렌더링한다", () => {
    const { container } = render(<LatexText text="답은 $$\\frac{625}{24}$$ 이다." />);

    expect(container.querySelector(".math-display .katex")).not.toBeNull();
  });

  it("시험지 <eq>...</eq> 마커를 인라인 수식으로 렌더링한다", () => {
    const { container } = render(<LatexText text="점 <eq>(-6,~2)</eq> 에서" />);

    expect(container.textContent).toContain("점");
    expect(container.querySelector(".math-inline .katex")).not.toBeNull();
  });

  it("잘못된 수식은 오류 없이 원본에 가깝게 렌더링된다", () => {
    const { container } = render(<LatexText text="조건 $x^$ 정리" />);

    expect(container.querySelector(".katex-error")).not.toBeNull();
  });
});
