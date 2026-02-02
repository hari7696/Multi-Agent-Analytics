import { useState } from 'react';
import { ChevronRight, ChevronDown, Loader2, CheckCircle2 } from 'lucide-react';
import { ToolCall } from '@/types/chat';
import { cn } from '@/lib/utils';

interface ToolCallDisplayProps {
  toolCalls: ToolCall[];
}

export function ToolCallDisplay({ toolCalls }: ToolCallDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!toolCalls || toolCalls.length === 0) return null;

  const latestToolCall = toolCalls[toolCalls.length - 1];
  const hasRunning = toolCalls.some((tc) => tc.status === 'running');

  return (
    <div className="mb-4 border border-border rounded-lg overflow-hidden bg-muted/50">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-muted transition-colors text-left"
      >
        <div className="flex items-center space-x-2">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          <span className="text-sm font-medium">
            {latestToolCall.name} {toolCalls.length > 1 && `(+${toolCalls.length - 1} more)`}
          </span>
          {hasRunning ? (
            <span className="flex items-center text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              Running...
            </span>
          ) : (
            <span className="flex items-center text-xs text-muted-foreground">
              <CheckCircle2 className="h-3 w-3 mr-1 text-primary" />
              Completed
            </span>
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-border">
          {toolCalls.map((toolCall, index) => (
            <div key={toolCall.id} className="p-4 border-b border-border last:border-b-0">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono bg-muted px-2 py-1 rounded">
                    #{index + 1}
                  </span>
                  <span className="text-sm font-medium">{toolCall.name}</span>
                </div>
                <span
                  className={cn(
                    'text-xs px-2 py-1 rounded',
                    toolCall.status === 'running'
                      ? 'bg-primary/10 text-primary'
                      : 'bg-muted text-muted-foreground'
                  )}
                >
                  {toolCall.status}
                </span>
              </div>

              <div className="space-y-2">
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">Arguments:</div>
                  <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                    {JSON.stringify(toolCall.arguments, null, 2)}
                  </pre>
                </div>

                {toolCall.result && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1">Result:</div>
                    <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                      {JSON.stringify(toolCall.result, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
