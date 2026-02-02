import { User, Bot, Download, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Message } from '@/types/chat';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { PlotlyVisualization } from './PlotlyVisualization';
import { Button } from '@/components/ui/button';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [showAllSteps, setShowAllSteps] = useState(false);

  if (isUser) {
    return (
      <div className="px-4 py-4 animate-fade-in">
        <div className="max-w-3xl mx-auto flex justify-end gap-4">
          <div className="flex-1 flex flex-col items-end">
            <div className="text-base whitespace-pre-wrap text-right text-white bg-gradient-to-br from-blue-500 to-blue-600 px-5 py-3 rounded-2xl shadow-[0_2px_12px_0_rgb(59_130_246_/0.25)] max-w-[85%]">
              {message.content}
            </div>
            <div className="text-xs text-muted-foreground mt-1.5">
              {message.timestamp.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>
          </div>
          <Avatar className="h-8 w-8 shrink-0">
            <AvatarFallback className="bg-primary shadow-md">
              <User className="h-4 w-4 text-primary-foreground" />
            </AvatarFallback>
          </Avatar>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 animate-fade-in">
      <div className="max-w-3xl mx-auto flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-muted">
            <Bot className="h-4 w-4 text-foreground" />
          </AvatarFallback>
        </Avatar>

        <div className="flex-1 space-y-2 overflow-hidden">
          <span className="text-sm font-semibold">Assistant</span>

          {message.processingSteps && message.processingSteps.length > 0 && (
            <div className="mb-3">
              {/* Current step - always visible */}
              <div className="flex items-center gap-2 bg-muted/30 px-3 py-1.5 rounded-lg border border-border/30">
                {message.isStreaming && (
                  <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
                )}
                <span className="text-xs text-muted-foreground font-medium flex-1">
                  {message.processingSteps[message.processingSteps.length - 1]?.message}
                </span>
                
                {/* Toggle button for previous steps */}
                {message.processingSteps.length > 1 && (
                  <button
                    onClick={() => setShowAllSteps(!showAllSteps)}
                    className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors shrink-0 group"
                    aria-label={showAllSteps ? "Hide previous steps" : "Show previous steps"}
                  >
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-muted group-hover:bg-muted/70 transition-colors">
                      {message.processingSteps.length - 1}
                    </span>
                    {showAllSteps ? (
                      <ChevronUp className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5" />
                    )}
                  </button>
                )}
              </div>

              {/* Previous steps - collapsible */}
              {showAllSteps && message.processingSteps.length > 1 && (
                <div className="mt-1.5 space-y-1.5 pl-3 border-l-2 border-border/30 ml-1.5 animate-slide-in">
                  {message.processingSteps.slice(0, -1).map((step, idx) => (
                    <div
                      key={idx}
                      className="text-xs text-muted-foreground/70 px-3 py-1 rounded bg-muted/20 hover:bg-muted/30 transition-colors"
                    >
                      {step.message}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {message.content && (
            <div className="bg-muted/50 border border-border/50 px-5 py-4 rounded-2xl shadow-[0_2px_8px_0_rgb(0_0_0_/0.04)] backdrop-blur-sm">
              <div className="prose-chat max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code(props) {
                      const { children, className, ...rest } = props;
                      const match = /language-(\w+)/.exec(className || '');
                      return match ? (
                        <div className="rounded-lg overflow-hidden my-4 shadow-sm">
                          <SyntaxHighlighter
                            style={vscDarkPlus as any}
                            language={match[1]}
                            PreTag="div"
                            customStyle={{
                              margin: 0,
                              borderRadius: '0.5rem',
                              fontSize: '0.875rem',
                              padding: '1rem',
                            }}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        </div>
                      ) : (
                        <code className={className} {...rest}>
                          {children}
                        </code>
                      );
                    },
                    p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                    ul: ({ children }) => <ul className="space-y-1.5 my-3">{children}</ul>,
                    ol: ({ children }) => <ol className="space-y-1.5 my-3">{children}</ol>,
                    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                    h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-3 first:mt-0">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-lg font-semibold mt-4 mb-2 first:mt-0">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-base font-semibold mt-3 mb-2 first:mt-0">{children}</h3>,
                    blockquote: ({ children }) => (
                      <blockquote className="border-l-4 border-primary/50 pl-4 py-1 my-3 italic text-muted-foreground bg-primary/5 rounded-r">
                        {children}
                      </blockquote>
                    ),
                    table: ({ children }) => (
                      <div className="overflow-x-auto my-4 rounded-lg border border-border">
                        <table className="min-w-full divide-y divide-border">{children}</table>
                      </div>
                    ),
                    thead: ({ children }) => <thead className="bg-muted/70">{children}</thead>,
                    tbody: ({ children }) => <tbody className="divide-y divide-border bg-background/50">{children}</tbody>,
                    tr: ({ children }) => <tr className="hover:bg-muted/30 transition-colors">{children}</tr>,
                    th: ({ children }) => <th className="px-4 py-3 text-left text-sm font-semibold">{children}</th>,
                    td: ({ children }) => <td className="px-4 py-3 text-sm">{children}</td>,
                    a: ({ children, href }) => (
                      <a href={href} className="text-primary hover:text-primary/80 underline-offset-2 hover:underline font-medium" target="_blank" rel="noopener noreferrer">
                        {children}
                      </a>
                    ),
                    strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {message.plotlyData && (
            <PlotlyVisualization data={message.plotlyData} />
          )}

          {message.files && message.files.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {message.files.map((file, idx) => (
                <Button
                  key={idx}
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(file.url, '_blank')}
                  className="flex items-center gap-2"
                >
                  <Download className="h-3 w-3" />
                  {file.type === 'csv' ? 'Download CSV' : 'View Chart'}
                </Button>
              ))}
            </div>
          )}

          <div className="text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>

          {message.isStreaming && (
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0.2s]" />
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0.4s]" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
