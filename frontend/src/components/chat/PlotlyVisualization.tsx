import { memo, useEffect, useRef, useState } from 'react';
// @ts-ignore
import Plotly from 'plotly.js-dist-min';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface PlotlyVisualizationProps {
  data: any;
}

function PlotlyVisualizationComponent({ data }: PlotlyVisualizationProps) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!data) {
      setError('No visualization data provided');
      setIsLoading(false);
      return;
    }

    if (plotRef.current) {
      try {
        setIsLoading(true);
        setError(null);
        
        // Parse data if it's a string
        const plotlyData = typeof data === 'string' ? JSON.parse(data) : data;
        
        // Validate plotly data structure
        if (!plotlyData || typeof plotlyData !== 'object') {
          throw new Error('Invalid Plotly data format');
        }
        
        const plotData = plotlyData.data || [];
        const plotLayout = plotlyData.layout || {};
        
        if (!Array.isArray(plotData) || plotData.length === 0) {
          throw new Error('No plot data available');
        }
        
        // Create the plot
        Plotly.newPlot(
          plotRef.current,
          plotData,
          plotLayout,
          { 
            responsive: true,
            displayModeBar: true,
            displaylogo: false
          }
        );
        
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to render Plotly chart:', error);
        setError(error instanceof Error ? error.message : 'Failed to render visualization');
        setIsLoading(false);
      }
    }
    
    return () => {
      if (plotRef.current) {
        try {
          Plotly.purge(plotRef.current);
        } catch (e) {
          // Ignore cleanup errors
        }
      }
    };
  }, [data]);

  if (error) {
    return (
      <div className="my-4">
        <Alert variant="destructive">
          <AlertDescription>
            ⚠️ Visualization Error: {error}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="my-4 p-4 border border-border rounded-lg bg-background">
      {isLoading && (
        <div className="flex items-center justify-center" style={{ minHeight: '400px' }}>
          <div className="text-muted-foreground">Loading visualization...</div>
        </div>
      )}
      <div 
        ref={plotRef} 
        className="w-full" 
        style={{ minHeight: '400px', display: isLoading ? 'none' : 'block' }} 
      />
    </div>
  );
}

export const PlotlyVisualization = memo(PlotlyVisualizationComponent);

