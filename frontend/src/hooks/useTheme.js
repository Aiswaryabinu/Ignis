import { useEffect } from 'react';
import { themeStore } from '../store/themeStore';

export function useTheme() {
  useEffect(() => {
    themeStore.setMode(themeStore.mode);
  }, []);

  return {
    theme: themeStore.mode,
    setTheme: (mode) => themeStore.setMode(mode),
  };
}
