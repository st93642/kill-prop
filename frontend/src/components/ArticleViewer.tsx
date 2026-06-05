import { useState, useEffect } from 'react';
import type { ArticleSummary, ClaimDetail } from '../types';
import * as api from '../api/client';

interface Props {
  articles: ArticleSummary[];
}

export default function ArticleViewer({ articles }: Props) {
  const [selectedArticle, setSelectedArticle] = useState<string | null>(null);
  const [articleDetail, setArticleDetail] = useState<{
    full_text: string;
    claims: ClaimDetail[];
  } | null>(null);

  useEffect(() => {
    if (selectedArticle) {
      api.getArticle(selectedArticle).then(setArticleDetail).catch(() => setArticleDetail(null));
    }
  }, [selectedArticle]);

  if (articles.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📄</div>
        <p>No articles ingested yet. Run the pipeline first.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 16 }}>
      <div>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
          Articles ({articles.length})
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
          {articles.map(a => (
            <button
              key={a.article_id}
              className={`btn ${selectedArticle === a.article_id ? 'btn-primary' : ''}`}
              style={{
                width: '100%',
                justifyContent: 'flex-start',
                padding: '8px 10px',
                textAlign: 'left',
                borderRadius: 6,
                border: '1px solid var(--border)',
                background: selectedArticle === a.article_id ? undefined : 'var(--bg-card)',
              }}
              onClick={() => setSelectedArticle(a.article_id)}
            >
              <div style={{ width: '100%', minWidth: 0 }}>
                <div style={{
                  fontSize: 12,
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: '100%',
                }}>
                  {a.title}
                </div>
                <div style={{
                  fontSize: 10,
                  color: 'var(--text-muted)',
                  marginTop: 2,
                  display: 'flex',
                  gap: 6,
                  alignItems: 'center',
                }}>
                  <span style={{
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}>
                    {a.source}
                  </span>
                  <span>·</span>
                  <span style={{ whiteSpace: 'nowrap' }}>{a.claim_count} claims</span>
                  <span style={{
                    marginLeft: 'auto',
                    fontSize: 9,
                    padding: '1px 5px',
                    borderRadius: 3,
                    background: 'rgba(96,165,250,0.1)',
                    color: 'var(--accent-blue)',
                    whiteSpace: 'nowrap',
                  }}>
                    {a.source_pool.replace(/_/g, ' ')}
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div>
        {!selectedArticle && (
          <div className="empty-state">
            <div className="empty-icon">👈</div>
            <p>Select an article to view its content and extracted claims.</p>
          </div>
        )}
        {selectedArticle && !articleDetail && (
          <div className="loading">
            <div className="spinner" />
            Loading article...
          </div>
        )}
        {articleDetail && (
          <div>
            <div className="pane" style={{ marginBottom: 12 }}>
              <div className="pane-header">
                <span className="pane-icon">📝</span>
                <h3>Full Text</h3>
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                {articleDetail.full_text}
              </p>
            </div>

            <div className="pane">
              <div className="pane-header">
                <span className="pane-icon">🔍</span>
                <h3>Extracted Claims ({articleDetail.claims.length})</h3>
              </div>
              <table className="source-claims-table">
                <thead>
                  <tr>
                    <th>Claim</th>
                    <th>Bucket</th>
                    <th>Arguments</th>
                    <th>Evidence</th>
                    <th>Propaganda</th>
                  </tr>
                </thead>
                <tbody>
                  {articleDetail.claims.map((c, i) => (
                    <tr key={c.claim_id || i}>
                      <td style={{ maxWidth: 250, fontSize: 12, lineHeight: 1.4 }}>
                        <div><strong>Original:</strong> {c.text_original}</div>
                        {c.text_normalized && (
                          <div style={{ color: 'var(--text-muted)', marginTop: 2 }}>
                            <strong>Normalized:</strong> {c.text_normalized}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`source-pool-label ${
                          c.bucket === 'verified_fact' ? 'badge-green' :
                          c.bucket === 'attributed_statement' ? 'badge-blue' :
                          c.bucket === 'inference' ? 'badge-yellow' : 'badge-red'
                        }`}>
                          {c.bucket.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td style={{ fontSize: 11 }}>
                        {Object.entries(c.arguments).map(([k, v]) => (
                          <div key={k}>
                            <strong>{k}:</strong> {v.normalized || v.value}
                            {v.attributed && ' (attributed)'}
                          </div>
                        ))}
                      </td>
                      <td style={{ fontSize: 11 }}>
                        {Object.entries(c.evidence)
                          .filter(([, v]) => v)
                          .map(([k]) => k)
                          .join(', ') || '—'}
                      </td>
                      <td style={{ fontSize: 11 }}>
                        {c.propaganda_flags.length > 0
                          ? c.propaganda_flags.map(f => (
                              <span key={f} className="source-pool-label badge-red" style={{ marginRight: 4 }}>
                                {f}
                              </span>
                            ))
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}