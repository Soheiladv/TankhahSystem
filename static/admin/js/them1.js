/* ============================================ */
/* ===    static/admin/js/theme.js         === */
/* ============================================ */
(() => {
    'use strict';

    const THEME_KEY = 'theme';
    const THEME_LIGHT = 'light';
    const THEME_DARK = 'dark';
    const THEME_AUTO = 'auto';

    // Function to get the saved theme preference from localStorage
    const getStoredTheme = () => localStorage.getItem(THEME_KEY);

    // Function to save the theme preference to localStorage
    const setStoredTheme = theme => localStorage.setItem(THEME_KEY, theme);

    // Function to get the preferred theme (saved, or system preference, or light)
    const getPreferredTheme = () => {
        const storedTheme = getStoredTheme();
        if (storedTheme) {
            return storedTheme;
        }
        // If no saved theme, check system preference only if auto is default/intended
        // return window.matchMedia('(prefers-color-scheme: dark)').matches ? THEME_DARK : THEME_LIGHT;
        // Defaulting to 'auto' might be better UX
        return THEME_AUTO;
    };

    // Function to apply the theme to the HTML document
    const applyTheme = theme => {
        const root = document.documentElement; // Apply to <html> tag
        if (theme === THEME_AUTO) {
            root.dataset.theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? THEME_DARK : THEME_LIGHT;
        } else {
            root.dataset.theme = theme;
        }
        updateToggleIcon(theme); // Update the button icon
    };

    // Function to update the toggle button icon based on the active theme
    const updateToggleIcon = (theme) => {
        document.querySelectorAll('.theme-toggle').forEach(toggle => {
            const useElement = toggle.querySelector('use');
            if (useElement) {
                let iconId = '#icon-theme-light'; // Default icon
                if (theme === THEME_DARK) {
                    iconId = '#icon-theme-dark';
                } else if (theme === THEME_AUTO) {
                    iconId = '#icon-theme-auto';
                }
                useElement.setAttribute('href', iconId);
                // Update aria-label for accessibility
                let label = 'Switch to light theme';
                 if (theme === THEME_LIGHT) label = 'Switch to dark theme';
                 if (theme === THEME_DARK) label = 'Switch to system theme';
                 toggle.setAttribute('aria-label', label);
            }
        });
    };

    // Media query listener for system preference changes when theme is 'auto'
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        const storedTheme = getStoredTheme();
        if (storedTheme === THEME_AUTO || !storedTheme) {
            applyTheme(THEME_AUTO);
        }
    });

    // Apply the theme on initial load
    window.addEventListener('DOMContentLoaded', () => {
        const initialTheme = getPreferredTheme();
        applyTheme(initialTheme);

        // Add click listeners to all theme toggle buttons
        document.querySelectorAll('.theme-toggle').forEach(toggle => {
            toggle.addEventListener('click', () => {
                const currentTheme = getStoredTheme() || THEME_AUTO;
                let nextTheme = THEME_LIGHT; // Default cycle: auto -> light -> dark -> auto

                if (currentTheme === THEME_LIGHT) {
                    nextTheme = THEME_DARK;
                } else if (currentTheme === THEME_DARK) {
                    nextTheme = THEME_AUTO;
                } // else (if currentTheme is auto), nextTheme remains light

                setStoredTheme(nextTheme);
                applyTheme(nextTheme);
            });
        });

         // Remove the 'no-js' class now that JS has loaded
         document.documentElement.classList.remove('no-js');
    });
})();