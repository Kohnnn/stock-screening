import { useState, useEffect, useCallback } from 'react';

const WATCHLIST_KEY = 'vnstock-watchlist';

/**
 * Hook for managing user's stock watchlist with localStorage persistence
 */
export function useWatchlist() {
    const [watchlist, setWatchlist] = useState<string[]>(() => {
        try {
            const stored = localStorage.getItem(WATCHLIST_KEY);
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    });

    // Persist to localStorage
    useEffect(() => {
        localStorage.setItem(WATCHLIST_KEY, JSON.stringify(watchlist));
    }, [watchlist]);

    const addToWatchlist = useCallback((symbol: string) => {
        setWatchlist(prev => {
            if (prev.includes(symbol)) return prev;
            return [...prev, symbol];
        });
    }, []);

    const removeFromWatchlist = useCallback((symbol: string) => {
        setWatchlist(prev => prev.filter(s => s !== symbol));
    }, []);

    const toggleWatchlist = useCallback((symbol: string) => {
        setWatchlist(prev => {
            if (prev.includes(symbol)) {
                return prev.filter(s => s !== symbol);
            }
            return [...prev, symbol];
        });
    }, []);

    const isInWatchlist = useCallback((symbol: string) => {
        return watchlist.includes(symbol);
    }, [watchlist]);

    const clearWatchlist = useCallback(() => {
        setWatchlist([]);
    }, []);

    return {
        watchlist,
        addToWatchlist,
        removeFromWatchlist,
        toggleWatchlist,
        isInWatchlist,
        clearWatchlist,
        count: watchlist.length,
    };
}

export default useWatchlist;
