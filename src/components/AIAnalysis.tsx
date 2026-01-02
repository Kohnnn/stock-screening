/**
 * AI Stock Analysis Component
 * 
 * Main UI for AI-powered stock analysis:
 * - Stock search and selection
 * - Analysis generation with Gemini
 * - Markdown rendering of 9-section Vietnamese analysis
 * - Loading states and error handling
 */

import React, { useState, useCallback } from 'react';
import { AISettingsPanel, useAISettings } from './AISettingsPanel';

// ============================================
// Types
// ============================================

interface Stock {
    symbol: string;
    company_name: string | null;
    exchange: string | null;
    sector: string | null;
}

interface AnalysisMetadata {
    symbol: string;
    company_name: string;
    model: string;
    grounding_sources: string[];
    generated_at: string;
    tokens_used: number | null;
}

interface AnalysisResult {
    analysis: string;
    metadata: AnalysisMetadata;
}

// ============================================
// Constants
// ============================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ============================================
// Markdown Renderer (Simple)
// ============================================

function renderMarkdown(text: string): React.ReactNode {
    // Split by headers and convert to React elements
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let currentList: string[] = [];
    let listKey = 0;

    const flushList = () => {
        if (currentList.length > 0) {
            elements.push(
                <ul key={`list-${listKey++}`} className="ai-analysis-list">
                    {currentList.map((item, i) => (
                        <li key={i} dangerouslySetInnerHTML={{ __html: formatInline(item) }} />
                    ))}
                </ul>
            );
            currentList = [];
        }
    };

    const formatInline = (text: string): string => {
        // Bold
        text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        // Italic
        text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
        // Links
        text = text.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
        // Code
        text = text.replace(/`(.+?)`/g, '<code>$1</code>');
        return text;
    };

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        // Headers
        if (line.startsWith('## ')) {
            flushList();
            elements.push(
                <h2 key={`h2-${i}`} className="ai-analysis-h2">
                    {line.substring(3)}
                </h2>
            );
        } else if (line.startsWith('### ')) {
            flushList();
            elements.push(
                <h3 key={`h3-${i}`} className="ai-analysis-h3">
                    {line.substring(4)}
                </h3>
            );
        } else if (line.startsWith('- ')) {
            currentList.push(line.substring(2));
        } else if (line.trim() === '') {
            flushList();
            // Add spacing between sections
        } else {
            flushList();
            elements.push(
                <p
                    key={`p-${i}`}
                    className="ai-analysis-paragraph"
                    dangerouslySetInnerHTML={{ __html: formatInline(line) }}
                />
            );
        }
    }

    flushList();
    return elements;
}

// ============================================
// Main Component
// ============================================

