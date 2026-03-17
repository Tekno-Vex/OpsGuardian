import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend
} from 'recharts';

// ⚠️ REPLACE WITH YOUR ACTUAL API GATEWAY URL
const API_BASE = 'https://25rpr9votc.execute-api.us-east-2.amazonaws.com/prod';
const POLL_INTERVAL = 3000;

// ── COLORS ────────────────────────────────────────────────────
const COLORS = {
  green:  '#00c853',
  red:    '#ff1744',
  orange: '#ff6d00',
  blue:   '#7ec8e3',
  purple: '#9c27b0',
  gray:   '#9e9e9e'
};

const PIE_COLORS = ['#00c853', '#ff1744', '#ff6d00', '#7ec8e3'];

// ── SHARED COMPONENTS ─────────────────────────────────────────
function StatCard({ label, value, color = COLORS.blue, subtitle }) {
  return (
    <div style={{
      backgroundColor: '#1e1e2e',
      borderRadius: '12px',
      padding: '24px',
      textAlign: 'center',
      border: `1px solid ${color}33`
    }}>
      <div style={{ color, fontSize: '36px', fontWeight: 'bold' }}>{value}</div>
      <div style={{ color: '#888', fontSize: '12px', marginTop: '4px', textTransform: 'uppercase', letterSpacing: '1px' }}>{label}</div>
      {subtitle && <div style={{ color: '#666', fontSize: '11px', marginTop: '4px' }}>{subtitle}</div>}
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <h2 style={{
      color: COLORS.blue,
      fontSize: '16px',
      fontWeight: 'bold',
      margin: '32px 0 16px',
      textTransform: 'uppercase',
      letterSpacing: '2px',
      borderBottom: `1px solid #ffffff11`,
      paddingBottom: '8px'
    }}>
      {children}
    </h2>
  );
}

// ── LIVE MONITOR TAB ──────────────────────────────────────────
function StatusBadge({ status }) {
  const colors = {
    Resolved:       { bg: '#00c853', label: '✅ RESOLVED' },
    Failed:         { bg: '#ff1744', label: '❌ FAILED' },
    Blocked:        { bg: '#ff6d00', label: '🛡️ BLOCKED' },
    DeniedByHuman:  { bg: '#9c27b0', label: '🚫 DENIED' },
    ApprovalExpired:{ bg: '#ff6d00', label: '⏱️ EXPIRED' },
    Healthy:        { bg: '#00c853', label: '💚 HEALTHY' },
    Unknown:        { bg: '#9e9e9e', label: '❓ UNKNOWN' },
  };
  const c = colors[status] || colors.Unknown;
  return (
    <div style={{
      backgroundColor: c.bg,
      color: 'white',
      padding: '16px 32px',
      borderRadius: '12px',
      fontSize: '20px',
      fontWeight: 'bold',
      display: 'inline-block',
      boxShadow: `0 0 20px ${c.bg}88`
    }}>
      {c.label}
    </div>
  );
}

