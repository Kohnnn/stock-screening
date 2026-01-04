import React, { useState, useEffect } from 'react';

// API Base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

interface Officer {
    name: string;
    position: string;
    appoint_date?: string;
    ownership_ratio?: number;
}

interface CompanyProfileProps {
    symbol: string;
}

export function CompanyProfile({ symbol }: CompanyProfileProps) {
    const [officers, setOfficers] = useState<Officer[]>([]);
    const [loading, setLoading] = useState(true);
    const [overview, setOverview] = useState<string>('');

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                // Fetch Profile for Overview (if available from backend)
                // Note: main.py /api/data/profile/{symbol} seems to return general stock info + maybe more details
                const profileRes = await fetch(`${API_BASE_URL}/api/data/profile/${symbol}`);
                if (profileRes.ok) {
                    const data = await profileRes.json();
                    setOverview(data.overview || 'Chưa có thông tin giới thiệu về công ty này.');
                }

                // Fetch Officers
                const officersRes = await fetch(`${API_BASE_URL}/api/data/officers/${symbol}`);
                if (officersRes.ok) {
                    const data = await officersRes.json();
                    setOfficers(data.officers || []);
                }
            } catch (error) {
                console.error("Failed to fetch profile/officers:", error);
            } finally {
                setLoading(false);
            }
        };

        if (symbol) {
            fetchData();
        }
    }, [symbol]);

    return (
        <div className="company-profile space-y-6">
            {/* Overview Section */}
            <div className="glass-panel p-6 rounded-xl bg-gray-900/40 backdrop-blur-md border border-white/10">
                <h3 className="text-xl font-bold mb-4 text-white flex items-center gap-2">
                    <span>🏢</span> Giới thiệu công ty
                </h3>
                <div className="text-gray-300 leading-relaxed text-sm">
                    {loading ? (
                        <div className="animate-pulse h-20 bg-gray-700/50 rounded"></div>
                    ) : (
                        overview
                    )}
                </div>
            </div>

            {/* Officers Section */}
            <div className="glass-panel p-6 rounded-xl bg-gray-900/40 backdrop-blur-md border border-white/10">
                <h3 className="text-xl font-bold mb-4 text-white flex items-center gap-2">
                    <span>👥</span> Ban lãnh đạo
                </h3>

                {loading ? (
                    <div className="space-y-3">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="animate-pulse h-12 bg-gray-700/50 rounded flex"></div>
                        ))}
                    </div>
                ) : officers.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wider">
                                    <th className="p-3">Họ tên</th>
                                    <th className="p-3">Chức vụ</th>
                                    <th className="p-3 text-right">Sở hữu</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-800/50">
                                {officers.map((officer, idx) => (
                                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                                        <td className="p-3 font-medium text-white">{officer.name}</td>
                                        <td className="p-3 text-gray-300 text-sm">{officer.position}</td>
                                        <td className="p-3 text-right text-emerald-400 font-mono">
                                            {officer.ownership_ratio ? `${(officer.ownership_ratio * 100).toFixed(2)}%` : '-'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="text-gray-500 text-center py-4">Chưa có thông tin ban lãnh đạo</div>
                )}
            </div>
        </div>
    );
}