export function AIAnalysis() {
    const settings = useAISettings();
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<Stock[]>([]);
    const [selectedStock, setSelectedStock] = useState<Stock | null>(null);
    const [isSearching, setIsSearching] = useState(false);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [settingsOpen, setSettingsOpen] = useState(false);

    // Search for stocks
    const searchStocks = useCallback(async (query: string) => {
        if (!query || query.length < 1) {
            setSearchResults([]);
            return;
        }

        setIsSearching(true);
        try {
            const response = await fetch(
                `${API_BASE_URL}/api/stocks?search=${encodeURIComponent(query)}&page_size=10`
            );
            if (response.ok) {
                const data = await response.json();
                setSearchResults(data.stocks || []);
            }
        } catch (e) {
            console.error('Search failed:', e);
        } finally {
            setIsSearching(false);
        }
    }, []);

    // Debounced search
    const handleSearchChange = (value: string) => {
        setSearchQuery(value);
        if (value.length >= 1) {
            const timeoutId = setTimeout(() => searchStocks(value), 300);
            return () => clearTimeout(timeoutId);
        } else {
            setSearchResults([]);
        }
    };

    // Select a stock
    const handleSelectStock = (stock: Stock) => {
        setSelectedStock(stock);
        setSearchQuery(stock.symbol);
        setSearchResults([]);
    };

    // Generate analysis
    const generateAnalysis = async () => {
        if (!selectedStock) return;

        if (!settings.apiKey) {
            setError('Please configure your API key in settings first');
            setSettingsOpen(true);
            return;
        }

        setIsAnalyzing(true);
        setError(null);
        setAnalysisResult(null);

        try {
            const response = await fetch(
                `${API_BASE_URL}/api/ai/analyze/${selectedStock.symbol}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: settings.apiKey,
                        model: settings.model,
                        custom_prompt: settings.customPrompt || null,
                        enable_grounding: settings.enableGrounding,
                    }),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Analysis failed');
            }

            if (data.success) {
                setAnalysisResult({
                    analysis: data.analysis,
                    metadata: data.metadata,
                });
            } else {
                throw new Error(data.message || 'Analysis failed');
            }
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Analysis failed');
        } finally {
            setIsAnalyzing(false);
        }
    };

    // Clear analysis
    const clearAnalysis = () => {
        setAnalysisResult(null);
        setSelectedStock(null);
        setSearchQuery('');
        setError(null);
    };

    return (
        <div className="ai-analysis-container">
            {/* Header */}
            <div className="ai-analysis-header">
                <div className="ai-analysis-title">
                    <span className="ai-analysis-icon">🤖</span>
                    <h1>AI Stock Analysis</h1>
                    <span className="ai-analysis-badge">Powered by Gemini</span>
                </div>
                <button
                    className="ai-analysis-settings-btn"
                    onClick={() => setSettingsOpen(true)}
                    title="AI Settings"
                >
                    ⚙️
                </button>
            </div>

            {/* Search Section */}
            <div className="ai-analysis-search-section">
                <div className="ai-analysis-search-container">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => handleSearchChange(e.target.value)}
                        placeholder="Tìm kiếm mã cổ phiếu (VD: VCB, FPT, VNM...)"
                        className="ai-analysis-search-input"
                    />
                    {isSearching && <span className="ai-analysis-search-spinner">⏳</span>}

                    {/* Search Results Dropdown */}
                    {searchResults.length > 0 && (
                        <div className="ai-analysis-search-results">
                            {searchResults.map((stock) => (
                                <div
                                    key={stock.symbol}
                                    className="ai-analysis-search-result"
                                    onClick={() => handleSelectStock(stock)}
                                >
                                    <span className="ai-analysis-stock-symbol">{stock.symbol}</span>
                                    <span className="ai-analysis-stock-name">{stock.company_name}</span>
                                    <span className="ai-analysis-stock-exchange">{stock.exchange}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Selected Stock Card */}
                {selectedStock && (
                    <div className="ai-analysis-selected-stock">
                        <div className="ai-analysis-selected-info">
                            <span className="ai-analysis-selected-symbol">{selectedStock.symbol}</span>
                            <span className="ai-analysis-selected-name">{selectedStock.company_name}</span>
                            <span className="ai-analysis-selected-sector">{selectedStock.sector}</span>
                        </div>
                        <button
                            onClick={generateAnalysis}
                            disabled={isAnalyzing}
                            className="ai-analysis-generate-btn"
                        >
                            {isAnalyzing ? (
                                <>
                                    <span className="ai-analysis-spinner">⏳</span>
                                    Đang phân tích...
                                </>
                            ) : (
                                <>🚀 Phân tích AI</>
                            )}
                        </button>
                    </div>
                )}
            </div>

            {/* Error Message */}
            {error && (
                <div className="ai-analysis-error">
                    <span>❌</span> {error}
                </div>
            )}

            {/* Loading State */}
            {isAnalyzing && (
                <div className="ai-analysis-loading">
                    <div className="ai-analysis-loading-spinner"></div>
                    <p>🤖 AI đang phân tích {selectedStock?.symbol}...</p>
                    <p className="ai-analysis-loading-hint">
                        Quá trình này có thể mất 15-30 giây với Google Search grounding
                    </p>
                </div>
            )}

            {/* Analysis Result */}
            {analysisResult && (
                <div className="ai-analysis-result">
                    <div className="ai-analysis-result-header">
                        <div className="ai-analysis-result-title">
                            <h2>Phân tích: {analysisResult.metadata.company_name} ({analysisResult.metadata.symbol})</h2>
                            <span className="ai-analysis-result-date">
                                {new Date(analysisResult.metadata.generated_at).toLocaleString('vi-VN')}
                            </span>
                        </div>
                        <div className="ai-analysis-result-actions">
                            <button
                                onClick={() => navigator.clipboard.writeText(analysisResult.analysis)}
                                className="ai-analysis-action-btn"
                                title="Copy to clipboard"
                            >
                                📋 Copy
                            </button>
                            <button
                                onClick={clearAnalysis}
                                className="ai-analysis-action-btn"
                                title="Clear analysis"
                            >
                                🗑️ Clear
                            </button>
                        </div>
                    </div>

                    {/* Metadata */}
                    <div className="ai-analysis-metadata">
                        <span>Model: {analysisResult.metadata.model}</span>
                        {analysisResult.metadata.tokens_used && (
                            <span>Tokens: {analysisResult.metadata.tokens_used.toLocaleString()}</span>
                        )}
                        {analysisResult.metadata.grounding_sources.length > 0 && (
                            <span>Sources: {analysisResult.metadata.grounding_sources.length}</span>
                        )}
                    </div>

                    {/* Rendered Analysis */}
                    <div className="ai-analysis-content">
                        {renderMarkdown(analysisResult.analysis)}
                    </div>

                    {/* Grounding Sources */}
                    {analysisResult.metadata.grounding_sources.length > 0 && (
                        <div className="ai-analysis-sources">
                            <h4>📚 Nguồn tham khảo</h4>
                            <ul>
                                {analysisResult.metadata.grounding_sources.map((source, i) => (
                                    <li key={i} dangerouslySetInnerHTML={{ __html: source }} />
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            {/* Empty State */}
            {!selectedStock && !analysisResult && (
                <div className="ai-analysis-empty">
                    <div className="ai-analysis-empty-icon">🔍</div>
                    <h3>Chọn cổ phiếu để phân tích</h3>
                    <p>Nhập mã cổ phiếu vào ô tìm kiếm ở trên để bắt đầu</p>
                    <div className="ai-analysis-empty-features">
                        <div className="ai-analysis-feature">
                            <span>📊</span>
                            <span>9 phần phân tích chi tiết</span>
                        </div>
                        <div className="ai-analysis-feature">
                            <span>🔍</span>
                            <span>Google Search real-time</span>
                        </div>
                        <div className="ai-analysis-feature">
                            <span>🇻🇳</span>
                            <span>Output tiếng Việt</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Settings Modal */}
            <AISettingsPanel
                isOpen={settingsOpen}
                onClose={() => setSettingsOpen(false)}
            />
        </div>
    );
}

export default AIAnalysis;
