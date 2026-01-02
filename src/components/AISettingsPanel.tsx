/**
 * AI Settings Panel Component
 * 
 * Provides UI for configuring AI analysis settings:
 * - API key input
 * - Model selection
 * - Custom prompt configuration
 * - Connection testing
 */

import React, { useState, useEffect } from 'react';

// ============================================
// Types
// ============================================

interface AISettings {
    apiKey: string;
    model: string;
    customPrompt: string;
    enableGrounding: boolean;
}

interface AIModel {
    id: string;
    name: string;
}

interface AISettingsPanelProps {
    isOpen: boolean;
    onClose: () => void;
    onSettingsSaved?: (settings: AISettings) => void;
}

// ============================================
// Constants
// ============================================

const STORAGE_KEY = 'vnstock_ai_settings';
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const DEFAULT_SETTINGS: AISettings = {
    apiKey: '',
    model: 'gemini-2.0-flash-exp',
    customPrompt: '',
    enableGrounding: true,
};

// ============================================
// Component
// ============================================

export function AISettingsPanel({ isOpen, onClose, onSettingsSaved }: AISettingsPanelProps) {
    const [settings, setSettings] = useState<AISettings>(DEFAULT_SETTINGS);
    const [models, setModels] = useState<AIModel[]>([]);
    const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
    const [testMessage, setTestMessage] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // Load settings from localStorage on mount
    useEffect(() => {
        const savedSettings = localStorage.getItem(STORAGE_KEY);
        if (savedSettings) {
            try {
                const parsed = JSON.parse(savedSettings);
                setSettings({ ...DEFAULT_SETTINGS, ...parsed });
            } catch (e) {
                console.error('Failed to parse saved AI settings:', e);
            }
        }
    }, []);

    // Fetch available models
    useEffect(() => {
        const fetchModels = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/ai/models`);
                if (response.ok) {
                    const data = await response.json();
                    setModels(data.models || []);
                }
            } catch (e) {
                console.error('Failed to fetch AI models:', e);
                // Fallback models
                setModels([
                    { id: 'gemini-2.0-flash-exp', name: 'Gemini 2.0 Flash (Experimental)' },
                    { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' },
                    { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro' },
                ]);
            }
        };

        if (isOpen) {
            fetchModels();
        }
    }, [isOpen]);

    // Handle input changes
    const handleChange = (field: keyof AISettings, value: string | boolean) => {
        setSettings(prev => ({ ...prev, [field]: value }));
    };

    // Test API connection
    const testConnection = async () => {
        if (!settings.apiKey) {
            setTestMessage('Please enter an API key first');
            setTestStatus('error');
            return;
        }

        setTestStatus('testing');
        setTestMessage('Testing connection...');

        try {
            const response = await fetch(`${API_BASE_URL}/api/ai/test-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    api_key: settings.apiKey,
                    model: settings.model,
                }),
            });

            const data = await response.json();

            if (data.success) {
                setTestStatus('success');
                setTestMessage(`✅ ${data.message}`);
            } else {
                setTestStatus('error');
                setTestMessage(`❌ ${data.message}`);
            }
        } catch (e) {
            setTestStatus('error');
            setTestMessage(`❌ Connection failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
        }
    };

    // Save settings
    const saveSettings = () => {
        setIsSaving(true);

        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
            onSettingsSaved?.(settings);
            setIsSaving(false);
            onClose();
        } catch (e) {
            console.error('Failed to save settings:', e);
            setIsSaving(false);
        }
    };

    // Clear settings
    const clearSettings = () => {
        if (confirm('Are you sure you want to clear all AI settings?')) {
            localStorage.removeItem(STORAGE_KEY);
            setSettings(DEFAULT_SETTINGS);
            setTestStatus('idle');
            setTestMessage('');
        }
    };

    if (!isOpen) return null;

    return (
        <div className="ai-settings-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="ai-settings-modal">
                <div className="ai-settings-header">
                    <h2>⚙️ Cài đặt AI</h2>
                    <button className="ai-settings-close" onClick={onClose}>×</button>
                </div>

                <div className="ai-settings-content">
                    {/* API Key */}
                    <div className="ai-settings-group">
                        <label htmlFor="apiKey">
                            🔑 API Key (Gemini)
                            <span className="ai-settings-hint">
                                Get your key from <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">Google AI Studio</a>
                            </span>
                        </label>
                        <input
                            type="password"
                            id="apiKey"
                            value={settings.apiKey}
                            onChange={(e) => handleChange('apiKey', e.target.value)}
                            placeholder="Enter your Gemini API key..."
                            className="ai-settings-input"
                        />
                    </div>

                    {/* Model Selection */}
                    <div className="ai-settings-group">
                        <label htmlFor="model">🤖 Model</label>
                        <select
                            id="model"
                            value={settings.model}
                            onChange={(e) => handleChange('model', e.target.value)}
                            className="ai-settings-select"
                        >
                            {models.map(model => (
                                <option key={model.id} value={model.id}>{model.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Enable Grounding */}
                    <div className="ai-settings-group ai-settings-checkbox-group">
                        <label className="ai-settings-checkbox-label">
                            <input
                                type="checkbox"
                                checked={settings.enableGrounding}
                                onChange={(e) => handleChange('enableGrounding', e.target.checked)}
                            />
                            <span>🔍 Enable Google Search (grounding)</span>
                        </label>
                        <span className="ai-settings-hint">
                            Allows AI to fetch real-time information from the web. Only works with Gemini 2.0 models.
                        </span>
                    </div>

                    {/* Custom Prompt */}
                    <div className="ai-settings-group">
                        <label htmlFor="customPrompt">
                            📝 Custom Prompt (Optional)
                            <span className="ai-settings-hint">
                                Add additional instructions to the default analysis prompt
                            </span>
                        </label>
                        <textarea
                            id="customPrompt"
                            value={settings.customPrompt}
                            onChange={(e) => handleChange('customPrompt', e.target.value)}
                            placeholder="Example: Focus more on dividend analysis and compare with industry peers..."
                            className="ai-settings-textarea"
                            rows={4}
                        />
                    </div>

                    {/* Test Connection */}
                    <div className="ai-settings-group">
                        <button
                            onClick={testConnection}
                            disabled={testStatus === 'testing' || !settings.apiKey}
                            className={`ai-settings-test-btn ${testStatus}`}
                        >
                            {testStatus === 'testing' ? '⏳ Testing...' : '🔌 Test Connection'}
                        </button>
                        {testMessage && (
                            <div className={`ai-settings-test-message ${testStatus}`}>
                                {testMessage}
                            </div>
                        )}
                    </div>
                </div>

                <div className="ai-settings-footer">
                    <button onClick={clearSettings} className="ai-settings-btn-secondary">
                        🗑️ Clear
                    </button>
                    <div className="ai-settings-footer-right">
                        <button onClick={onClose} className="ai-settings-btn-secondary">
                            Cancel
                        </button>
                        <button
                            onClick={saveSettings}
                            className="ai-settings-btn-primary"
                            disabled={isSaving}
                        >
                            {isSaving ? 'Saving...' : '💾 Save Settings'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ============================================
// Helper Hook for using AI Settings
// ============================================

export function useAISettings(): AISettings {
    const [settings, setSettings] = useState<AISettings>(DEFAULT_SETTINGS);

    useEffect(() => {
        const loadSettings = () => {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                try {
                    setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(saved) });
                } catch {
                    // Use defaults
                }
            }
        };

        loadSettings();

        // Listen for storage changes (if settings changed in another tab)
        window.addEventListener('storage', loadSettings);
        return () => window.removeEventListener('storage', loadSettings);
    }, []);

    return settings;
}

export default AISettingsPanel;
