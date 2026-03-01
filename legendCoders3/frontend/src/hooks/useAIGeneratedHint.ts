
import { useState } from 'react';
import { ProblemDetail } from '@/types/problem';

// AI 원칙 4: 전문 AI 팀원 + 단축 명령어 (역할 정의 및 효율화)
// AI의 역할을 '소크라테스식 프로그래밍 튜터'로 정의하고, 일관된 결과를 위해 프롬프트 구조를 템플릿화합니다.
const createAIPrompt = (problem: ProblemDetail, userCode: string): string => {
  return `
    You are an expert Socratic programming tutor. Your goal is to help a user solve an algorithmic problem without giving away the solution.
    Analyze the user's code for the given problem and provide a single, concise hint to guide them in the right direction.

    Problem Description:
    ---
    ${problem.description}
    ---

    User's Code:
    ---
    ${userCode}
    ---

    Based on the problem and the user's code, what is one small, guiding hint you can provide?
    Focus on potential logic errors, missed edge cases, or inefficient approaches.
    Do not write code. Do not give away the answer.
    Your hint should be a single sentence.
  `;
};

interface UseAIGeneratedHintParams {
  problemId: number;
}

/**
 * AI-powered hints for Legend Pro users.
 * This hook encapsulates the logic for fetching and managing AI-generated hints for a given problem.
 */
export const useAIGeneratedHint = ({ problemId }: UseAIGeneratedHintParams) => {
  const [hint, setHint] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  /**
   * Fetches a hint from the backend AI service.
   * @param userCode The user's current code in the editor.
   */
  const getHint = async (userCode: string) => {
    setIsLoading(true);
    setError(null);
    setHint(null);

    try {
      // AI 원칙 1: AI 자동 매뉴얼 시스템 (컨텍스트 자동화)
      // 백엔드는 problemId를 사용해 문제 정보(설명, 테스트케이스 등)를 자동으로 조회하고,
      // 이를 사용자 코드와 함께 AI 프롬프트에 포함시켜 완전한 컨텍스트를 제공합니다.
      
      // --- API Call Placeholder ---
      // In a real implementation, this would be a fetch call to our backend API,
      // e.g., POST /api/v1/problems/${problemId}/hint
      console.log("Generating AI prompt for problem:", problemId);
      
      // AI 원칙 2: AI 작업 기억 시스템 (단계적 작업 분할)
      // 백엔드 API는 이 요청을 받아 AI에게 단순히 힌트를 요청하는 것이 아니라,
      // '분석' -> '힌트 생성'의 두 단계로 나누어 처리하여 더 높은 품질의 결과를 도출합니다.
      
      // Simulating network delay and AI response
      await new Promise(resolve => setTimeout(resolve, 1500));

      const mockHint = "Have you considered what happens if the input array is empty?";
      
      // AI 원칙 3: 자동 품질 검사 + AI 자가 진단 (결과물 검증)
      // 백엔드는 AI로부터 받은 응답이 '정답'과 같은 금지어를 포함하는지 검사하고,
      // 프롬프트 내에서 AI에게 스스로 답변을 검토하도록 하여 힌트의 품질을 높입니다.
      setHint(mockHint);
      
    } catch (e) {
      setError(e as Error);
      console.error("Failed to fetch AI hint:", e);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    hint,
    isLoading,
    error,
    getHint,
  };
};
