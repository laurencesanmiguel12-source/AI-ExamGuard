import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function loginRedirectPath() {
  // School-scoped routes are always "/:schoolSlug/...". Deep-link back into the same school's
  // login instead of the tenant-less SchoolPicker, so an expired token doesn't force the user to
  // re-find their school from scratch on top of logging back in.
  const [, firstSegment] = window.location.pathname.split("/");
  if (!firstSegment || firstSegment === "login" || firstSegment === "schools") {
    return "/login";
  }
  return `/${firstSegment}/login`;
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      const target = loginRedirectPath();
      if (window.location.pathname !== target) {
        window.location.href = target;
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
