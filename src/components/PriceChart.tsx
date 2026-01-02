/**
 * Price Chart Component using Chart.js
 */
import React, { useEffect, useState, useRef } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

interface PriceData {
    date: string;
    open_price: number;
    high_price: number;
    low_price: number;
    close_price: number;
    volume: number;
}

interface PriceChartProps {
    symbol: string;
    height?: number;
    showVolume?: boolean;
}

export function PriceChart({ symbol, height = 300, showVolume = false }: PriceChartProps) {
    const [history, setHistory] = useState<PriceData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchHistory = async () => {
            setLoading(true);
            setError(null);

            try {
                const res = await fetch(`http://localhost:8000/api/stocks/${symbol}/history?days=30`);
                if (!res.ok) {
                    throw new Error(`Failed to fetch history: ${res.status}`);
                }
                const data = await res.json();
                // Reverse to show oldest first
                setHistory((data.history || []).reverse());
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to fetch data');
            } finally {
                setLoading(false);
            }
        };

        if (symbol) {
            fetchHistory();
        }
    }, [symbol]);

    if (loading) {
        return (
            <div style={{
                height,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-secondary)'
            }}>
                Loading chart...
            </div>
        );
    }

    if (error || history.length === 0) {
        return (
            <div style={{
                height,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-secondary)'
            }}>
                {error || 'No price history available'}
            </div>
        );
    }

    const labels = history.map(h => {
        const date = new Date(h.date);
        return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
    });

    const prices = history.map(h => h.close_price);
    const volumes = history.map(h => h.volume);

    // Determine if price went up or down
    const firstPrice = prices[0] || 0;
    const lastPrice = prices[prices.length - 1] || 0;
    const priceUp = lastPrice >= firstPrice;

    const chartColor = priceUp ? 'rgb(16, 185, 129)' : 'rgb(239, 68, 68)';
    const chartColorLight = priceUp ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';

    const data = {
        labels,
        datasets: [
            {
                label: `${symbol} Price`,
                data: prices,
                borderColor: chartColor,
                backgroundColor: chartColorLight,
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                pointHoverRadius: 4,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false,
            },
            tooltip: {
                mode: 'index' as const,
                intersect: false,
                callbacks: {
                    label: (context: any) => {
                        const value = context.parsed.y;
                        return `Price: ${value.toLocaleString('vi-VN')} ₫`;
                    },
                },
            },
        },
        scales: {
            x: {
                grid: {
                    display: false,
                },
                ticks: {
                    maxTicksLimit: 7,
                    color: 'var(--text-secondary)',
                },
            },
            y: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.1)',
                },
                ticks: {
                    color: 'var(--text-secondary)',
                    callback: (value: any) => `${value.toLocaleString()} ₫`,
                },
            },
        },
        interaction: {
            mode: 'nearest' as const,
            axis: 'x' as const,
            intersect: false,
        },
    };

    return (
        <div style={{ height }}>
            <Line data={data} options={options} />
        </div>
    );
}

export default PriceChart;
