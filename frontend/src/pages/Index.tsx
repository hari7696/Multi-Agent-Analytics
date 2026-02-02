import { useState, useEffect, useRef, useCallback } from "react";
import { ChatSession, Message } from "@/types/chat";
import { SessionSidebar } from "@/components/chat/SessionSidebar";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { LandingPrompts } from "@/components/chat/LandingPrompts";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/services/api";
import { toast } from "sonner";

const Index = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<(() => void) | null>(null);

  const currentSession = sessions.find((s) => s.id === currentSessionId);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [currentSession?.messages]);

  // Handle pending messages after session creation
  useEffect(() => {
    if (pendingMessage && currentSessionId) {
      setPendingMessage(null);
      handleSendMessage(pendingMessage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSessionId, pendingMessage]);

  // Load messages when session changes (only if not already loaded and not processing)
  useEffect(() => {
    if (currentSessionId && !isProcessing && !pendingMessage) {
      const session = sessions.find(s => s.id === currentSessionId);
      if (session && session.messages.length === 0) {
        loadMessages(currentSessionId);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSessionId]);

  const loadSessions = async () => {
    try {
      const apiSessions = await api.getSessions();
      const chatSessions: ChatSession[] = apiSessions.map(s => ({
        id: s.id,
        title: s.title,
        messages: [],
        createdAt: new Date(s.created_at),
        updatedAt: new Date(s.last_activity),
      }));
      setSessions(chatSessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      toast.error('Failed to load sessions');
    }
  };

  const loadMessages = async (sessionId: string) => {
    try {
      const apiMessages = await api.getMessages(sessionId);
      const messages: Message[] = await Promise.all(apiMessages.map(async (m) => {
        let plotlyData = undefined;
        
        // If there's a visualization file, fetch the plotly JSON from the URL
        const vizFile = m.files?.find(f => f.type === 'visualization');
        if (vizFile?.url) {
          try {
            const response = await fetch(vizFile.url);
            if (response.ok) {
              plotlyData = await response.json();
            }
          } catch (error) {
            console.error('Failed to fetch visualization data:', error);
          }
        }
        
        return {
          id: m.id,
          role: m.message_type === 'user' ? 'user' : 'assistant',
          content: m.content,
          timestamp: new Date(m.timestamp),
          files: m.files,
          plotlyData: plotlyData,
        };
      }));
      
      // Only update if not currently processing (to avoid overwriting streaming messages)
      setSessions(prev => prev.map(s => {
        if (s.id === sessionId) {
          // Keep any local messages if we're processing
          const hasStreamingMessage = s.messages.some(m => m.isStreaming);
          return hasStreamingMessage ? s : { ...s, messages };
        }
        return s;
      }));
    } catch (error) {
      console.error('Failed to load messages:', error);
      toast.error('Failed to load messages');
    }
  };

  const createNewSession = useCallback(async () => {
    try {
      const newSession = await api.createSession('New Chat');
      const chatSession: ChatSession = {
        id: newSession.id,
        title: newSession.title,
        messages: [],
        createdAt: new Date(newSession.created_at),
        updatedAt: new Date(newSession.last_activity),
      };
      setSessions((prev) => [chatSession, ...prev]);
      setCurrentSessionId(newSession.id);
      return newSession.id;
    } catch (error) {
      console.error('Failed to create session:', error);
      toast.error('Failed to create session');
      return null;
    }
  }, []);

  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await api.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      setCurrentSessionId((current) => (current === sessionId ? null : current));
      toast.success('Session deleted');
    } catch (error) {
      console.error('Failed to delete session:', error);
      toast.error('Failed to delete session');
    }
  }, []);


  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!currentSessionId) {
        setPendingMessage(content);
        createNewSession();
        return;
      }

      const userMessage: Message = {
        id: `msg-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date(),
      };

      // Add user message
      setSessions((prev) =>
        prev.map((session) => {
          if (session.id === currentSessionId) {
            return {
              ...session,
              messages: [...session.messages, userMessage],
              updatedAt: new Date(),
            };
          }
          return session;
        }),
      );

      setIsProcessing(true);

      // Create assistant message placeholder
      const assistantMessageId = `msg-${Date.now() + 1}`;
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
        processingSteps: [],
      };

      setSessions((prev) =>
        prev.map((session) =>
          session.id === currentSessionId ? { ...session, messages: [...session.messages, assistantMessage] } : session,
        ),
      );

      // Start streaming
      const abort = api.streamMessage(
        currentSessionId,
        content,
        (event) => {
          // Log all events for debugging
          if (event.type !== 'content') {
            console.log('[Stream Event]', event.type, event);
          }
          
          setSessions((prev) =>
            prev.map((session) => {
              if (session.id !== currentSessionId) return session;
              
              return {
                ...session,
                messages: session.messages.map((msg) => {
                  if (msg.id !== assistantMessageId) return msg;
                  
                  const updatedMsg = { ...msg };
                  
                  if (event.type === 'content') {
                    updatedMsg.content += event.data;
                  } else if (event.type === 'thinking' || event.type === 'tool_call' || event.type === 'tool_response' || event.type === 'agent_switch') {
                    updatedMsg.processingSteps = [
                      ...(updatedMsg.processingSteps || []),
                      {
                        type: event.type,
                        message: event.data,
                        agent: event.agent,
                      }
                    ];
                  } else if (event.type === 'plotly_visualization') {
                    updatedMsg.plotlyData = event.plotly_json;
                  } else if (event.type === 'complete') {
                    updatedMsg.isStreaming = false;
                    updatedMsg.files = [];
                    if (event.csv_file_url) {
                      updatedMsg.files.push({
                        url: event.csv_file_url,
                        type: 'csv',
                        metadata: {}
                      });
                    }
                    if (event.visualization_url) {
                      updatedMsg.files.push({
                        url: event.visualization_url,
                        type: 'visualization',
                        metadata: {}
                      });
                    }
                  } else if (event.type === 'error') {
                    updatedMsg.isStreaming = false;
                    updatedMsg.content += '\n\n**Error:** ' + event.data;
                  }
                  
                  return updatedMsg;
                }),
              };
            }),
          );
        },
        (error) => {
          console.error('Streaming error:', error);
          toast.error('Failed to send message');
          setIsProcessing(false);
        },
        () => {
          setIsProcessing(false);
          
          // Refresh session title after a brief delay (title generation runs in parallel with response)
          const refreshTitle = async () => {
            try {
              const updatedSession = await api.getSession(currentSessionId);
              if (updatedSession && updatedSession.title !== 'New Chat') {
                setSessions(prev => prev.map(s => 
                  s.id === currentSessionId ? { ...s, title: updatedSession.title } : s
                ));
                return true; // Title updated
              }
              return false; // Title still "New Chat"
            } catch (error) {
              console.error('Failed to refresh session title:', error);
              return false;
            }
          };
          
          // First attempt at 1.5 seconds
          setTimeout(async () => {
            const updated = await refreshTitle();
            // If not updated yet, try again after 2 more seconds
            if (!updated) {
              setTimeout(refreshTitle, 2000);
            }
          }, 1500);
        }
      );

      abortControllerRef.current = abort;
    },
    [currentSessionId, createNewSession],
  );

  const handlePromptSelect = useCallback(
    (prompt: string) => {
      handleSendMessage(prompt);
    },
    [handleSendMessage],
  );

  return (
    <div className="flex h-screen w-full bg-background">
      <SessionSidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSessionSelect={setCurrentSessionId}
        onNewSession={createNewSession}
        onDeleteSession={deleteSession}
      />

      <div className="flex-1 flex flex-col">
        <ChatHeader />

        <div className="flex-1 overflow-hidden">
          {!currentSession || currentSession.messages.length === 0 ? (
            <LandingPrompts onSelectPrompt={handlePromptSelect} />
          ) : (
            <ScrollArea className="h-full" ref={scrollRef}>
              <div>
                {currentSession.messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        <ChatInput onSendMessage={handleSendMessage} disabled={isProcessing} />
      </div>
    </div>
  );
};

export default Index;
