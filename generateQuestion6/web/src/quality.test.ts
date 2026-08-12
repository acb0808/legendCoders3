import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

type PackageJson = {
  scripts?: Record<string, string>;
  devDependencies?: Record<string, string>;
};

function readPackageJson(): PackageJson {
  return JSON.parse(readFileSync(resolve(webRoot, "package.json"), "utf8")) as PackageJson;
}

describe("T00.1 프론트엔드 품질 게이트", () => {
  it("lint·typecheck·test 명령이 선언되어 있다", () => {
    const scripts = readPackageJson().scripts ?? {};

    expect(scripts.lint).toBeDefined();
    expect(scripts.typecheck).toBeDefined();
    expect(scripts.test).toBeDefined();
  });

  it("Node 의존성 잠금 파일이 존재한다", () => {
    expect(existsSync(resolve(webRoot, "package-lock.json"))).toBe(true);
  });
});
