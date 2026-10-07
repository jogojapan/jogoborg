const KEY = 'jogoborg_theme';
export type ThemeMode = 'light' | 'dark';

function load(): ThemeMode {
  try {
    const t = localStorage.getItem(KEY);
    if (t === 'light' || t === 'dark') return t;
  } catch {
    /* ignore */
  }
  return 'light'; // matches the original ThemeService default
}

// Exported as an object so component consumers can read `theme.mode` while
// we reassign the property (a top-level reassigned $state cannot be exported).
export const theme = $state<{ mode: ThemeMode }>({ mode: load() });

export function applyTheme(): void {
  document.documentElement.setAttribute('data-theme', theme.mode);
  try {
    localStorage.setItem(KEY, theme.mode);
  } catch {
    /* ignore */
  }
}

export function toggleTheme(): void {
  theme.mode = theme.mode === 'light' ? 'dark' : 'light';
  applyTheme();
}

applyTheme();