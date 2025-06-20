import React, { useState } from 'react';
import './App.css';

const initialSections = [
  { title: 'sin2eng Input', input: '', response: '', loading: false, endpoint: '/translate/sin2eng' },
  { title: 'T5 Input', input: '', response: '', loading: false, endpoint: '/translate/T5' },
];

function App() {
  const [sections, setSections] = useState(initialSections);

  const handleInputChange = (idx, value) => {
    setSections(sections =>
      sections.map((sec, i) =>
        i === idx ? { ...sec, input: value } : sec
      )
    );
  };

  const handleSubmit = async (idx, e) => {
    e.preventDefault();
    if (!sections[idx].input.trim()) return;

    setSections(sections =>
      sections.map((sec, i) =>
        i === idx ? { ...sec, loading: true, response: '' } : sec
      )
    );

    try {
      const res = await fetch(`http://localhost:5000${sections[idx].endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: sections[idx].input }),
      });
      const data = await res.json();
      setSections(sections =>
        sections.map((sec, i) =>
          i === idx
            ? { ...sec, response: data.english || 'No response', loading: false }
            : sec
        )
      );
    } catch (err) {
      setSections(sections =>
        sections.map((sec, i) =>
          i === idx
            ? { ...sec, response: 'Error contacting backend', loading: false }
            : sec
        )
      );
    }
  };

  return (
    <div className="app-bg">
      <div className="card">
        <div className="translator-label">Translator</div>
        {sections.map((section, idx) => (
          <div key={idx} className="section-block">
            <div className="section-title">{section.title}</div>
            <form className="input-form" onSubmit={e => handleSubmit(idx, e)}>
              <textarea
                value={section.input}
                onChange={e => handleInputChange(idx, e.target.value)}
                placeholder={`Enter text for ${section.title.toLowerCase()}...`}
                className="input-field input-textarea"
                disabled={section.loading}
                autoFocus={idx === 0}
                rows="3"
              />
              <button
                type="submit"
                className="submit-button"
                disabled={section.loading || !section.input.trim()}
              >
                {section.loading ? (
                  <span className="loader"></span>
                ) : (
                  'Translate'
                )}
              </button>
            </form>
            <div
              className={`response-area response-textarea${section.response ? ' response-visible' : ''}`}
            >
              {section.response}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
