import { useCallback, useEffect, useRef, useState } from "react";
import { createExam, deleteExam, describeError, listExams } from "./api.js";

export function useExams() {
  const [status, setStatus] = useState("loading");
  const [exams, setExams] = useState([]);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [revision, setRevision] = useState(0);
  const [pendingAction, setPendingAction] = useState(false);
  const actionInProgress = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setStatus("loading");
    setError("");

    listExams(controller.signal)
      .then((data) => {
        if (cancelled) return;
        setExams(Array.isArray(data) ? data : data.results ?? []);
        setStatus("success");
      })
      .catch((requestError) => {
        if (cancelled) return;
        setError(describeError(requestError));
        setStatus("error");
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [revision]);

  const reload = useCallback(() => setRevision((value) => value + 1), []);

  const runAction = useCallback(async (action) => {
    if (actionInProgress.current) return;
    actionInProgress.current = true;
    setPendingAction(true);
    setActionError("");
    try {
      return await action();
    } catch (requestError) {
      setActionError(describeError(requestError));
      return false;
    } finally {
      actionInProgress.current = false;
      setPendingAction(false);
    }
  }, []);

  const create = useCallback((title) => runAction(async () => {
    const exam = await createExam(title.trim());
    setExams((current) => [exam, ...current]);
    return true;
  }), [runAction]);

  const remove = useCallback((id) => runAction(async () => {
    await deleteExam(id);
    setExams((current) => current.filter((exam) => exam.id !== id));
    return true;
  }), [runAction]);

  return { status, exams, error, actionError, pendingAction, reload, create, remove };
}
