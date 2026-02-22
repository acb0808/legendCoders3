export interface ProblemDetail {
  id: string;
  baekjoon_problem_id: number;
  title: string;
  description: string;
  input_example: string;
  output_example: string;
  time_limit_ms: number;
  memory_limit_mb: number;
  difficulty_level: string;
  algorithm_type: string[];
  created_at: string;
}
