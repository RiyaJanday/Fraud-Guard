import Badge from '../ui/Badge'
import { STATUS_META } from '../../lib/utils'

export default function StatusBadge({ status }) {
  const meta = STATUS_META[status] || STATUS_META.approved
  return <Badge color={meta.color}>{meta.label}</Badge>
}
