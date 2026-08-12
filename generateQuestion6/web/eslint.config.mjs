import coreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const eslintConfig = [
  ...coreWebVitals,
  ...nextTypescript,
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts", "coverage/**"],
  },
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      eqeqeq: ["error", "always"],
    },
  },
];

export default eslintConfig;
