// D:\FYP\FORGE-1\frontend\src\types\chat.ts

export type ChatIntent = "greeting" | "out_of_scope" | "website_build" | "general";

export interface ChatMessage {
  id: string;
  sender: "user" | "forge";
  text: string;
  timestamp: string;
  intent?: ChatIntent;
  turnCount?: number;
  isError?: boolean;
}

export interface SendMessagePayload {
  message: string;
  session_id?: string;
}

export interface ChatApiResponse {
  session_id: string;
  reply: string;
  intent: ChatIntent;
  turn_count: number;
}

export interface ResetApiResponse {
  status: string;
  session_id: string;
  success: boolean;
}
