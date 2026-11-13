import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/";

export const api = axios.create({
  baseURL: API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`,
  timeout: 8000,
  headers: { Accept: "application/json", "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("quizToken");
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

export async function listExams(signal) {
  const exams = [];
  let next = "exams/";
  while (next) {
    const response = await api.get(next, { signal });
    const page = response.data;
    exams.push(...(Array.isArray(page) ? page : page.results ?? []));
    next = Array.isArray(page) ? null : page.next;
  }
  return exams;
}

export async function createExam(title) {
  const response = await api.post("exams/", { title });
  return response.data;
}

export async function deleteExam(id) {
  await api.delete(`exams/${id}/`);
}

export function describeError(error) {
  if (axios.isCancel(error) || error?.code === "ERR_CANCELED") return "";
  if (!error?.response) {
    return "No se pudo conectar con la API. Comprueba que Django esté activo y vuelve a intentarlo.";
  }

  const { status, data } = error.response;
  if (status === 401) return "Token inválido o ausente. Revisa la credencial de acceso.";
  if (status === 403) return "Tu usuario no tiene permiso para realizar esta operación.";
  if (status === 404) return "El examen ya no existe o la dirección solicitada no es válida.";
  if (status >= 500) return "La API tuvo un problema interno. Inténtalo de nuevo.";

  const messages = data && typeof data === "object"
    ? Object.values(data).flatMap((value) => Array.isArray(value) ? value : [value])
    : [];
  return messages.find((value) => typeof value === "string") || "La API rechazó la solicitud.";
}
