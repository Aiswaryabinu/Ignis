export const themeStore = {
  mode: 'light',

  setMode(mode) {
    this.mode = mode;
    document.documentElement.setAttribute('data-theme', mode);
  },
};
