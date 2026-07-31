// Deterministic-ish mock data generators for FraudGuard.
// In production these would be replaced by calls through src/lib/api.js

const MERCHANTS = [
  'Amazon.in', 'Swiggy', 'Zomato', 'Flipkart', 'Apple Store', 'Uber', 'Netflix',
  'BigBasket', 'MakeMyTrip', 'IRCTC', 'Myntra', 'PayPal Transfer', 'Steam',
  'BookMyShow', 'Reliance Digital', 'Croma Electronics', 'Airbnb', 'Ola Cabs',
]

const CITIES = [
  'Mumbai, IN', 'Bengaluru, IN', 'Delhi, IN', 'Ahmedabad, IN', 'Pune, IN',
  'Lagos, NG', 'Moscow, RU', 'Jakarta, ID', 'São Paulo, BR', 'Dubai, AE',
  'London, UK', 'Singapore, SG', 'New York, US',
]

const CARD_TYPES = ['Visa •••• 4471', 'Mastercard •••• 8823', 'RuPay •••• 1190', 'Amex •••• 3005']

const DEVICES = ['iOS App v4.2', 'Android App v4.2', 'Chrome / Windows', 'Safari / macOS', 'POS Terminal #22']

function seededRandom(seed) {
  let value = seed
  return () => {
    value = (value * 9301 + 49297) % 233280
    return value / 233280
  }
}

const rand = seededRandom(42)

function pick(arr) {
  return arr[Math.floor(rand() * arr.length)]
}

function statusFromRisk(risk) {
  if (risk >= 75) return 'blocked'
  if (risk >= 40) return 'mfa'
  return 'approved'
}

export const SHAP_FEATURE_POOL = [
  { key: 'txn_velocity', label: 'Transaction velocity (5 min window)' },
  { key: 'geo_mismatch', label: 'Billing / device geo mismatch' },
  { key: 'amount_deviation', label: 'Deviation from average spend' },
  { key: 'merchant_risk', label: 'Merchant risk category' },
  { key: 'device_trust', label: 'Device trust score' },
  { key: 'time_of_day', label: 'Unusual transaction hour' },
  { key: 'card_age', label: 'Card account age' },
  { key: 'ip_reputation', label: 'IP reputation score' },
  { key: 'cvv_retries', label: 'CVV entry retries' },
  { key: 'prior_chargebacks', label: 'Prior chargeback history' },
]

function generateShapFeatures(risk) {
  const shuffled = [...SHAP_FEATURE_POOL].sort(() => rand() - 0.5).slice(0, 5)
  return shuffled
    .map((f) => ({
      ...f,
      impact: +(rand() * (risk / 100) * 0.4 + (rand() > 0.5 ? 0.02 : -0.06)).toFixed(3),
    }))
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
}

export function generateTransactions(count = 60) {
  const now = Date.now()
  return Array.from({ length: count }).map((_, i) => {
    const risk = Math.round(rand() * 100)
    const status = statusFromRisk(risk)
    const amount = +(rand() * (risk > 60 ? 90000 : 12000) + 99).toFixed(2)
    const timestamp = new Date(now - i * (rand() * 6 + 2) * 60 * 1000)
    return {
      id: `TXN-${(84210 + i).toString(36).toUpperCase()}-${7000 + i}`,
      merchant: pick(MERCHANTS),
      amount,
      currency: 'INR',
      timestamp: timestamp.toISOString(),
      risk,
      status,
      city: pick(CITIES),
      card: pick(CARD_TYPES),
      device: pick(DEVICES),
      customer: `Customer #${10432 + i}`,
      shap: generateShapFeatures(risk),
      history: [
        { step: 'Transaction initiated', time: '-2.4s', actor: 'Payment Gateway' },
        { step: 'Risk model scored transaction', time: '-1.1s', actor: 'FraudGuard AI Engine' },
        {
          step: status === 'blocked' ? 'Transaction blocked automatically' : status === 'mfa' ? 'Step-up authentication requested' : 'Transaction approved',
          time: '-0.3s',
          actor: 'FraudGuard AI Engine',
        },
      ],
    }
  })
}

