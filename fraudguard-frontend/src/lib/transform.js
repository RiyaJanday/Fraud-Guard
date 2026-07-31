// Maps real backend response shapes (snake_case, decision enums, SHAP
// arrays, decision_history, etc.) onto the shape the UI components were
// originally built against with mockData.js. Keeping this mapping in one
// place means Dashboard/Transactions/TransactionTable/TransactionDrawer
// didn't need to be rewritten field-by-field.

const DECISION_TO_STATUS = {
  approve: 'approved',
  mfa_required: 'mfa',
  blocked: 'blocked',
}

export function statusToDecision(status) {
  const map = { approved: 'approve', mfa: 'mfa_required', blocked: 'blocked' }
  return map[status] || null
}

export function timeAgo(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime()
  const mins = Math.round(diffMs / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs} hr ago`
  const days = Math.round(hrs / 24)
  return `${days}d ago`
}

/** TransactionOut (list item) -> mock-shaped row for TransactionTable */
export function mapTransactionListItem(t) {
  return {
    id: t.id,
    merchant: t.merchant || 'Unknown Merchant',
    amount: t.amount,
    currency: t.currency,
    timestamp: t.created_at,
    risk: t.risk_score != null ? Math.round(t.risk_score) : 0,
    status: DECISION_TO_STATUS[t.decision] || 'approved',
    customer: t.customer_reference || '—',
  }
}

/** TransactionDetailOut -> mock-shaped detail object for TransactionDrawer */
export function mapTransactionDetail(t) {
  const pred = t.prediction
  const risk = pred ? Math.round(pred.risk_score) : 0
  const status = pred ? DECISION_TO_STATUS[pred.decision] || 'approved' : 'approved'

  const shap = (pred?.top_shap_features || []).map((f) => ({
    key: f.feature,
    label: f.label,
    impact: f.impact,
  }))

  const history = (t.decision_history || []).map((h) => ({
    step: h.message || `${h.stage} ${h.status}`,
    time: new Date(h.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true }),
    actor: h.stage === 'prediction' ? 'FraudGuard AI Engine' : 'FraudGuard Pipeline',
  }))

  return {
    id: t.id,
    merchant: t.merchant || 'Unknown Merchant',
    amount: t.amount,
    currency: t.currency,
    timestamp: t.created_at,
    risk,
    status,
    city: t.location || '—',
    card: t.card_last4 ? `•••• ${t.card_last4}` : '—',
    device: t.device_info || '—',
    customer: t.customer_reference || '—',
    shap: shap.length ? shap : [{ key: 'no_data', label: 'No SHAP data available', impact: 0 }],
    history: history.length ? history : [{ step: 'Transaction recorded', time: '', actor: 'FraudGuard' }],
    explanationText: pred?.explanation,
  }
}

/** DashboardStatsOut -> mock-shaped stats object */
export function mapDashboardStats(s) {
  return {
    totalTransactions: s.total_transactions,
    fraudDetected: s.fraud_detected,
    fraudBlocked: s.fraud_blocked,
    detectionAccuracy: s.detection_accuracy,
    avgRiskScore: s.avg_risk_score,
    deltas: {
      totalTransactions: s.deltas.total_transactions,
      fraudDetected: s.deltas.fraud_detected,
      fraudBlocked: s.deltas.fraud_blocked,
      detectionAccuracy: s.deltas.detection_accuracy,
      avgRiskScore: s.deltas.avg_risk_score,
    },
  }
}

/** DashboardChartsOut -> the 5 chart-shaped objects the Dashboard page expects */
export function mapDashboardCharts(c) {
  return {
    volume: c.volume,
    distribution: c.fraud_distribution,
    trend: c.risk_trend,
    performance: c.model_performance,
    heatmap: c.heatmap,
    heatmapHours: c.heatmap_hours,
  }
}

/** AlertOut[] -> mock-shaped RECENT_ALERTS */
export function mapAlerts(alerts) {
  return alerts.map((a) => ({
    id: a.id,
    title: a.title,
    merchant: a.merchant || '—',
    risk: Math.round(a.risk_score),
    time: timeAgo(a.time),
    severity: a.severity,
  }))
}
