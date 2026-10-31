export const authStore = {
  token: null,
  user: null,

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  },

  setUser(user) {
    this.user = user;
  },
};
