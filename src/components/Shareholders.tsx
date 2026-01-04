import React, { useState, useEffect } from 'react';

// API Base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

interface Shareholder {
    name: string;
    share_count: number;
    percentage: number;
    type?: string; // 'individual', 'organization', 'foreign'
}

interface ShareholdersProps {
    symbol: string;
}

export function Shareholders({ symbol }: ShareholdersProps) {
    const [shareholders, setShareholders] = useState<Shareholder[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchShareholders = async () => {
            setLoading(true);
            try {
                const res = await fetch(`${API_BASE_URL}/api/data/shareholders/${symbol}`);
                if (res.ok) {
                    const data = await res.json();
                    setShareholders(data.shareholders || []);
                }
            } catch (error) {
                console.error("Failed to fetch shareholders:", error);
            } finally {
                setLoading(false);
            }
        };

        if (symbol) fetchShareholders();
    }, [symbol]);

    return (
        <div className="shareholders space-y-6">
            <div className="glass-panel p-6 rounded-xl bg-gray-900/40 backdrop-blur-md border border-white/10">
                <h3 className="text-xl font-bold mb-4 text-white flex items-center gap-2">
                    <span>💎</span> Danh sách cổ đông
                </h3>

                {loading ? (
                    <div className="space-y-3">
                        {[1, 2, 3, 4].map(i => (
                            <div key={i} className="animate-pulse h-12 bg-gray-700/50 rounded"></div>
                        ))}
                    </div>
                ) : shareholders.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wider">
                                    <th className="p-3">Cổ đông</th>
                                    <th className="p-3 text-right">Số lượng</th>
                                    <th className="p-3 text-right">Tỷ lệ</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-800/50">
                                {shareholders.map((sh, idx) => (
                                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                                        <td className="p-3 font-medium text-white">{sh.name}</td>
                                        <td className="p-3 text-right text-gray-300 font-mono">
                                            {sh.share_count.toLocaleString()}
                                        </td>
                                        <td className="p-3 text-right text-emerald-400 font-mono font-bold">
                                            {(sh.percentage * 100).toFixed(2)}%
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="text-center text-gray-500 py-8">
                        Chưa có dữ liệu cổ đông cho mã {symbol}
                    </div>
                )}
            </div>

            {/* Optional: Add a helper summary or chart later */}
        </div>
    );
}