export const TRANSACTIONS = generateTransactions(80)

export function getDashboardStats() {
  const total = 128492
  const fraud = 1042
  const blocked = 812
  return {
    totalTransactions: total,
    fraudDetected: fraud,
    fraudBlocked: blocked,
    detectionAccuracy: 98.7,
    avgRiskScore: 24.3,
    deltas: {
      totalTransactions: 8.2,
      fraudDetected: -3.1,
      fraudBlocked: 5.6,
      detectionAccuracy: 0.4,
      avgRiskScore: -1.8,
    },
  }
}

export function getVolumeSeries() {
  const labels = Array.from({ length: 24 }).map((_, i) => `${i}:00`)
  const legit = labels.map(() => Math.round(400 + rand() * 500))
  const fraud = labels.map(() => Math.round(rand() * 40))
  return { labels, legit, fraud }
}

export function getFraudDistribution() {
  return {
    labels: ['Card Testing', 'Account Takeover', 'Stolen Card', 'Synthetic Identity', 'Friendly Fraud'],
    values: [28, 24, 21, 15, 12],
  }
}

export function getRiskTrend() {
  const labels = Array.from({ length: 14 }).map((_, i) => `Day ${i + 1}`)
  let base = 30
  const values = labels.map(() => {
    base += (rand() - 0.5) * 8
    base = Math.max(10, Math.min(70, base))
    return Math.round(base)
  })
  return { labels, values }
}

export function getModelPerformance() {
  return {
    labels: ['Precision', 'Recall', 'F1 Score', 'AUC-ROC', 'Specificity', 'Accuracy'],
    values: [96, 93, 94, 98, 97, 98.7],
  }
}

export function getHeatmapData() {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const hours = ['00', '04', '08', '12', '16', '20']
  return days.map((day) => ({
    day,
    values: hours.map(() => Math.round(rand() * 100)),
  }))
}

export const HEATMAP_HOURS = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00']

export function getRiskTimeline() {
  const labels = Array.from({ length: 20 }).map((_, i) => `${i * 3}m`)
  const values = labels.map(() => Math.round(rand() * 100))
  return { labels, values }
}

export const RECENT_ALERTS = [
  { id: 1, title: 'High-velocity card testing detected', merchant: 'Amazon.in', risk: 92, time: '2 min ago', severity: 'danger' },
  { id: 2, title: 'Device fingerprint mismatch flagged', merchant: 'PayPal Transfer', risk: 71, time: '6 min ago', severity: 'warning' },
  { id: 3, title: 'Unusual cross-border transaction', merchant: 'Dubai Duty Free', risk: 84, time: '11 min ago', severity: 'danger' },
  { id: 4, title: 'New device step-up verification', merchant: 'Flipkart', risk: 55, time: '18 min ago', severity: 'warning' },
  { id: 5, title: 'Synthetic identity pattern matched', merchant: 'Steam', risk: 88, time: '27 min ago', severity: 'danger' },
]

export const NOTIFICATIONS = [
  { id: 1, title: 'Model retrained successfully', desc: 'v4.2.1 deployed with +0.4% AUC improvement', time: '12 min ago', type: 'success' },
  { id: 2, title: 'Spike in blocked transactions', desc: 'Card testing pattern from IP range 41.203.x.x', time: '34 min ago', type: 'danger' },
  { id: 3, title: 'Weekly fraud report ready', desc: 'Your Jul 7 – Jul 13 summary has been generated', time: '2 hr ago', type: 'info' },
  { id: 4, title: 'New team member added', desc: 'Aditi Sharma joined as Fraud Analyst', time: '5 hr ago', type: 'info' },
]

export function randomLiveTransaction() {
  const risk = Math.round(rand() * 100)
  const status = statusFromRisk(risk)
  return {
    id: `TXN-${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
    merchant: pick(MERCHANTS),
    amount: +(rand() * 50000 + 99).toFixed(2),
    risk,
    status,
    city: pick(CITIES),
    timestamp: new Date().toISOString(),
  }
}
