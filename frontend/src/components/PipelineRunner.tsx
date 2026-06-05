import { useState } from 'react';
import * as api from '../api/client';

interface Props {
  onComplete: () => void;
}

export default function PipelineRunner({ onComplete }: Props) {
  const [status, setStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [log, setLog] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);
  const [useLLM, setUseLLM] = useState(false);
  const [useAPI, setUseAPI] = useState(false);

  const handleRun = async () => {
    setStatus('running');
    setLog([]);
    setResult(null);

    try {
      setLog(prev => [...prev, `🚀 Stage 1-2: Ingesting & normalizing articles... (Source: ${useAPI ? 'Live API' : 'Seed data'}, LLM: ${useLLM ? 'ON' : 'OFF'})`]);
      setLog(prev => [...prev, '📦 Stage 3-4: Extracting claims & clustering events...']);
      setLog(prev => [...prev, '🎯 Stage 5-6: Running consensus, scoring & presentation...']);

      const pipelineResult = await api.runPipeline(useLLM, useAPI);
      setLog(prev => [...prev, `   ✅ ${pipelineResult.summary}`]);
      setResult(pipelineResult);

      setLog(prev => [...prev, '✅ Pipeline complete!']);
      setStatus('done');
    } catch (err: any) {
      setLog(prev => [...prev, `❌ Error: ${err.message}`]);
      setStatus('idle');
    }
  };

  return (
    <div>
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-value blue">6</div>
          <div className="stat-label">Pipeline Stages</div>
        </div>
        <div className="stat-card">
          <div className="stat-value green">{status === 'done' ? 'Complete' : 'Ready'}</div>
          <div className="stat-label">Status</div>
        </div>
        <div className="stat-card">
          <div className="stat-value purple">MVP</div>
          <div className="stat-label">Version</div>
        </div>
      </div>

      <div className="pipeline-status">
        {['Source Intake', 'Normalization', 'Clustering', 'Extraction', 'Scoring', 'Presentation'].map(
          (step, i) => (
            <span key={step}>
              <span
                className={`pipeline-step ${
                  status === 'done'
                    ? 'completed'
                    : status === 'running' && i <= log.length
                    ? 'active'
                    : ''
                }`}
              >
                {status === 'done' ? '✓' : status === 'running' && i === log.length - 1 ? '⟳' : '○'} {step}
              </span>
              {i < 5 && <span className="pipeline-separator">→</span>}
            </span>
          )
        )}
      </div>

      <div style={{ background: 'var(--bg-card)', borderRadius: 8, border: '1px solid var(--border)', padding: 16, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Pipeline Console</h3>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-muted)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={useLLM}
                onChange={(e) => setUseLLM(e.target.checked)}
                disabled={status === 'running'}
                style={{ cursor: 'pointer' }}
              />
              LLM
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-muted)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={useAPI}
                onChange={(e) => setUseAPI(e.target.checked)}
                disabled={status === 'running'}
                style={{ cursor: 'pointer' }}
              />
              Live API
            </label>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleRun}
            disabled={status === 'running'}
          >
            {status === 'running' ? '⟳ Running...' : '▶ Run Full Pipeline'}
          </button>
        </div>

        <div
          style={{
            background: '#000',
            borderRadius: 6,
            padding: 12,
            fontFamily: 'monospace',
            fontSize: 12,
            lineHeight: 1.7,
            minHeight: 200,
            maxHeight: 400,
            overflow: 'auto',
            color: '#34d399',
          }}
        >
          {log.length === 0 ? (
            <span style={{ color: '#6b7280' }}>Click "Run Full Pipeline" to start the 6-stage process...</span>
          ) : (
            log.map((line, i) => <div key={i}>{line}</div>)
          )}
        </div>
      </div>

      {result && (
        <div className="pane">
          <div className="pane-header">
            <span className="pane-icon">📊</span>
            <h3>Pipeline Results</h3>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            {Object.entries(result.stages).map(([stage, data]: [string, any]) => (
              <div key={stage}>
                <strong style={{ color: 'var(--accent-blue)' }}>{stage.replace(/_/g, ' ')}:</strong>{' '}
                {Object.entries(data).map(([k, v]) => `${k}: ${v}`).join(', ')}
              </div>
            ))}
            <div style={{ marginTop: 8, padding: '8px 12px', background: 'rgba(52,211,153,0.1)', borderRadius: 6, color: 'var(--accent-green)' }}>
              {result.summary}
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <button className="btn btn-primary" onClick={onComplete}>
              View Event Feed →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}