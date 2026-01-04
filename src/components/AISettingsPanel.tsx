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
import { AISettings } from '../contexts/AISettingsContext';

// ============================================
// Types
// ============================================

// Local interfaces removed, using context types

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
// Empty string default = relative paths (works with nginx proxy in Docker)
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const DEFAULT_SETTINGS: AISettings = {
    apiKey: '',
    model: 'gemini-2.0-flash-exp',
    customPrompt: '',
    promptTemplate: '',
    enableGrounding: true,
};

// ============================================
// Component
// ============================================

export function AISettingsPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    const { settings, updateSettings, saveSettings } = useAISettings();
    const [models, setModels] = useState<AIModel[]>([]);
    const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
    const [testMessage, setTestMessage] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    const [defaultPromptText, setDefaultPromptText] = useState('');

    // Load default prompt
    const loadDefaultPrompt = async (updateSettingsVal = false) => {
        try {
            const res = await fetch(`${API_BASE_URL}/api/ai/default-prompt`);
            if (res.ok) {
                const data = await res.json();
                setDefaultPromptText(data.template);
                if (updateSettingsVal) {
                    handleChange('promptTemplate', data.template);
                }
            }
        } catch (e) {
            console.error('Failed to load default prompt:', e);
        }
    };

    // Fetch available models and default prompt
    useEffect(() => {
        const fetchModels = async () => {
            // ... existing fetchModels code ... (kept below logic implies I should merging, but tool replaces block. I need to be careful)
            try {
                const response = await fetch(`${API_BASE_URL}/api/ai/models`);
                if (response.ok) {
                    const data = await response.json();
                    setModels(data.models || []);
                }
            } catch (e) {
                console.error('Failed to fetch AI models:', e);
                setModels([
                    { id: 'gemini-2.0-flash-exp', name: 'Gemini 2.0 Flash (Experimental)' },
                    { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' },
                    { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro' },
                ]);
            }
        };

        if (isOpen) {
            fetchModels();
            loadDefaultPrompt();
        }
    }, [isOpen]);

    // Handle input changes
    const handleChange = (field: keyof AISettings, value: string | boolean) => {
        updateSettings({ [field]: value });
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
    const handleSave = () => {
        setIsSaving(true);
        try {
            saveSettings();
            setIsSaving(false);
            onClose();
        } catch (e) {
            console.error('Failed to save settings:', e);
            setIsSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>🤖 AI Settings</h2>
                    <button className="btn btn-icon" onClick={onClose}>×</button>
                </div>
                <div className="modal-body">
                    <div className="form-group">
                        <label className="form-label">API Key</label>
                        <input
                            type="password"
                            className="form-input"
                            placeholder="Enter your Gemini API key"
                            value={settings.apiKey}
                            onChange={e => handleChange('apiKey', e.target.value)}
                        />
                    </div>


                    <div className="form-group">
                        <label className="form-label">Model</label>
                        <div className="flex flex-col gap-2">
                            <select
                                className="form-select"
                                value={models.some(m => m.id === settings.model) ? settings.model : 'custom'}
                                onChange={e => {
                                    if (e.target.value !== 'custom') {
                                        handleChange('model', e.target.value);
                                    } else {
                                        // Switch to custom mode - maybe clear model or keep current?
                                        if (models.some(m => m.id === settings.model)) {
                                            handleChange('model', ''); // Clear to force input to appear and be empty? Or keep?
                                        }
                                    }
                                }}
                            >
                                {models.map(m => (
                                    <option key={m.id} value={m.id}>{m.name}</option>
                                ))}
                                <option value="custom">Custom (Enter ID)...</option>
                            </select>

                            {(settings.model === '' || !models.some(m => m.id === settings.model)) && (
                                <input
                                    type="text"
                                    className="form-input"
                                    placeholder="Enter custom model ID (e.g. gemini-1.5-pro-latest)"
                                    value={settings.model}
                                    onChange={e => handleChange('model', e.target.value)}
                                />
                            )}
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="flex items-center gap-sm">
                            <input
                                type="checkbox"
                                checked={settings.enableGrounding}
                                onChange={e => handleChange('enableGrounding', e.target.checked)}
                            />
                            <span>Enable Google Search Grounding</span>
                        </label>
                    </div>

                    <div className="divider">Prompts</div>

                    <div className="form-group">
                        <label className="form-label">System Prompt Template</label>
                        <div className="text-xs text-base-content/70 mb-2">
                            Base template including {`{stock_data}`} placeholder. Leave empty to use default.
                        </div>
                        <textarea
                            className="form-input font-mono text-xs"
                            placeholder="Default system prompt..."
                            value={settings.promptTemplate}
                            onChange={e => handleChange('promptTemplate', e.target.value)}
                            rows={6}
                        />
                        <div className="flex justify-end mt-1">
                            <button
                                className="btn btn-xs btn-ghost"
                                onClick={() => loadDefaultPrompt(true)}
                            >
                                Reset to Default
                            </button>
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Custom Instructions (Appended)</label>
                        <textarea
                            className="form-input"
                            placeholder="Add specific instructions (e.g. 'Focus on risks', 'Use funny tone')..."
                            value={settings.customPrompt}
                            onChange={e => handleChange('customPrompt', e.target.value)}
                            rows={3}
                        />
                    </div>

                    {testMessage && (
                        <div className={`badge ${testStatus === 'success' ? 'badge-success' : testStatus === 'error' ? 'badge-error' : 'badge-info'}`}>
                            {testMessage}
                        </div>
                    )}
                </div>

                <div className="modal-footer">
                    <button
                        className="btn btn-secondary"
                        onClick={testConnection}
                        disabled={testStatus === 'testing'}
                    >
                        {testStatus === 'testing' ? '🔄 Testing...' : '🔌 Test Connection'}
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={handleSave}
                        disabled={isSaving}
                    >
                        {isSaving ? 'Saving...' : '💾 Save Settings'}
                    </button>
                </div>
            </div>
        </div>
    );
}

import { useAISettings as useAISettingsContext } from '../contexts/AISettingsContext';
export const useAISettings = useAISettingsContext;
export default AISettingsPanel;
