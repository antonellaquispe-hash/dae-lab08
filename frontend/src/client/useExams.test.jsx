import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExamManager } from "../components/ExamManager/ExamManager.jsx";

vi.mock("./api.js", () => ({
  createExam: vi.fn(),
  deleteExam: vi.fn(),
  describeError: (error) => error.message,
  listExams: vi.fn(),
}));

import { createExam, deleteExam, listExams } from "./api.js";

describe("ExamManager", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the loading state before the API responds", () => {
    listExams.mockReturnValue(new Promise(() => {}));
    render(<ExamManager />);
    expect(screen.getByText("Cargando tus exámenes")).toBeInTheDocument();
  });

  it("renders exam data returned by the paginated API", async () => {
    listExams.mockResolvedValue({ results: [{ id: 1, title: "Django REST", question_count: 4 }] });
    render(<ExamManager />);
    expect(await screen.findByRole("heading", { name: "Django REST" })).toBeInTheDocument();
    expect(screen.getByText("4 preguntas")).toBeInTheDocument();
  });

  it("shows a request error and offers retry", async () => {
    listExams.mockRejectedValueOnce(new Error("API fuera de línea"));
    render(<ExamManager />);
    expect(await screen.findByText("API fuera de línea")).toBeInTheDocument();
    listExams.mockResolvedValue({ results: [] });
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Tu biblioteca empieza hoy")).toBeInTheDocument();
  });

  it("creates an exam and removes it only after server confirmation", async () => {
    listExams.mockResolvedValue({ results: [{ id: 1, title: "Django REST", question_count: 2 }] });
    createExam.mockResolvedValue({ id: 2, title: "React", question_count: 0 });
    deleteExam.mockResolvedValue(undefined);
    render(<ExamManager />);

    await screen.findByRole("heading", { name: "Django REST" });
    await userEvent.type(screen.getByLabelText("Título del examen"), "React");
    await userEvent.click(screen.getByRole("button", { name: "Crear examen" }));
    expect(await screen.findByRole("heading", { name: "React" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Eliminar React" }));
    await waitFor(() => expect(screen.queryByRole("heading", { name: "React" })).not.toBeInTheDocument());
    expect(deleteExam).toHaveBeenCalledWith(2);
  });

  it("shows the API validation message for an empty title", async () => {
    listExams.mockResolvedValue({ results: [] });
    createExam.mockRejectedValue(new Error("Este campo no puede estar en blanco."));
    render(<ExamManager />);

    await screen.findByText("Tu biblioteca empieza hoy");
    await userEvent.click(screen.getByRole("button", { name: "Crear examen" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Este campo no puede estar en blanco.");
    expect(createExam).toHaveBeenCalledWith("");
  });
});

