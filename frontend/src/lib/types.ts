export interface TopicCardData {
  card_id: string;
  title: string;
  reason: string;
  heat_index: number;
  estimated_traffic: string;
}

export interface VisualGuidance {
  cover_suggestion: string;
  shot_descriptions: string[];
  domestic_image_prompts: string[];
}

export interface TaskData {
  thread_id: string;
  user_input: string;
  status: string;
  column: string;
  revision_count: number;
  draft_copy: string | null;
  final_copy: string | null;
  visual_guidance: VisualGuidance | null;
  created_at: string;
  updated_at: string;
}

export interface KanbanBoard {
  inspiration: TopicCardData[];
  in_progress: TaskData[];
  pending_review: TaskData[];
  done: TaskData[];
}

export interface AgentStatus {
  thread_id: string;
  status: string;
  current_step: string;
  draft_copy: string | null;
  visual_guidance: VisualGuidance | null;
  error_logs: string[];
}

export type FeedbackAction = "approve" | "revise";
