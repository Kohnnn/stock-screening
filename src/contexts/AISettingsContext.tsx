
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// ============================================
// Types
// ============================================

export interface AISettings {
    apiKey: string;
    model: string;
    customPrompt: string;
    promptTemplate: string;
    enableGrounding: boolean;
}

interface AISettingsContextType {
    settings: AISettings;
    updateSettings: (newSettings: Partial<AISettings>) => void;
    saveSettings: () => void;
}

const STORAGE_KEY = 'vnstock_ai_settings';

const DEFAULT_SETTINGS: AISettings = {
    apiKey: '',
    model: 'gemini-2.0-flash-exp',
    customPrompt: '',
    promptTemplate: '',
    enableGrounding: true,
};

// ============================================
// Context
// ============================================

const AISettingsContext = createContext<AISettingsContextType | undefined>(undefined);

// ============================================
// Provider
// ============================================

export function AISettingsProvider({ children }: { children: ReactNode }) {
    const [settings, setSettings] = useState<AISettings>(DEFAULT_SETTINGS);

    // Load settings on mount
    useEffect(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(saved) });
            }
        } catch (e) {
            console.error('Failed to load AI settings:', e);
        }
    }, []);

    const updateSettings = (newSettings: Partial<AISettings>) => {
        setSettings(prev => ({ ...prev, ...newSettings }));
    };

    const saveSettings = () => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
        } catch (e) {
            console.error('Failed to save AI settings:', e);
        }
    };

    return (
        <AISettingsContext.Provider value={{ settings, updateSettings, saveSettings }}>
            {children}
        </AISettingsContext.Provider>
    );
}

// ============================================
// Hook
// ============================================

export function useAISettings() {
    const context = useContext(AISettingsContext);
    if (context === undefined) {
        throw new Error('useAISettings must be used within an AISettingsProvider');
    }
    return context;
}
