import { ChevronDown } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Model } from '@/types/chat';

interface ModelSelectorProps {
  models: Model[];
  selectedModel: Model;
  onModelSelect: (model: Model) => void;
}

export function ModelSelector({ models, selectedModel, onModelSelect }: ModelSelectorProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="justify-between">
          <span className="text-sm">{selectedModel.name}</span>
          <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-80 bg-popover z-50" align="start">
        <DropdownMenuLabel>Select Model</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {models.map((model) => (
          <DropdownMenuItem
            key={model.id}
            onClick={() => onModelSelect(model)}
            className="cursor-pointer flex-col items-start py-3"
          >
            <div className="font-medium">{model.name}</div>
            <div className="text-xs text-muted-foreground mt-1">{model.description}</div>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
