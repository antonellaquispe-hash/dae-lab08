import { useState } from "react";
import { useExams } from "../../client/useExams.js";

export function ExamManager() {
  const { status, exams, error, actionError, pendingAction, reload, create, remove } = useExams();
  const [title, setTitle] = useState("");
  const [token, setToken] = useState(() => localStorage.getItem("quizToken") ?? "");
  const [tokenSaved, setTokenSaved] = useState(false);

  async function handleCreate(event) {
    event.preventDefault();
    const trimmedTitle = title.trim();
    const created = await create(trimmedTitle);
    if (created) setTitle("");
  }

  function saveToken(event) {
    event.preventDefault();
    const trimmedToken = token.trim();
    if (trimmedToken) localStorage.setItem("quizToken", trimmedToken);
    else localStorage.removeItem("quizToken");
    setToken(trimmedToken);
    setTokenSaved(true);
    reload();
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="#inicio" aria-label="DAE Laboratorio 08, inicio">
          <span className="brand-mark">Q</span>
          <span>QUIZ<span className="brand-light">SPACE</span></span>
        </a>
        <div className="topbar-meta"><span className="status-dot" /> API de cuestionarios <span className="meta-divider">/</span> Laboratorio 08</div>
      </header>

      <section className="hero" id="inicio">
        <div className="hero-copy">
          <p className="eyebrow"><span /> TU ESPACIO DE APRENDIZAJE</p>
          <h1>Cada pregunta<br />abre una <em>posibilidad.</em></h1>
          <p className="hero-description">Organiza tus exámenes y transforma lo que sabes en nuevos desafíos.</p>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" />
          <div className="art-card card-back"><span>✳</span><small>APRENDER</small></div>
          <div className="art-card card-front"><div className="art-spark">✦</div><strong>Tu siguiente<br />gran idea.</strong><div className="art-lines"><i /><i /><i /></div></div>
          <span className="art-star star-one">✳</span><span className="art-star star-two">✦</span>
        </div>
      </section>

      <section className="workspace" aria-labelledby="exams-title">
        <div className="section-heading">
          <div><p className="eyebrow">BIBLIOTECA</p><h2 id="exams-title">Tus exámenes</h2></div>
          {status === "success" && <span className="count-pill">{exams.length} {exams.length === 1 ? "examen" : "exámenes"}</span>}
        </div>

        <form className="token-panel" onSubmit={saveToken}>
          <label htmlFor="api-token">Token de acceso de la API</label>
          <div className="token-controls"><input id="api-token" type="password" autoComplete="current-password" value={token} onChange={(event) => { setToken(event.target.value); setTokenSaved(false); }} placeholder="Pega el token generado por seed_quiz" /><button type="submit" className="button button-subtle">Guardar token</button></div>
          {tokenSaved && <span className="token-saved" role="status">Token guardado. Consultando exámenes…</span>}
        </form>

        <form className="create-panel" onSubmit={handleCreate}>
          <div className="create-icon" aria-hidden="true">＋</div>
          <div className="create-copy"><strong>Un nuevo reto comienza aquí</strong><span>Crea un examen para agregarlo a tu biblioteca.</span></div>
          <label className="sr-only" htmlFor="exam-title">Título del examen</label>
          <input id="exam-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Ej. Fundamentos de Django" maxLength={120} />
          <button className="button button-primary" type="submit" disabled={pendingAction}>{pendingAction ? "Guardando…" : "Crear examen"}<span aria-hidden="true">↗</span></button>
        </form>

        {actionError && <p className="notice notice-error" role="alert">{actionError}</p>}

        <div className="exam-list" aria-live="polite" aria-busy={status === "loading"}>
          {status === "loading" && <div className="state-card"><span className="spinner" /><strong>Cargando tus exámenes</strong><span>Estamos preparando tu biblioteca.</span></div>}
          {status === "error" && <div className="state-card state-error"><span className="state-symbol">!</span><strong>No pudimos cargar los exámenes</strong><span>{error}</span><button className="button button-subtle" type="button" onClick={reload}>Reintentar</button></div>}
          {status === "success" && exams.length === 0 && <div className="state-card"><span className="state-symbol empty-symbol">✧</span><strong>Tu biblioteca empieza hoy</strong><span>Crea tu primer examen con el formulario de arriba.</span></div>}
          {status === "success" && exams.length > 0 && <div className="exam-grid">{exams.map((exam, index) => <article className="exam-card" key={exam.id}>
            <div className={`exam-art exam-art-${index % 3}`}><span>{String(index + 1).padStart(2, "0")}</span><i aria-hidden="true">✳</i></div>
            <div className="exam-card-body"><div className="exam-card-title"><h3>{exam.title}</h3><button className="delete-button" type="button" aria-label={`Eliminar ${exam.title}`} disabled={pendingAction} onClick={() => remove(exam.id)}>×</button></div><div className="exam-meta"><span>{exam.question_count ?? 0} preguntas</span><span className="exam-tag">EXAMEN</span></div></div>
          </article>)}</div>}
        </div>
      </section>

      <footer><span>QUIZSPACE <i>·</i> DAE LAB 08</span><span>Aprender también es crear.</span></footer>
    </main>
  );
}

