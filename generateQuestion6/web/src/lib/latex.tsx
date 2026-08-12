import katex from "katex";

type Token =
  | { type: "text"; value: string }
  | { type: "math"; value: string; display: boolean };

const DOLLAR_PATTERN = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g;

function tokenize(text: string): Token[] {
  const normalized = text.replace(/<eq>([\s\S]*?)<\/eq>/g, "$$$1$$");
  const tokens: Token[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = DOLLAR_PATTERN.exec(normalized)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({ type: "text", value: normalized.slice(lastIndex, match.index) });
    }
    if (match[1] !== undefined) {
      tokens.push({ type: "math", value: match[1], display: true });
    } else {
      tokens.push({ type: "math", value: match[2] ?? "", display: false });
    }
    lastIndex = DOLLAR_PATTERN.lastIndex;
  }
  if (lastIndex < normalized.length) {
    tokens.push({ type: "text", value: normalized.slice(lastIndex) });
  }
  return tokens;
}

function renderMath(value: string, display: boolean): string {
  return katex.renderToString(value, {
    throwOnError: false,
    displayMode: display,
    strict: false,
  });
}

/** 텍스트 안의 $...$ / $$...$$ / <eq>...</eq> 를 KaTeX 로 렌더링한다. */
export function LatexText({ text }: { text: string }) {
  const tokens = tokenize(text);
  return (
    <>
      {tokens.map((token, index) => {
        if (token.type === "text") {
          return <span key={index}>{token.value}</span>;
        }
        return (
          <span
            key={index}
            className={token.display ? "math-display" : "math-inline"}
            // KaTeX 의 renderToString 은 자체 이스케이프로 안전한 HTML 을 생성한다.
            dangerouslySetInnerHTML={{ __html: renderMath(token.value, token.display) }}
          />
        );
      })}
    </>
  );
}
