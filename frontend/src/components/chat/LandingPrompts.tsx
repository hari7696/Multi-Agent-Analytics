import { Lightbulb, Code, Search, Sparkles } from 'lucide-react';
import { memo } from 'react';
import { Card } from '@/components/ui/card';
import { PromptSuggestion } from '@/types/chat';

const suggestions: PromptSuggestion[] = [
  {
    icon: 'search',
    title: 'Sales Analytics',
    description: 'Analyze customer revenue and performance',
    prompt: 'Show me top 10 customers by revenue in 2023',
  },
  {
    icon: 'code',
    title: 'Inventory Management',
    description: 'Monitor product stock levels',
    prompt: 'Which products have low inventory below 100 units?',
  },
  {
    icon: 'lightbulb',
    title: 'Vendor Performance',
    description: 'Track supplier quality metrics',
    prompt: 'Show me vendor quality metrics and rejection rates',
  },
  {
    icon: 'sparkles',
    title: 'HR Insights',
    description: 'Analyze employee compensation',
    prompt: 'Compare average pay rates between departments',
  },
];

const iconMap = {
  lightbulb: Lightbulb,
  code: Code,
  search: Search,
  sparkles: Sparkles,
};

interface LandingPromptsProps {
  onSelectPrompt: (prompt: string) => void;
}

function LandingPromptsComponent({ onSelectPrompt }: LandingPromptsProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8 bg-gradient-to-b from-primary/5 to-background">
      <div className="max-w-4xl w-full space-y-8">
        <div className="text-center space-y-4 mb-12 animate-fade-in">
          <div className="flex items-center justify-center mb-4">
            <div className="flex items-center justify-center h-16 w-16 rounded-2xl bg-primary shadow-lg animate-scale-in">
              <Sparkles className="h-8 w-8 text-primary-foreground" />
            </div>
          </div>
          <h1 className="text-5xl font-bold">Business Intelligence Hub</h1>
          <p className="text-lg text-muted-foreground">
            Your AI-powered assistant for Adventure Works analytics
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {suggestions.map((suggestion, index) => {
            const Icon = iconMap[suggestion.icon as keyof typeof iconMap];
            return (
              <Card
                key={suggestion.title}
                className="p-6 cursor-pointer border-border/50 hover:border-primary/30 transition-all duration-300 group shadow-[0_2px_8px_0_rgb(0_0_0_/0.04)] hover:shadow-[0_8px_16px_0_rgb(0_0_0_/0.08)] hover:-translate-y-1 animate-fade-in"
                style={{ animationDelay: `${index * 100}ms` }}
                onClick={() => onSelectPrompt(suggestion.prompt)}
              >
                <div className="flex items-start space-x-4">
                  <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-all duration-300 group-hover:scale-110">
                    <Icon className="h-6 w-6 text-primary" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold mb-1 group-hover:text-primary transition-colors">{suggestion.title}</h3>
                    <p className="text-sm text-muted-foreground">{suggestion.description}</p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export const LandingPrompts = memo(LandingPromptsComponent);
