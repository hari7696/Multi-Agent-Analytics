import { useState, memo, useRef, useEffect } from 'react';
import { MessageSquarePlus, ChevronLeft, Trash2, Search, PanelLeftOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { ChatSession } from '@/types/chat';

interface SessionSidebarProps {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
  onDeleteSession: (sessionId: string) => void;
}

function SessionSidebarComponent({
  sessions,
  currentSessionId,
  onSessionSelect,
  onNewSession,
  onDeleteSession,
}: SessionSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [width, setWidth] = useState(256); // Default 256px (w-64)
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = useRef<HTMLDivElement>(null);

  const filteredSessions = sessions.filter(session =>
    session.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Handle resize
  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!sidebarRef.current) return;
      const newWidth = e.clientX;
      if (newWidth >= 200 && newWidth <= 500) {
        setWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  return (
    <>
      {/* Global cursor style when resizing */}
      {isResizing && (
        <style>{`* { cursor: col-resize !important; user-select: none !important; }`}</style>
      )}
      
      {/* Collapsed state - show open button */}
      {isCollapsed && (
        <div className="h-full flex items-start pt-4 pl-1 pr-2 border-r border-border bg-sidebar">
          <Button
            onClick={() => setIsCollapsed(false)}
            variant="ghost"
            size="icon"
            className="shrink-0"
            title="Open sidebar"
          >
            <PanelLeftOpen className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Sidebar */}
      <div
        ref={sidebarRef}
        className={cn(
          'h-full border-r border-border bg-sidebar flex flex-col relative transition-none',
          isCollapsed && 'hidden'
        )}
        style={{ width: isCollapsed ? 0 : `${width}px` }}
      >
      <div className="flex items-center justify-between p-4 border-b border-border">
        {!isCollapsed && (
          <Button onClick={onNewSession} variant="default" size="sm" className="flex-1 mr-2">
            <MessageSquarePlus className="h-4 w-4 mr-2" />
            New Chat
          </Button>
        )}
        <Button
          onClick={() => setIsCollapsed(!isCollapsed)}
          variant="ghost"
          size="icon"
          className="shrink-0"
          title="Collapse sidebar"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      </div>

      {!isCollapsed && (
        <>
          <div className="p-2 border-b border-border">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search sessions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 h-9"
              />
            </div>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1 w-full">
              {filteredSessions.map((session) => (
              <div
                key={session.id}
                className={cn(
                  'group relative p-3 rounded-lg cursor-pointer transition-colors w-full overflow-hidden',
                  currentSessionId === session.id
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'hover:bg-sidebar-accent/50'
                )}
                onClick={() => onSessionSelect(session.id)}
              >
                <div className="pr-10 w-full overflow-hidden">
                  <div className="text-sm font-medium truncate w-full">
                    {session.title}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5 truncate">
                    {session.updatedAt.toLocaleDateString()}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "absolute right-1 top-2 h-7 w-7 transition-opacity",
                    currentSessionId === session.id 
                      ? "opacity-100" 
                      : "opacity-0 group-hover:opacity-100"
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
              ))}
            </div>
          </ScrollArea>
        </>
      )}
      
      {/* Resize handle */}
      <div
        className={cn(
          "absolute -right-1 top-0 bottom-0 w-2 cursor-col-resize hover:bg-primary/30 active:bg-primary/50 transition-colors group",
          isResizing && "bg-primary/50"
        )}
        onMouseDown={() => setIsResizing(true)}
        title="Drag to resize"
      >
        <div className="absolute right-0 top-0 bottom-0 w-0.5 bg-border group-hover:bg-primary/50 transition-colors" />
      </div>
    </div>
    </>
  );
}

export const SessionSidebar = memo(SessionSidebarComponent);
