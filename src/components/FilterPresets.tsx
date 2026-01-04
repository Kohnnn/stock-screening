import React, { useState, useEffect } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { StockFilters } from '../types';

interface FilterPresetsProps {
    currentFilters: StockFilters;
    onLoadPreset: (preset: StockFilters) => void;
}

interface Preset {
    id: string;
    name: string;
    filters: StockFilters;
}

export function FilterPresets({ currentFilters, onLoadPreset }: FilterPresetsProps) {
    const { t } = useLanguage();
    const [presets, setPresets] = useState<Preset[]>([]);
    const [isCreating, setIsCreating] = useState(false);
    const [newPresetName, setNewPresetName] = useState('');

    // Load presets from localStorage on mount
    useEffect(() => {
        const saved = localStorage.getItem('screener_presets');
        if (saved) {
            try {
                setPresets(JSON.parse(saved));
            } catch (e) {
                console.error('Failed to parse presets', e);
            }
        }
    }, []);

    const savePresets = (newPresets: Preset[]) => {
        setPresets(newPresets);
        localStorage.setItem('screener_presets', JSON.stringify(newPresets));
    };

    const handleCreate = () => {
        if (!newPresetName.trim()) return;
        const newPreset: Preset = {
            id: Date.now().toString(),
            name: newPresetName.trim(),
            filters: { ...currentFilters } // Clone current filters
        };
        savePresets([...presets, newPreset]);
        setNewPresetName('');
        setIsCreating(false);
    };

    const handleDelete = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (window.confirm('Delete this preset?')) {
            savePresets(presets.filter(p => p.id !== id));
        }
    };

    return (
        <div className="mb-4 pb-4 border-b border-base-300">
            <div className="flex justify-between items-center mb-2">
                <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Presets</h4>
                {!isCreating && (
                    <button
                        className="text-xs text-primary hover:text-primary-focus"
                        onClick={() => setIsCreating(true)}
                    >
                        + Save
                    </button>
                )}
            </div>

            {isCreating && (
                <div className="mb-2 flex gap-1">
                    <input
                        type="text"
                        className="form-input text-sm py-1 px-2"
                        placeholder="Preset name..."
                        value={newPresetName}
                        onChange={(e) => setNewPresetName(e.target.value)}
                        autoFocus
                        onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                    />
                    <button className="btn btn-xs btn-primary" onClick={handleCreate}>✓</button>
                    <button className="btn btn-xs btn-ghost" onClick={() => setIsCreating(false)}>✕</button>
                </div>
            )}

            <div className="flex flex-col gap-1 max-h-40 overflow-y-auto custom-scrollbar">
                {presets.length === 0 ? (
                    <div className="text-xs text-gray-500 italic py-1">No saved presets</div>
                ) : (
                    presets.map(preset => (
                        <div
                            key={preset.id}
                            className="flex justify-between items-center p-2 rounded hover:bg-base-300 cursor-pointer group text-sm"
                            onClick={() => onLoadPreset(preset.filters)}
                        >
                            <span className="truncate">{preset.name}</span>
                            <button
                                className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-500 transition-opacity"
                                onClick={(e) => handleDelete(preset.id, e)}
                                title="Delete preset"
                            >
                                ✕
                            </button>
                        </div>
                    ))
                )}
            </div>

            {/* Default Presets (Hardcoded examples) */}
            <div className="mt-2 text-xs text-gray-500">
                <div className="uppercase tracking-wider font-semibold mb-1 mt-2">Recommended</div>
                <div
                    className="p-2 rounded hover:bg-base-300 cursor-pointer text-sm"
                    onClick={() => onLoadPreset({ peMax: 15, roeMin: 15, marketCapMin: 1000 })}
                >
                    💎 Value & Growth
                </div>
                <div
                    className="p-2 rounded hover:bg-base-300 cursor-pointer text-sm"
                    onClick={() => onLoadPreset({ rsiMin: 30, rsiMax: 45, stockTrend: 'uptrend' })}
                >
                    📉 Oversold Uptrend
                </div>
                <div
                    className="p-2 rounded hover:bg-base-300 cursor-pointer text-sm"
                    onClick={() => onLoadPreset({ stockTrend: 'breakout', adtvValueMin: 1 })}
                >
                    🚀 Breakout Volume
                </div>
            </div>
        </div>
    );
}
