import { afterEach, describe, expect, it, vi } from "vitest";
import { api, createExam, deleteExam, describeError, listExams } from "./api.js";

afterEach(() => vi.restoreAllMocks());

describe("API client", () => {
  it("keeps the API base URL centralized and configures a timeout", () => {
    expect(api.defaults.baseURL).toBe("http://127.0.0.1:8000/api/");
    expect(api.defaults.timeout).toBe(8000);
  });

  it("collects all pages and passes the abort signal", async () => {
    const signal = new AbortController().signal;
    const get = vi.spyOn(api, "get")
      .mockResolvedValueOnce({ data: { results: [{ id: 1 }], next: "http://127.0.0.1:8000/api/exams/?page=2" } })
      .mockResolvedValueOnce({ data: { results: [{ id: 2 }], next: null } });

    await expect(listExams(signal)).resolves.toEqual([{ id: 1 }, { id: 2 }]);
    expect(get).toHaveBeenNthCalledWith(1, "exams/", { signal });
    expect(get).toHaveBeenNthCalledWith(2, "http://127.0.0.1:8000/api/exams/?page=2", { signal });
  });

  it("uses POST and DELETE against the centralized exam routes", async () => {
    const post = vi.spyOn(api, "post").mockResolvedValue({ data: { id: 7, title: "React" } });
    const remove = vi.spyOn(api, "delete").mockResolvedValue({ status: 204 });

    await expect(createExam("React")).resolves.toEqual({ id: 7, title: "React" });
    await deleteExam(7);
    expect(post).toHaveBeenCalledWith("exams/", { title: "React" });
    expect(remove).toHaveBeenCalledWith("exams/7/");
  });

  it("turns common authentication and connection failures into readable messages", () => {
    expect(describeError({ response: { status: 401 } })).toMatch(/Token inválido/);
    expect(describeError({ message: "offline" })).toMatch(/no se pudo conectar/i);
  });
});
