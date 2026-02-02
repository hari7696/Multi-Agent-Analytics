import { useState, useRef, useEffect, memo } from 'react';
import { Send, Paperclip } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

function ChatInputComponent({ onSendMessage, disabled }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  const handleSubmit = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border bg-background/80 backdrop-blur-sm p-4">
      <div className="max-w-3xl mx-auto">
        <div className="relative flex items-end space-x-2">
          <Button variant="ghost" size="icon" className="shrink-0 mb-2 hover:bg-primary/10 transition-colors">
            <Paperclip className="h-5 w-5" />
          </Button>

          <div className="flex-1 relative">
            <Textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              disabled={disabled}
              className="min-h-[60px] max-h-[200px] resize-none pr-12 border-2 focus-visible:border-primary/50 transition-colors shadow-sm"
              rows={1}
            />
            <Button
              onClick={handleSubmit}
              disabled={!message.trim() || disabled}
              size="icon"
              className="absolute bottom-2 right-2 h-8 w-8 shadow-md hover:shadow-lg transition-shadow"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="text-xs text-muted-foreground mt-2 text-center">
          Press Enter to send, Shift + Enter for new line
        </div>
      </div>
    </div>
  );
}

export const ChatInput = memo(ChatInputComponent);
