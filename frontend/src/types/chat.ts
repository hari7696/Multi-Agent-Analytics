export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  agent?: string;
  files?: Array<{
    url: string;
    type: string;
    metadata?: any;
  }>;
  plotlyData?: any;
  processingSteps?: Array<{
    type: string;
    message: string;
    agent?: string;
  }>;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export interface PromptSuggestion {
  icon: string;
  title: string;
  description: string;
  prompt: string;
}