function IncidentCard({ incident, isLatest }) {
  const statusColors = {
    Resolved: '#00c853',
    Failed:   '#ff1744',
    Blocked:  '#ff6d00',
    DeniedByHuman: '#9c27b0',
    ApprovalExpired: '#ff6d00'
  };
  const color = statusColors[incident.status] || '#9e9e9e';
  const icons = { Resolved: '✅', Failed: '❌', Blocked: '🛡️', DeniedByHuman: '🚫' };

  return (
    <div style={{
      backgroundColor: '#1e1e2e',
      border: `1px solid ${color}44`,
      borderLeft: `4px solid ${color}`,
      borderRadius: '8px',
      padding: '16px',
      marginBottom: '12px',
      fontFamily: 'monospace'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ color, fontWeight: 'bold' }}>
          {icons[incident.status] || '❓'} {incident.status}
          {isLatest && <span style={{ marginLeft: '8px', fontSize: '11px', backgroundColor: '#333', padding: '2px 8px', borderRadius: '4px', color: '#aaa' }}>LATEST</span>}
        </span>
        <span style={{ color: '#666', fontSize: '12px' }}>{incident.timestamp}</span>
      </div>
      <div style={{ color: '#ccc', marginBottom: '6px' }}>
        <span style={{ color: '#888' }}>Alarm:</span> {incident.alarm_type} &nbsp;|&nbsp;
        <span style={{ color: '#888' }}>Instance:</span> {incident.instance_id}
      </div>
      {incident.command && incident.command !== 'none' && (
        <div style={{ color: '#7ec8e3', marginBottom: '6px' }}>
          <span style={{ color: '#888' }}>Command:</span>{' '}
          <code style={{ backgroundColor: '#2a2a3e', padding: '2px 6px', borderRadius: '4px' }}>{incident.command}</code>
        </div>
      )}
      {incident.similarity_score && incident.similarity_score !== 'N/A' && (
        <div style={{ color: '#888', fontSize: '12px', marginBottom: '4px' }}>
          RAG Match: {incident.rag_match_id} — {(parseFloat(incident.similarity_score) * 100).toFixed(1)}% confidence
        </div>
      )}
      <div style={{ color: '#b0b0b0', fontSize: '13px', lineHeight: '1.5' }}>
        <span style={{ color: '#888' }}>Reasoning:</span> {incident.reasoning}
      </div>
    </div>
  );
}

