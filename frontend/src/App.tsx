import { useState, useEffect, useCallback } from 'react';
import './App.css';
import * as api from './api/client';
import type {
  DashboardStats,
  EventSummary,
  EventDetail,
  ArticleSummary,
} from './types';
import EventFeed from './components/EventFeed';
import EventDetailView from './components/EventDetail';
import ReviewConsole from './components/ReviewConsole';
import PipelineRunner from './components/PipelineRunner';
import ArticleViewer from './components/ArticleViewer';

type View = 'events' | 'detail' | 'review' | 'articles' | 'pipeline';

function App() {
  const [currentView, setCurrentView] = useState<View>('pipeline');
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [eventDetail, setEventDetail] = useState<EventDetail | null>(null);
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [pipelineComplete, setPipelineComplete] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState({ pool: '', min_confidence: '', topic: '' });

  const loadEvents = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listEvents(filter);
      setEvents(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  const loadArticles = useCallback(async () => {
    try {
      const data = await api.listArticles();
      setArticles(data);
    } catch (err: any) {
      // Articles may not be ingested yet
      setArticles([]);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const data = await api.getReviewDashboard();
      setStats(data);
    } catch {
      // Stats may not be available
    }
  }, []);

  const handlePipelineComplete = useCallback(() => {
    setPipelineComplete(true);
    setCurrentView('events');
  }, []);

  const handleSelectEvent = async (eventId: string) => {
    setLoading(true);
    try {
      const detail = await api.getEventDetail(eventId);
      setEventDetail(detail);
      setSelectedEventId(eventId);
      setCurrentView('detail');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setCurrentView('events');
    setSelectedEventId(null);
    setEventDetail(null);
    loadEvents();
    loadStats();
  };

  const handleRefresh = async () => {
    loadEvents();
    loadStats();
    loadArticles();
  };

  // Load data when switching to a view
  useEffect(() => {
    if (currentView === 'events') loadEvents();
    if (currentView === 'review') { loadEvents(); loadStats(); }
    if (currentView === 'articles') loadArticles();
  }, [currentView, loadEvents, loadArticles, loadStats]);

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>kill-prop</h1>
          <div className="subtitle">Source Triangulation Analyzer</div>
        </div>
        <nav className="sidebar-nav">
          <button
            className={currentView === 'pipeline' ? 'active' : ''}
            onClick={() => setCurrentView('pipeline')}
          >
            <span className="nav-icon">⚡</span>
            Pipeline
          </button>
          <button
            className={currentView === 'events' ? 'active' : ''}
            onClick={() => setCurrentView('events')}
          >
            <span className="nav-icon">📰</span>
            Event Feed
          </button>
          <button
            className={currentView === 'review' ? 'active' : ''}
            onClick={() => setCurrentView('review')}
          >
            <span className="nav-icon">🔍</span>
            Review Console
          </button>
          <button
            className={currentView === 'articles' ? 'active' : ''}
            onClick={() => setCurrentView('articles')}
          >
            <span className="nav-icon">📄</span>
            Articles
          </button>
        </nav>
        <div className="sidebar-footer">
          v0.1.0 • {stats ? `${stats.total_events} events` : '...'}
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        <div className="top-header">
          <h2>
            {currentView === 'pipeline' && 'Pipeline Runner'}
            {currentView === 'events' && 'Event Feed'}
            {currentView === 'detail' && (eventDetail?.title || 'Event Detail')}
            {currentView === 'review' && 'Review Console'}
            {currentView === 'articles' && 'Articles'}
          </h2>
          <div className="header-actions">
            {currentView !== 'pipeline' && (
              <button className="btn btn-sm" onClick={handleRefresh}>
                ↻ Refresh
              </button>
            )}
            {currentView === 'detail' && (
              <button className="btn btn-sm" onClick={handleBack}>
                ← Back to Events
              </button>
            )}
          </div>
        </div>

        <div className="content-area">
          {error && (
            <div className="pipeline-status" style={{ borderColor: 'var(--accent-red)' }}>
              <span style={{ color: 'var(--accent-red)' }}>⚠️ {error}</span>
              <button className="btn btn-sm btn-danger" onClick={() => setError(null)}>Dismiss</button>
            </div>
          )}

          {currentView === 'pipeline' && (
            <PipelineRunner onComplete={handlePipelineComplete} />
          )}

          {currentView === 'events' && (
            <EventFeed
              events={events}
              loading={loading}
              filter={filter}
              onFilterChange={setFilter}
              onSelectEvent={handleSelectEvent}
              onRefresh={loadEvents}
            />
          )}

          {currentView === 'detail' && eventDetail && (
            <EventDetailView
              event={eventDetail}
              onBack={handleBack}
              onUpdate={handleSelectEvent}
            />
          )}

          {currentView === 'review' && (
            <ReviewConsole
              events={events}
              stats={stats}
              loading={loading}
              onSelectEvent={handleSelectEvent}
              onRefresh={loadEvents}
            />
          )}

          {currentView === 'articles' && (
            <ArticleViewer articles={articles} />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;