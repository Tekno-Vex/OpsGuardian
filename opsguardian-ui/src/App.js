import React, { useState, useEffect } from 'react';
import axios from 'axios';

// ⚠️ REPLACE THIS WITH YOUR ACTUAL API GATEWAY URL
const API_URL = 'https://25rpr9votc.execute-api.us-east-2.amazonaws.com/prod/status';

const POLL_INTERVAL = 3000; // 3 seconds

function StatusBadge({ status }) {
  const colors = {
    Resolved: { bg: '#00c853', text: 'white',  label: '✅ RESOLVED'  },
    Failed:   { bg: '#ff1744', text: 'white',  label: '❌ FAILED'    },
    Blocked:  { bg: '#ff6d00', text: 'white',  label: '🛡️ BLOCKED'   },
    Healthy:  { bg: '#00c853', text: 'white',  label: '💚 HEALTHY'   },
    Unknown:  { bg: '#9e9e9e', text: 'white',  label: '❓ UNKNOWN'   },
  };
  const c = colors[status] || colors.Unknown;
  return (
    <div style={{
      backgroundColor: c.bg,
      color: c.text,
      padding: '20px 40px',
      borderRadius: '12px',
      fontSize: '24px',
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
  };
  const color = statusColors[incident.status] || '#9e9e9e';

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
        <span style={{ color: color, fontWeight: 'bold' }}>
          {incident.status === 'Resolved' ? '✅' : incident.status === 'Blocked' ? '🛡️' : '❌'} {incident.status}
          {isLatest && <span style={{ marginLeft: '8px', fontSize: '11px', backgroundColor: '#333', padding: '2px 8px', borderRadius: '4px', color: '#aaa' }}>LATEST</span>}
        </span>
        <span style={{ color: '#666', fontSize: '12px' }}>{incident.timestamp}</span>
      </div>
      <div style={{ color: '#ccc', marginBottom: '6px' }}>
        <span style={{ color: '#888' }}>Alarm:</span> {incident.alarm_type} &nbsp;|&nbsp;
        <span style={{ color: '#888' }}>Instance:</span> {incident.instance_id}
      </div>
      <div style={{ color: '#7ec8e3', marginBottom: '6px' }}>
        <span style={{ color: '#888' }}>Command:</span> <code style={{ backgroundColor: '#2a2a3e', padding: '2px 6px', borderRadius: '4px' }}>{incident.command}</code>
      </div>
      <div style={{ color: '#b0b0b0', fontSize: '13px', lineHeight: '1.5' }}>
        <span style={{ color: '#888' }}>Reasoning:</span> {incident.reasoning}
      </div>
    </div>
  );
}

export default function App() {
  const [data,       setData]       = useState(null);
  const [error,      setError]      = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [pulse,      setPulse]      = useState(false);

  const fetchData = async () => {
    try {
      const response = await axios.get(API_URL);
      setData(response.data);
      setLastUpdate(new Date().toLocaleTimeString());
      setPulse(true);
      setTimeout(() => setPulse(false), 500);
      setError(null);
    } catch (err) {
      setError('Failed to reach OpsGuardian API — is the API Gateway deployed?');
      console.error(err);
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
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#0d0d1a',
      color: '#e0e0e0',
      fontFamily: "'Segoe UI', sans-serif",
      padding: '24px'
    }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <h1 style={{
          color: '#7ec8e3',
          fontSize: '36px',
          margin: 0,
          letterSpacing: '3px',
          textTransform: 'uppercase'
        }}>
          🛡️ OpsGuardian
        </h1>
        <p style={{ color: '#666', margin: '8px 0 0' }}>
          Autonomous Cloud SRE — Mission Control
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div style={{
          backgroundColor: '#ff174422',
          border: '1px solid #ff1744',
          borderRadius: '8px',
          padding: '12px 16px',
          marginBottom: '24px',
          color: '#ff1744'
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Status + Stats Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr',
        gap: '16px',
        marginBottom: '32px',
        alignItems: 'center'
      }}>
        {/* System Status */}
        <div style={{
          gridColumn: '1 / 3',
          backgroundColor: '#1e1e2e',
          borderRadius: '12px',
          padding: '24px',
          textAlign: 'center'
        }}>
          <div style={{ color: '#888', marginBottom: '12px', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px' }}>System Status</div>
          <StatusBadge status={systemStatus} />
        </div>

        {/* Stats */}
        {[
          { label: 'Total Incidents', value: stats.total    || 0, color: '#7ec8e3' },
          { label: 'Resolved',        value: stats.resolved || 0, color: '#00c853' },
          { label: 'Failed',          value: stats.failed   || 0, color: '#ff1744' },
        ].map(stat => (
          <div key={stat.label} style={{
            backgroundColor: '#1e1e2e',
            borderRadius: '12px',
            padding: '24px',
            textAlign: 'center',
          }}>
            <div style={{ color: stat.color, fontSize: '36px', fontWeight: 'bold' }}>{stat.value}</div>
            <div style={{ color: '#888', fontSize: '12px', marginTop: '4px', textTransform: 'uppercase', letterSpacing: '1px' }}>{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Live Indicator */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px'
      }}>
        <h2 style={{ color: '#7ec8e3', margin: 0, fontSize: '18px' }}>
          📋 Incident Log
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#666', fontSize: '13px' }}>
          <div style={{
            width: '8px', height: '8px',
            borderRadius: '50%',
            backgroundColor: pulse ? '#00c853' : '#00c85388',
            transition: 'background-color 0.3s'
          }} />
          Live — polling every 3s &nbsp;|&nbsp; Last update: {lastUpdate || '...'}
        </div>
      </div>

      {/* Incident Cards */}
      {incidents.length === 0 ? (
        <div style={{
          backgroundColor: '#1e1e2e',
          borderRadius: '12px',
          padding: '40px',
          textAlign: 'center',
          color: '#666'
        }}>
          No incidents recorded yet. Run the chaos script to trigger OpsGuardian!
        </div>
      ) : (
        incidents.map((incident, idx) => (
          <IncidentCard
            key={incident.incident_id}
            incident={incident}
            isLatest={idx === 0}
          />
        ))
      )}

      {/* Footer */}
      <div style={{ textAlign: 'center', marginTop: '40px', color: '#444', fontSize: '12px' }}>
        OpsGuardian — Autonomous SRE Agent &nbsp;|&nbsp; Amazon Bedrock Nova Micro &nbsp;|&nbsp; AWS Lambda + SSM + DynamoDB
      </div>
    </div>
  );
}