function LiveMonitorTab() {
  const [data,       setData]       = useState(null);
  const [error,      setError]      = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [pulse,      setPulse]      = useState(false);

  const fetchData = async () => {
    try {
      const response = await axios.get(`${API_BASE}/status`);
      setData(response.data);
      setLastUpdate(new Date().toLocaleTimeString());
      setPulse(true);
      setTimeout(() => setPulse(false), 500);
      setError(null);
    } catch (err) {
      setError('Failed to reach OpsGuardian API');
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  const systemStatus = data?.system_status || 'Healthy';
  const stats        = data?.stats         || {};
  const incidents    = data?.all_incidents || [];

  return (
    <div>
      {error && (
        <div style={{ backgroundColor: '#ff174422', border: '1px solid #ff1744', borderRadius: '8px', padding: '12px 16px', marginBottom: '24px', color: '#ff1744' }}>
          ⚠️ {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px', marginBottom: '32px' }}>
        <div style={{ gridColumn: '1 / 2', backgroundColor: '#1e1e2e', borderRadius: '12px', padding: '24px', textAlign: 'center' }}>
          <div style={{ color: '#888', marginBottom: '12px', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px' }}>System Status</div>
          <StatusBadge status={systemStatus} />
        </div>
        <StatCard label="Total Incidents" value={stats.total    || 0} color={COLORS.blue} />
        <StatCard label="Resolved"        value={stats.resolved || 0} color={COLORS.green} />
        <StatCard label="Failed"          value={stats.failed   || 0} color={COLORS.red} />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 style={{ color: COLORS.blue, margin: 0, fontSize: '18px' }}>📋 Incident Log</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#666', fontSize: '13px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: pulse ? '#00c853' : '#00c85388', transition: 'background-color 0.3s' }} />
          Live — polling every 3s | Last update: {lastUpdate || '...'}
        </div>
      </div>

      {incidents.length === 0 ? (
        <div style={{ backgroundColor: '#1e1e2e', borderRadius: '12px', padding: '40px', textAlign: 'center', color: '#666' }}>
          No incidents recorded yet. Run the chaos script to trigger OpsGuardian!
        </div>
      ) : (
        incidents.map((incident, idx) => (
          <IncidentCard key={incident.incident_id} incident={incident} isLatest={idx === 0} />
        ))
      )}
    </div>
  );
}

// ── ANALYTICS TAB ─────────────────────────────────────────────
function AnalyticsTab() {
  const [data,       setData]       = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API_BASE}/analytics`);
      setData(response.data);
      setLastUpdate(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Analytics fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading) return (
    <div style={{ textAlign: 'center', padding: '80px', color: '#666' }}>
      Loading analytics...
    </div>
  );

  if (!data) return (
    <div style={{ textAlign: 'center', padding: '80px', color: '#666' }}>
      No analytics data available yet.
    </div>
  );

  // Prepare chart data
  const hourData = Object.entries(data.incidents_by_hour || {})
    .map(([hour, count]) => ({ hour: `${hour}:00`, count }))
    .sort((a, b) => a.hour.localeCompare(b.hour));

  const alarmData = Object.entries(data.top_alarms || {})
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  const pieData = [
    { name: 'Resolved', value: data.resolved_count || 0 },
    { name: 'Failed',   value: data.failed_count   || 0 },
    { name: 'Blocked',  value: data.blocked_count  || 0 },
    { name: 'Denied',   value: data.denied_count   || 0 },
  ].filter(d => d.value > 0);

  const trendData = (data.incidents_last_7_days || []).map(d => ({
    date:  d.date.slice(5),  // show MM-DD only
    count: d.count
  }));

  const commandData = Object.entries(data.command_success_rates || {})
    .map(([cmd, rate]) => ({ cmd, rate: Math.round(rate * 100) }));

  return (
    <div>
      {/* KPI Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '8px' }}>
        <StatCard
          label="Avg MTTR"
          value={`${data.mttr_minutes}m`}
          color={COLORS.blue}
          subtitle="Mean Time To Resolve"
        />
        <StatCard
          label="Success Rate"
          value={`${Math.round((data.success_rate || 0) * 100)}%`}
          color={data.success_rate >= 0.8 ? COLORS.green : COLORS.red}
          subtitle="Resolved / Total"
        />
        <StatCard
          label="Total Incidents"
          value={data.total_incidents || 0}
          color={COLORS.blue}
          subtitle="All time"
        />
        <StatCard
          label="Resolved"
          value={data.resolved_count || 0}
          color={COLORS.green}
          subtitle={`${data.failed_count || 0} failed, ${data.blocked_count || 0} blocked`}
        />
      </div>

      {/* Row 1: Pie + Trend */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '16px', marginTop: '24px' }}>

        {/* Outcome Distribution Donut */}
        <div style={{ backgroundColor: '#1e1e2e', borderRadius: '12px', padding: '24px' }}>
          <SectionTitle>Outcome Distribution</SectionTitle>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e1e2e', border: '1px solid #333', borderRadius: '8px', color: '#fff' }}
                />
                <Legend
                  formatter={(value) => <span style={{ color: '#ccc', fontSize: '12px' }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: '#666', textAlign: 'center', padding: '40px' }}>No data yet</div>
          )}
        </div>

        {/* 7-Day Trend */}
        <div style={{ backgroundColor: '#1e1e2e', borderRadius: '12px', padding: '24px' }}>
          <SectionTitle>7-Day Incident Trend</SectionTitle>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff11" />
              <XAxis dataKey="date" tick={{ fill: '#888', fontSize: 12 }} />
              <YAxis tick={{ fill: '#888', fontSize: 12 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e1e2e', border: '1px solid #333', borderRadius: '8px', color: '#fff' }}
              />
              <Line type="monotone" dataKey="count" stroke={COLORS.blue} strokeWidth={2} dot={{ fill: COLORS.blue, r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 2: Incidents by Hour */}
      <div style={{ backgroundColor: '#1e1e2e', borderRadius: '12px', padding: '24px', marginTop: '16px' }}>
        <SectionTitle>Incidents by Hour of Day (UTC)</SectionTitle>
        {hourData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={hourData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff11" />
              <XAxis dataKey="hour" tick={{ fill: '#888', fontSize: 11 }} />
              <YAxis tick={{ fill: '#888', fontSize: 12 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e1e2e', border: '1px solid #333', borderRadius: '8px', color: '#fff' }}
              />
              <Bar dataKey="count" fill={COLORS.blue} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ color: '#666', textAlign: 'center', padding: '40px' }}>No data yet</div>
        )}
      </div>

      {/* Row 3: Top Alarms + Command Success Rates */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>

        {/* Top Alarm Types */}
        <div style={{ backgroundColor: '#1e1e2e', borderRadius: '12px', padding: '24px' }}>
          <SectionTitle>Top Alarm Types</SectionTitle>
          {alarmData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={alarmData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff11" />
                <XAxis type="number" tick={{ fill: '#888', fontSize: 12 }} allowDecimals={false} />
                <YAxis type="category" dataKey="name" tick={{ fill: '#ccc', fontSize: 12 }} width={100} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e1e2e', border: '1px solid #333', borderRadius: '8px', color: '#fff' }}
                />
                <Bar dataKey="count" fill={COLORS.purple} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: '#666', textAlign: 'center', padding: '40px' }}>No data yet</div>
          )}
        </div>

        {/* Command Success Rates */}
        <div style={{ backgroundColor: '#1e1e2e', borderRadius: '12px', padding: '24px' }}>
          <SectionTitle>Command Success Rates</SectionTitle>
          {commandData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={commandData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff11" />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#888', fontSize: 12 }} unit="%" />
                <YAxis type="category" dataKey="cmd" tick={{ fill: '#ccc', fontSize: 11 }} width={140} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e1e2e', border: '1px solid #333', borderRadius: '8px', color: '#fff' }}
                  formatter={(v) => [`${v}%`, 'Success Rate']}
                />
                <Bar dataKey="rate" fill={COLORS.green} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: '#666', textAlign: 'center', padding: '40px' }}>No data yet</div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{ textAlign: 'center', marginTop: '24px', color: '#444', fontSize: '12px' }}>
        Last updated: {lastUpdate || '...'} — refreshes every 10 seconds
      </div>
    </div>
  );
}

// ── MAIN APP ──────────────────────────────────────────────────
export default function App() {
  const [activeTab, setActiveTab] = useState('monitor');

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#0d0d1a',
      color: '#e0e0e0',
      fontFamily: "'Segoe UI', sans-serif",
      padding: '24px'
    }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <h1 style={{ color: COLORS.blue, fontSize: '36px', margin: 0, letterSpacing: '3px', textTransform: 'uppercase' }}>
          🛡️ OpsGuardian
        </h1>
        <p style={{ color: '#666', margin: '8px 0 0' }}>
          Autonomous Cloud SRE — Mission Control
        </p>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '32px', borderBottom: '1px solid #ffffff11', paddingBottom: '0' }}>
        {[
          { id: 'monitor',   label: '📡 Live Monitor' },
          { id: 'analytics', label: '📊 Analytics' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              background:    'none',
              border:        'none',
              color:          activeTab === tab.id ? COLORS.blue : '#666',
              fontSize:      '15px',
              fontWeight:    activeTab === tab.id ? 'bold' : 'normal',
              padding:       '12px 24px',
              cursor:        'pointer',
              borderBottom:  activeTab === tab.id ? `2px solid ${COLORS.blue}` : '2px solid transparent',
              marginBottom:  '-1px',
              transition:    'all 0.2s'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'monitor'   && <LiveMonitorTab />}
      {activeTab === 'analytics' && <AnalyticsTab />}

      {/* Footer */}
      <div style={{ textAlign: 'center', marginTop: '40px', color: '#444', fontSize: '12px' }}>
        OpsGuardian — Autonomous SRE Agent &nbsp;|&nbsp; Amazon Bedrock Nova Micro &nbsp;|&nbsp; AWS Lambda + SSM + DynamoDB
      </div>
    </div>
  );
}