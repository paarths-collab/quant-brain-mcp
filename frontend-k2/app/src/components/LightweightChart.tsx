
import {
    createChart,
    createSeriesMarkers,
    ColorType,
    CrosshairMode,
    type IChartApi,
    type ISeriesApi,
    type ISeriesMarkersPluginApi,
    LineStyle,
    LineSeries,
    CandlestickSeries,
    AreaSeries,
    HistogramSeries,
    type SeriesMarker,
} from 'lightweight-charts';
import React, { useEffect, useRef } from 'react';

interface ChartProps {
    data: {
        candleData: any[];
        volumeData?: any[];
        lineData?: any[];
        markers?: any[];
        areaData?: any[]; // For area charts (simple price)
    };
    chartType?: 'candle' | 'line' | 'area';
    colors?: {
        backgroundColor?: string;
        textColor?: string;
        upColor?: string;
        downColor?: string;
        gridColor?: string;
        accentColor?: string; // Used for line/area charts + overlays
    };
    height?: number;
}

const hexToRgba = (hex: string, alpha: number) => {
    const h = hex.replace('#', '').trim();
    if (h.length !== 6) return `rgba(255, 255, 255, ${alpha})`;
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

export const LightweightChart: React.FC<ChartProps> = ({
    data,
    chartType = 'candle',
    colors = {
        backgroundColor: 'transparent',
        textColor: '#D9D9D9',
        upColor: '#26a69a',
        downColor: '#ef5350',
        gridColor: 'rgba(255, 255, 255, 0.06)', // Very subtle grid
    },
    height = 400
}) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | ISeriesApi<"Area"> | ISeriesApi<"Line"> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const handleResize = () => {
            chartRef.current?.applyOptions({ width: chartContainerRef.current!.clientWidth });
        };

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: colors.backgroundColor },
                textColor: colors.textColor,
            },
            width: chartContainerRef.current.clientWidth,
            height: height,
            grid: {
                vertLines: { color: colors.gridColor },
                horzLines: { color: colors.gridColor },
            },
            crosshair: {
                mode: CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: colors.gridColor,
            },
            timeScale: {
                borderColor: colors.gridColor,
                timeVisible: true,
            },
        });

        chartRef.current = chart;

        const accent = colors.accentColor || colors.upColor || '#2962FF';
        const accentTop = accent.startsWith('#') ? hexToRgba(accent, 0.35) : 'rgba(41, 98, 255, 0.35)';
        const accentBottom = accent.startsWith('#') ? hexToRgba(accent, 0.0) : 'rgba(41, 98, 255, 0.0)';

        // --- Main Series (Candle or Area/Line) ---
        let mainSeries;
        if (chartType === 'candle') {
            mainSeries = chart.addSeries(CandlestickSeries, {
                upColor: colors.upColor,
                downColor: colors.downColor,
                borderVisible: false,
                wickUpColor: colors.upColor,
                wickDownColor: colors.downColor,
            });
            mainSeries.setData(data.candleData);
        } else if (chartType === 'line') {
            mainSeries = chart.addSeries(LineSeries, {
                color: accent,
                lineWidth: 2,
            });
            const simpleData = data.areaData || data.candleData.map((d: any) => ({ time: d.time, value: d.close }));
            mainSeries.setData(simpleData);
        } else {
            // Area Chart
            mainSeries = chart.addSeries(AreaSeries, {
                lineColor: accent,
                topColor: accentTop,
                bottomColor: accentBottom,
            });
            const simpleData = data.areaData || data.candleData.map((d: any) => ({ time: d.time, value: d.close }));
            mainSeries.setData(simpleData);
        }

        seriesRef.current = mainSeries;

        // --- Volume Series ---
        if (data.volumeData && data.volumeData.length > 0) {
            const volumeSeries = chart.addSeries(HistogramSeries, {
                color: colors.accentColor || '#26a69a',
                priceFormat: {
                    type: 'volume',
                },
                priceScaleId: '', // Overlay on main chart but scaled separately? Or separate pane? 
                // For simple overlay, we can use a separate scale or 'overlay' property
            });

            // Separate pane for volume (scale margins)
            volumeSeries.priceScale().applyOptions({
                scaleMargins: {
                    top: 0.8, // Highest volume bar is at 80% from top (bottom 20%)
                    bottom: 0,
                },
            });

            volumeSeries.setData(data.volumeData);
            volumeSeriesRef.current = volumeSeries;
        }

        // --- Markers (Signals) ---
        let markersPlugin: ISeriesMarkersPluginApi<any> | null = null;
        if (data.markers && data.markers.length > 0) {
            // Accept either:
            // 1) Pre-formatted Lightweight Charts markers: { time, position, color, shape, text }
            // 2) Raw trade signals: { date|time, type: BUY|SELL, price }
            const first = data.markers[0] as any;

            const isPreformatted =
                typeof first?.time !== 'undefined' &&
                typeof first?.position === 'string' &&
                typeof first?.shape === 'string';

            const lwMarkers: SeriesMarker<any>[] = isPreformatted
                ? (data.markers as any)
                : data.markers.map((m: any) => {
                    const t = (m.time || m.date || '').toString();
                    const time = t.includes('T') ? t.split('T')[0] : t; // Ensure YYYY-MM-DD
                    const type = (m.type || '').toString().toUpperCase();
                    const price = Number(m.price);
                    return {
                        time,
                        position: type === 'BUY' ? 'belowBar' : 'aboveBar',
                        color: type === 'BUY' ? '#00E676' : '#FF1744',
                        shape: type === 'BUY' ? 'arrowUp' : 'arrowDown',
                        text: price ? `${type} @ ${price.toFixed(2)}` : `${type}`,
                    };
                });

            markersPlugin = createSeriesMarkers(mainSeries, lwMarkers);
        }

        // --- Extra Lines (Indicators) ---
        if (data.lineData) {
            // Expecting lineData to be array of { name, data, color }
            // We'll treat 'data.lineData' as an ARRAY of line series configs
            // For backward compatibility or if passed as flat object, we handle it.

            // If data.lineData is array of series objects
            if (Array.isArray(data.lineData)) {
                data.lineData.forEach((line: any) => {
                    const lineSeries = chart.addSeries(LineSeries, {
                        color: line.color || colors.accentColor || '#F57F17',
                        lineWidth: 2,
                        priceScaleId: 'right', // Share scale?
                        lineStyle: LineStyle.Solid,
                    });
                    lineSeries.setData(line.data);
                });
            }
        }

        chart.timeScale().fitContent();

        window.addEventListener('resize', handleResize);
        
        // Use ResizeObserver to detect container size changes (e.g., when Analytics Terminal expands)
        let resizeObserver: ResizeObserver | null = null;
        
        if (chartContainerRef.current) {
            resizeObserver = new ResizeObserver(() => {
                requestAnimationFrame(handleResize);
            });
            resizeObserver.observe(chartContainerRef.current);
        }

        return () => {
            window.removeEventListener('resize', handleResize);
            if (resizeObserver && chartContainerRef.current) {
                resizeObserver.unobserve(chartContainerRef.current);
                resizeObserver.disconnect();
            }
            markersPlugin?.detach();
            chart.remove();
        };
    }, [data, chartType, colors, height]);

    // Lightweight Charts requires the container to have a non-zero height.
    return <div ref={chartContainerRef} className="w-full relative" style={{ height }} />;
};
