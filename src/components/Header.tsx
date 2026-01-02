import React from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { useTheme } from '../contexts/ThemeContext';

// ============================================
// Header Component
// ============================================

export function Header() {
    const { language, setLanguage, t } = useLanguage();
    const { theme, toggleTheme, isDark } = useTheme();

    return (
        <header className="header">
            <div className="header-content">
                <div className="header-title">
                    <span>🇻🇳</span>
                    <span>{t('app.title')}</span>
                </div>

                <div className="header-actions">
                    {/* Language Toggle */}
                    <button
                        className="btn btn-icon"
                        onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
                        title={language === 'vi' ? 'Switch to English' : 'Chuyển sang Tiếng Việt'}
                    >
                        {language === 'vi' ? '🇻🇳 VI' : '🇺🇸 EN'}
                    </button>

                    {/* Theme Toggle */}
                    <button
                        className="btn btn-icon"
                        onClick={toggleTheme}
                        title={isDark ? t('theme.light') : t('theme.dark')}
                    >
                        {isDark ? '☀️' : '🌙'}
                    </button>
                </div>
            </div>
        </header>
    );
}

export default Header;
