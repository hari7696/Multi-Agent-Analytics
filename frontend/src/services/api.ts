const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';
const USER_ID = 'web_user';

export interface Session {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  last_activity: string;
  message_count: number;
  is_shared: boolean;
}

export interface Message {
  id: string;
  session_id: string;
  user_id: string;
  message_type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  files?: Array<{
    url: string;
    type: string;
    metadata?: any;
  }>;
  processing_steps?: any[];
  execution_time?: number;
}

export interface StreamEvent {
  type: 'thinking' | 'agent_switch' | 'tool_call' | 'tool_response' | 'content' | 'plotly_visualization' | 'complete' | 'error';
  data: any;
  agent?: string;
  tool?: string;
  from_agent?: string;
  to_agent?: string;
  timestamp?: string;
  plotly_json?: any;
  metadata?: any;
  hasDownloadData?: boolean;
  csv_file_url?: string;
  visualization_url?: string;
}

export const api = {
  async getSessions(): Promise<Session[]> {
    const response = await fetch(`${API_BASE}/users/${USER_ID}/sessions`);
    if (!response.ok) throw new Error('Failed to fetch sessions');
    return response.json();
  },

  async getSession(sessionId: string): Promise<Session> {
    const response = await fetch(`${API_BASE}/users/${USER_ID}/sessions/${sessionId}`);
    if (!response.ok) throw new Error('Failed to fetch session');
    return response.json();
  },

  async createSession(title: string = 'New Chat'): Promise<Session> {
    const response = await fetch(`${API_BASE}/users/${USER_ID}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, initial_state: {} }),
    });
    if (!response.ok) throw new Error('Failed to create session');
    return response.json();
  },

  async deleteSession(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/users/${USER_ID}/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete session');
  },

  async getMessages(sessionId: string): Promise<Message[]> {
    const response = await fetch(`${API_BASE}/users/${USER_ID}/sessions/${sessionId}/messages`);
    if (!response.ok) throw new Error('Failed to fetch messages');
    return response.json();
  },

  streamMessage(
    sessionId: string,
    content: string,
    onEvent: (event: StreamEvent) => void,
    onError: (error: Error) => void,
    onComplete: () => void
  ): () => void {
    const controller = new AbortController();
    
    fetch(`${API_BASE}/users/${USER_ID}/sessions/${sessionId}/messages/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, message_type: 'user', user_id: USER_ID }),
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error('Failed to send message');
        
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        
        function readStream() {
          reader?.read().then(({ done, value }) => {
            if (done) {
              onComplete();
              return;
            }
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            let shouldComplete = false;
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const eventData = JSON.parse(line.slice(6));
                  onEvent(eventData);
                  
                  if (eventData.type === 'complete' || eventData.type === 'error') {
                    shouldComplete = true;
                  }
                } catch (e) {
                  console.error('Failed to parse SSE data:', e);
                }
              }
            }
            
            if (shouldComplete) {
              onComplete();
              return;
            }
            
            readStream();
          }).catch((error) => {
            if (error.name !== 'AbortError') {
              onError(error);
            }
          });
        }
        
        readStream();
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          onError(error);
        }
      });
    
    return () => controller.abort();
  },
};

