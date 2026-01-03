/**
 * Filter Presets Component
 * 
 * Allows users to save, load, rename, and delete filter presets.
 * Presets are stored in localStorage as JSON.
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface StockFilters {
    exchange?: 'HOSE' | 'HNX' | 'UPCOM' | '';
    sector?: string;
    industry?: string;
    search?: string;
    marketCapMin?: number;
    marketCapMax?: number;
    priceMin?: number;
    priceMax?: number;
    priceChangeMin?: number;
    priceChangeMax?: number;
    adtvValueMin?: number;
    rsiMin?: number;
    rsiMax?: number;
    rsMin?: number;
    rsMax?: number;
    priceVsSma20Min?: number;
    priceVsSma20Max?: number;
    macdHistogramMin?: number;
    macdHistogramMax?: number;
    stockTrend?: string;
    priceReturn1mMin?: number;
    peMin?: number;
    peMax?: number;
    pbMin?: number;
    pbMax?: number;
    roeMin?: number;
    roeMax?: number;
    revenueGrowthMin?: number;
    npatGrowthMin?: number;
    netMarginMin?: number;
    grossMarginMin?: number;
    dividendYieldMin?: number;
}

interface FilterPreset {
    id: string;
    name: string;
    filters: StockFilters;
    createdAt: string;
    updatedAt: string;
}

// Storage key
const PRESETS_STORAGE_KEY = 'vnstock-filter-presets';

// Generate unique ID
const generateId = () => Math.random().toString(36).substr(2, 9);

// Load presets from localStorage
export function loadPresets(): FilterPreset[] {
    try {
        const stored = localStorage.getItem(PRESETS_STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch {
        return [];
    }
}

// Save presets to localStorage
export function savePresets(presets: FilterPreset[]): void {
    try {
        localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(presets));
    } catch (e) {
        console.error('Failed to save presets:', e);
    }
}

// Hook for managing presets
export function useFilterPresets() {
    const [presets, setPresets] = useState<FilterPreset[]>([]);
    const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);

    // Load on mount
    useEffect(() => {
        setPresets(loadPresets());
    }, []);

    // Save preset
    const savePreset = useCallback((name: string, filters: StockFilters) => {
        const now = new Date().toISOString();
        const newPreset: FilterPreset = {
            id: generateId(),
            name,
            filters,
            createdAt: now,
            updatedAt: now,
        };

        setPresets(prev => {
            const updated = [newPreset, ...prev];
            savePresets(updated);
            return updated;
        });

        return newPreset;
    }, []);

    // Update existing preset
    const updatePreset = useCallback((id: string, updates: Partial<FilterPreset>) => {
        setPresets(prev => {
            const updated = prev.map(p =>
                p.id === id
                    ? { ...p, ...updates, updatedAt: new Date().toISOString() }
                    : p
            );
            savePresets(updated);
            return updated;
        });
    }, []);

    // Delete preset
    const deletePreset = useCallback((id: string) => {
        setPresets(prev => {
            const updated = prev.filter(p => p.id !== id);
            savePresets(updated);
            return updated;
        });
        if (selectedPresetId === id) {
            setSelectedPresetId(null);
        }
    }, [selectedPresetId]);

    // Get selected preset
    const selectedPreset = presets.find(p => p.id === selectedPresetId) || null;

    return {
        presets,
        selectedPreset,
        selectedPresetId,
        setSelectedPresetId,
        savePreset,
        updatePreset,
        deletePreset,
    };
}

// Filter Presets UI Component
interface FilterPresetsProps {
    currentFilters: StockFilters;
    onLoadPreset: (filters: StockFilters) => void;
}

export function FilterPresets({ currentFilters, onLoadPreset }: FilterPresetsProps) {
    const {
        presets,
        selectedPresetId,
        setSelectedPresetId,
        savePreset,
        updatePreset,
        deletePreset,
    } = useFilterPresets();

    const [showSaveModal, setShowSaveModal] = useState(false);
    const [newPresetName, setNewPresetName] = useState('');
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editName, setEditName] = useState('');

    // Check if current filters are empty
    const hasActiveFilters = Object.values(currentFilters).some(v => v !== undefined && v !== '');

    // Handle save new preset
    const handleSave = () => {
        if (!newPresetName.trim()) return;

        const preset = savePreset(newPresetName.trim(), currentFilters);
        setSelectedPresetId(preset.id);
        setNewPresetName('');
        setShowSaveModal(false);
    };

    // Handle load preset
    const handleLoad = (preset: FilterPreset) => {
        setSelectedPresetId(preset.id);
        onLoadPreset(preset.filters);
    };

    // Handle rename
    const handleRename = (id: string) => {
        if (!editName.trim()) return;
        updatePreset(id, { name: editName.trim() });
        setEditingId(null);
        setEditName('');
    };

    // Handle delete with confirmation
    const handleDelete = (id: string, name: string) => {
        if (window.confirm(`Xóa bộ lọc "${name}"?`)) {
            deletePreset(id);
        }
    };

    return (
        <div className="filter-presets">
            {/* Preset Selector & Actions */}
            <div className="preset-controls">
                <select
                    className="form-select preset-select"
                    value={selectedPresetId || ''}
                    onChange={(e) => {
                        const preset = presets.find(p => p.id === e.target.value);
                        if (preset) handleLoad(preset);
                    }}
                >
                    <option value="">📁 Bộ lọc đã lưu...</option>
                    {presets.map(preset => (
                        <option key={preset.id} value={preset.id}>
                            {preset.name}
                        </option>
                    ))}
                </select>

                <button
                    className="btn btn-sm btn-primary"
                    onClick={() => setShowSaveModal(true)}
                    disabled={!hasActiveFilters}
                    title={!hasActiveFilters ? "Cần có ít nhất một bộ lọc" : "Lưu bộ lọc hiện tại"}
                >
                    💾 Lưu
                </button>

                {selectedPresetId && (
                    <>
                        <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => {
                                const preset = presets.find(p => p.id === selectedPresetId);
                                if (preset) {
                                    updatePreset(preset.id, { filters: currentFilters });
                                }
                            }}
                            title="Cập nhật bộ lọc đã chọn"
                        >
                            🔄
                        </button>
                        <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => {
                                const preset = presets.find(p => p.id === selectedPresetId);
                                if (preset) {
                                    setEditName(preset.name);
                                    setEditingId(preset.id);
                                }
                            }}
                            title="Đổi tên"
                        >
                            ✏️
                        </button>
                        <button
                            className="btn btn-sm btn-danger"
                            onClick={() => {
                                const preset = presets.find(p => p.id === selectedPresetId);
                                if (preset) handleDelete(preset.id, preset.name);
                            }}
                            title="Xóa"
                        >
                            🗑️
                        </button>
                    </>
                )}
            </div>

            {/* Save Modal */}
            {showSaveModal && (
                <div className="preset-modal-overlay" onClick={() => setShowSaveModal(false)}>
                    <div className="preset-modal" onClick={e => e.stopPropagation()}>
                        <h4>💾 Lưu bộ lọc</h4>
                        <input
                            type="text"
                            className="form-input"
                            placeholder="Tên bộ lọc..."
                            value={newPresetName}
                            onChange={(e) => setNewPresetName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                            autoFocus
                        />
                        <div className="preset-modal-actions">
                            <button className="btn btn-secondary" onClick={() => setShowSaveModal(false)}>
                                Hủy
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={handleSave}
                                disabled={!newPresetName.trim()}
                            >
                                Lưu
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Rename Modal */}
            {editingId && (
                <div className="preset-modal-overlay" onClick={() => setEditingId(null)}>
                    <div className="preset-modal" onClick={e => e.stopPropagation()}>
                        <h4>✏️ Đổi tên bộ lọc</h4>
                        <input
                            type="text"
                            className="form-input"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleRename(editingId)}
                            autoFocus
                        />
                        <div className="preset-modal-actions">
                            <button className="btn btn-secondary" onClick={() => setEditingId(null)}>
                                Hủy
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={() => handleRename(editingId)}
                                disabled={!editName.trim()}
                            >
                                Lưu
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default FilterPresets;
